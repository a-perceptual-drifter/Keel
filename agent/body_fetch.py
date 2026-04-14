"""Shared article-body fetch + extraction used by prefetch task and on-demand summarize."""
from __future__ import annotations

MIN_BODY_CHARS = 400

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}


def _looks_like_cf_challenge(html: str) -> bool:
    if not html:
        return False
    head = html[:2000].lower()
    return "just a moment" in head or "cf-browser-verification" in head or "challenge-platform" in head


def _fetch_with_cloudscraper(url: str) -> str:
    try:
        import cloudscraper
    except ImportError:
        return ""
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, timeout=30, allow_redirects=True)
        if resp.status_code != 200 or not resp.text:
            return ""
        return resp.text
    except Exception:
        return ""


def fetch_article_body(url: str, timeout: int = 15) -> str:
    """Fetch the article body. Returns extracted plain text or '' on failure."""
    try:
        import requests
        import trafilatura
    except Exception:
        return ""
    html = ""
    try:
        resp = requests.get(url, headers=_BROWSER_HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and resp.text and not _looks_like_cf_challenge(resp.text):
            html = resp.text
    except Exception:
        pass
    if not html:
        html = _fetch_with_cloudscraper(url)
    if not html:
        return ""
    try:
        return trafilatura.extract(html, url=url) or ""
    except Exception:
        return ""
