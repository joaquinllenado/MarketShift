import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from exa_py import Exa
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prefect import flow, task
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="MarketShift API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time as _time

    start = _time.perf_counter()
    logger.info("→  %s %s", request.method, request.url.path)
    response = await call_next(request)
    elapsed_ms = (_time.perf_counter() - start) * 1000
    logger.info("←  %s %s  %d  (%.0f ms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response

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
    logger.info("Searching companies for query: %s", query)
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
    logger.info("Found %d companies", len(companies))
    return companies


@task(name="scrape-urls")
def scrape_urls_task(urls: list[str]) -> list[ScrapedResult]:
    logger.info("Scraping %d URLs: %s", len(urls), urls)
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
    logger.info("Scraped %d pages", len(scraped))
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
    logger.info("Research request — query=%r, urls=%s", request.query, request.urls)
    if not request.query and not request.urls:
        raise HTTPException(
            status_code=400,
            detail="Provide at least a company query or one URL to scrape.",
        )
    result = research_flow(query=request.query, urls=request.urls)
    logger.info("Research complete — %d companies, %d scraped pages", len(result.companies), len(result.scraped))
    return result


@app.get("/hello")
def hello():
    return {"message": "MarketShift API is running."}


RESULTS_PATH = Path(__file__).parent / "data" / "results.json"


@app.get("/pipeline/results")
def get_pipeline_results():
    if not RESULTS_PATH.exists():
        logger.warning("Pipeline results requested but %s does not exist", RESULTS_PATH)
        raise HTTPException(status_code=404, detail="No pipeline results found.")
    logger.info("Serving cached pipeline results from %s", RESULTS_PATH)
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


@app.post("/pipeline", response_model=PipelineResponse)
def pipeline(request: PipelineRequest):
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url must not be empty.")
    logger.info("Pipeline started for URL: %s", url)

    from agents.orchestrator import run_pipeline
    result = run_pipeline(url)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = result if isinstance(result, dict) else result.model_dump()
    payload["persisted_at"] = datetime.now(timezone.utc).isoformat()
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    logger.info("Pipeline complete — results persisted to %s", RESULTS_PATH)
    return payload


@app.post("/pipeline/voice-summary")
def voice_summary():
    if not RESULTS_PATH.exists():
        logger.warning("Voice summary requested but no pipeline results exist")
        raise HTTPException(status_code=404, detail="No pipeline results found. Run the pipeline first.")

    logger.info("Generating voice summary from %s", RESULTS_PATH)
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
