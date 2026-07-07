import uuid
from datetime import datetime, timezone

from security_guardian import run_security_guardian
from intake_agent import run_intake_agent
from knowledge_retrieval_agent import run_knowledge_retrieval_agent
from resolution_agent import run_resolution_agent
from knowledge_extraction_agent import run_knowledge_extraction_agent
from logger import get_logger

logger = get_logger(__name__)


def run_secureops_pipeline_generator(raw_request: str, user_id: str = "demo_user", company_id: str = "demo_company"):
    """
    Generator version of the SecureOps orchestrator.
    Yields dicts describing the state of each step.
    Each yield is of format:
    {
        "step": str,
        "status": "running" | "completed" | "failed",
        "message": str,
        "data": dict
    }
    The final yielded item is the final result dictionary (which does not contain a "step" key).
    """
    trace_id = str(uuid.uuid4())
    logger.info(f"trace={trace_id} pipeline started (generator)")

    # Step 1: Security Guardian
    yield {
        "step": "security_guardian",
        "status": "running",
        "message": "Security Guardian is validating the input request...",
        "data": {}
    }

    try:
        verdict = run_security_guardian(
            raw_request=raw_request,
            user_id=user_id,
            company_id=company_id,
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.error(f"trace={trace_id} Security Guardian failed: {exc}")
        yield {
            "step": "security_guardian",
            "status": "failed",
            "message": f"Security Guardian failed: {exc}",
            "data": {}
        }
        raise exc

    if verdict.validation_result == "rejected":
        logger.info(f"trace={trace_id} pipeline stopped at Security Guardian")
        final_result = {
            "trace_id": trace_id,
            "status": "rejected",
            "rejection_reason": verdict.rejection_reason,
            "risk_flags": verdict.risk_flags,
        }
        yield {
            "step": "security_guardian",
            "status": "completed",
            "message": f"Security Guardian: Rejected ({verdict.rejection_reason or 'No reason provided'})",
            "data": final_result
        }
        yield final_result
        return

    yield {
        "step": "security_guardian",
        "status": "completed",
        "message": "Security Guardian: Approved request",
        "data": {
            "validation_result": verdict.validation_result,
            "risk_flags": verdict.risk_flags
        }
    }

    # Step 2: Intake Agent
    yield {
        "step": "intake_agent",
        "status": "running",
        "message": "Intake Agent is classifying request and generating ticket...",
        "data": {}
    }
    intake_result = run_intake_agent(
        raw_request=raw_request,
        user_id=user_id,
        company_id=company_id,
        trace_id=trace_id,
    )
    yield {
        "step": "intake_agent",
        "status": "completed",
        "message": f"Intake Agent: Classified as {intake_result['category']}, Priority: {intake_result['priority']} (Ticket ID: {intake_result['ticket_id'][:8]})",
        "data": intake_result
    }

    # Step 3: Knowledge Retrieval Agent
    yield {
        "step": "knowledge_retrieval_agent",
        "status": "running",
        "message": "Knowledge Retrieval Agent is querying vector database...",
        "data": {}
    }
    retrieval_result = run_knowledge_retrieval_agent(
        ticket_id=intake_result["ticket_id"],
        category=intake_result["category"],
        summary=intake_result["summary"],
        trace_id=trace_id,
    )
    yield {
        "step": "knowledge_retrieval_agent",
        "status": "completed",
        "message": f"Knowledge Retrieval Agent: Query matched with {retrieval_result['confidence'] * 100:.1f}% confidence",
        "data": retrieval_result
    }

    # Step 4: Resolution Agent
    yield {
        "step": "resolution_agent",
        "status": "running",
        "message": "Resolution Agent is evaluating resolution...",
        "data": {}
    }
    resolution_result = run_resolution_agent(
        ticket_id=intake_result["ticket_id"],
        summary=intake_result["summary"],
        matched_articles=retrieval_result["matched_articles"],
        confidence=retrieval_result["confidence"],
        trace_id=trace_id,
    )
    
    action_text = "Auto-resolved" if resolution_result["action"] == "auto_resolve" else f"Escalated ({resolution_result['escalation_reason']})"
    yield {
        "step": "resolution_agent",
        "status": "completed",
        "message": f"Resolution Agent: {action_text}",
        "data": resolution_result
    }

    result = {
        "trace_id": trace_id,
        "status": "processed",
        "ticket_id": intake_result["ticket_id"],
        "category": intake_result["category"],
        "priority": intake_result["priority"],
        "confidence": retrieval_result["confidence"],
        "action": resolution_result["action"],
        "resolution_text": resolution_result["resolution_text"],
        "escalation_reason": resolution_result["escalation_reason"],
        "article_created": False,
        "article_id": None,
    }

    # Step 5: Knowledge Extraction Agent
    if resolution_result["action"] == "auto_resolve":
        yield {
            "step": "knowledge_extraction_agent",
            "status": "running",
            "message": "Knowledge Extraction Agent is checking generalizability...",
            "data": {}
        }
        extraction_result = run_knowledge_extraction_agent(
            ticket_id=intake_result["ticket_id"],
            summary=intake_result["summary"],
            resolution_text=resolution_result["resolution_text"],
            trace_id=trace_id,
        )
        result["article_created"] = extraction_result["article_created"]
        result["article_id"] = extraction_result["article_id"]
        
        extracted_msg = f"Knowledge Extraction Agent: Created knowledge article {extraction_result['article_id'][:8]}" if extraction_result["article_created"] else "Knowledge Extraction Agent: Resolution not generalizable, no article created."
        yield {
            "step": "knowledge_extraction_agent",
            "status": "completed",
            "message": extracted_msg,
            "data": extraction_result
        }

    logger.info(f"trace={trace_id} pipeline completed with status: {resolution_result['action']}")
    yield result


def run_secureops_pipeline(raw_request: str, user_id: str = "demo_user", company_id: str = "demo_company") -> dict:
    """
    The SecureOps orchestrator. Wraps the generator version to maintain backwards compatibility.
    """
    generator = run_secureops_pipeline_generator(raw_request, user_id, company_id)
    final_result = None
    for step in generator:
        if isinstance(step, dict) and "step" not in step:
            final_result = step
    return final_result
