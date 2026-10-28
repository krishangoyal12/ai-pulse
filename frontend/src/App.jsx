import React, { useState } from "react";
import Login from "./pages/Login.jsx";
import OrgPicker from "./pages/OrgPicker.jsx";
import Diagnostic from "./pages/Diagnostic.jsx";
import Report from "./pages/Report.jsx";
import Dashboard from "./pages/Dashboard.jsx";

export default function App() {
  const [step, setStep] = useState("login");
  const [session, setSession] = useState(null);
  const [org, setOrg] = useState(null);

  function handleLogout() {
    localStorage.removeItem("token");
    setSession(null);
    setOrg(null);
    setStep("login");
  }

  function handleSwitchOrg() {
    setOrg(null);
    setStep("org");
  }

  return (
    <div className="wrap">
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <h1 style={{ margin: 0 }}>AI Pulse</h1>
        {session && (
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "14px" }}>
              <b>{session.name}</b> {org && <span style={{ color: "#667085" }}>({org.org_name})</span>}
            </span>
            {session.organizations && session.organizations.length > 1 && (
              <button
                style={{ background: "#e9ecef", color: "#333", padding: "6px 12px", fontSize: "13px" }}
                onClick={handleSwitchOrg}
              >
                Switch Org
              </button>
            )}
            <button
              style={{ background: "#e9ecef", color: "#333", padding: "6px 12px", fontSize: "13px" }}
              onClick={handleLogout}
            >
              Log Out
            </button>
          </div>
        )}
      </header>

      {step === "login" && (
        <Login onDone={(s) => { setSession(s); setStep("org"); }} />
      )}
      {step === "org" && (
        <OrgPicker
          orgs={session.organizations}
          onPick={(o) => { setOrg(o); setStep(o.role === "admin" ? "dashboard" : "diagnostic"); }}
        />
      )}
      {step === "diagnostic" && <Diagnostic onDone={() => setStep("report")} />}
      {step === "report" && <Report onRetake={() => setStep("diagnostic")} />}
      {step === "dashboard" && <Dashboard org={org} />}
    </div>
  );
}

