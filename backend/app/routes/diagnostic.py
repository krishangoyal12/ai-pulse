from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..services.questions import questions_for, load_questions
from ..services.scoring import score_open_answer

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


class AnswerIn(BaseModel):
    question_id: str
    answer: str


class SubmitIn(BaseModel):
    answers: list[AnswerIn]


@router.get("/questions")
def get_questions(m: models.Membership = Depends(current_membership)):
    qs = questions_for(m.job_role, m.seniority)
    return [
        {k: v for k, v in q.items() if k != "points"} | (
            {"options": [o["text"] for o in q["options"]]} if q["type"] == "mcq" else {}
        )
        for q in qs
    ]


class DraftQuestionIn(BaseModel):
    job_role: str = "engineering"
    seniority: str = "mid"
    topic: str = "security and productivity"


@router.post("/draft-question")
def draft_question(body: DraftQuestionIn, m: models.Membership = Depends(current_membership)):
    """Admin feature: Uses AI to draft a new diagnostic assessment question for any role."""
    from ..services.llm import draft_diagnostic_question
    return draft_diagnostic_question(body.job_role, body.seniority, body.topic)



@router.post("/submit")
def submit(body: SubmitIn, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    from ..services.questions import get_active_question_bank
    bank = get_active_question_bank(m.job_role, m.seniority)

    # Clear prior responses for this user so re-submitting replaces old answers
    db.query(models.Response).filter_by(membership_id=m.id).delete()
    for a in body.answers:
        q = bank.get(a.question_id)
        if not q:
            raise HTTPException(400, f"Unknown question {a.question_id}")
        resp = models.Response(membership_id=m.id, question_id=q["id"], answer=a.answer)
        if q["type"] == "mcq":
            option = next((o for o in q["options"] if o["text"] == a.answer), None)
            if option is None:
                raise HTTPException(400, f"Invalid option for {q['id']}")
            resp.score = option["points"]
            # Infer risk flags from multiple-choice choices with low safety scores
            mcq_flags = []
            if option["points"] <= 2:
                qid = q["id"].lower()
                if "privacy" in qid or "data" in qid:
                    mcq_flags.append("customer_data_shared")
                elif "review" in qid:
                    mcq_flags.append("unreviewed_output")
                elif "policy" in qid:
                    mcq_flags.append("policy_unaware")
            resp.flags = mcq_flags
        else:
            result = score_open_answer(q["text"], a.answer)
            resp.score = result["score"]
            resp.reason = result["reason"]
            resp.flags = result["flags"]
        db.add(resp)
    db.commit()
    return {"saved": len(body.answers)}



