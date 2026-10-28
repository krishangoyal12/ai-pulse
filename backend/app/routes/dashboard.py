from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..utils import maturity_level

router = APIRouter(prefix="/dashboard", tags=["dashboard"])




RISK_PLAYBOOKS = {
    "customer_data_shared": {
        "title": "Customer Data Protection & Redaction Protocol",
        "severity": "Critical",
        "legal_implication": "Immediate exposure under GDPR / DPDP. Prompts containing customer PII entered into commercial models may be logged or retained.",
        "immediate_action": "Issue an immediate directive prohibiting customer identifiable data (PII) in public AI tools. Implement client-side redaction guidelines.",
        "systemic_fix": "Deploy an enterprise LLM gateway with automated PII masking and zero-data-retention agreements.",
        "articles": [
            {
                "title": "Protecting Sensitive Data & PII in Large Language Models (Towards Data Science)",
                "url": "https://towardsdatascience.com/protecting-sensitive-data-in-llm-applications-a-practical-guide",
                "source": "Towards Data Science",
            },
            {
                "title": "Enterprise AI Guardrails: Automated Client-Side Redaction & Tokenization (Medium)",
                "url": "https://medium.com/towards-artificial-intelligence/enterprise-ai-guardrails-data-masking",
                "source": "Medium / AI Infosec",
            },
            {
                "title": "NIST AI Risk Management Framework (NIST AI RMF 1.0)",
                "url": "https://www.nist.gov/itl/ai-risk-management-framework",
                "source": "NIST Guidelines",
            },
        ],
    },
    "confidential_data_shared": {
        "title": "Intellectual Property & Confidentiality Safeguards",
        "severity": "High",
        "legal_implication": "Breach of trade secrets and confidentiality agreements by uploading internal strategy, financial, or source code data.",
        "immediate_action": "Audit which cloud AI services are accessed via company SSO; circulate a list of non-approved consumer AI tools.",
        "systemic_fix": "Negotiate enterprise vendor contracts that contractually guarantee prompt data is not used for model retraining.",
        "articles": [
            {
                "title": "Intellectual Property & Generative AI: How Vendors Handle Prompt Data (Medium)",
                "url": "https://medium.com/swlh/intellectual-property-and-generative-ai",
                "source": "Medium / Tech & Law",
            },
            {
                "title": "OWASP Top 10 for LLM: LLM06 Sensitive Information Disclosure",
                "url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
                "source": "OWASP Foundation",
            },
        ],
    },
    "unreviewed_output": {
        "title": "Human-in-the-Loop Verification Standard",
        "severity": "High",
        "legal_implication": "Liability for hallucinated, biased, or copyrighted content in deliverables and external communications.",
        "immediate_action": "Establish a mandatory 'Review Before Dispatch' rule: every AI-assisted email, contract, or code commit must be verified by a human.",
        "systemic_fix": "Integrate AI verification checklists into existing code review and content sign-off workflows.",
        "articles": [
            {
                "title": "Managing the Risks of Generative AI: Human-in-the-Loop Oversight (Harvard Business Review)",
                "url": "https://hbr.org/2023/11/managing-the-risks-of-generative-ai",
                "source": "Harvard Business Review",
            },
            {
                "title": "Peer Review Checklists for AI-Generated Code & Content (Towards Data Science)",
                "url": "https://towardsdatascience.com/reviewing-ai-generated-code-checklist",
                "source": "Towards Data Science",
            },
        ],
    },
    "policy_unaware": {
        "title": "AI Policy Training & Acceptable Use Governance",
        "severity": "Medium",
        "legal_implication": "Regulatory non-compliance and employee confusion regarding permissible AI tools and workflows.",
        "immediate_action": "Publish a 1-page 'Acceptable AI Use Policy' cheat sheet to all staff.",
        "systemic_fix": "Make annual AI Governance & Responsible Use training mandatory during onboarding.",
        "articles": [
            {
                "title": "Writing an AI Acceptable Use Policy Employees Will Actually Follow (Medium)",
                "url": "https://medium.com/better-programming/practical-ai-policy-for-tech-teams",
                "source": "Medium / Better Programming",
            },
            {
                "title": "EU AI Act Compliance: What Enterprise Leaders Need to Know (World Economic Forum)",
                "url": "https://www.weforum.org/agenda/2024/03/eu-ai-act-what-it-means-for-business/",
                "source": "World Economic Forum",
            },
        ],
    },
}


def _calculate_confidence(participation_rate: float, total_responded: int) -> dict:
    """Calculate statistical confidence rating based on sample size and response rate."""
    if total_responded == 0:
        return {
            "level": "Insufficient Data",
            "score_validity": "None",
            "description": "No responses submitted yet. Await diagnostic submissions before taking action.",
            "color": "#98a2b3",
        }
    if participation_rate >= 70 or total_responded >= 30:
        return {
            "level": "High Statistical Confidence",
            "score_validity": "Authoritative",
            "description": "Representative sample. Scores accurately reflect operational reality; suitable for executive resource allocation.",
            "color": "#027a48",
        }
    if participation_rate >= 40 or total_responded >= 10:
        return {
            "level": "Moderate Statistical Confidence",
            "score_validity": "Directional",
            "description": "Sample indicates emerging trends, but small department gaps remain. Use for directional planning.",
            "color": "#b54708",
        }
    return {
        "level": "Low Statistical Confidence",
        "score_validity": "Preliminary",
        "description": "Sample is currently non-representative. High risk of selection bias; survey completion campaigns recommended.",
        "color": "#b42318",
    }


@router.get("")
def org_dashboard(org_id: int, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    if m.role != "admin":
        raise HTTPException(403, "Admins only")
    if m.org_id != org_id:
        raise HTTPException(403, "Cannot view another organization's dashboard")

    org = db.get(models.Organization, org_id)
    if not org:

        raise HTTPException(404, "Organization not found")

    members = db.query(models.Membership).filter_by(org_id=org_id).all()
    departments = []
    all_flags = {}

    other_employees = 0
    other_responded = 0
    other_scores = []
    masked_departments_details = []

    total_org_employees = len(members)
    total_org_responded = 0

    for dept in org.departments:
        dept_members = [x for x in members if x.department_id == dept.id]
        scores = []
        responded = 0
        for dm in dept_members:
            rows = db.query(models.Response).filter_by(membership_id=dm.id).all()
            if rows:
                responded += 1
            for r in rows:
                if r.score is not None:
                    scores.append(r.score)
                for f in r.flags or []:
                    all_flags[f] = all_flags.get(f, 0) + 1

        total_org_responded += responded

        if responded >= 5:
            avg = sum(scores) / len(scores) if scores else None
            rate = round((responded / len(dept_members)) * 100) if dept_members else 0
            departments.append({
                "department": dept.name,
                "employees": len(dept_members),
                "responded": responded,
                "participation_rate": rate,
                "average_score": round(avg, 2) if avg is not None else None,
                "level": maturity_level(avg),
                "is_masked": False,
                "responses_needed_to_unmask": 0,
            })
        else:
            # Client requirement: group departments with < 5 respondents under "Other teams"
            other_employees += len(dept_members)
            other_responded += responded
            other_scores.extend(scores)
            needed = max(0, 5 - responded)
            masked_departments_details.append({
                "department": dept.name,
                "employees": len(dept_members),
                "responded": responded,
                "responses_needed_to_unmask": needed,
            })

    if other_employees > 0:
        if other_scores:
            other_avg = sum(other_scores) / len(other_scores)
            other_avg_score = round(other_avg, 2)
            other_lvl = maturity_level(other_avg)
        else:
            other_avg_score = None
            other_lvl = "Not assessed"

        other_rate = round((other_responded / other_employees) * 100) if other_employees else 0
        departments.append({
            "department": "Other teams",
            "employees": other_employees,
            "responded": other_responded,
            "participation_rate": other_rate,
            "average_score": other_avg_score,
            "level": other_lvl,
            "is_masked": True,
            "masked_teams": masked_departments_details,
        })

    # Overall org participation & confidence
    org_participation_rate = round((total_org_responded / total_org_employees) * 100) if total_org_employees > 0 else 0
    confidence_data = _calculate_confidence(org_participation_rate, total_org_responded)

    return {
        "organization": org.name,
        "total_headcount": total_org_employees,
        "total_responded": total_org_responded,
        "participation_rate": org_participation_rate,
        "statistical_confidence": confidence_data,
        "departments": departments,
        "top_risks": sorted(all_flags.items(), key=lambda kv: -kv[1])[:5],
    }


@router.get("/remediation-plan")
def get_remediation_plan(org_id: int, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    """Generates an executive remediation playbook and action brief for leadership."""
    if m.role != "admin":
        raise HTTPException(403, "Admins only")
    if m.org_id != org_id:
        raise HTTPException(403, "Cannot view another organization's remediation plan")

    dashboard_data = org_dashboard(org_id=org_id, m=m, db=db)

    detected_risks = dashboard_data["top_risks"]
    departments = dashboard_data["departments"]

    # Build targeted action items based on active risks
    action_items = []
    for flag, count in detected_risks:
        playbook = RISK_PLAYBOOKS.get(flag, {
            "title": f"Governance Standard for {flag.replace('_', ' ').title()}",
            "severity": "Medium",
            "legal_implication": "Operational risk identified from employee self-reporting.",
            "immediate_action": "Conduct targeted review with department leads.",
            "systemic_fix": "Add verification controls in relevant workflows.",
        })
        action_items.append({
            "flag": flag,
            "occurrences": count,
            **playbook,
        })

    # Identify priority focus departments
    priority_departments = []
    for d in departments:
        if d.get("is_masked"):
            continue
        if d.get("average_score") is not None and d.get("average_score") < 3.0:
            priority_departments.append({
                "department": d["department"],
                "score": d["average_score"],
                "level": d["level"],
                "focus": "Fundamental AI safety training and tool onboarding needed.",
            })

    # Generate 3-phase roadmap
    roadmap = {
        "phase_1_immediate_7d": [
            "Executive Memo: Issue clarifying acceptable AI tools and prohibiting unvetted customer PII entry.",
            "Approve an initial vetted whitelist of tools with enterprise data-retention guarantees.",
        ],
        "phase_2_systemic_30d": [
            "Roll out department-specific prompt guidelines (especially for engineering and customer support).",
            "Establish Human-in-the-Loop peer review requirements for all AI-generated deliverables.",
        ],
        "phase_3_governance_90d": [
            "Establish an AI Governance Working Group (HR, Legal, Tech Lead).",
            "Institute recurring quarterly diagnostic pulses to benchmark progress against this baseline.",
        ],
    }

    if any(item["flag"] == "customer_data_shared" for item in action_items):
        roadmap["phase_1_immediate_7d"].insert(0, "URGENT: Enforce client-side masking & review all customer data ingestion points.")

    return {
        "organization": dashboard_data["organization"],
        "generated_for": m.user.name,
        "executive_summary": {
            "total_headcount": dashboard_data["total_headcount"],
            "total_responded": dashboard_data["total_responded"],
            "participation_rate": f"{dashboard_data['participation_rate']}%",
            "statistical_confidence": dashboard_data["statistical_confidence"]["level"],
            "validity_rating": dashboard_data["statistical_confidence"]["score_validity"],
            "critical_risk_count": len([i for i in action_items if i.get("severity") in ("Critical", "High")]),
        },
        "action_playbooks": action_items,
        "priority_departments": priority_departments,
        "roadmap": roadmap,
    }

