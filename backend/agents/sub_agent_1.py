"""
Sub-Agent 1: Data Gathering

Receives the intake_agent output which includes a market-level query
string and a list of discovered competitors.

For each competitor, runs targeted news searches (funding, launches,
partnerships, expansion). Also runs market-level web and Product Hunt
searches using the overall query.

Returns a dict preserving all upstream keys plus: web, product_hunt, news.
News items include title, url, highlights, and logo (favicon URL).
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from dotenv import load_dotenv
from exa_py import Exa
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool

load_dotenv()

logger = logging.getLogger(__name__)

exa = Exa(api_key=os.environ.get("EXA_API_KEY"))

# Favicon service for logo fallback (domain-based)
FAVICON_BASE = "https://www.google.com/s2/favicons?domain={domain}&sz=64"


def _logo_url_from_url(url: str) -> str:
    """Derive a logo/favicon URL from an article URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0] or "example.com"
        if domain and "." in domain:
            return FAVICON_BASE.format(domain=domain)
    except Exception:
        pass
    return FAVICON_BASE.format(domain="example.com")


def _exa_news_search(query: str, num_results: int = 5) -> list[dict]:
    """Run a single Exa news search and return items with logo."""
    results = exa.search_and_contents(
        query,
        category="news",
        type="auto",
        num_results=num_results,
        highlights={"num_sentences": 3, "highlights_per_url": 2},
    )
    return [
        {
            "title": r.title or r.url,
            "url": r.url,
            "highlights": r.highlights or [],
            "logo": _logo_url_from_url(r.url),
        }
        for r in results.results
    ]


# ---------------------------------------------------------------------------
# Tools — decorated with @tool so they are ready for LLM bind_tools() later
# ---------------------------------------------------------------------------

@tool
def web_search_tool(query: str) -> list[dict]:
    """Search the web for companies and competitors matching the query."""
    results = exa.search_and_contents(
        query,
        category="company",
        type="auto",
        num_results=3,
        highlights={"num_sentences": 2, "highlights_per_url": 1},
    )
    return [
        {
            "title": r.title or r.url,
            "url": r.url,
            "highlights": r.highlights or [],
        }
        for r in results.results
    ]


@tool
def product_hunt_tool(query: str) -> list[dict]:
    """Search Product Hunt for products related to the query."""
    results = exa.search_and_contents(
        f"{query} site:producthunt.com",
        type="auto",
        num_results=3,
        highlights={"num_sentences": 2, "highlights_per_url": 1},
    )
    return [
        {
            "title": r.title or r.url,
            "url": r.url,
            "highlights": r.highlights or [],
        }
        for r in results.results
    ]


@tool
def news_tool(query: str) -> list[dict]:
    """Fetch recent news about the query (big moves: funding, launches, partnerships)."""
    seen_urls: set[str] = set()
    merged: list[dict] = []

    # Main news query
    for item in _exa_news_search(query, num_results=5):
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            merged.append(item)

    # One extra query for funding (trimmed for speed)
    for item in _exa_news_search(f"{query} funding round series", num_results=3):
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            merged.append(item)
        if len(merged) >= 10:
            break

    return merged[:10]


# ---------------------------------------------------------------------------
# Per-competitor news gathering
# ---------------------------------------------------------------------------

def _competitor_news(competitor_name: str, max_items: int = 3) -> list[dict]:
    """Fetch news about a single competitor (single query for speed)."""
    return _exa_news_search(competitor_name, num_results=max_items)


# ---------------------------------------------------------------------------
# Sub-Agent 1 chain
# ---------------------------------------------------------------------------

def _gather(inputs: dict) -> dict:
    query = inputs["query"]
    competitors = inputs.get("competitors", [])
    stage_start = time.perf_counter()
    logger.info("[sub_agent_1] Starting data gathering — query=%r, %d competitors", query, len(competitors))

    def get_news():
        if competitors:
            names = [c.get("name", "") for c in competitors[:3]]
            logger.info("[sub_agent_1] Fetching per-competitor news for: %s", names)
            out = []
            for c in competitors[:3]:
                comp_name = c.get("name", "")
                if comp_name:
                    items = _competitor_news(comp_name, max_items=3)
                    logger.info("[sub_agent_1]   %s → %d news items", comp_name, len(items))
                    out.extend(items)
            return out
        return news_tool.invoke({"query": query})

    logger.info("[sub_agent_1] Running web / ProductHunt / news searches in parallel …")
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_web = ex.submit(web_search_tool.invoke, {"query": query})
        f_ph = ex.submit(product_hunt_tool.invoke, {"query": query})
        f_news = ex.submit(get_news)
        web = f_web.result()
        product_hunt = f_ph.result()
        all_news = f_news.result()

    elapsed = time.perf_counter() - stage_start
    logger.info("[sub_agent_1] Done in %.1f s — web=%d, product_hunt=%d, news=%d",
                elapsed, len(web), len(product_hunt), len(all_news))

    return {
        **inputs,
        "web": web,
        "product_hunt": product_hunt,
        "news": all_news,
    }


sub_agent_1 = RunnableLambda(_gather)
