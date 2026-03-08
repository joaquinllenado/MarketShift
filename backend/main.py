import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from exa_py import Exa
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prefect import flow, task
from pydantic import BaseModel

logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="MarketShift API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

exa = Exa(api_key=os.environ.get("EXA_API_KEY"))


# --- Request / Response models ---

class ResearchRequest(BaseModel):
    query: Optional[str] = None
    urls: list[str] = []


class CompanyResult(BaseModel):
    title: str
    url: str
    highlights: list[str]


class ScrapedResult(BaseModel):
    url: str
    title: str
    text: str


class ResearchResponse(BaseModel):
    companies: list[CompanyResult]
    scraped: list[ScrapedResult]


# --- Pipeline models (multi-agent flow) ---

class PipelineRequest(BaseModel):
    url: str


class ProductAnnouncement(BaseModel):
    company: str
    abbreviation: str
    title: str
    url: str
    logo: str = ""


class FundingItem(BaseModel):
    company: str
    abbreviation: str
    title: str
    amount: str = ""
    url: str
    logo: str = ""


class PartnershipItem(BaseModel):
    company: str
    abbreviation: str
    title: str
    url: str
    logo: str = ""


class MarketSignalItem(BaseModel):
    company: str
    abbreviation: str
    title: str
    description: str = ""
    url: str
    logo: str = ""


class ActionStep(BaseModel):
    step: int
    title: str


class PipelineResponse(BaseModel):
    query: str
    product_announcements: list[ProductAnnouncement] = []
    funding: list[FundingItem] = []
    partnerships: list[PartnershipItem] = []
    market_signals: list[MarketSignalItem] = []
    market_opportunities: list[str] = []
    competitive_risks: list[str] = []
    action_steps: list[ActionStep] = []
    persisted_at: str = ""


# --- Prefect tasks ---

@task(name="search-companies")
def search_companies_task(query: str) -> list[CompanyResult]:
    results = exa.search_and_contents(
        query,
        category="company",
        type="auto",
        num_results=5,
        highlights={"num_sentences": 3, "highlights_per_url": 2},
    )
    companies = []
    for r in results.results:
        highlights = r.highlights if r.highlights else []
        companies.append(
            CompanyResult(
                title=r.title or r.url,
                url=r.url,
                highlights=highlights,
            )
        )
    return companies


@task(name="scrape-urls")
def scrape_urls_task(urls: list[str]) -> list[ScrapedResult]:
    results = exa.get_contents(urls, text={"max_characters": 5000})
    scraped = []
    for r in results.results:
        scraped.append(
            ScrapedResult(
                url=r.url,
                title=r.title or r.url,
                text=r.text or "",
            )
        )
    return scraped


# --- Prefect flow ---

@flow(name="competitor-research-flow")
def research_flow(query: Optional[str], urls: list[str]) -> ResearchResponse:
    companies: list[CompanyResult] = []
    scraped: list[ScrapedResult] = []

    if query:
        companies = search_companies_task(query)
    if urls:
        scraped = scrape_urls_task(urls)

    return ResearchResponse(companies=companies, scraped=scraped)


# --- FastAPI endpoints ---

@app.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest):
    if not request.query and not request.urls:
        raise HTTPException(
            status_code=400,
            detail="Provide at least a company query or one URL to scrape.",
        )
    result = research_flow(query=request.query, urls=request.urls)
    return result


@app.get("/hello")
def hello():
    return {"message": "MarketShift API is running."}


RESULTS_PATH = Path(__file__).parent / "data" / "results.json"


@app.get("/pipeline/results")
def get_pipeline_results():
    if not RESULTS_PATH.exists():
        raise HTTPException(status_code=404, detail="No pipeline results found.")
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


@app.post("/pipeline", response_model=PipelineResponse)
def pipeline(request: PipelineRequest):
    if not request.url.strip():
        raise HTTPException(status_code=400, detail="url must not be empty.")
    from agents.orchestrator import run_pipeline
    result = run_pipeline(request.url.strip())

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = result if isinstance(result, dict) else result.model_dump()
    payload["persisted_at"] = datetime.now(timezone.utc).isoformat()
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return payload


@app.post("/pipeline/voice-summary")
def voice_summary():
    if not RESULTS_PATH.exists():
        raise HTTPException(status_code=404, detail="No pipeline results found. Run the pipeline first.")

    raw = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    pipeline_data = raw[-1] if isinstance(raw, list) else raw

    from agents.voice_summary import generate_voice_summary
    try:
        audio_bytes = generate_voice_summary(pipeline_data)
    except Exception as exc:
        logger.exception("Voice summary generation failed")
        raise HTTPException(status_code=502, detail=f"Voice summary generation failed: {exc}")

    audio_path = RESULTS_PATH.parent / "voice_summary.mp3"
    audio_path.write_bytes(audio_bytes)
    logger.info("Voice summary saved to %s", audio_path)

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=market_briefing.mp3"},
    )
