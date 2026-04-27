import json

import pytest
from pydantic import BaseModel

from app.services import cohere_service
from app.services.cohere_service import (
    LABEL_NOT_RELEVANT,
    LABEL_PARTIALLY_RELEVANT,
    LABEL_RELEVANT,
    RERANK_MODEL,
    _score_to_label,
    generate_rerank_suggestion,
)


class _FakeResult(BaseModel):
    index: int = 0
    relevance_score: float


class _FakeRerankResponse(BaseModel):
    results: list[_FakeResult]


class _FakeCohereClient:
    instances: list["_FakeCohereClient"] = []

    def __init__(self, api_key: str, score: float):
        self.api_key = api_key
        self._score = score
        self.calls: list[dict] = []
        _FakeCohereClient.instances.append(self)

    def rerank(self, *, model: str, query: str, documents: list[str]):
        self.calls.append({"model": model, "query": query, "documents": documents})
        return _FakeRerankResponse(results=[_FakeResult(relevance_score=self._score)])


def _patch_client_factory(monkeypatch: pytest.MonkeyPatch, score: float) -> None:
    _FakeCohereClient.instances = []

    class _Factory:
        @staticmethod
        def Client(api_key: str) -> _FakeCohereClient:
            return _FakeCohereClient(api_key, score)

    monkeypatch.setattr(cohere_service, "cohere", _Factory)


def test_score_to_label_thresholds():
    assert _score_to_label(1.0) == LABEL_RELEVANT
    assert _score_to_label(0.70) == LABEL_RELEVANT
    assert _score_to_label(0.6999) == LABEL_PARTIALLY_RELEVANT
    assert _score_to_label(0.40) == LABEL_PARTIALLY_RELEVANT
    assert _score_to_label(0.3999) == LABEL_NOT_RELEVANT
    assert _score_to_label(0.0) == LABEL_NOT_RELEVANT


def test_generate_rerank_suggestion_no_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(cohere_service.settings, "cohere_api_key", "")
    with pytest.raises(RuntimeError, match="COHERE_API_KEY"):
        generate_rerank_suggestion("q", "d")


def test_generate_rerank_suggestion_happy_path(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(cohere_service.settings, "cohere_api_key", "test-key")
    _patch_client_factory(monkeypatch, score=0.83)

    score, label, raw = generate_rerank_suggestion(
        "What is the capital of France?",
        "Paris is the capital of France.",
    )

    assert score == 0.83
    assert label == LABEL_RELEVANT
    assert raw == {"results": [{"index": 0, "relevance_score": 0.83}]}
    json.dumps(raw)

    assert len(_FakeCohereClient.instances) == 1
    client = _FakeCohereClient.instances[0]
    assert client.api_key == "test-key"
    assert client.calls == [
        {
            "model": RERANK_MODEL,
            "query": "What is the capital of France?",
            "documents": ["Paris is the capital of France."],
        }
    ]


def test_generate_rerank_suggestion_partial_label(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(cohere_service.settings, "cohere_api_key", "test-key")
    _patch_client_factory(monkeypatch, score=0.55)

    score, label, _ = generate_rerank_suggestion("q", "d")

    assert score == 0.55
    assert label == LABEL_PARTIALLY_RELEVANT


def test_generate_rerank_suggestion_not_relevant_label(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(cohere_service.settings, "cohere_api_key", "test-key")
    _patch_client_factory(monkeypatch, score=0.10)

    score, label, _ = generate_rerank_suggestion("q", "d")

    assert score == 0.10
    assert label == LABEL_NOT_RELEVANT
