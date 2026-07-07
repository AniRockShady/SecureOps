"""
Shared Gemini embedding function for ChromaDB collections.

Extracted from knowledge_retrieval_agent.py and knowledge_extraction_agent.py
to eliminate duplication and ensure both agents use an identical embedding
implementation. Any future changes to the model name, retry logic, or API
version need only be made here.
"""
import os
from chromadb import Documents, EmbeddingFunction, Embeddings
from google import genai
from dotenv import load_dotenv

load_dotenv()

_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


class GeminiEmbeddingFunction(EmbeddingFunction):
    """ChromaDB-compatible embedding function backed by gemini-embedding-001."""

    def __call__(self, input: Documents) -> Embeddings:
        result = _client.models.embed_content(
            model="gemini-embedding-001",
            contents=input,
        )
        return [e.values for e in result.embeddings]
