# 🔭 Linkscope: AI Website Link Analysis

FastAPI + SQLite + single-page frontend. Paste a URL and get **competitors, top-5 search queries, SEO fixes, top-5 services and target audience**, powered by an LLM (Anthropic, OpenAI or Gemini, switchable via `.env`).

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add ONE api key + set LLM_PROVIDER
uvicorn app.main:app --host 0.0.0.0 --port 4000
```
- App UI: http://localhost:4000  |  Swagger: http://localhost:4000/docs  |  Tests: `pytest`
- Docker: `docker build -t linkscope . && docker run -p 4000:4000 --env-file .env linkscope`
- Deploy: any container host (Render, Railway, Fly.io). Set env vars there. Mount a volume at `/srv/data` to persist history.

## API
`POST /link-analysis` with `{"url": "https://example.com", "force_refresh": false}`
Also: `GET /api/history`, `GET /api/history/{id}`, `DELETE /api/history/{id}`, `GET /health`.

```bash
curl -X POST localhost:4000/link-analysis -H "Content-Type: application/json" -d '{"url":"https://example.com"}'
```
Errors return `{"success": false, "error": {"type", "message"}}` with 400 (invalid/private URL), 422/502/504 (site unreachable or blocked), 502 (LLM failure).
*Add your own real sample response + screenshots here after running it.*

## Architecture
`validators` (URL + SSRF) → `website_extractor` (safe fetch, homepage + up to 2 about/services pages, noise stripped) → `analysis_service` (prompt, validation with Pydantic, one repair retry) → `llm_service` (provider abstraction, retry, optional fallback provider) → `db` (SQLite history + cache keyed by URL + content hash).

**Security:** every redirect hop is re-resolved and blocked if private/loopback/link-local; response size capped; credentials only via env; `.env` git-ignored. *Known limit:* a DNS-rebinding race between check and connect is not fully eliminated; production should pin the resolved IP or use an egress proxy.

**Honesty rules:** competitors and queries are labelled AI-generated; no search volumes are invented; services are flagged `website` vs `inferred`.

## LLM research (fill in with YOUR measurements)
Pricing and model names change often. **Copy current prices from the provider pages on your submission date**; the figures below are deliberately left blank rather than guessed.

| Criteria | Anthropic (Claude Haiku-class) | OpenAI (mini-class) | Google (Gemini Flash-class) |
|---|---|---|---|
| Env model name | `ANTHROPIC_MODEL` | `OPENAI_MODEL` | `GEMINI_MODEL` |
| Input / output price per 1M tokens | *from anthropic.com/pricing* | *from openai.com/api/pricing* | *from ai.google.dev/pricing* |
| Context window | *docs* | *docs* | *docs* |
| JSON support | Prompted JSON + validation | Native `json_object` mode | Native `responseMimeType` |
| Measured latency (this app) | *run 5 sites, record `meta.latency_ms`* | *same* | *same* |
| Measured quality (1-5, your rubric) | *test* | *test* | *test* |

**Token estimate (estimate, not measured):** ~3-5k input tokens (12k-char cap + prompt), ~1.5-2.5k output. Cost per analysis = `(in/1e6 × input_price) + (out/1e6 × output_price)`; the API returns real token counts in `meta`, so compute actuals.

**Recommendation approach:** default to a small/fast tier model (it is enough for extraction + structured JSON), keep a second provider as `FALLBACK_PROVIDER`, and escalate to a larger model only if your rubric scores show weak competitor insights. Do not claim "maximum accuracy" without running your own comparison.

**Cost optimisation already implemented:** boilerplate/HTML stripped and de-duplicated; hard content cap; single LLM call for all five sections; cache by URL + content hash (24h); one repair retry only on validation failure.
