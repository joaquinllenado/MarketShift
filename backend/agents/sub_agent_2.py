"""
Sub-Agent 2: Aggregation

Receives the gathered data from Sub-Agent 1, deduplicates results
across all three sources by URL.

Returns the same dict with two extra keys:
  - aggregated   → deduplicated list of all results with a "source" tag
  - persisted_at → UTC ISO timestamp

Storage is not persisted here; the caller will add DB persistence later.
"""

import logging
from datetime import datetime, timezone

from langchain_core.runnables import RunnableLambda

logger = logging.getLogger(__name__)


def _aggregate_and_persist(inputs: dict) -> dict:
    logger.info("[sub_agent_2] Aggregating and deduplicating results …")

    raw_counts = {k: len(inputs.get(k, [])) for k in ("web", "product_hunt", "news")}
    logger.info("[sub_agent_2] Raw item counts: %s", raw_counts)

    seen_urls: set[str] = set()
    aggregated: list[dict] = []
    for source_key in ("web", "product_hunt", "news"):
        for item in inputs.get(source_key, []):
            url = item.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                aggregated.append({**item, "source": source_key})

    timestamp = datetime.now(timezone.utc).isoformat()

    logger.info("[sub_agent_2] %d unique items aggregated (from %d raw)",
                len(aggregated), sum(raw_counts.values()))

    return {**inputs, "aggregated": aggregated, "persisted_at": timestamp}


sub_agent_2 = RunnableLambda(_aggregate_and_persist)
