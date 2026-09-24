"""
SentinelDesk API.   uvicorn app:app --reload    ->  http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from decision_trace import Ticket
from gen4.api import common_router
from service import SentinelDeskService

service = SentinelDeskService()
app = FastAPI(title="SentinelDesk", version="2.0.0",
              description="Explicit, testable ticket escalation: literal policy rules, legal-threat intent "
                          "classification, repeat-contact memory, and precedents learned from agent corrections.")
app.include_router(common_router(service, "sentineldesk"))


class TicketIn(BaseModel):
    ticket_id: str
    text: str
    age_hours: float = Field(..., ge=0)
    customer_tier: Literal["standard", "premium"] = "standard"
    refund_requested: float = Field(0.0, ge=0)
    customer_id: str | None = None


class OverrideIn(BaseModel):
    decision_id: str
    should_escalate: bool
    legal_threat: bool | None = Field(None, description="Agent's call on whether the text was a genuine legal threat")
    agent: str = "agent"
    note: str = ""


@app.get("/", tags=["ops"])
def root():
    return {"service": "SentinelDesk", "docs": "/docs", "flow": "POST /evaluate -> POST /override (agent correction)"}


@app.post("/evaluate", tags=["decision"])
def evaluate(body: TicketIn):
    d = body.model_dump()
    cid = d.pop("customer_id")
    return service.evaluate(Ticket(**d), customer_id=cid)


@app.post("/override", tags=["feedback"])
def override(body: OverrideIn):
    try:
        return service.override(**body.model_dump())
    except KeyError:
        raise HTTPException(404, "unknown decision_id")


@app.get("/metrics", tags=["feedback"])
def metrics():
    return service.override_rates()
