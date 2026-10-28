import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Diagnostic({ onDone }) {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [loadingQuestions, setLoadingQuestions] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoadingQuestions(true);
    api("/diagnostic/questions")
      .then((data) => {
        setQuestions(data);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || "Failed to load diagnostic questions.");
      })
      .finally(() => setLoadingQuestions(false));
  }, []);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const payload = Object.entries(answers).map(([question_id, answer]) => ({ question_id, answer }));
      await api("/diagnostic/submit", { method: "POST", body: JSON.stringify({ answers: payload }) });
      onDone();
    } catch (err) {
      setError(err.message || "Failed to submit diagnostic.");
      setSubmitting(false);
    }
  }

  if (loadingQuestions) {
    return (
      <div className="card">
        <div className="loading-container">
          <div className="spinner spinner-dark"></div>
          <div>Generating customized diagnostic assessment…</div>
        </div>
      </div>
    );
  }

  if (error && questions.length === 0) {
    return (
      <div className="card">
        <h3 style={{ color: "#b42318" }}>Error Loading Diagnostic</h3>
        <p className="error">{error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Your AI diagnostic</h2>
      <p style={{ color: "#667085", fontSize: "14px", marginTop: "-6px", marginBottom: "20px" }}>
        Answer honestly to help benchmark your team's AI adoption and surface practical ways to work faster and safer.
      </p>

      {error && <p className="error">{error}</p>}

      {questions.map((q) => (
        <div key={q.id} style={{ marginBottom: "22px" }}>
          <p style={{ margin: "0 0 8px 0" }}><b>{q.text}</b></p>
          {q.type === "mcq" ? (
            <select
              onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
              defaultValue=""
              disabled={submitting}
            >
              <option value="" disabled>Choose an option…</option>
              {q.options.map((o) => <option key={o}>{o}</option>)}
            </select>
          ) : (
            <textarea
              rows={4}
              placeholder="Describe a recent work task where you used AI..."
              onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
              disabled={submitting}
            />
          )}
        </div>
      ))}

      <button
        onClick={submit}
        disabled={submitting || questions.length === 0}
        style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
      >
        {submitting && <span className="spinner"></span>}
        <span>{submitting ? "Evaluating responses with AI…" : "Submit Diagnostic"}</span>
      </button>
    </div>
  );
}

