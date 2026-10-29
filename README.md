# AI Pulse: Enterprise AI Adoption Diagnostic & Governance Platform

AI Pulse is an enterprise platform helping organizations measure, govern, and improve employee AI maturity across teams.

This codebase has been audited, secured, and extended from a legacy prototype to an enterprise client-ready deployment for Northwind Logistics and Bluepeak Retail.

---

## 1. Quick Start & Local Run

### Prerequisites
- Python 3.12+
- Node.js 18+

### Backend Setup
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python -m app.seed          # Seeds demo users (Password: pulse123)
uvicorn app.main:app --reload
```
Runs at: `http://localhost:8000` (Swagger docs at `/docs`)

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Runs at: `http://localhost:5173`

### Run Automated Tests
```bash
cd backend
.venv\Scripts\python -m pytest
```
**19 passed** across `test_api.py`, `test_questions.py`, and `test_scoring.py`.

---

## 2. Demo Accounts (Password: `pulse123`)

| Email | Role | Organization(s) | Key Capability / Flow |
| :--- | :--- | :--- | :--- |
| `asha@northwind.test` | Admin | Northwind Logistics | Executive Dashboard, Coverage Confidence, Remediation Playbooks |
| `meera@bluepeak.test` | Admin | Bluepeak Retail | Isolated Tenant Admin Dashboard |
| `ravi@consult.test` | Multi-Org | Both | Cross-Tenant Isolation: Employee at Northwind, Admin at Bluepeak |
| `priya@northwind.test` | Employee | Northwind Logistics | Customer Support Diagnostic, Risk Detection, Right to Delete Data |
| `dev@northwind.test` | Employee | Northwind Logistics | Engineering Lead Diagnostic, Seniority Question Hierarchy |

---

## 3. Responses to the Four Brief Evaluation Questions

### Question 1: What was wrong with the codebase, what was fixed, and what was deliberately left?

#### What was wrong & fixed:
1. **Critical Tenant IDOR & Authorization Bypass (`dashboard.py`):** The endpoint accepted `?org_id=` from query parameters without verifying that the requesting administrator belonged to that organization. Admins could view other companies' confidential scores. **Fixed:** Enforced `m.org_id != org_id` check (HTTP 403 Forbidden).
2. **Forged JWT Token Generation (`auth_routes.py`):** In `/auth/select-org`, any authenticated user could pass an arbitrary `org_id` and receive a signed JWT with admin claims for an organization they didn't belong to. **Fixed:** Verified `(user_id, org_id)` against the `Membership` table before issuing tokens.
3. **Flawed Seniority Comparison (`questions.py`):** Evaluated rank via string comparison (`"lead" < "senior"`), which evaluated to `True` in ASCII, skipping lead engineers from senior questions. **Fixed:** Implemented explicit integer rank mapping (`junior: 1`, `mid: 2`, `senior: 3`, `lead: 4`).
4. **Conflicting Maturity Rating Scales (`utils.py` vs `dashboard.py`):** Reports and dashboards used conflicting cutoffs (e.g. score of 3.6 was Practitioner on report, but Leader on dashboard). **Fixed:** Unified under a single authoritative scale in `utils.py`.
5. **Mathematical Averaging Bug (`dashboard.py`):** Average scores were calculated by dividing by total department headcount rather than completed responses, unfairly penalizing teams with low turnout. **Fixed:** Computed true arithmetic mean based on actual respondent scores.
6. **Survey Re-submission Duplication (`diagnostic.py`):** Re-taking the survey appended new rows rather than replacing prior answers, inflating scores and distorting participation. **Fixed:** Prior responses are cleared before saving new answers.
7. **Crash on Model Output / JSON Injection (`scoring.py`):** Naked `json.loads()` crashed FastAPI with 500 errors when models returned markdown code fences, non-JSON text, or unvetted risk tags. **Fixed:** Multi-stage regex sanitization, code fence stripping, score clamping (1–5), and rubric flag whitelisting with graceful fallback.
8. **Wildcard Production CORS (`main.py`):** Used `allow_origins=["*"]` with `allow_credentials=True`. **Fixed:** Replaced with explicit `ALLOWED_ORIGINS` environment whitelist.

#### What was deliberately left:
- **SQLite Database:** For an assessment and single-container prototype, SQLite provides zero-dependency, instantaneous local testing and auto-seeding. In production with horizontal scaling, switching to PostgreSQL requires only updating `DATABASE_URL`.
- **JWT in LocalStorage:** While HTTP-only secure cookies provide superior XSS resistance, LocalStorage was retained for frontend architecture simplicity while securing endpoints with strict server-side claims validation.

---

### Question 2: How Northwind HR's requests were handled & questions to ask them next

#### How the requests were handled:
1. **Client Request #1 (k-Anonymity Threshold $n < 5$):**
   - Implemented strict suppression: Any department with fewer than 5 respondents (e.g. Sales, Support, HR in seed data) is hidden from isolated display.
   - Grouped under `"Other teams"` with a pooled, mathematically weighted average score (`sum(all_scores) / len(all_scores)`).
   - Displayed with a clear `🔒 Protected Group` badge on the dashboard.
2. **Client Request #2 (Right to Delete Data Immediately):**
   - Added `DELETE /reports/me` in `reports.py` and connected it to a confirmation dialog in `Report.jsx`.
   - Execution is synchronous in the database (`db.commit()`), immediately removing responses from all leadership aggregate scores and setting personal report state to `answered: 0`.

#### Strategic questions to ask Northwind HR next:
1. *"When a team crosses from 4 to 5 respondents mid-quarter, should their score become visible immediately, or only when a survey cohort closes to prevent tracking who just submitted?"*
2. *"When employees exercise their Right to Delete, should their answers be removed from historical aggregate snapshots, or should anonymous department benchmarks be frozen at survey close?"*
3. *"Would leadership prefer department managers to view their own team's metrics once unmasked, or remain strictly restricted to central HR admins?"*

---

### Question 3: One feature of your own — What problem it solves and why you chose it

#### Feature: Executive AI Readiness Health & Remediation Action Center
- **The Problem It Solves:**
  1. *The "False Confidence" Problem:* Raw numeric scores (e.g. `3.4 / 5.0`) give leaders false confidence without knowing whether sample sizes are statistically representative.
  2. *The "Action Void" Problem:* Flagging abstract risks like `customer_data_shared` creates legal awareness but gives HR zero actionable playbooks on **what policies, controls, or trainings to implement next week**.
- **What Was Built:**
  - **Survey Coverage & Statistical Validity Meter:** Dynamically computes response coverage % and grades data reliability (*Authoritative* $\ge 70\%$, *Directional* $40\text{–}69\%$, *Preliminary* $< 40\%$).
  - **Small-Team Privacy Nudge Tool:** For teams grouped under `"Other teams"`, displays how many more responses are needed to unmask them safely, with a 1-click **"📢 Nudge Team (+X needed)"** copying a professional reminder email to the clipboard.
  - **Executive Remediation Plan Generator (`GET /dashboard/remediation-plan`):** A board-ready modal translating detected risks into concrete legal exposure assessments (GDPR, trade secrets, copyright), a 3-phase 30-60-90 day roadmap, and **curated authoritative reading articles** (Towards Data Science, Harvard Business Review, NIST, OWASP). Includes **🖨️ Print / PDF** and **Copy Markdown** export for board decks.
- **Why Chosen:** "Small and sharp beats big and generic." It directly bridges the gap between diagnostic telemetry and executive action.

---

### Question 4: How AI tools were used, where they helped, and where they got it wrong

#### Where AI helped:
- Rapid generation of test assertions and realistic mock seed datasets.
- Accelerated regex design for sanitizing malformed JSON blocks with markdown code fences.
- Brainstorming comprehensive risk mitigation playbooks aligned with the NIST AI RMF and ISO 42001.

#### Where AI got it wrong & human correction was required:
- **Rate Limit Blindspots (HTTP 429 on Groq):** LLMs originally generated an overly verbose 4-question prompt with lengthy schemas, which caused Groq's free tier to throw HTTP 429 Too Many Requests errors. A human engineer identified the token limit bottleneck, streamlined the prompt schema, and added `max_tokens: 1200` to ensure resilient execution.
- **Flawed Arithmetic in Aggregation:** Early AI-suggested code attempted to compute the pooled `"Other teams"` score by averaging the department averages (`sum(dept_avgs) / len(depts)`), which is mathematically incorrect for unequal sample sizes. Replaced with true aggregate mean over all response scores.
- **Overly Generic Risk Flagging:** Early LLM outputs hallucinated custom flags like `["careless_worker", "unauthorized_tool"]`. Corrected by enforcing strict whitelist filtering against the established rubric.