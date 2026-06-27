import { useState } from "react";
import type { UserSession } from "../types/pms";
import { PROPERTY_CODE } from "../config/pms";
import { loginPmsUser } from "../services/authService";
import { getErrorMessage } from "../services/http";

type LoginPageProps = {
  onLogin: (session: UserSession) => void;
};

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [email, setEmail] = useState("admin@guzo.local");
  const [password, setPassword] = useState("admin123");
  const [propertyCode, setPropertyCode] = useState(PROPERTY_CODE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      setLoading(true);
      setError("");
      const session = await loginPmsUser({
        email: email.trim(),
        password,
        property_code: propertyCode.trim().toUpperCase(),
      });
      onLogin(session);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
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
              Enterprise Hotel Operations Platform
            </div>

            <h1
              style={{
                fontSize: "48px",
                lineHeight: "1.1",
                margin: "0 0 18px 0",
                fontWeight: 800,
              }}
            >
              Guzo PMS
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
              AI-powered Hotel Property Management System with Built-in Guest CRM
            </p>
            <p
              style={{
                fontSize: "15px",
                lineHeight: "1.7",
                color: "var(--muted)",
                maxWidth: "760px",
                marginTop: "12px",
              }}
            >
              Manage reservations, front desk operations, housekeeping, folio,
              payments, reports, night audit, and guest relationships from one
              modern hotel platform.
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
            Sign in with your PMS user account. Local development seeds an admin user unless configured otherwise.
          </p>

          <form onSubmit={handleSubmit} className="form-grid" style={{ marginTop: "24px" }}>
            <div className="field">
              <label>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@guzo.local"
                autoComplete="username"
                required
              />
            </div>

            <div className="field">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>

            <div className="field">
              <label>Property Code</label>
              <input
                value={propertyCode}
                onChange={(e) => setPropertyCode(e.target.value)}
                placeholder="DRE001"
                required
              />
            </div>

            {error ? <div className="error-box">{error}</div> : null}

            <button type="submit" className="primary-btn" style={{ marginTop: "6px" }} disabled={loading}>
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <div className="card" style={{ marginTop: "22px", padding: "16px" }}>
            <div style={{ fontWeight: 700, marginBottom: "10px" }}>Local login notes</div>
            <div className="muted" style={{ fontSize: "14px", lineHeight: "1.7" }}>
              Default local admin: admin@guzo.local
              <br />
              Default local password: admin123
              <br />
              Change GUZO_DEFAULT_ADMIN_PASSWORD before pilot use.
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
