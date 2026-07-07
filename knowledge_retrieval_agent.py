import time
import uuid
from datetime import datetime, timezone
import os

import chromadb
from google import genai
from dotenv import load_dotenv

from config import GOOGLE_API_KEY  # SO-005: use config module, not raw os.environ
from embeddings import GeminiEmbeddingFunction  # SO-007: shared embedding class
from database import SessionLocal
from models import AgentTrace
from logger import get_logger, sanitize_for_log  # SO-008: log sanitisation

load_dotenv()

logger = get_logger(__name__)

client_genai = genai.Client(api_key=GOOGLE_API_KEY)

embedding_fn = GeminiEmbeddingFunction()
chroma_client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_data"))
collection = chroma_client.get_or_create_collection(
    name="knowledge_articles",
    metadata={"hnsw:space": "cosine"},
    embedding_function=embedding_fn,
)



def _distance_to_confidence(distance: float) -> float:
    return max(0.0, min(1.0, 1.0 - distance))


def _log_agent_trace(trace_id: str, input_summary: str, output_summary: str, duration_ms: int) -> None:
    session = SessionLocal()
    try:
        trace = AgentTrace(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            agent_name="knowledge_retrieval_agent",
            input_summary=input_summary[:200],
            output_summary=output_summary[:200],
            duration_ms=duration_ms,
            created_at=datetime.now(timezone.utc),
        )
        session.add(trace)
        session.commit()
    finally:
        session.close()


def run_knowledge_retrieval_agent(ticket_id: str, category: str, summary: str, trace_id: str, n_results: int = 3) -> dict:
    """
    Searches the knowledge base for articles relevant to the ticket summary.
    Returns the top matches along with an overall confidence score based on
    the closest match.
    """
    start = time.monotonic()

    results = collection.query(
        query_texts=[summary],
        n_results=n_results,
    )

    matched_articles = []
    if results["ids"] and results["ids"][0]:
        for doc_id, distance, metadata, content in zip(
            results["ids"][0], results["distances"][0], results["metadatas"][0], results["documents"][0]
        ):
            matched_articles.append({
                "article_id": doc_id,
                "title": metadata.get("title", ""),
                "content": content,
                "similarity_score": _distance_to_confidence(distance),
            })

    confidence = matched_articles[0]["similarity_score"] if matched_articles else 0.0

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(f"trace={trace_id} ticket={ticket_id} top confidence={confidence:.3f}")

    output_summary = f"matches={[m['article_id'] for m in matched_articles]}, confidence={confidence:.3f}"
    _log_agent_trace(trace_id, f"category={category}, summary={sanitize_for_log(summary)}", output_summary, duration_ms)

    return {
        "matched_articles": matched_articles,
        "confidence": confidence,
    }
