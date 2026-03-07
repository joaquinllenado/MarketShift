"""Quick test: analysis_agent with existing data + competitor context."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

from agents.analysis_agent import analysis_agent

data = json.loads((Path(__file__).parent / "data" / "results.json").read_text())
sample = data[-1]

result = analysis_agent.invoke({
    "query": sample["query"],
    "aggregated": sample["aggregated"],
    "persisted_at": sample.get("timestamp", ""),
    "product_name": "Alcemi",
    "product_summary": "AI shopping agent for Shopify stores",
    "competitors": [
        {"name": "Kopa.ai", "url": "https://kopa.ai"},
        {"name": "Askflow AI", "url": "https://askflow.ai"},
        {"name": "Qlode.ai", "url": "https://qlode.ai"},
        {"name": "Askly", "url": "https://askly.me"},
        {"name": "Ami AI", "url": "https://meetami.ai"},
    ],
})

keys = [
    "product_announcements", "funding", "partnerships",
    "market_signals", "market_opportunities", "competitive_risks",
    "action_steps",
]

for k in keys:
    items = result.get(k, [])
    print(f"{k}: {len(items)} items")
    for item in items:
        if isinstance(item, dict):
            print(f"  [{item.get('abbreviation','')}] {item.get('title','')}")
        else:
            print(f"  - {item}")
