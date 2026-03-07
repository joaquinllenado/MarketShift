"""
Sub-Agent 2: Aggregation + Persistence

Receives the gathered data from Sub-Agent 1, deduplicates results
across all three sources by URL, and appends the full run record
to backend/data/results.json.

Returns the same dict with two extra keys:
  - aggregated   → deduplicated list of all results with a "source" tag
  - persisted_at → UTC ISO timestamp of when the record was written

LLM hook: pass aggregated results through a summarisation chain
(e.g. ChatOpenAI | StrOutputParser) before persisting to produce
a concise summary field alongside the raw data.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.runnables import RunnableLambda

DATA_FILE = Path(__file__).parent.parent / "data" / "results.json"


def _aggregate_and_persist(inputs: dict) -> dict:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load existing runs
    existing: list = []
    if DATA_FILE.exists():
        try:
            existing = json.loads(DATA_FILE.read_text())
        except (json.JSONDecodeError, ValueError):
            existing = []

    # Deduplicate across sources by URL
    seen_urls: set[str] = set()
    aggregated: list[dict] = []
    for source_key in ("web", "product_hunt", "news"):
        for item in inputs.get(source_key, []):
            url = item.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                aggregated.append({**item, "source": source_key})

    timestamp = datetime.now(timezone.utc).isoformat()

    record = {
        "query": inputs["query"],
        "timestamp": timestamp,
        "web": inputs.get("web", []),
        "product_hunt": inputs.get("product_hunt", []),
        "news": inputs.get("news", []),
        "aggregated": aggregated,
    }

    existing.append(record)
    DATA_FILE.write_text(json.dumps(existing, indent=2))

    return {**inputs, "aggregated": aggregated, "persisted_at": timestamp}


sub_agent_2 = RunnableLambda(_aggregate_and_persist)
