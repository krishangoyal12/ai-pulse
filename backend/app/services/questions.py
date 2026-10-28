import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "questions.json")


_CACHE = {}


def load_questions():
    with open(_PATH) as f:
        return json.load(f)


def get_active_question_bank(job_role: str = "all", seniority: str = "mid") -> dict[str, dict]:
    """Returns a lookup dictionary of question_id -> question for validation during submission."""
    # Start with baseline questions
    bank = {q["id"]: q for q in load_questions()}
    # Add any cached dynamic questions
    for role_suite in _CACHE.values():
        for q in role_suite:
            bank[q["id"]] = q
    return bank


SENIORITY_RANKS = {
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "lead": 4,
}


def questions_for(job_role: str, seniority: str):
    """Returns questions. In AI_MODE=live, dynamically generates and caches a role-tailored suite via LLM."""
    from ..config import AI_MODE

    if AI_MODE == "live":
        cache_key = f"{job_role}:{seniority}"
        if cache_key in _CACHE:
            return _CACHE[cache_key]

        from .llm import generate_role_diagnostic_suite
        dynamic_suite = generate_role_diagnostic_suite(job_role, seniority)
        if dynamic_suite:
            _CACHE[cache_key] = dynamic_suite
            return dynamic_suite

    # Fallback to static questions (for mock mode or when LLM is unavailable)
    result = []
    user_rank = SENIORITY_RANKS.get(seniority, 1)
    for q in load_questions():
        if q["roles"] != ["all"] and job_role not in q["roles"]:
            continue
        min_rank = SENIORITY_RANKS.get(q.get("min_seniority", "junior"), 1)
        if user_rank < min_rank:
            continue
        result.append(q)
    return result


