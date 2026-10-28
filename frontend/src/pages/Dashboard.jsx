import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Dashboard({ org }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

  // Calculate high-level summary KPIs
  const totalEmployees = data.departments.reduce((sum, d) => sum + (d.employees || 0), 0);
  const totalResponded = data.departments.reduce((sum, d) => sum + (d.responded || 0), 0);
  const participationRate = totalEmployees > 0 ? Math.round((totalResponded / totalEmployees) * 100) : 0;

  // Calculate weighted overall average across scored departments
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

  return (
    <div>
      {/* Header */}
      <div className="card" style={{ marginBottom: "16px" }}>
        <h2 style={{ margin: "0 0 6px 0" }}>{data.organization}</h2>
        <p style={{ margin: 0, color: "#667085", fontSize: "14px" }}>
          Company-wide AI adoption, department maturity levels, and security risk signals.
        </p>
      </div>

      {/* KPI Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Headcount</div>
          <div className="stat-value">{totalEmployees}</div>
          <div className="stat-sub">Across all teams</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Diagnostic Completed</div>
          <div className="stat-value">{totalResponded}</div>
          <div className="stat-sub">{participationRate}% participation rate</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Company AI Maturity</div>
          <div className="stat-value">{overallAvg} <small style={{ fontSize: "15px", color: "#667085" }}>/ 5.0</small></div>
          <div className="stat-sub">Weighted average score</div>
        </div>
      </div>

      {/* Department Breakdown Table */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "8px" }}>
          <h3 style={{ margin: 0 }}>Department AI Maturity</h3>
          <span style={{ fontSize: "12px", color: "#667085" }}>
            Teams with &lt; 5 respondents are grouped to preserve employee privacy.
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
              </tr>
            </thead>
            <tbody>
              {data.departments.map((d) => {
                const pct = d.employees > 0 ? Math.round((d.responded / d.employees) * 100) : 0;
                return (
                  <tr key={d.department}>
                    <td>
                      <b>{d.department}</b>
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
    </div>
  );
}
