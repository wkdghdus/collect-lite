from app.services.consensus import compute_agreement_score, compute_majority_vote


def test_majority_vote_single_label() -> None:
    labels = [{"value": "relevant"}, {"value": "relevant"}, {"value": "irrelevant"}]
    result = compute_majority_vote(labels, "value")
    assert result is not None
    assert result["value"] == "relevant"
    assert result["_count"] == 2


def test_majority_vote_empty() -> None:
    result = compute_majority_vote([], "value")
    assert result is None


def test_agreement_score_full_agreement() -> None:
    labels = [{"value": "relevant"}, {"value": "relevant"}]
    score = compute_agreement_score(labels, "value")
    assert score == 1.0


def test_agreement_score_no_agreement() -> None:
    labels = [{"value": "relevant"}, {"value": "irrelevant"}]
    score = compute_agreement_score(labels, "value")
    assert score == 0.5
