import asyncio
import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import analysis_service
from app.utils.validators import URLValidationError, assert_public_host, normalize_url

FAKE_SITE = {"url": "https://example.com", "title": "ABC", "meta_description": "", "meta_keywords": "",
             "headings": ["H1: ABC"], "content": "We build websites for small businesses. " * 5, "pages_used": 1}
FAKE_LLM = {"brand": {"name": "ABC", "category": "Web", "summary": "s"},
            "analysis": {"competitor_analysis": {"competitors": [{"name": "X"}, {"name": "x"}, {"name": "Y"}]},
                         "top_services": [{"name": "Web design"}]}}


def test_normalize_adds_scheme():
    assert normalize_url("example.com") == "https://example.com"


@pytest.mark.parametrize("bad", ["", "ftp://x.com", "http://localhost", "https://user:pw@a.com"])
def test_invalid_urls(bad):
    with pytest.raises(URLValidationError):
        normalize_url(bad)


@pytest.mark.parametrize("host", ["127.0.0.1", "10.0.0.5", "169.254.169.254", "192.168.1.1"])
def test_ssrf_blocked(host):
    with pytest.raises(URLValidationError):
        asyncio.run(assert_public_host(host))


def test_endpoint_with_mocks(monkeypatch):
    async def fake_extract(url): return FAKE_SITE
    async def fake_llm(s, u): return FAKE_LLM, {"provider": "mock", "model": "m", "latency_ms": 1}
    monkeypatch.setattr(analysis_service, "extract_website", fake_extract)
    monkeypatch.setattr(analysis_service.llm_service, "complete_json", fake_llm)
    with TestClient(app) as c:
        r = c.post("/link-analysis", json={"url": "example.com"})
        assert r.status_code == 200
        body = r.json()
        assert body["brand"]["name"] == "ABC"
        assert len(body["analysis"]["competitor_analysis"]["competitors"]) == 2  # de-duplicated
        assert c.post("/link-analysis", json={"url": "example.com"}).json()["cached"] is True
        assert len(c.get("/api/history").json()["items"]) == 1


def test_bad_url_returns_400():
    with TestClient(app) as c:
        r = c.post("/link-analysis", json={"url": "http://127.0.0.1"})
        assert r.status_code == 400 and r.json()["success"] is False
