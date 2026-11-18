import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    fallback_provider = os.getenv("FALLBACK_PROVIDER", "").lower()
    keys = {
        "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
        "openai": os.getenv("OPENAI_API_KEY", ""),
        "gemini": os.getenv("GEMINI_API_KEY", ""),
    }
    models = {
        "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5"),
        "openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "gemini": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    }
    cache_ttl_hours = int(os.getenv("CACHE_TTL_HOURS", "24"))
    max_content_chars = int(os.getenv("MAX_CONTENT_CHARS", "12000"))
    db_path = os.getenv("DB_PATH", "data/analyses.db")


settings = Settings()
