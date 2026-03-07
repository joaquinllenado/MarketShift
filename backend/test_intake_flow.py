"""
Test script for the intake agent + full pipeline flow.

Runs multiple flexible user inputs through:
  1. intake_agent alone  → shows the optimised query
  2. full pipeline       → shows the complete research result

Writes all output to backend/test_intake_output.txt
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from agents.intake_agent import intake_agent
from agents.orchestrator import run_pipeline

TEST_INPUTS = [
    # Guided-style (matches the suggested format closely)
    "alcemi.ai, US SaaS market. Competitors: jasper.ai, copy.ai, writesonic.com. Focus on pricing",
    # Conversational
    "I run alcemi.ai in the US - track competitor1.com, competitor2.com. Focus on pricing",
    # Minimal / vague
    "Find competitors to Notion in the project management space",
    # Multi-competitor list, no product or region
    "Track Figma, Canva, and Adobe XD for design tool market trends",
]

OUTPUT_PATH = Path(__file__).parent / "test_intake_output.txt"


def _serialize(obj):
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    return obj


def main():
    lines: list[str] = []
    lines.append("=" * 80)
    lines.append("MARKETSHIFT INTAKE AGENT + PIPELINE FLOW TEST")
    lines.append("=" * 80)

    for i, raw_input in enumerate(TEST_INPUTS, start=1):
        lines.append("")
        lines.append("#" * 80)
        lines.append(f"TEST {i} / {len(TEST_INPUTS)}")
        lines.append("#" * 80)
        lines.append(f"\nRAW USER INPUT:\n  {raw_input!r}\n")

        # --- Step A: Intake Agent only ---
        lines.append("-" * 80)
        lines.append("STEP A: INTAKE AGENT — Query Parsing (DeepSeek R1)")
        lines.append("-" * 80)
        try:
            intake_result = intake_agent.invoke({"query": raw_input})
            optimized_query = intake_result["query"]
            lines.append(f"Optimised query: {optimized_query!r}\n")
        except Exception as e:
            lines.append(f"ERROR in intake_agent: {e}\n")
            continue

        # --- Step B: Full pipeline ---
        lines.append("-" * 80)
        lines.append("STEP B: FULL PIPELINE (intake → gather → aggregate → format)")
        lines.append("-" * 80)
        try:
            result = run_pipeline(raw_input)
            lines.append(json.dumps(_serialize(result), indent=2))
        except Exception as e:
            lines.append(f"ERROR in pipeline: {e}")

        lines.append("")

    lines.append("=" * 80)
    lines.append("END OF TEST")
    lines.append("=" * 80)

    OUTPUT_PATH.write_text("\n".join(lines))
    print(f"Test complete. Output written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
