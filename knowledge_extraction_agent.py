import time
import uuid
import os
import re
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel
from google import genai
import chromadb
from dotenv import load_dotenv

from config import GOOGLE_API_KEY, MODEL_FLASH
from embeddings import GeminiEmbeddingFunction  # SO-007: shared embedding class
from database import SessionLocal
from models import KnowledgeArticle, AgentTrace
from logger import get_logger, sanitize_for_log  # SO-008: log sanitisation

load_dotenv()

logger = get_logger(__name__)

client = genai.Client(api_key=GOOGLE_API_KEY)

embedding_fn = GeminiEmbeddingFunction()
chroma_client = chromadb.PersistentClient(
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_data")
)
collection = chroma_client.get_or_create_collection(
    name="knowledge_articles",
    metadata={"hnsw:space": "cosine"},
    embedding_function=embedding_fn,
)

# SO-003: Maximum length allowed for a stored knowledge article.
# Prevents LLM-generated content that embeds arbitrarily long
# instructions from being stored in the knowledge base unchecked.
_MAX_ARTICLE_CONTENT = 8000
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_article_content(text: str) -> str:
    """
    SO-003: Strip control characters from LLM-generated article content
    and enforce a maximum length before persisting to ChromaDB / SQLite.
    Newlines are preserved as they are structurally meaningful in articles.
    """
    sanitized = _CONTROL_CHARS.sub("", text or "")
    return sanitized[:_MAX_ARTICLE_CONTENT]


EXTRACTION_INSTRUCTION = """
You are the Knowledge Extraction Agent for SecureOps, an IT Service
Management system. You are given a ticket summary and its resolution text.
Decide whether this resolution represents a generalizable fix that would
help resolve future, similar tickets, as opposed to something specific to
one user's unique circumstances.

If generalizable, write a knowledge article title and content, written
the way a real support team documents a known fix for future reference.
The content should be written generally, describing the class of problem
and its resolution, not tied to the specific ticket's exact wording.

If not generalizable, indicate that clearly and do not write article
content.

Respond only with the requested structured output.
"""


class ExtractionResult(BaseModel):
    generalizable: bool
    title: Optional[str] = None
    content: Optional[str] = None


def _log_agent_trace(trace_id: str, input_summary: str, output_summary: str, duration_ms: int) -> None:
    session = SessionLocal()
    try:
        trace = AgentTrace(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            agent_name="knowledge_extraction_agent",
            input_summary=input_summary[:200],
            output_summary=output_summary[:200],
            duration_ms=duration_ms,
            created_at=datetime.now(timezone.utc),
        )
        session.add(trace)
        session.commit()
    finally:
        session.close()


def run_knowledge_extraction_agent(ticket_id: str, summary: str, resolution_text: str, trace_id: str) -> dict:
    """
    Evaluates a confirmed resolution and, if generalizable, writes a new
    knowledge article to both the relational database and the vector
    store, closing the knowledge flywheel loop.
    """
    start = time.monotonic()

    response = client.models.generate_content(
        model=MODEL_FLASH,
        contents=(
            f"{EXTRACTION_INSTRUCTION}\n\nTicket summary:\n{summary}\n\n"
            f"Resolution:\n{resolution_text}"
        ),
        config={
            "response_mime_type": "application/json",
            "response_schema": ExtractionResult,
        },
    )
    result = ExtractionResult.model_validate_json(response.text)

    if not result.generalizable:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(f"trace={trace_id} ticket={ticket_id} resolution not generalizable, no article created")
        _log_agent_trace(trace_id, summary, "not generalizable", duration_ms)
        return {"article_created": False, "article_id": None}

    article_id = str(uuid.uuid4())

    # SO-003: Sanitise LLM-generated content before persisting to prevent
    # knowledge base poisoning via embedded instructions.
    safe_content = _sanitize_article_content(result.content)
    safe_title = _sanitize_article_content(result.title)

    session = SessionLocal()
    try:
        article = KnowledgeArticle(
            id=article_id,
            title=safe_title,
            content=safe_content,
            source_ticket_id=ticket_id,
            created_at=datetime.now(timezone.utc),
        )
        session.add(article)
        session.commit()
    finally:
        session.close()

    collection.add(
        ids=[article_id],
        documents=[safe_content],
        metadatas=[{
            "title": safe_title,
            "category": "generated",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }],
    )

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(f"trace={trace_id} ticket={ticket_id} article={article_id} created: {sanitize_for_log(safe_title)}")
    _log_agent_trace(trace_id, sanitize_for_log(summary), f"article created: {safe_title}", duration_ms)

    return {"article_created": True, "article_id": article_id}
