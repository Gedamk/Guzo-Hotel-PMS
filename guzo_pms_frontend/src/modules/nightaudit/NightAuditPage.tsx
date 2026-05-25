import { useEffect, useState } from "react";
import PageHeader from "../../components/PageHeader";
import KpiCard from "../../components/KpiCard";
import { usePmsContext } from "../../context/PmsContext";
import { getErrorMessage } from "../../services/http";
import {
  fetchNightAuditStatus,
  overrideBusinessDate,
  runNightAudit,
  type NightAuditStatus,
} from "../../services/nightAuditService";

export default function NightAuditPage() {
  const { propertyCode, businessDate, setBusinessDate } = usePmsContext();
  const [status, setStatus] = useState<NightAuditStatus | null>(null);
  const [notes, setNotes] = useState("");
  const [overrideDate, setOverrideDate] = useState(businessDate);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadStatus() {
    try {
      setLoading(true);
      setError("");
      const data = await fetchNightAuditStatus(propertyCode);
      setStatus(data);
      setOverrideDate(data.business_date || businessDate);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStatus();
  }, [propertyCode]);

  async function handleRunAudit() {
    try {
      setRunning(true);
      setError("");
      setMessage("");
      const result = await runNightAudit(propertyCode, notes);
      setMessage(result.message);
      setBusinessDate(result.next_business_date);
      setNotes("");
      await loadStatus();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setRunning(false);
    }
  }

  async function handleOverrideDate() {
    try {
      setError("");
      setMessage("");
      await overrideBusinessDate(propertyCode, overrideDate);
      setBusinessDate(overrideDate);
      setMessage(`Business date set to ${overrideDate}.`);
      await loadStatus();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  const snapshot = status?.operational_snapshot;

  return (
    <div className="page-grid">
      <PageHeader
        title="Night Audit"
        subtitle={`Close-day controls for ${propertyCode}`}
        rightSlot={
          <>
            <div className="pill">Business Date: {status?.business_date || businessDate}</div>
            <button className="small-btn" onClick={loadStatus}>
              Refresh
            </button>
          </>
        }
      />

      {loading ? <div className="card">Loading night audit status...</div> : null}
      {error ? <div className="error-box">{error}</div> : null}
      {message ? <div className="card">{message}</div> : null}

      {status ? (
        <>
          <div className="kpi-grid">
            <KpiCard
              label="Arrivals"
              value={String(snapshot?.arrivals_count ?? 0)}
            />
            <KpiCard
              label="Departures"
              value={String(snapshot?.departures_count ?? 0)}
            />
            <KpiCard
              label="In House"
              value={String(snapshot?.in_house_count ?? 0)}
            />
            <KpiCard
              label="No-Shows"
              value={String(snapshot?.no_show_count ?? 0)}
            />
          </div>

          <div className="page-grid two-col">
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Audit Readiness</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Review front office movement, folios, and housekeeping before rolling the date.
              </div>
              <div className="sop-list">
                <label className="sop-item">
                  <input type="checkbox" /> Arrivals, departures, and no-shows reviewed.
                </label>
                <label className="sop-item">
                  <input type="checkbox" /> Open folio balances reviewed by cashier.
                </label>
                <label className="sop-item">
                  <input type="checkbox" /> Housekeeping room status checked.
                </label>
                <label className="sop-item">
                  <input type="checkbox" /> Daily manager report exported or reviewed.
                </label>
              </div>
            </div>

            <div className="card">
              <h2 style={{ marginTop: 0 }}>Close Business Date</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Current date {status.business_date}; next date {status.next_business_date}.
              </div>
              <label>
                Audit Notes
                <textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Manager notes for the night audit log"
                />
              </label>
              <button
                className="primary-btn"
                onClick={handleRunAudit}
                disabled={running}
                style={{ marginTop: "12px" }}
              >
                {running ? "Running Audit..." : "Run Night Audit"}
              </button>
            </div>
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0 }}>Business Date Override</h2>
            <div className="form-grid">
              <label>
                Business Date
                <input
                  type="date"
                  value={overrideDate}
                  onChange={(event) => setOverrideDate(event.target.value)}
                />
              </label>
              <div style={{ display: "flex", alignItems: "end" }}>
                <button className="small-btn" onClick={handleOverrideDate}>
                  Set Date
                </button>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
