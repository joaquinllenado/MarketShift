"""
Intake Agent: Product URL → Competitor Discovery

Accepts a product URL, scrapes it via Exa to understand the company,
discovers competitors via Exa's find_similar_and_contents, then uses
DeepSeek R1 to pick the top 5 most relevant competitors and generate
a market-context string for downstream agents.

Input:  {"url": "<product URL>"}
Output: {
    "query":           "<market context for downstream search>",
    "product_url":     "<original URL>",
    "product_name":    "<company name>",
    "product_summary": "<what the company does>",
    "competitors":     [{"name": str, "url": str}, ...]
}
"""

import json
import os
import re

from dotenv import load_dotenv
from exa_py import Exa
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

load_dotenv()

exa = Exa(api_key=os.environ.get("EXA_API_KEY"))

SYSTEM_PROMPT = """\
You are a competitive-intelligence analyst.

You will receive:
1. A product URL and scraped description of what the company does.
2. A list of similar companies discovered via web similarity search.

Your job:
1. Pick the **top 5 most relevant direct competitors** from the list.
   Prefer companies in the same market/vertical that compete for the
   same customers. Exclude unrelated results, generic directories,
   or the product itself.
2. For each competitor, return its name and URL.
3. Generate a concise **market context string** (max 15 words) describing
   the competitive landscape (e.g. "AI writing assistants SaaS market"
   or "e-commerce customer support chatbot platforms").
4. Extract the product's company name from its URL/description.
5. Write a one-sentence summary of what the product does.

Reply with ONLY a JSON object (no markdown fences, no explanation):

{
  "product_name": "<company name>",
  "product_summary": "<one-sentence description>",
  "market_context": "<concise market description, max 15 words>",
  "competitors": [
    {"name": "<competitor name>", "url": "<competitor URL>"},
    ...
  ]
}\
"""

llm = ChatOpenAI(
    model="deepseek-ai/DeepSeek-R1-0528",
    base_url="https://api.gmi-serving.com/v1",
    api_key=os.environ.get("GMI_API_KEY"),
    temperature=0.3,
    max_tokens=4096,
)


def _strip_thinking(text: str) -> str:
    """Remove DeepSeek R1 <think>…</think> reasoning blocks."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _extract_json(raw: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _discover_competitors(inputs: dict) -> dict:
    product_url = inputs["url"]

    # Step 1: Scrape the product URL to understand what it does
    try:
        scraped = exa.get_contents(
            [product_url],
            text={"max_characters": 3000},
            highlights={"num_sentences": 3, "highlights_per_url": 2},
        )
        product_page = scraped.results[0] if scraped.results else None
        product_text = product_page.text if product_page and product_page.text else ""
        product_title = product_page.title if product_page and product_page.title else product_url
        product_highlights = product_page.highlights if product_page and product_page.highlights else []
    except Exception:
        product_text = ""
        product_title = product_url
        product_highlights = []

    # Step 2: Find similar companies via Exa
    try:
        similar = exa.find_similar_and_contents(
            product_url,
            category="company",
            num_results=10,
            highlights={"num_sentences": 2, "highlights_per_url": 1},
        )
        similar_companies = [
            {
                "title": r.title or r.url,
                "url": r.url,
                "highlights": r.highlights or [],
            }
            for r in similar.results
        ]
    except Exception:
        similar_companies = []

    # Step 3: Use LLM to pick top 5 competitors and generate context
    product_description = "\n".join([
        f"Title: {product_title}",
        f"URL: {product_url}",
        f"Highlights: {product_highlights}",
        f"Text excerpt: {product_text[:1500]}",
    ])

    user_msg = (
        f"Product:\n{product_description}\n\n"
        f"Similar companies found ({len(similar_companies)}):\n"
        f"{json.dumps(similar_companies, indent=2)}"
    )

    response = llm.invoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ])

    cleaned = _strip_thinking(response.content)

    try:
        parsed = _extract_json(cleaned)
    except (json.JSONDecodeError, ValueError):
        parsed = {
            "product_name": product_title,
            "product_summary": "",
            "market_context": "",
            "competitors": [],
        }

    competitors = parsed.get("competitors", [])[:5]
    product_name = parsed.get("product_name", product_title)
    product_summary = parsed.get("product_summary", "")
    market_context = parsed.get("market_context", "")

    competitor_names = ", ".join(c["name"] for c in competitors)
    query = f"{competitor_names} {market_context}".strip()

    return {
        "url": product_url,
        "query": query,
        "product_url": product_url,
        "product_name": product_name,
        "product_summary": product_summary,
        "competitors": competitors,
    }


intake_agent = RunnableLambda(_discover_competitors)
