"""
Analysis Agent: LLM-Powered Classification & Synthesis

Uses DeepSeek R1 via GMI Cloud to transform raw aggregated search
results into structured dashboard categories:

  - product_announcements
  - funding
  - partnerships
  - market_signals
  - market_opportunities  (synthesised)
  - competitive_risks     (synthesised)
  - action_steps          (synthesised)

Input:  dict with "query", "aggregated" (list of items), "persisted_at", …
Output: same dict with the 7 dashboard keys added
"""

import json
import os
import re
from urllib.parse import urlparse

from dotenv import load_dotenv
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

load_dotenv()

FAVICON_BASE = "https://www.google.com/s2/favicons?domain={domain}&sz=64"

SYSTEM_PROMPT = """\
You are a competitive-intelligence analyst. You will receive a JSON array of
search results about companies in a specific market. Each item has a "title",
"url", and "highlights" (key sentences from the page).

Your job is to classify each item into ONE of these categories, extract
structured fields, and then synthesise higher-level insights.

### Categories (classify each item into exactly one, or skip it)

1. **product_announcement** — A company shipped, launched, or announced a new
   product, feature, tool, or major update.
2. **funding** — A company raised a funding round (seed, Series A/B/C, etc.).
3. **partnership** — A company announced a partnership, integration, or
   collaboration with another company.
4. **market_signal** — A company is expanding to a new market, vertical, or
   customer segment, or is pivoting strategy.
5. **skip** — The item is irrelevant, generic, or doesn't fit any category.

### Output format

Return a single JSON object (no markdown fences, no explanation) with this
exact structure:

{
  "product_announcements": [
    {
      "company": "<full company name>",
      "abbreviation": "<2-letter uppercase abbreviation, e.g. LC for LangChain>",
      "title": "<one-line summary of the announcement>",
      "url": "<source url>"
    }
  ],
  "funding": [
    {
      "company": "<full company name>",
      "abbreviation": "<2-letter abbreviation>",
      "title": "<e.g. 'raised Series B'>",
      "amount": "<e.g. '$125M', or '' if unknown>",
      "url": "<source url>"
    }
  ],
  "partnerships": [
    {
      "company": "<full company name>",
      "abbreviation": "<2-letter abbreviation>",
      "title": "<one-line summary, e.g. 'announced partnership with Shopify'>",
      "url": "<source url>"
    }
  ],
  "market_signals": [
    {
      "company": "<full company name>",
      "abbreviation": "<2-letter abbreviation>",
      "title": "<headline, e.g. 'expanding to enterprise market'>",
      "description": "<one-sentence detail>",
      "url": "<source url>"
    }
  ],
  "market_opportunities": [
    "<short bullet point string — an opportunity in this market>"
  ],
  "competitive_risks": [
    "<short bullet point string — a risk or gap in this market>"
  ],
  "action_steps": [
    { "step": 1, "title": "<actionable recommendation>" }
  ]
}

### Rules
- Return EXACTLY 5 items per classified category (product_announcements, funding,
  partnerships, market_signals). If the raw data has fewer than 5 explicit matches
  for a category, infer plausible items from the companies and market context
  provided. Use your knowledge of these companies to fill gaps — for example,
  if a competitor is known to have raised funding or launched a product, include it
  even if the search results didn't surface that specific article. Use the
  company's own URL when no article URL is available.
- market_opportunities: exactly 5 bullet strings based on overall trends you observe.
- competitive_risks: exactly 5 bullet strings based on gaps or threats you observe.
- action_steps: exactly 5 numbered steps a product team should take.
- Abbreviations: use the first letters of multi-word names (e.g. LangChain → LC,
  Crew AI → CR, StackAI → SA, Voiceflow → VF). For single-word names use first
  two letters uppercase (e.g. Figma → FI).
- Every category MUST have exactly 5 items. This is critical for the dashboard UI.
- Return ONLY valid JSON. No markdown code fences. No extra text.\
"""

llm = ChatOpenAI(
    model="deepseek-ai/DeepSeek-V3-0324",
    base_url="https://api.gmi-serving.com/v1",
    api_key=os.environ.get("GMI_API_KEY"),
    temperature=0.3,
    max_tokens=2048,
)


def _strip_thinking(text: str) -> str:
    """Remove DeepSeek R1 <think>…</think> reasoning blocks."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _logo_url(url: str) -> str:
    """Derive a favicon URL from an article URL."""
    try:
        domain = urlparse(url).netloc or "example.com"
        if "." in domain:
            return FAVICON_BASE.format(domain=domain)
    except Exception:
        pass
    return FAVICON_BASE.format(domain="example.com")


def _extract_json(raw: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


_EMPTY_RESULT: dict = {
    "product_announcements": [],
    "funding": [],
    "partnerships": [],
    "market_signals": [],
    "market_opportunities": [],
    "competitive_risks": [],
    "action_steps": [],
}


def _inject_logos(items: list[dict]) -> list[dict]:
    """Add a logo field to each item based on its url."""
    for item in items:
        item["logo"] = _logo_url(item.get("url", ""))
    return items


def _analyse(inputs: dict) -> dict:
    aggregated = inputs.get("aggregated", [])

    if not aggregated:
        return {**inputs, **_EMPTY_RESULT}

    items_for_llm = [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "highlights": item.get("highlights", []),
        }
        for item in aggregated
    ]

    competitors = inputs.get("competitors", [])
    product_name = inputs.get("product_name", "")
    product_summary = inputs.get("product_summary", "")

    context_parts = [f"Market research query: {inputs.get('query', '')}"]
    if product_name:
        context_parts.append(f"Product being analysed: {product_name} — {product_summary}")
    if competitors:
        comp_list = ", ".join(c.get("name", "") for c in competitors)
        context_parts.append(f"Identified competitors: {comp_list}")

    context_parts.append(
        f"\nSearch results ({len(items_for_llm)} items):\n"
        f"{json.dumps(items_for_llm, indent=2)}"
    )

    user_msg = "\n".join(context_parts)

    response = llm.invoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ])

    cleaned = _strip_thinking(response.content)

    try:
        parsed = _extract_json(cleaned)
    except (json.JSONDecodeError, ValueError):
        parsed = _EMPTY_RESULT

    result = {}
    for key, default in _EMPTY_RESULT.items():
        result[key] = parsed.get(key, default)

    _inject_logos(result.get("product_announcements", []))
    _inject_logos(result.get("funding", []))
    _inject_logos(result.get("partnerships", []))
    _inject_logos(result.get("market_signals", []))

    return {**inputs, **result}


analysis_agent = RunnableLambda(_analyse)
