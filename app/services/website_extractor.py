"""Fetches a website safely and distils it into LLM-ready content."""
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.utils.validators import URLValidationError, assert_public_host, normalize_url

MAX_BYTES = 2_000_000
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LinkAnalysisBot/1.0)", "Accept": "text/html,*/*;q=0.8"}
SUBPAGE_HINTS = ("about", "service", "product", "solution", "offering", "what-we-do")


class ExtractionError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


async def _get(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    """GET with manual redirect handling so every hop is SSRF-checked."""
    for _ in range(6):
        await assert_public_host(urlparse(url).hostname)
        async with client.stream("GET", url, follow_redirects=False) as r:
            if r.is_redirect:
                url = normalize_url(urljoin(url, r.headers.get("location", "")))
                continue
            if r.status_code in (401, 403, 429):
                raise ExtractionError(f"The website blocked automated access (HTTP {r.status_code}).")
            if r.status_code >= 400:
                raise ExtractionError(f"The website returned HTTP {r.status_code}.")
            if "html" not in r.headers.get("content-type", "html").lower():
                raise ExtractionError("The URL does not point to an HTML page.")
            body, size = [], 0
            async for chunk in r.aiter_bytes():
                body.append(chunk)
                size += len(chunk)
                if size > MAX_BYTES:
                    break
            return b"".join(body).decode(r.encoding or "utf-8", errors="replace"), url
    raise ExtractionError("Too many redirects.")


def _parse(html: str, base: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    def meta(**attrs):
        t = soup.find("meta", attrs=attrs)
        return (t.get("content") or "").strip() if t else ""

    data = {
        "title": soup.title.get_text(strip=True) if soup.title else "",
        "meta_description": meta(name="description"),
        "meta_keywords": meta(name="keywords"),
        "site_name": meta(property="og:site_name"),
        "headings": [],
        "text": "",
        "links": [],
    }
    for a in soup.find_all("a", href=True):
        full = urljoin(base, a["href"])
        if urlparse(full).netloc == urlparse(base).netloc and any(h in full.lower() for h in SUBPAGE_HINTS):
            data["links"].append(full.split("#")[0])
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "nav", "form"]):
        tag.decompose()
    seen = set()
    for h in soup.find_all(["h1", "h2", "h3"]):
        t = h.get_text(" ", strip=True)
        if t and t not in seen:
            seen.add(t)
            data["headings"].append(f"{h.name.upper()}: {t}")
    lines = []
    for el in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "td"]):
        t = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        if len(t) > 12 and t not in seen:
            seen.add(t)
            lines.append(t)
        if not lines and soup.body:
            lines = [re.sub(r"\s+", " ", soup.body.get_text(" ", strip=True))]
    data["text"] = "\n".join(lines)
    return data


async def extract_website(url: str) -> dict:
    url = normalize_url(url)
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=httpx.Timeout(15.0)) as client:
            html, final_url = await _get(client, url)
            home = _parse(html, final_url)
            pages = [("Homepage", home["text"])]
            for link in list(dict.fromkeys(home["links"]))[:2]:
                try:
                    sub_html, sub_url = await _get(client, link)
                    pages.append((sub_url, _parse(sub_html, sub_url)["text"]))
                except (ExtractionError, URLValidationError, httpx.HTTPError):
                    continue
    except httpx.TimeoutException:
        raise ExtractionError("The website took too long to respond.", 504)
    except httpx.HTTPError as e:
        raise ExtractionError(f"Could not reach the website ({type(e).__name__}).", 502)
    text = ""
    for name, body in pages:
        text += f"\n--- {name} ---\n{body}"[: max(settings.max_content_chars - len(text), 0)]
    has_signal = home["title"] or home["meta_description"] or home["headings"]
    if len(text.strip()) < 80 and not has_signal:
        raise ExtractionError("Not enough readable content found (the site may be JavaScript-rendered).")
    return {**home, "url": final_url, "content": text.strip(), "pages_used": len(pages)}
