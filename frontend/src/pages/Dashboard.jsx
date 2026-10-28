import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Dashboard({ org }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [nudgeNotice, setNudgeNotice] = useState(null);

  // Executive Remediation Plan Modal State
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [planData, setPlanData] = useState(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [copiedMarkdown, setCopiedMarkdown] = useState(false);

  useEffect(() => {
    setLoading(true);
    api(`/dashboard?org_id=${org.org_id}`)
      .then((res) => {
        setData(res);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || "Failed to load dashboard");
      })
      .finally(() => setLoading(false));
  }, [org]);

  function handleOpenRemediationPlan() {
    setShowPlanModal(true);
    setPlanLoading(true);
    api(`/dashboard/remediation-plan?org_id=${org.org_id}`)
      .then((res) => {
        setPlanData(res);
      })
      .catch((err) => {
        console.error("Failed to load remediation plan", err);
      })
      .finally(() => setPlanLoading(false));
  }

  function handleCopyNudge(deptName, needed) {
    const text = `Hi ${deptName} Team,\n\nWe are conducting our quarterly AI Readiness & Safety diagnostic. Your department currently needs ${needed} more respondent(s) to reach statistical validity and unlock department-specific insights.\n\nPlease take 5 minutes to complete your assessment: ${window.location.origin}\n\nThank you,\n${data?.organization || "HR Leadership"}`;
    navigator.clipboard.writeText(text);
    setNudgeNotice(`Copied reminder email template for ${deptName} to clipboard!`);
    setTimeout(() => setNudgeNotice(null), 4000);
  }

  function handleCopyPlanMarkdown() {
    if (!planData) return;
    const md = `# Executive AI Remediation Plan: ${planData.organization}
Generated for: ${planData.generated_for}
Date: ${new Date().toLocaleDateString()}

## 1. Executive Summary
- Total Headcount: ${planData.executive_summary.total_headcount}
- Completed Diagnostic: ${planData.executive_summary.total_responded} (${planData.executive_summary.participation_rate})
- Statistical Confidence: ${planData.executive_summary.statistical_confidence} (${planData.executive_summary.validity_rating})
- High/Critical Risk Areas: ${planData.executive_summary.critical_risk_count}

## 2. Priority Risk Playbooks
${planData.action_playbooks.map(p => `### ${p.title} (${p.severity})
- **Exposure:** ${p.legal_implication}
- **Immediate Directive (7 Days):** ${p.immediate_action}
- **Systemic Fix (30-60 Days):** ${p.systemic_fix}
`).join("\n")}

## 3. Recommended Phased Roadmap
### Phase 1: Immediate Safety (7 Days)
${planData.roadmap.phase_1_immediate_7d.map(s => `- ${s}`).join("\n")}

### Phase 2: Systemic Controls (30 Days)
${planData.roadmap.phase_2_systemic_30d.map(s => `- ${s}`).join("\n")}

### Phase 3: Enterprise Governance (90 Days)
${planData.roadmap.phase_3_governance_90d.map(s => `- ${s}`).join("\n")}
`;
    navigator.clipboard.writeText(md);
    setCopiedMarkdown(true);
    setTimeout(() => setCopiedMarkdown(false), 3000);
  }

  if (loading) {
    return (
      <div className="card">
        <p style={{ color: "#667085" }}>Loading organization dashboard…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h2 style={{ color: "#b42318" }}>Error Loading Dashboard</h2>
        <p className="error">{error}</p>
      </div>
    );
  }

  if (!data) return null;

  const totalEmployees = data.total_headcount ?? data.departments.reduce((sum, d) => sum + (d.employees || 0), 0);
  const totalResponded = data.total_responded ?? data.departments.reduce((sum, d) => sum + (d.responded || 0), 0);
  const participationRate = data.participation_rate ?? (totalEmployees > 0 ? Math.round((totalResponded / totalEmployees) * 100) : 0);

  const scoredDepts = data.departments.filter((d) => d.average_score !== null && d.average_score !== undefined);
  const totalScoresSum = scoredDepts.reduce((sum, d) => sum + (d.average_score * d.responded), 0);
  const overallAvg = totalResponded > 0 && scoredDepts.length > 0
    ? (totalScoresSum / totalResponded).toFixed(2)
    : "—";

  function getBadgeClass(level) {
    if (!level) return "badge-not-assessed";
    const key = level.toLowerCase();
    if (key.includes("leader")) return "badge-leader";
    if (key.includes("practitioner")) return "badge-practitioner";
    if (key.includes("exploring")) return "badge-exploring";
    if (key.includes("beginner")) return "badge-beginner";
    return "badge-not-assessed";
  }

  const confidence = data.statistical_confidence || {
    level: "Moderate Statistical Confidence",
    score_validity: "Directional",
    description: "Sample shows key department signals.",
    color: "#b54708",
  };

  return (
    <div>
      {/* Header with Executive Remediation Plan Trigger */}
      <div className="card" style={{ marginBottom: "16px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ margin: "0 0 6px 0" }}>{data.organization}</h2>
          <p style={{ margin: 0, color: "#667085", fontSize: "14px" }}>
            Leadership AI adoption telemetry, statistical validity, and executive remediation.
          </p>
        </div>
        <button
          onClick={handleOpenRemediationPlan}
          style={{ background: "#3f2a71", display: "flex", alignItems: "center", gap: "8px" }}
        >
          <span>📋</span>
          <span>Generate Executive Remediation Plan</span>
        </button>
      </div>

      {nudgeNotice && (
        <div className="success-banner" style={{ marginBottom: "16px" }}>
          ✅ {nudgeNotice}
        </div>
      )}

      {/* Statistical Confidence & Coverage Banner */}
      <div className="confidence-banner">
        <div className="confidence-info">
          <div style={{ fontSize: "24px" }}>📊</div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontWeight: 700, fontSize: "14px", color: "#1d2939" }}>Survey Confidence:</span>
              <span className="confidence-badge" style={{ background: `${confidence.color}15`, color: confidence.color }}>
                {confidence.level} ({confidence.score_validity})
              </span>
            </div>
            <div style={{ fontSize: "12px", color: "#475467", marginTop: "3px" }}>
              {confidence.description}
            </div>
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontWeight: 700, fontSize: "16px", color: "#1d2939" }}>{participationRate}% Coverage</div>
          <div style={{ fontSize: "12px", color: "#667085" }}>{totalResponded} of {totalEmployees} employees</div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Headcount</div>
          <div className="stat-value">{totalEmployees}</div>
          <div className="stat-sub">Across all registered teams</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Diagnostic Completed</div>
          <div className="stat-value">{totalResponded}</div>
          <div className="stat-sub">{participationRate}% participation rate</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Company AI Maturity</div>
          <div className="stat-value">{overallAvg} <small style={{ fontSize: "15px", color: "#667085" }}>/ 5.0</small></div>
          <div className="stat-sub">Weighted operational score</div>
        </div>
      </div>

      {/* Department Breakdown Table */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "8px" }}>
          <h3 style={{ margin: 0 }}>Department AI Maturity & Participation</h3>
          <span style={{ fontSize: "12px", color: "#667085" }}>
            🔒 Teams with &lt; 5 respondents are grouped to preserve employee privacy.
          </span>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table className="dash-table">
            <thead>
              <tr>
                <th>Department</th>
                <th>Headcount</th>
                <th>Participation</th>
                <th>Average Score</th>
                <th>Maturity Level</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.departments.map((d) => {
                const pct = d.employees > 0 ? Math.round((d.responded / d.employees) * 100) : 0;
                return (
                  <tr key={d.department}>
                    <td>
                      <b>{d.department}</b>
                      {d.is_masked && (
                        <span className="badge-privacy">Protected Group</span>
                      )}
                    </td>
                    <td>{d.employees}</td>
                    <td>
                      {d.responded} of {d.employees} <span style={{ color: "#667085", fontSize: "12px" }}>({pct}%)</span>
                    </td>
                    <td>
                      {d.average_score !== null && d.average_score !== undefined ? (
                        <span><b>{d.average_score}</b> <span style={{ color: "#667085", fontSize: "12px" }}>/ 5.0</span></span>
                      ) : (
                        <span style={{ color: "#98a2b3" }}>—</span>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${getBadgeClass(d.level)}`}>
                        {d.level}
                      </span>
                    </td>
                    <td>
                      {d.is_masked && d.masked_teams && d.masked_teams.length > 0 ? (
                        <button
                          className="btn-nudge"
                          onClick={() => handleCopyNudge(d.masked_teams[0].department, d.masked_teams[0].responses_needed_to_unmask)}
                          title={`Copy reminder to unmask ${d.masked_teams[0].department}`}
                        >
                          📢 Nudge Team (+{d.masked_teams[0].responses_needed_to_unmask} needed)
                        </button>
                      ) : (
                        <span style={{ color: "#027a48", fontSize: "12px", fontWeight: 500 }}>✓ Validated</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top Risks Section */}
      <div className="card">
        <h3 style={{ margin: "0 0 6px 0" }}>Top Company AI Risk Signals</h3>
        <p style={{ margin: "0 0 14px 0", color: "#667085", fontSize: "13px" }}>
          Identified automatically from open-ended assessment answers.
        </p>

        {data.top_risks && data.top_risks.length > 0 ? (
          <div className="risk-grid">
            {data.top_risks.map(([flag, count]) => (
              <div key={flag} className="risk-item">
                <div className="risk-name">
                  <span style={{ fontSize: "16px" }}>⚠️</span>
                  <span>{flag.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</span>
                </div>
                <div className="risk-count">
                  {count} {count === 1 ? "occurrence" : "occurrences"}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: "#027a48", margin: 0 }}>
            ✅ No security or data risks have been flagged across company responses.
          </p>
        )}
      </div>

      {/* Executive Remediation Plan Modal */}
      {showPlanModal && (
        <div className="modal-overlay" onClick={() => setShowPlanModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3 style={{ margin: "0 0 4px 0", color: "#101828" }}>
                  Executive AI Remediation Brief & Action Plan
                </h3>
                <span style={{ fontSize: "13px", color: "#667085" }}>
                  Prepared for {data.organization} Leadership • {new Date().toLocaleDateString()}
                </span>
              </div>
              <div className="no-print" style={{ display: "flex", gap: "8px" }}>
                <button
                  className="btn-secondary"
                  onClick={handleCopyPlanMarkdown}
                  style={{ fontSize: "12px", padding: "6px 12px" }}
                >
                  {copiedMarkdown ? "✓ Copied MD" : "Copy Markdown"}
                </button>
                <button
                  onClick={() => window.print()}
                  style={{ fontSize: "12px", padding: "6px 12px" }}
                >
                  🖨️ Print / PDF
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => setShowPlanModal(false)}
                  style={{ fontSize: "12px", padding: "6px 10px" }}
                >
                  ✕
                </button>
              </div>
            </div>

            {planLoading ? (
              <div className="loading-container">
                <div className="spinner spinner-dark"></div>
                <div>Synthesizing organizational action plan & legal playbooks…</div>
              </div>
            ) : planData ? (

              <div>
                {/* Executive Summary Cards */}
                <div className="stats-grid" style={{ marginBottom: "16px" }}>
                  <div className="stat-card" style={{ padding: "12px" }}>
                    <div className="stat-label">Survey Participation</div>
                    <div style={{ fontSize: "20px", fontWeight: 700 }}>{planData.executive_summary.participation_rate}</div>
                    <div className="stat-sub">{planData.executive_summary.total_responded} respondents</div>
                  </div>
                  <div className="stat-card" style={{ padding: "12px" }}>
                    <div className="stat-label">Data Validity</div>
                    <div style={{ fontSize: "20px", fontWeight: 700, color: "#3f2a71" }}>{planData.executive_summary.validity_rating}</div>
                    <div className="stat-sub">{planData.executive_summary.statistical_confidence}</div>
                  </div>
                  <div className="stat-card" style={{ padding: "12px" }}>
                    <div className="stat-label">Critical Risk Flags</div>
                    <div style={{ fontSize: "20px", fontWeight: 700, color: "#b42318" }}>{planData.executive_summary.critical_risk_count}</div>
                    <div className="stat-sub">Require immediate action</div>
                  </div>
                </div>

                {/* Priority Risk Playbooks */}
                <div className="plan-section">
                  <h4>1. Active Exposure Playbooks</h4>
                  {planData.action_playbooks.map((p) => (
                    <div key={p.flag} className="playbook-card">
                      <div className="playbook-header">
                        <span style={{ fontWeight: 700, color: "#101828", fontSize: "14px" }}>
                          ⚠️ {p.title}
                        </span>
                        <span className={`severity-pill severity-${p.severity.toLowerCase()}`}>
                          {p.severity} Severity ({p.occurrences}x)
                        </span>
                      </div>
                      <p style={{ margin: "0 0 8px 0", fontSize: "13px", color: "#475467" }}>
                        <b>Regulatory / Operational Exposure:</b> {p.legal_implication}
                      </p>
                      <div style={{ fontSize: "13px", color: "#1d2939", background: "#fff", padding: "8px 12px", borderRadius: "6px", border: "1px solid #eaecf0", marginBottom: "6px" }}>
                        <b>Immediate Directive (7 Days):</b> {p.immediate_action}
                      </div>
                      <div style={{ fontSize: "13px", color: "#1d2939", background: "#fff", padding: "8px 12px", borderRadius: "6px", border: "1px solid #eaecf0", marginBottom: "8px" }}>
                        <b>Systemic Fix (30 Days):</b> {p.systemic_fix}
                      </div>
                      {p.articles && p.articles.length > 0 && (
                        <div style={{ marginTop: "8px" }}>
                          <span style={{ fontSize: "12px", fontWeight: 600, color: "#475467" }}>
                            📚 Authoritative Reading & Remediation Articles:
                          </span>
                          <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "4px" }}>
                            {p.articles.map((art, aIdx) => (
                              <a
                                key={aIdx}
                                href={art.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{
                                  fontSize: "12px",
                                  color: "#3f2a71",
                                  textDecoration: "none",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "6px",
                                }}
                              >
                                <span>🔗</span>
                                <span style={{ textDecoration: "underline" }}>{art.title}</span>
                                <span style={{ color: "#667085", fontSize: "11px" }}>({art.source})</span>
                              </a>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>


                {/* Phased Roadmap */}
                <div className="plan-section">
                  <h4>2. Executive 30-60-90 Day Roadmap</h4>
                  <div className="roadmap-phase">
                    <b style={{ color: "#3f2a71" }}>Phase 1: Immediate Safety (7 Days)</b>
                    <ul style={{ margin: "6px 0 0 16px", padding: 0, fontSize: "13px", color: "#344054" }}>
                      {planData.roadmap.phase_1_immediate_7d.map((s, idx) => (
                        <li key={idx} style={{ marginBottom: "4px" }}>{s}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="roadmap-phase">
                    <b style={{ color: "#3f2a71" }}>Phase 2: Systemic Controls (30 Days)</b>
                    <ul style={{ margin: "6px 0 0 16px", padding: 0, fontSize: "13px", color: "#344054" }}>
                      {planData.roadmap.phase_2_systemic_30d.map((s, idx) => (
                        <li key={idx} style={{ marginBottom: "4px" }}>{s}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="roadmap-phase">
                    <b style={{ color: "#3f2a71" }}>Phase 3: Governance & Review (90 Days)</b>
                    <ul style={{ margin: "6px 0 0 16px", padding: 0, fontSize: "13px", color: "#344054" }}>
                      {planData.roadmap.phase_3_governance_90d.map((s, idx) => (
                        <li key={idx} style={{ marginBottom: "4px" }}>{s}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ) : (
              <p className="error">Failed to load remediation plan.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

