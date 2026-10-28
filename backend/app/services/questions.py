import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "questions.json")


def load_questions():
    with open(_PATH) as f:
        return json.load(f)


SENIORITY_RANKS = {
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "lead": 4,
}


def questions_for(job_role: str, seniority: str):
    """Common questions for everyone + questions for this job role, filtered by seniority."""
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

