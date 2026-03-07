"""
Orchestrator Agent

Defines the pipeline flow by composing the sub-agents into a single
LangChain RunnableSequence using the | pipe operator.

Data flow:
  {"url": str}   (product URL from the user)
    → intake_agent    (scrape URL, discover competitors via Exa + LLM)
    → sub_agent_1     (per-competitor news + market-level web/PH search)
    → sub_agent_2     (aggregate + persist to data/results.json)
    → analysis_agent  (LLM classifies items into dashboard categories)
    → sub_agent_3     (format for frontend)
    → {"query", "product_announcements", "funding", "partnerships",
       "market_signals", "market_opportunities", "competitive_risks",
       "action_steps", "persisted_at"}

GMI Cloud / LangChain config (used by intake_agent & analysis_agent):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        model="deepseek-ai/DeepSeek-R1-0528",
        base_url="https://api.gmi-serving.com/v1",
        api_key=os.environ.get("GMI_API_KEY"),
    )
"""

from .intake_agent import intake_agent
from .sub_agent_1 import sub_agent_1
from .sub_agent_2 import sub_agent_2
from .analysis_agent import analysis_agent
from .sub_agent_3 import sub_agent_3

pipeline = intake_agent | sub_agent_1 | sub_agent_2 | analysis_agent | sub_agent_3


def run_pipeline(url: str) -> dict:
    """Entry point called by the FastAPI /pipeline endpoint.

    Accepts a product URL. The intake_agent scrapes it, discovers
    competitors, and the rest of the pipeline researches them.
    """
    return pipeline.invoke({"url": url})
