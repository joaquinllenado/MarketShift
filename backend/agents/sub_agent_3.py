"""
Sub-Agent 3: Frontend Delivery

Shapes the analysis-agent output into the final frontend-ready response
dict matching the dashboard sections: Product Announcements, Funding,
Partnerships, Market Signals, Market Opportunities, Competitive Risks,
and Action Steps.

This is the last step before the FastAPI endpoint serialises the output
into the PipelineResponse Pydantic model.
"""

import logging

from langchain_core.runnables import RunnableLambda

logger = logging.getLogger(__name__)

_FRONTEND_KEYS = (
    "product_announcements", "funding", "partnerships",
    "market_signals", "market_opportunities", "competitive_risks", "action_steps",
)


def _format_for_frontend(inputs: dict) -> dict:
    output = {
        "query": inputs.get("query", ""),
        "product_name": inputs.get("product_name", ""),
        "product_summary": inputs.get("product_summary", ""),
        "competitors": inputs.get("competitors", []),
        "product_announcements": inputs.get("product_announcements", []),
        "funding": inputs.get("funding", []),
        "partnerships": inputs.get("partnerships", []),
        "market_signals": inputs.get("market_signals", []),
        "market_opportunities": inputs.get("market_opportunities", []),
        "competitive_risks": inputs.get("competitive_risks", []),
        "action_steps": inputs.get("action_steps", []),
        "persisted_at": inputs.get("persisted_at", ""),
    }
    counts = {k: len(output.get(k, [])) for k in _FRONTEND_KEYS}
    logger.info("[sub_agent_3] Formatted for frontend — %s", counts)
    return output


sub_agent_3 = RunnableLambda(_format_for_frontend)
