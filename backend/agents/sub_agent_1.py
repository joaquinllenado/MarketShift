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

import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from exa_py import Exa
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool

load_dotenv()

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
        num_results=5,
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
        num_results=5,
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
    """Fetch recent news about the query (big moves: funding, launches, partnerships, expansion)."""
    seen_urls: set[str] = set()
    merged: list[dict] = []

    # Main news query
    for item in _exa_news_search(query, num_results=8):
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            merged.append(item)

    # Targeted queries for big moves (cap total to avoid rate limits)
    for extra_query in [
        f"{query} funding round series",
        f"{query} product launch partnership",
        f"{query} expansion region US EU APAC",
    ]:
        if len(merged) >= 15:
            break
        for item in _exa_news_search(extra_query, num_results=4):
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                merged.append(item)
                if len(merged) >= 15:
                    break

    return merged[:15]


# ---------------------------------------------------------------------------
# Per-competitor news gathering
# ---------------------------------------------------------------------------

def _competitor_news(competitor_name: str, max_items: int = 6) -> list[dict]:
    """Fetch news about a single competitor (funding, launches, partnerships)."""
    seen_urls: set[str] = set()
    merged: list[dict] = []

    for item in _exa_news_search(competitor_name, num_results=4):
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            merged.append(item)

    for extra in [
        f"{competitor_name} funding round",
        f"{competitor_name} product launch partnership",
    ]:
        if len(merged) >= max_items:
            break
        for item in _exa_news_search(extra, num_results=3):
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                merged.append(item)
                if len(merged) >= max_items:
                    break

    return merged[:max_items]


# ---------------------------------------------------------------------------
# Sub-Agent 1 chain
# ---------------------------------------------------------------------------

def _gather(inputs: dict) -> dict:
    query = inputs["query"]
    competitors = inputs.get("competitors", [])

    all_news: list[dict] = []
    if competitors:
        for comp in competitors:
            comp_name = comp.get("name", "")
            if comp_name:
                all_news.extend(_competitor_news(comp_name))
    else:
        all_news = news_tool.invoke({"query": query})

    return {
        **inputs,
        "web": web_search_tool.invoke({"query": query}),
        "product_hunt": product_hunt_tool.invoke({"query": query}),
        "news": all_news,
    }


sub_agent_1 = RunnableLambda(_gather)
