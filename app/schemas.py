from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class LinkRequest(BaseModel):
    url: str = Field(..., examples=["https://example.com"])
    force_refresh: bool = False


class _Lenient(BaseModel):
    model_config = ConfigDict(extra="allow")


class Brand(_Lenient):
    name: str = ""
    category: str = ""
    summary: str = ""


class Competitor(_Lenient):
    name: str
    website: Optional[str] = None
    target_market: str = ""
    main_service: str = ""
    key_strength: str = ""
    weaknesses: List[str] = []
    source: str = "ai_suggested"  # competitors are LLM suggestions, not researched data


class CompetitorAnalysis(_Lenient):
    brand_overview: str = ""
    main_products_services: List[str] = []
    competitors: List[Competitor] = []
    strengths: List[str] = []
    competitive_advantages: List[str] = []
    opportunities: List[str] = []


class SearchQuery(_Lenient):
    query: str
    platforms: List[str] = []
    intent: str = ""
    business_relevance: str = ""
    target_audience: str = ""


class SupportContent(_Lenient):
    type: str = ""
    title: str = ""
    reason: str = ""


class SEO(_Lenient):
    primary_keyword: str = ""
    secondary_keywords: List[str] = []
    long_tail_keywords: List[str] = []
    business_keywords: List[str] = []
    recommended_title: str = ""
    title_structure: str = ""
    meta_description: str = ""
    supporting_content: List[SupportContent] = []


class Service(_Lenient):
    name: str
    description: str = ""
    target_industry: str = ""
    target_customer: str = ""
    main_benefit: str = ""
    source: str = "website"  # "website" or "inferred"


class Audience(_Lenient):
    primary_audience: List[str] = []
    secondary_audience: List[str] = []
    industries: List[str] = []
    business_types: List[str] = []
    customer_profiles: List[str] = []
    geographic_focus: str = ""
    customer_needs: List[str] = []
    interests: List[str] = []
    marketing_segments: List[str] = []


class Analysis(_Lenient):
    competitor_analysis: CompetitorAnalysis = CompetitorAnalysis()
    target_search_queries: List[SearchQuery] = []
    seo_improvements: SEO = SEO()
    top_services: List[Service] = []
    target_audience: Audience = Audience()


class LLMOutput(_Lenient):
    brand: Brand = Brand()
    analysis: Analysis = Analysis()
