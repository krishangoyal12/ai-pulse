from tests.conftest import login


def test_login_lists_organizations(client):
    _, data = login(client, "ravi@consult.test")
    names = {o["org_name"] for o in data["organizations"]}
    assert names == {"Northwind Logistics", "Bluepeak Retail"}


def test_employee_sees_questions(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.get("/diagnostic/questions", headers=headers)
    assert r.status_code == 200
    assert any(q["id"] == "sup-drafts" for q in r.json())


def test_admin_dashboard(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    depts = r.json()["departments"]
    # All seeded departments have < 5 respondents, so they are grouped under 'Other teams'
    assert len(depts) == 1
    assert depts[0]["department"] == "Other teams"
    assert depts[0]["responded"] == 2
    assert depts[0]["average_score"] == 3.25
    assert depts[0]["level"] == "Practitioner"



def test_admin_cannot_see_other_org(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    r = client.get("/dashboard?org_id=2", headers=headers)
    assert r.status_code == 403


def test_select_org_rejects_unauthorized_org(client):
    # Priya only belongs to Northwind (org_id 1), not Bluepeak (org_id 2)
    r = client.post("/auth/login", json={"email": "priya@northwind.test", "password": "pulse123"})
    token = r.json()["token"]
    res = client.post(
        "/auth/select-org",
        json={"org_id": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_dashboard_groups_small_teams_into_other_teams(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    depts = {d["department"]: d for d in r.json()["departments"]}
    # Small teams must NOT appear individually
    assert "Sales" not in depts
    assert "Support" not in depts
    # Instead, pooled into "Other teams" with combined average
    assert "Other teams" in depts
    assert depts["Other teams"]["responded"] == 2
    assert depts["Other teams"]["average_score"] == 3.25


def test_submitting_twice_replaces_responses(client):
    headers, _ = login(client, "dev@northwind.test", "Northwind Logistics")
    payload = {
        "answers": [
            {"question_id": "common-freq", "answer": "Daily"},
            {"question_id": "common-policy", "answer": "Yes, I've read it"},
        ]

    }
    # First submission
    r1 = client.post("/diagnostic/submit", json=payload, headers=headers)
    assert r1.status_code == 200

    report1 = client.get("/reports/me", headers=headers).json()
    assert report1["answered"] == 2

    # Second submission (retaking with 1 answer)
    payload2 = {
        "answers": [
            {"question_id": "common-freq", "answer": "Never"},
        ]
    }
    r2 = client.post("/diagnostic/submit", json=payload2, headers=headers)
    assert r2.status_code == 200

    report2 = client.get("/reports/me", headers=headers).json()
    # Must be 1, not 3 (prior answers cleared, not duplicated)
    assert report2["answered"] == 1


def test_delete_my_data_clears_report_and_dashboard(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    # Verify Priya currently has responses
    report_before = client.get("/reports/me", headers=headers).json()
    assert report_before["answered"] > 0

    # Priya deletes her data
    del_res = client.delete("/reports/me", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # Report now reflects zero responses
    report_after = client.get("/reports/me", headers=headers).json()
    assert report_after["answered"] == 0
    assert report_after["average_score"] is None
    assert report_after["level"] == "Not assessed"





