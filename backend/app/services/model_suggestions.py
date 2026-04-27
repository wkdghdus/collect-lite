import uuid
from sqlalchemy.orm import Session

from app.config import settings


def run_cohere_rerank(query: str, documents: list[str]) -> list[dict]:
    """Score documents against query using Cohere Rerank. Returns ranked list with scores."""
    if not settings.cohere_api_key:
        return _local_fallback_rank(query, documents)
    import cohere
    co = cohere.Client(settings.cohere_api_key)
    response = co.rerank(model="rerank-english-v3.0", query=query, documents=documents)
    return [{"index": r.index, "relevance_score": r.relevance_score} for r in response.results]


def _local_fallback_rank(query: str, documents: list[str]) -> list[dict]:
    """Deterministic fallback when Cohere key is not configured."""
    return [{"index": i, "relevance_score": 0.5} for i in range(len(documents))]


def generate_suggestion_for_task(db: Session, task_id: uuid.UUID) -> None:
    """Generate and persist a ModelSuggestion for the given task."""
    pass
