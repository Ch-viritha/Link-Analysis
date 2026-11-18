"""Provider-agnostic LLM client (Anthropic / OpenAI / Gemini) using plain HTTPX."""
import json
import re
import time

import httpx

from app.config import settings


class LLMError(Exception):
    pass


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise LLMError("The model did not return JSON.")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise LLMError(f"The model returned malformed JSON: {e}")


async def _call(provider: str, system: str, user: str) -> tuple[str, dict]:
    key, model = settings.keys.get(provider, ""), settings.models.get(provider, "")
    if not key:
        raise LLMError(f"No API key configured for provider '{provider}'.")
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as c:
        if provider == "anthropic":
            r = await c.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                json={"model": model, "max_tokens": 4096, "system": system,
                      "messages": [{"role": "user", "content": user}]},
            )
            r.raise_for_status()
            j = r.json()
            return "".join(b.get("text", "") for b in j["content"]), {
                "input_tokens": j["usage"]["input_tokens"], "output_tokens": j["usage"]["output_tokens"]}
        if provider == "openai":
            r = await c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "response_format": {"type": "json_object"},
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            )
            r.raise_for_status()
            j = r.json()
            return j["choices"][0]["message"]["content"], {
                "input_tokens": j["usage"]["prompt_tokens"], "output_tokens": j["usage"]["completion_tokens"]}
        if provider == "gemini":
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": key},
                json={"system_instruction": {"parts": [{"text": system}]},
                      "contents": [{"role": "user", "parts": [{"text": user}]}],
                      "generationConfig": {"responseMimeType": "application/json"}},
            )
            r.raise_for_status()
            j = r.json()
            u = j.get("usageMetadata", {})
            return j["candidates"][0]["content"]["parts"][0]["text"], {
                "input_tokens": u.get("promptTokenCount", 0), "output_tokens": u.get("candidatesTokenCount", 0)}
    raise LLMError(f"Unknown provider '{provider}'.")


async def complete_json(system: str, user: str) -> tuple[dict, dict]:
    """Returns (parsed_json, meta). Tries primary provider (with one retry), then fallback."""
    providers = [p for p in (settings.provider, settings.fallback_provider) if p]
    last = None
    for provider in providers:
        for _ in range(2):
            started = time.perf_counter()
            try:
                text, usage = await _call(provider, system, user)
                data = _extract_json(text)
                return data, {"provider": provider, "model": settings.models[provider],
                              "latency_ms": int((time.perf_counter() - started) * 1000), **usage}
            except httpx.HTTPStatusError as e:
                last = LLMError(f"{provider} API error {e.response.status_code}.")
                if e.response.status_code in (400, 401, 403, 404):
                    break  # retrying will not help
            except (httpx.HTTPError, KeyError, LLMError) as e:
                last = e if isinstance(e, LLMError) else LLMError(f"{provider} request failed ({type(e).__name__}).")
    raise last or LLMError("No LLM provider configured.")
