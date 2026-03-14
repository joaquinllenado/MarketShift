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
import logging
import os
import re
import time
from urllib.parse import urlparse

from dotenv import load_dotenv
from exa_py import Exa
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

exa = Exa(api_key=os.environ.get("EXA_API_KEY"))

SYSTEM_PROMPT = """\
# Role
You are a competitive-intelligence analyst.

# Goal
Identify the top 5 most relevant direct competitors for a given product, summarize the product, and describe its market context. The output must be a strictly formatted JSON object.

# Input
The input will be a JSON object containing the product's URL.

```json
{
  "product_url": "string",
}
```

# Output
The output must be a JSON object containing the product's URL, name, a one-sentence summary, a concise market context, and a list of exactly 5 direct competitors with their names and homepage URLs.

```json
{
  "product_name": "<company name>",
  "product_summary": "<one-sentence description>",
  "market_context": "<concise market description, max 15 words>",
  "competitors": [
    {"name": "<competitor name>", "url": "<competitor homepage URL>"},
    {"name": "<competitor name>", "url": "<competitor homepage URL>"},
    {"name": "<competitor name>", "url": "<competitor homepage URL>"},
    {"name": "<competitor name>", "url": "<competitor homepage URL>"},
    {"name": "<competitor name>", "url": "<competitor homepage URL>"}
  ]
}
```

# Rules
- **Competitor Selection:**
    - Select the top 5 most relevant direct competitors from the `similar_companies` list.
    - Prioritize companies operating in the same market/vertical and targeting the same customer base as the product.
    - If the `similar_companies` list contains fewer than 5 valid direct competitors, use your own knowledge to identify and include well-known, genuinely independent competitors until exactly 5 are listed.
    - For each selected competitor, provide its official name and homepage URL.
- **Exclusions:**
    - **STRICTLY EXCLUDE** the product company itself (including regional variants, e.g., "Notion Korea").
    - **STRICTLY EXCLUDE** subsidiaries, divisions, bottlers, or affiliates of the product company.
    - **STRICTLY EXCLUDE** generic directories, news articles, review sites, or any entity that is not a genuinely independent competing company.
    - **STRICTLY EXCLUDE** any content that is illegal, harmful, or promotes discrimination.
- **Market Context:**
    - Generate a concise market context string, describing the competitive landscape.
- **Product Information:**
    - Extract the product's company name from its URL.
    - Write a single, concise sentence summarizing what the product does.
- **Input Handling:**
    - If `product_url` is missing or malformed, return an error JSON indicating "Invalid Input".
- **Output Format:**
    - The output MUST be a JSON object, without any markdown fences, explanations, or additional text.
    - The `competitors` array MUST always contain exactly 5 entries.

## Examples
### Valid Input and Expected Output
- input
```json
{
  "product_url": "https://www.example.com/product-a"
}
```
- output
```json
{
  "product_name": "Product A",
  "product_summary": "Product A is an AI-powered writing assistant for content creators, generating blog posts and marketing copy.",
  "market_context": "AI writing assistants SaaS market for content creators",
  "competitors": [
    {"name": "ContentGenius", "url": "https://contentgenius.ai"},
    {"name": "WriterPro", "url": "https://writerpro.com"},
    {"name": "BlogMaster", "url": "https://blogmaster.io"},
    {"name": "CopyCraft", "url": "https://copycraft.co"},
    {"name": "TextFlow", "url": "https://textflow.app"}
  ]
}
```

### Input with Fewer than 5 Valid Competitors
- input
```json
{
  "product_url": "https://www.example.com/product-b"
}
```
- output
```json
{
  "product_name": "Product B",
  "product_summary": "Product B is a cloud-based project management software for small teams, supporting agile methodologies.",
  "market_context": "Cloud-based agile project management software for small teams",
  "competitors": [
    {"name": "TaskFlow", "url": "https://taskflow.io"},
    {"name": "Jira", "url": "https://www.atlassian.com/software/jira"},
    {"name": "Asana", "url": "https://asana.com"},
    {"name": "Trello", "url": "https://trello.com"},
    {"name": "Monday.com", "url": "https://monday.com"}
  ]
}
```

### Input with Malformed Data (Missing URL)
- input
```json
{
  "product_url": null
}
```
- output
```json
{
  "error": "Invalid Input",
  "details": "product_url is missing or malformed."
}
```

# Constraints
- The `market_context` string MUST be a maximum of 15 words.
- The `product_summary` MUST be a single sentence.
- The output MUST be a valid JSON object.
- The `competitors` array in the output MUST always contain exactly 5 entries.
- All URLs in the output MUST be valid and accessible homepage URLs.

# Steps
1.  Parse the input JSON to extract `product_url`.
2.  **Validate Input:** If `product_url` is missing or malformed, construct an error JSON and terminate.
3.  Extract the `product_name` from `product_url`.
4.  Generate a one-sentence `product_summary` based on the product page.
5.  Generate a concise `market_context` string (max 15 words).
6.  Construct the final JSON output object, ensuring all fields are populated according to the specified format and constraints.
"""

llm = ChatOpenAI(
    model="deepseek-ai/DeepSeek-V3-0324",
    base_url="https://api.gmi-serving.com/v1",
    api_key=os.environ.get("GMI_API_KEY"),
    temperature=0.3,
    max_tokens=1024,
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
    stage_start = time.perf_counter()
    logger.info("[intake] Starting competitor discovery for %s", product_url)

    # Step 1: Scrape the product URL to understand what it does
    logger.info("[intake] Scraping product page …")
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
        logger.info("[intake] Scraped product page — title=%r, text_len=%d", product_title, len(product_text))
    except Exception:
        logger.exception("[intake] Failed to scrape product URL %s — continuing with empty data", product_url)
        product_text = ""
        product_title = product_url
        product_highlights = []

    # Step 2: Find similar companies via Exa
    logger.info("[intake] Searching for similar companies …")
    product_domain = urlparse(product_url).netloc.lower().removeprefix("www.")
    # Build a short brand keyword from the domain for fuzzy self-filtering
    brand_root = product_domain.split(".")[0].replace("-", "").replace("company", "").lower()

    def _is_self(result_url: str, result_title: str) -> bool:
        """Return True if a result appears to belong to the product company."""
        rdomain = urlparse(result_url).netloc.lower().removeprefix("www.")
        if product_domain in rdomain or rdomain in product_domain:
            return True
        rdomain_root = rdomain.split(".")[0].replace("-", "").lower()
        if len(brand_root) >= 3 and brand_root in rdomain_root:
            return True
        title_lower = result_title.lower().replace("-", " ")
        if len(brand_root) >= 3 and brand_root in title_lower.replace(" ", ""):
            return True
        return False

    try:
        similar = exa.find_similar_and_contents(
            product_url,
            category="company",
            num_results=15,
            highlights={"num_sentences": 2, "highlights_per_url": 1},
            exclude_domains=[product_domain],
        )
        similar_companies = [
            {
                "title": r.title or r.url,
                "url": r.url,
                "highlights": r.highlights or [],
            }
            for r in similar.results
            if not _is_self(r.url, r.title or "")
        ]
        logger.info("[intake] Found %d similar companies (after self-filter)", len(similar_companies))
    except Exception:
        logger.exception("[intake] Exa find_similar failed — continuing with empty list")
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

    logger.info("[intake] Calling LLM to select top competitors …")
    response = llm.invoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ])

    cleaned = _strip_thinking(response.content)

    try:
        parsed = _extract_json(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.warning("[intake] LLM returned unparseable JSON — using fallback")
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

    elapsed = time.perf_counter() - stage_start
    comp_names = [c.get("name", "?") for c in competitors]
    logger.info("[intake] Done in %.1f s — product=%r, competitors=%s, query=%r",
                elapsed, product_name, comp_names, query)

    return {
        "url": product_url,
        "query": query,
        "product_url": product_url,
        "product_name": product_name,
        "product_summary": product_summary,
        "competitors": competitors,
    }


intake_agent = RunnableLambda(_discover_competitors)
