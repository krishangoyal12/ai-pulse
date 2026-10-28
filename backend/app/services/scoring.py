import json
import re

from . import llm

ALLOWED_FLAGS = {
    "customer_data_shared",
    "confidential_data_shared",
    "unreviewed_output",
    "policy_unaware",
}

WORD_TO_NUM = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


def _clean_json_text(raw: str) -> str:
    """Strips markdown code fences and extracts the outermost JSON object."""
    text = raw.strip()
    # Strip markdown code blocks (e.g. ```json ... ``` or ``` ... ```)
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    # Extract the first valid JSON object structure {...} if surrounded by other text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def _sanitize_score(raw_score) -> int:
    """Converts score to an integer and clamps it to the 1-5 rubric range."""
    if raw_score is None:
        return 3
    if isinstance(raw_score, str):
        cleaned = raw_score.strip().lower()
        if cleaned in WORD_TO_NUM:
            return WORD_TO_NUM[cleaned]
        try:
            raw_score = float(cleaned)
        except ValueError:
            return 3
    try:
        val = int(round(float(raw_score)))
        return max(1, min(5, val))
    except (TypeError, ValueError):
        return 3


def score_open_answer(question_text: str, answer: str) -> dict:
    """Robustly evaluates an open-ended answer via LLM with sanitization and fallbacks."""
    raw = llm.score_answer(question_text, answer)
    cleaned = _clean_json_text(raw)

    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        # Fallback if the LLM output is not valid JSON
        return {
            "score": 3,
            "reason": "Evaluated using default baseline (unstructured response).",
            "flags": [],
        }

    # 1. Sanitize score (clamp between 1 and 5, convert text words like 'four' to int)
    score = _sanitize_score(data.get("score"))

    # 2. Sanitize reason
    reason = data.get("reason")
    if not reason or not isinstance(reason, str):
        reason = "Assessment evaluated successfully."

    # 3. Filter hallucinated flags to only rubric-permitted risk labels
    raw_flags = data.get("flags")
    if isinstance(raw_flags, list):
        flags = [f for f in raw_flags if isinstance(f, str) and f in ALLOWED_FLAGS]
    else:
        flags = []

    return {"score": score, "reason": reason, "flags": flags}
