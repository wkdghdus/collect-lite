import cohere

from app.config import settings

RERANK_MODEL = "rerank-english-v3.0"

LABEL_RELEVANT = "relevant"
LABEL_PARTIALLY_RELEVANT = "partially_relevant"
LABEL_NOT_RELEVANT = "not_relevant"

THRESHOLD_RELEVANT = 0.70
THRESHOLD_PARTIALLY_RELEVANT = 0.40


def _score_to_label(score: float) -> str:
    if score >= THRESHOLD_RELEVANT:
        return LABEL_RELEVANT
    if score >= THRESHOLD_PARTIALLY_RELEVANT:
        return LABEL_PARTIALLY_RELEVANT
    return LABEL_NOT_RELEVANT


def generate_rerank_suggestion(query: str, document: str) -> tuple[float, str, dict]:
    if not settings.cohere_api_key:
        raise RuntimeError("COHERE_API_KEY is not configured; cannot call Cohere Rerank.")

    client = cohere.Client(settings.cohere_api_key)
    response = client.rerank(model=RERANK_MODEL, query=query, documents=[document])

    score = float(response.results[0].relevance_score)
    label = _score_to_label(score)
    raw = response.model_dump(mode="json")
    return score, label, raw
