"""
Test script for the intake agent + full pipeline flow.

Runs product URLs through the full pipeline:
  intake_agent → sub_agent_1 → sub_agent_2 → analysis_agent → sub_agent_3

Writes all output to backend/tests/test_intake_output.txt
"""

import json
import sys
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_BACKEND / ".env")

from agents.intake_agent import intake_agent
from agents.orchestrator import run_pipeline

TEST_URLS = [
    "https://alcemi.ai",
    "https://notion.so",
    "https://figma.com",
]

OUTPUT_PATH = Path(__file__).resolve().parent / "test_intake_output.txt"


def _serialize(obj):
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    return obj


def main():
    lines: list[str] = []
    lines.append("=" * 80)
    lines.append("MARKETSHIFT PIPELINE FLOW TEST")
    lines.append("=" * 80)

    total_start = time.perf_counter()

    for i, url in enumerate(TEST_URLS, start=1):
        lines.append("")
        lines.append("#" * 80)
        lines.append(f"TEST {i} / {len(TEST_URLS)}")
        lines.append("#" * 80)
        lines.append(f"\nURL: {url}\n")

        # --- Step A: Intake Agent only ---
        lines.append("-" * 80)
        lines.append("STEP A: INTAKE AGENT — Competitor Discovery")
        lines.append("-" * 80)
        t0 = time.perf_counter()
        try:
            intake_result = intake_agent.invoke({"url": url})
            t1 = time.perf_counter()
            lines.append(f"Duration: {t1 - t0:.1f}s")
            lines.append(f"Product: {intake_result.get('product_name', '?')}")
            lines.append(f"Query: {intake_result.get('query', '?')[:120]}")
            comps = intake_result.get("competitors", [])
            lines.append(f"Competitors ({len(comps)}): {', '.join(c.get('name','') for c in comps)}\n")
        except Exception as e:
            t1 = time.perf_counter()
            lines.append(f"ERROR in intake_agent ({t1 - t0:.1f}s): {e}\n")
            continue

        # --- Step B: Full pipeline ---
        lines.append("-" * 80)
        lines.append("STEP B: FULL PIPELINE (intake → gather → aggregate → analyse → format)")
        lines.append("-" * 80)
        t0 = time.perf_counter()
        try:
            result = run_pipeline(url)
            t1 = time.perf_counter()
            lines.append(f"Duration: {t1 - t0:.1f}s")
            lines.append(f"Product announcements: {len(result.get('product_announcements', []))}")
            lines.append(f"Funding: {len(result.get('funding', []))}")
            lines.append(f"Partnerships: {len(result.get('partnerships', []))}")
            lines.append(f"Market signals: {len(result.get('market_signals', []))}")
            lines.append(f"Market opportunities: {len(result.get('market_opportunities', []))}")
            lines.append(f"Competitive risks: {len(result.get('competitive_risks', []))}")
            lines.append(f"Action steps: {len(result.get('action_steps', []))}")
            lines.append("")
            lines.append(json.dumps(_serialize(result), indent=2))
        except Exception as e:
            t1 = time.perf_counter()
            lines.append(f"ERROR in pipeline ({t1 - t0:.1f}s): {e}")

        lines.append("")

    total_elapsed = time.perf_counter() - total_start
    lines.append("=" * 80)
    lines.append(f"TOTAL TIME: {total_elapsed:.1f}s")
    lines.append("=" * 80)

    OUTPUT_PATH.write_text("\n".join(lines))
    print(f"Test complete ({total_elapsed:.1f}s total). Output written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
