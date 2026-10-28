from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..utils import maturity_level

router = APIRouter(prefix="/reports", tags=["reports"])

NEXT_STEPS = {
    "support": ["Use AI to draft first replies, then edit", "Summarise long ticket threads before escalating", "Never paste customer details into public chatbots"],
    "engineering": ["Use a code assistant for tests and refactors", "Review every AI suggestion before merging", "Keep secrets and customer data out of prompts"],
    "sales": ["Draft outreach emails with AI and personalise them", "Summarise call notes into CRM updates", "Check AI-written claims before sending"],
    "manager": ["Agree an AI usage policy with your team", "Pick one workflow per quarter to improve with AI", "Track time saved, not tool licences"],
}


RECOMMENDED_ARTICLES = {
    "customer_data_shared": {
        "title": "Protecting Sensitive PII When Prompting LLMs: Practical Guide",
        "source": "Towards Data Science",
        "url": "https://towardsdatascience.com/protecting-sensitive-data-in-llm-applications-a-practical-guide",
    },
    "confidential_data_shared": {
        "title": "Enterprise IP & Confidentiality Safeguards with Generative AI",
        "source": "Medium / Tech & Law",
        "url": "https://medium.com/swlh/intellectual-property-and-generative-ai",
    },
    "unreviewed_output": {
        "title": "Human-in-the-Loop: Review Checklists for AI-Generated Outputs",
        "source": "Harvard Business Review",
        "url": "https://hbr.org/2023/11/managing-the-risks-of-generative-ai",
    },
    "policy_unaware": {
        "title": "Understanding Your Company's AI Acceptable Use Policy",
        "source": "Medium / Better Programming",
        "url": "https://medium.com/better-programming/practical-ai-policy-for-tech-teams",
    },
}

ROLE_MASTERY_ARTICLES = {
    "engineering": [
        {
            "title": "Advanced Prompt Engineering & Agentic Workflows for Senior Developers",
            "source": "Towards Data Science",
            "url": "https://towardsdatascience.com/advanced-prompt-engineering-for-developers",
        },
        {
            "title": "Evaluating LLM System Reliability & Benchmark Design",
            "source": "Medium / Towards AI",
            "url": "https://medium.com/towards-artificial-intelligence/evaluating-llm-applications",
        },
    ],
    "support": [
        {
            "title": "AI Copilots in Customer Experience: Scaling Empathy and Rapid Resolution",
            "source": "Harvard Business Review",
            "url": "https://hbr.org/2023/04/how-generative-ai-changes-customer-service",
        },
        {
            "title": "Building Context-Aware Support Workflows with Internal AI Tools",
            "source": "Medium / CX Today",
            "url": "https://medium.com/swlh/generative-ai-in-customer-support-playbook",
        },
    ],
    "sales": [
        {
            "title": "Hyper-Personalization at Scale: Ethical AI Outreach That Converts",
            "source": "Harvard Business Review",
            "url": "https://hbr.org/2023/09/how-ai-is-transforming-sales",
        },
        {
            "title": "AI in Deal Intelligence & Pipeline Acceleration",
            "source": "Medium / Enterprise Strategy",
            "url": "https://medium.com/towards-data-science/ai-powered-sales-intelligence",
        },
    ],
    "manager": [
        {
            "title": "Leading Through the AI Transition: Managing Culture, Upskilling, & ROI",
            "source": "Harvard Business Review",
            "url": "https://hbr.org/2024/01/how-leaders-can-navigate-generative-ai",
        },
        {
            "title": "Establishing Enterprise AI Governance: Frameworks & Best Practices",
            "source": "World Economic Forum",
            "url": "https://www.weforum.org/agenda/2024/03/responsible-ai-leadership/",
        },
    ],
}


@router.get("/me")
def my_report(m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    rows = db.query(models.Response).filter_by(membership_id=m.id).all()
    scores = [r.score for r in rows if r.score is not None]
    avg = sum(scores) / len(scores) if scores else None
    flags = sorted({f for r in rows for f in (r.flags or [])})

    # 1. First add targeted remediation articles for any detected risk flags
    articles = [RECOMMENDED_ARTICLES[f] for f in flags if f in RECOMMENDED_ARTICLES]

    # 2. For high performers (or users without flagged risks), provide advanced mastery & growth articles
    role_guides = ROLE_MASTERY_ARTICLES.get(m.job_role, ROLE_MASTERY_ARTICLES["manager"])
    for guide in role_guides:
        if guide not in articles:
            articles.append(guide)

    # Limit to top 3 relevant articles so employee isn't overwhelmed
    articles = articles[:3]

    return {

        "name": m.user.name,
        "organization": m.org.name,
        "answered": len(rows),
        "average_score": round(avg, 2) if avg is not None else None,
        "level": maturity_level(avg),
        "risks": flags,
        "next_steps": NEXT_STEPS.get(m.job_role, NEXT_STEPS["manager"]),
        "recommended_articles": articles,
    }



@router.delete("/me")
def delete_my_data(m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    """Allows an employee to permanently delete their diagnostic answers and personal report."""
    deleted = db.query(models.Response).filter_by(membership_id=m.id).delete()
    db.commit()
    return {"deleted": True, "count": deleted}

