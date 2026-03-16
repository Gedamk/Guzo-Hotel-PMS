import { useState } from "react";
import type { UserSession } from "../types/pms";

type LoginPageProps = {
  onLogin: (session: UserSession) => void;
};

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("manager");
  const [role, setRole] = useState<UserSession["role"]>("frontdesk");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onLogin({
      username: username.trim() || "manager",
      role,
    });
  }

  return (
    <div className="login-page">
      <div
        style={{
          width: "100%",
          maxWidth: "1180px",
          display: "grid",
          gridTemplateColumns: "1.2fr 0.8fr",
          gap: "24px",
        }}
      >
        <section
          className="card"
          style={{
            padding: "36px",
            minHeight: "560px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            background:
              "linear-gradient(135deg, rgba(14,165,233,0.10), rgba(15,23,42,0.96))",
          }}
        >
          <div>
            <div
              className="pill"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "20px",
              }}
            >
              Hotel Operations Platform
            </div>

            <h1
              style={{
                fontSize: "48px",
                lineHeight: "1.1",
                margin: "0 0 18px 0",
                fontWeight: 800,
              }}
            >
              Guzo Guest Assist PMS
            </h1>

            <p
              style={{
                fontSize: "18px",
                lineHeight: "1.7",
                color: "var(--muted)",
                maxWidth: "760px",
                margin: 0,
              }}
            >
              Global hotel operations, one standard workflow. Front office,
              housekeeping, finance, reporting, and admin in one operational
              dashboard designed for daily hotel use.
            </p>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                gap: "16px",
                marginTop: "36px",
              }}
            >
              <div className="card" style={{ background: "rgba(2,6,23,0.45)" }}>
                <div className="muted" style={{ fontSize: "13px" }}>
                  Front Desk
                </div>
                <div style={{ fontSize: "20px", fontWeight: 700, marginTop: "8px" }}>
                  Check-in control
                </div>
                <p
                  style={{
                    marginTop: "10px",
                    marginBottom: 0,
                    color: "var(--muted)",
                    lineHeight: "1.6",
                    fontSize: "14px",
                  }}
                >
                  Manage arrivals, departures, stayovers, and guest movement.
                </p>
              </div>

              <div className="card" style={{ background: "rgba(2,6,23,0.45)" }}>
                <div className="muted" style={{ fontSize: "13px" }}>
                  Housekeeping
                </div>
                <div style={{ fontSize: "20px", fontWeight: 700, marginTop: "8px" }}>
                  Room status board
                </div>
                <p
                  style={{
                    marginTop: "10px",
                    marginBottom: 0,
                    color: "var(--muted)",
                    lineHeight: "1.6",
                    fontSize: "14px",
                  }}
                >
                  Track occupancy, room readiness, and operational room flow.
                </p>
              </div>

              <div className="card" style={{ background: "rgba(2,6,23,0.45)" }}>
                <div className="muted" style={{ fontSize: "13px" }}>
                  Reports
                </div>
                <div style={{ fontSize: "20px", fontWeight: 700, marginTop: "8px" }}>
                  Manager reporting
                </div>
                <p
                  style={{
                    marginTop: "10px",
                    marginBottom: 0,
                    color: "var(--muted)",
                    lineHeight: "1.6",
                    fontSize: "14px",
                  }}
                >
                  Review KPIs, daily performance, and export-ready reports.
                </p>
              </div>
            </div>
          </div>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "10px",
              marginTop: "28px",
            }}
          >
            <div className="pill">Multi-module workflow</div>
            <div className="pill">Property-aware design</div>
            <div className="pill">Daily hotel operations</div>
          </div>
        </section>

        <section
          className="login-card"
          style={{
            padding: "34px",
            alignSelf: "center",
            width: "100%",
            maxWidth: "420px",
            justifySelf: "center",
          }}
        >
          <div
            className="pill"
            style={{
              display: "inline-flex",
              marginBottom: "18px",
            }}
          >
            Secure Access
          </div>

          <h2 style={{ margin: 0, fontSize: "34px" }}>Sign in</h2>
          <p
            className="muted"
            style={{
              marginTop: "10px",
              lineHeight: "1.6",
              fontSize: "14px",
            }}
          >
            Demo access for PMS module testing and workflow validation.
          </p>

          <form onSubmit={handleSubmit} className="form-grid" style={{ marginTop: "24px" }}>
            <div className="field">
              <label>Username</label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
              />
            </div>

            <div className="field">
              <label>Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as UserSession["role"])}
              >
                <option value="manager">Manager</option>
                <option value="frontdesk">Front Desk</option>
                <option value="housekeeping">Housekeeping</option>
                <option value="finance">Finance</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            <button type="submit" className="primary-btn" style={{ marginTop: "6px" }}>
              Enter PMS
            </button>
          </form>

          <div className="card" style={{ marginTop: "22px", padding: "16px" }}>
            <div style={{ fontWeight: 700, marginBottom: "10px" }}>Demo login notes</div>
            <div className="muted" style={{ fontSize: "14px", lineHeight: "1.7" }}>
              • Use any username for testing
              <br />
              • Select the role that matches your workflow
              <br />
              • Best first test: Front Desk or Manager
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
