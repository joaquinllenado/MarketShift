"""Pipeline request/response schemas."""

from pydantic import BaseModel


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
