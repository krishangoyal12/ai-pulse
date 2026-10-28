from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..utils import maturity_level

router = APIRouter(prefix="/dashboard", tags=["dashboard"])



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

        if responded >= 5:
            avg = sum(scores) / len(scores) if scores else None
            departments.append({
                "department": dept.name,
                "employees": len(dept_members),
                "responded": responded,
                "average_score": round(avg, 2) if avg is not None else None,
                "level": maturity_level(avg),
            })
        else:
            # Client requirement: group departments with < 5 respondents under "Other teams"
            other_employees += len(dept_members)
            other_responded += responded
            other_scores.extend(scores)

    if other_employees > 0:
        if other_scores:
            other_avg = sum(other_scores) / len(other_scores)
            other_avg_score = round(other_avg, 2)
            other_lvl = maturity_level(other_avg)

        else:
            other_avg_score = None
            other_lvl = "Not assessed"

        departments.append({
            "department": "Other teams",
            "employees": other_employees,
            "responded": other_responded,
            "average_score": other_avg_score,
            "level": other_lvl,
        })



    return {
        "organization": org.name,
        "departments": departments,
        "top_risks": sorted(all_flags.items(), key=lambda kv: -kv[1])[:5],
    }
