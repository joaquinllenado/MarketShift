import os
from typing import Optional

from dotenv import load_dotenv
from exa_py import Exa
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prefect import flow, task
from pydantic import BaseModel

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
