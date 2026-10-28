import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Report({ onRetake }) {
  const [report, setReport] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadReport();
  }, []);

  function loadReport() {
    api("/reports/me").then(setReport);
  }

  async function handleDelete() {
    const confirmed = window.confirm(
      "Are you sure you want to permanently delete your diagnostic answers and report? This will remove your responses from all company dashboards immediately."
    );
    if (!confirmed) return;

    setDeleting(true);
    try {
      await api("/reports/me", { method: "DELETE" });
      setMessage("Your diagnostic responses and report have been permanently deleted.");
      loadReport();
    } catch (err) {
      alert("Failed to delete data: " + err.message);
    } finally {
      setDeleting(false);
    }
  }

  if (!report) return <p>Loading…</p>;

  if (report.answered === 0) {
    return (
      <div className="card">
        <h2>Personal Diagnostic Report</h2>
        {message ? (
          <p className="success-banner">{message}</p>
        ) : (
          <p>You have not completed the AI diagnostic yet, or your data has been deleted.</p>
        )}
        {onRetake && (
          <button style={{ marginTop: "12px" }} onClick={onRetake}>
            Take the Diagnostic
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h2>{report.name}</h2>
        <span className={`badge badge-${report.level.toLowerCase().replace(/\s+/g, "-")}`}>
          {report.level}
        </span>
      </div>
      <p><b>Organization:</b> {report.organization}</p>
      <p><b>Average Score:</b> {report.average_score} / 5.0</p>
      <p><b>Questions Answered:</b> {report.answered}</p>

      <h3>Identified Risks</h3>
      {report.risks && report.risks.length > 0 ? (
        <ul>
          {report.risks.map((r) => (
            <li key={r} style={{ color: "#b42318" }}>{r.replace(/_/g, " ")}</li>
          ))}
        </ul>
      ) : (
        <p style={{ color: "#027a48" }}>No security or compliance risks flagged in your answers.</p>
      )}

      <h3>Recommended Next Steps</h3>
      <ul>
        {report.next_steps.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>

      <hr style={{ margin: "24px 0", borderColor: "#eaecf0", borderStyle: "solid" }} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h4 style={{ margin: "0 0 4px 0", color: "#b42318" }}>Privacy & Data Control</h4>
          <small style={{ color: "#667085" }}>
            Under corporate privacy policies, you may erase your answers at any time.
          </small>
        </div>
        <button
          className="btn-danger"
          onClick={handleDelete}
          disabled={deleting}
          style={{ background: "#b42318" }}
        >
          {deleting ? "Deleting…" : "Delete My Data"}
        </button>
      </div>
    </div>
  );
}

