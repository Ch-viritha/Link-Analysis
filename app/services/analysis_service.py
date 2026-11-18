"""Orchestrates extraction -> LLM -> validation -> storage."""
import hashlib
import json

from pydantic import ValidationError

from app import db
from app.config import settings
from app.schemas import LLMOutput
from app.services import llm_service
from app.services.competitor_service import COMPETITOR_RULES, finalize_competitors
from app.services.website_extractor import extract_website

SYSTEM = """You are a senior digital-marketing and competitive-intelligence analyst.
Analyse ONLY the website content provided. Respond with a single valid JSON object, no prose, no markdown.
Rules: base services and audience on the actual content and set "source" to "website"; if inferred, set "source" to "inferred".
Never invent search volumes or traffic numbers. Search query platforms must be from: Google, Facebook, Instagram, LinkedIn, X.
""" + COMPETITOR_RULES

SCHEMA = """{
 "brand": {"name": "", "category": "", "summary": ""},
 "analysis": {
  "competitor_analysis": {"brand_overview": "", "main_products_services": [], "competitors": [
     {"name": "", "website": "", "target_market": "", "main_service": "", "key_strength": "", "weaknesses": []}],
     "strengths": [], "competitive_advantages": [], "opportunities": []},
  "target_search_queries": [{"query": "", "platforms": [], "intent": "", "business_relevance": "", "target_audience": ""}],
  "seo_improvements": {"primary_keyword": "", "secondary_keywords": [], "long_tail_keywords": [], "business_keywords": [],
     "recommended_title": "(max 60 chars)", "title_structure": "", "meta_description": "(max 155 chars)",
     "supporting_content": [{"type": "FAQ|Blog|Landing page|Location page|Industry page", "title": "", "reason": ""}]},
  "top_services": [{"name": "", "description": "", "target_industry": "", "target_customer": "", "main_benefit": "", "source": "website|inferred"}],
  "target_audience": {"primary_audience": [], "secondary_audience": [], "industries": [], "business_types": [],
     "customer_profiles": [], "geographic_focus": "", "customer_needs": [], "interests": [], "marketing_segments": []}
 }}
Exactly 5 target_search_queries and exactly 5 top_services."""


def _prompt(site: dict) -> str:
    return (f"URL: {site['url']}\nTitle: {site['title']}\nMeta description: {site['meta_description']}\n"
            f"Meta keywords: {site['meta_keywords']}\nHeadings:\n" + "\n".join(site["headings"][:40]) +
            f"\n\nPage content:\n{site['content']}\n\nReturn JSON in exactly this shape:\n{SCHEMA}")


async def analyze(url: str, force: bool = False) -> dict:
    site = await extract_website(url)
    content_hash = hashlib.sha256(site["content"].encode()).hexdigest()[:16]
    if not force:
        cached = db.find_cached(site["url"], content_hash, settings.cache_ttl_hours)
        if cached:
            return {**cached, "cached": True}
    prompt, error = _prompt(site), ""
    for _ in range(2):  # one repair attempt if validation fails
        raw, meta = await llm_service.complete_json(SYSTEM, prompt + error)
        try:
            out = LLMOutput.model_validate(raw)
            break
        except ValidationError as e:
            error = f"\n\nYour previous JSON failed validation: {str(e)[:400]}. Fix it."
    else:
        raise llm_service.LLMError("The model returned JSON that did not match the expected structure.")
    ca = out.analysis.competitor_analysis
    ca.competitors = finalize_competitors(ca.competitors)
    result = {
        "success": True,
        "website": site["url"],
        "brand": out.brand.model_dump(),
        "analysis": out.analysis.model_dump(),
        "meta": {**meta, "pages_analyzed": site["pages_used"], "content_chars": len(site["content"]),
                 "note": "Competitors and search queries are AI-generated suggestions; no search-volume data is included."},
    }
    rid = db.save(site["url"], content_hash, result)
    return {**result, "id": rid, "cached": False}
