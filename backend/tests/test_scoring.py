import pytest
from app.services import scoring


def test_score_open_answer_markdown_fences(monkeypatch):
    canned = '```json\n{"score": 4, "reason": "Good thoughtful usage.", "flags": []}\n```'
    monkeypatch.setattr(scoring.llm, "score_answer", lambda q, a: canned)

    res = scoring.score_open_answer("How do you use AI?", "I use it for emails.")
    assert res["score"] == 4
    assert res["reason"] == "Good thoughtful usage."
    assert res["flags"] == []


def test_score_open_answer_word_score(monkeypatch):
    canned = '{"score": "four", "reason": "Regular usage.", "flags": ["unreviewed_output"]}'
    monkeypatch.setattr(scoring.llm, "score_answer", lambda q, a: canned)

    res = scoring.score_open_answer("How do you use AI?", "Daily.")
    assert res["score"] == 4
    assert res["flags"] == ["unreviewed_output"]


def test_score_open_answer_out_of_bounds_and_hallucinated_flags(monkeypatch):
    canned = '{"score": 9, "reason": "Advanced.", "flags": ["probably_lying", "customer_data_shared"]}'
    monkeypatch.setattr(scoring.llm, "score_answer", lambda q, a: canned)

    res = scoring.score_open_answer("How do you use AI?", "Workflows.")
    # Clamped to 5
    assert res["score"] == 5
    # "probably_lying" filtered out, "customer_data_shared" retained
    assert res["flags"] == ["customer_data_shared"]


def test_score_open_answer_invalid_json_fallback(monkeypatch):
    canned = "I think this answer deserves 5 stars! (not json)"
    monkeypatch.setattr(scoring.llm, "score_answer", lambda q, a: canned)

    # Must not raise JSONDecodeError or crash
    res = scoring.score_open_answer("How do you use AI?", "Random text.")
    assert isinstance(res["score"], int)
    assert 1 <= res["score"] <= 5
    assert isinstance(res["flags"], list)
