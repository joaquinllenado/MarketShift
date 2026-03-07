"""
Test script for the agent pipeline flow.

Runs each sub-agent individually and the full pipeline, then writes
all outputs to backend/tests/test_flow_output.txt for inspection.
"""

import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_BACKEND / ".env")

from agents.sub_agent_1 import sub_agent_1
from agents.sub_agent_2 import sub_agent_2
from agents.sub_agent_3 import sub_agent_3
from agents.orchestrator import run_pipeline


def _serialize(obj):
    """Convert objects to JSON-serializable form."""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    return obj


def main():
    test_query = "AI writing assistants"
    output_path = Path(__file__).resolve().parent / "test_flow_output.txt"

    lines = []
    lines.append("=" * 80)
    lines.append("MARKETSHIFT AGENT FLOW TEST")
    lines.append("=" * 80)
    lines.append(f"\nTest query: {test_query!r}\n")

    # --- Step 1: Sub-Agent 1 (Data Gathering) ---
    lines.append("-" * 80)
    lines.append("STEP 1: SUB-AGENT 1 — Data Gathering")
    lines.append("(web_search_tool + product_hunt_tool + news_tool in parallel)")
    lines.append("-" * 80)
    try:
        out_1 = sub_agent_1.invoke({"query": test_query})
        lines.append(json.dumps(_serialize(out_1), indent=2))
    except Exception as e:
        lines.append(f"ERROR: {e}")
        lines.append("")
        with output_path.open("w") as f:
            f.write("\n".join(lines))
        print(f"Sub-agent 1 failed. Output written to {output_path}")
        sys.exit(1)

    # --- Step 2: Sub-Agent 2 (Aggregation + Persistence) ---
    lines.append("\n")
    lines.append("-" * 80)
    lines.append("STEP 2: SUB-AGENT 2 — Aggregation + Persistence")
    lines.append("(deduplicates by URL, appends to data/results.json)")
    lines.append("-" * 80)
    try:
        out_2 = sub_agent_2.invoke(out_1)
        lines.append(json.dumps(_serialize(out_2), indent=2))
    except Exception as e:
        lines.append(f"ERROR: {e}")
        lines.append("")
        with output_path.open("w") as f:
            f.write("\n".join(lines))
        print(f"Sub-agent 2 failed. Output written to {output_path}")
        sys.exit(1)

    # --- Step 3: Sub-Agent 3 (Frontend Delivery) ---
    lines.append("\n")
    lines.append("-" * 80)
    lines.append("STEP 3: SUB-AGENT 3 — Frontend Delivery")
    lines.append("(formats response, adds total_results)")
    lines.append("-" * 80)
    try:
        out_3 = sub_agent_3.invoke(out_2)
        lines.append(json.dumps(_serialize(out_3), indent=2))
    except Exception as e:
        lines.append(f"ERROR: {e}")
        lines.append("")
        with output_path.open("w") as f:
            f.write("\n".join(lines))
        print(f"Sub-agent 3 failed. Output written to {output_path}")
        sys.exit(1)

    # --- Full pipeline (orchestrator) ---
    lines.append("\n")
    lines.append("-" * 80)
    lines.append("FULL PIPELINE — Orchestrator (sub_1 | sub_2 | sub_3)")
    lines.append("-" * 80)
    try:
        full_result = run_pipeline(test_query)
        lines.append(json.dumps(_serialize(full_result), indent=2))
    except Exception as e:
        lines.append(f"ERROR: {e}")

    lines.append("\n")
    lines.append("=" * 80)
    lines.append("END OF TEST")
    lines.append("=" * 80)

    output_path.write_text("\n".join(lines))
    print(f"Test complete. Output written to: {output_path}")


if __name__ == "__main__":
    main()
