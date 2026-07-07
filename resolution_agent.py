import time
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel
from google import genai

from config import GOOGLE_API_KEY, MODEL_FLASH, RESOLUTION_CONFIDENCE_THRESHOLD
from database import SessionLocal
from models import Ticket, Escalation, AgentTrace
from logger import get_logger

logger = get_logger(__name__)

client = genai.Client(api_key=GOOGLE_API_KEY)

RESOLUTION_INSTRUCTION = RESOLUTION_INSTRUCTION = """
You are the Resolution Agent for SecureOps, an IT Service Management system.
You are given a ticket summary and one or more retrieved knowledge base
articles that may be relevant. First, judge honestly whether the retrieved
articles actually address this specific ticket's problem.

If they do, set can_resolve to true and write a clear, actionable
resolution based on the retrieved knowledge, adapted to the specific
ticket. Do not invent steps that are not grounded in the retrieved
articles.

If the retrieved articles do not meaningfully address the ticket's actual
problem, set can_resolve to false and leave resolution_text empty, even
if the articles are topically related. Do not write a resolution that
merely states the knowledge base is insufficient; that is not a
resolution.

Respond only with the requested structured output.
"""


class ResolutionDraft(BaseModel):
    can_resolve: bool
    resolution_text: Optional[str] = None


def _log_agent_trace(trace_id: str, input_summary: str, output_summary: str, duration_ms: int) -> None:
    session = SessionLocal()
    try:
        trace = AgentTrace(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            agent_name="resolution_agent",
            input_summary=input_summary[:200],
            output_summary=output_summary[:200],
            duration_ms=duration_ms,
            created_at=datetime.now(timezone.utc),
        )
        session.add(trace)
        session.commit()
    finally:
        session.close()


def _mark_ticket_resolved(ticket_id: str) -> None:
    session = SessionLocal()
    try:
        ticket = session.get(Ticket, ticket_id)
        if ticket:
            ticket.status = "resolved"
            ticket.resolved_at = datetime.now(timezone.utc)
            session.commit()
    finally:
        session.close()


def _create_escalation(ticket_id: str, reason: str) -> None:
    session = SessionLocal()
    try:
        escalation = Escalation(
            id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            reason=reason,
            escalated_at=datetime.now(timezone.utc),
        )
        session.add(escalation)

        ticket = session.get(Ticket, ticket_id)
        if ticket:
            ticket.status = "escalated"

        session.commit()
    finally:
        session.close()


def run_resolution_agent(
    ticket_id: str,
    summary: str,
    matched_articles: list[dict],
    confidence: float,
    trace_id: str,
) -> dict:
    """
    Decides whether to auto-resolve or escalate based on retrieval
    confidence, and either writes a resolution or creates an escalation
    record accordingly.
    """
    start = time.monotonic()

    if confidence < RESOLUTION_CONFIDENCE_THRESHOLD:
        reason = (
            f"Retrieval confidence {confidence:.3f} is below the threshold "
            f"of {RESOLUTION_CONFIDENCE_THRESHOLD}, no sufficiently strong "
            f"match was found in the knowledge base."
        )
        _create_escalation(ticket_id, reason)

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(f"trace={trace_id} ticket={ticket_id} escalated: confidence {confidence:.3f}")
        _log_agent_trace(trace_id, summary, f"escalated, confidence={confidence:.3f}", duration_ms)

        return {
            "action": "escalate",
            "resolution_text": None,
            "escalation_reason": reason,
        }

    article_context = "\n\n".join(
        f"Article: {a['title']}\n{a.get('content', '')}" for a in matched_articles
    )

    response = client.models.generate_content(
        model=MODEL_FLASH,
        contents=(
            f"{RESOLUTION_INSTRUCTION}\n\nTicket summary:\n{summary}\n\n"
            f"Retrieved knowledge:\n{article_context}"
        ),
        config={
            "response_mime_type": "application/json",
            "response_schema": ResolutionDraft,
        },
    )
    draft = ResolutionDraft.model_validate_json(response.text)

    if not draft.can_resolve:
        reason = (
            f"Retrieval confidence {confidence:.3f} cleared the threshold, "
            f"but the Resolution Agent determined the retrieved articles do "
            f"not actually address this ticket's problem."
        )
        _create_escalation(ticket_id, reason)

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(f"trace={trace_id} ticket={ticket_id} escalated: model reported low grounding")
        _log_agent_trace(trace_id, summary, f"escalated, can_resolve=false", duration_ms)

        return {
            "action": "escalate",
            "resolution_text": None,
            "escalation_reason": reason,
        }

    _mark_ticket_resolved(ticket_id)

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(f"trace={trace_id} ticket={ticket_id} auto-resolved")
    _log_agent_trace(trace_id, summary, draft.resolution_text, duration_ms)

    return {
        "action": "auto_resolve",
        "resolution_text": draft.resolution_text,
        "escalation_reason": None,
    }
