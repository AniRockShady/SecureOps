import time
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel
from google import genai

from config import GOOGLE_API_KEY, MODEL_FLASH
from database import SessionLocal
from models import Ticket, AgentTrace
from logger import get_logger

logger = get_logger(__name__)

client = genai.Client(api_key=GOOGLE_API_KEY)

INTAKE_INSTRUCTION = """
You are the Intake Agent for SecureOps, an IT Service Management system.
You receive a request that has already passed security validation. Your job
is to classify it accurately so it can be routed and resolved efficiently.

Classify the request into:
- category: a short label describing the type of issue, for example
  "Access Management", "Network", "Email", "Hardware", "Software Licensing",
  or "Infrastructure". Use your judgment if none fit exactly.
- priority: one of low, medium, high, critical. Base this on business impact
  and urgency as described in the request, not on the tone of the language.
- affected_system: the specific system, application, or piece of hardware
  affected, in a few words.
- summary: a single clear sentence summarizing the issue for a support agent
  who has not seen the original request.

Respond only with the requested structured output.
"""


class IntakeResult(BaseModel):
    category: str
    priority: Literal["low", "medium", "high", "critical"]
    affected_system: str
    summary: str


def _log_agent_trace(trace_id: str, input_summary: str, output_summary: str, duration_ms: int) -> None:
    session = SessionLocal()
    try:
        trace = AgentTrace(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            agent_name="intake_agent",
            input_summary=input_summary[:200],
            output_summary=output_summary[:200],
            duration_ms=duration_ms,
            created_at=datetime.now(timezone.utc),
        )
        session.add(trace)
        session.commit()
    finally:
        session.close()


def run_intake_agent(raw_request: str, user_id: str, company_id: str, trace_id: str) -> dict:
    """
    Classifies an approved request and creates the ticket record.
    Should only ever be called after the Security Guardian has approved
    the request.
    """
    start = time.monotonic()

    response = client.models.generate_content(
        model=MODEL_FLASH,
        contents=f"{INTAKE_INSTRUCTION}\n\nRequest to classify:\n{raw_request}",
        config={
            "response_mime_type": "application/json",
            "response_schema": IntakeResult,
        },
    )
    result = IntakeResult.model_validate_json(response.text)

    ticket_id = str(uuid.uuid4())

    session = SessionLocal()
    try:
        ticket = Ticket(
            id=ticket_id,
            company_id=company_id,
            user_id=user_id,
            category=result.category,
            priority=result.priority,
            status="open",
            summary=result.summary,
            created_at=datetime.now(timezone.utc),
        )
        session.add(ticket)
        session.commit()
    finally:
        session.close()

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(f"trace={trace_id} ticket={ticket_id} classified as {result.category}, priority {result.priority}")
    _log_agent_trace(trace_id, raw_request, result.model_dump_json(), duration_ms)

    return {
        "ticket_id": ticket_id,
        "category": result.category,
        "priority": result.priority,
        "affected_system": result.affected_system,
        "summary": result.summary,
    }