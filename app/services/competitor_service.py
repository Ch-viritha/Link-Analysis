"""Competitor-specific prompt guidance and post-processing."""
from app.schemas import Competitor

COMPETITOR_RULES = """Competitors: list 3-5 real, well-known competitors in the same category/market as this brand.
Mark uncertainty honestly: these are AI-generated suggestions from model knowledge, not live research.
Never invent companies; if fewer than 3 reliable competitors exist, return fewer."""


def finalize_competitors(items: list[Competitor]) -> list[Competitor]:
    seen, out = set(), []
    for c in items:
        key = c.name.strip().lower()
        if key and key not in seen:
            seen.add(key)
            c.source = "ai_suggested"
            out.append(c)
    return out[:5]
