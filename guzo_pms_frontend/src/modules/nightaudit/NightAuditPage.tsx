import { useEffect, useState } from "react";
import PageHeader from "../../components/PageHeader";
import KpiCard from "../../components/KpiCard";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { usePmsContext } from "../../context/PmsContext";
import { getErrorMessage } from "../../services/http";
import { permissionMessage, roleCan } from "../../auth/permissions";
import {
  fetchNightAuditExceptions,
  fetchNightAuditReadiness,
  fetchNightAuditStatus,
  generateNightAuditReports,
  overrideBusinessDate,
  runNightAudit,
  runNightAuditValidation,
  type NightAuditReadiness,
  type NightAuditRunResponse,
  type NightAuditStatus,
  type NightAuditValidation,
} from "../../services/nightAuditService";

export default function NightAuditPage() {
  const { propertyCode, businessDate, setBusinessDate } = usePmsContext();
  const [status, setStatus] = useState<NightAuditStatus | null>(null);
  const [readiness, setReadiness] = useState<NightAuditReadiness | null>(null);
  const [validation, setValidation] = useState<NightAuditValidation | null>(null);
  const [activeTab, setActiveTab] = useState("readiness");
  const [notes, setNotes] = useState("");
  const [overrideDate, setOverrideDate] = useState(businessDate);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [lastRun, setLastRun] = useState<NightAuditRunResponse | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const canRunValidation = roleCan("night_audit.run_validation");
  const canRunAudit = roleCan("night_audit.run_audit");
  const canLockDate = roleCan("night_audit.override_exception");

  async function loadStatus() {
    try {
      setLoading(true);
      setError("");
      const data = await fetchNightAuditStatus(propertyCode);
      const auditDate = data.business_date || businessDate;
      const [readinessData, exceptionData] = await Promise.all([
        fetchNightAuditReadiness(propertyCode, auditDate),
        fetchNightAuditExceptions(propertyCode, auditDate),
      ]);
      setStatus(data);
      setReadiness(readinessData);
      setValidation(exceptionData);
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
      const result = await runNightAudit(propertyCode, notes, status?.business_date || businessDate);
      setLastRun(result);
      setMessage(result.message);
      if (result.ok) {
        setBusinessDate(result.next_business_date);
        setNotes("");
      }
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
      await overrideBusinessDate(propertyCode, overrideDate, notes || "Manager business date adjustment");
      setBusinessDate(overrideDate);
      setMessage(`Business date set to ${overrideDate}.`);
      await loadStatus();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleRunValidation() {
    try {
      setError("");
      setMessage("");
      const result = await runNightAuditValidation(propertyCode, status?.business_date || businessDate);
      setValidation(result);
      setMessage(
        result.ready_to_run
          ? "Validation passed. Night Audit is ready to run."
          : `Validation failed: ${result.blocking_count} blocking issue(s), ${result.warning_count} warning(s).`
      );
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleGenerateReports() {
    try {
      setError("");
      setMessage("");
      const result = await generateNightAuditReports(propertyCode, status?.business_date || businessDate);
      setMessage(`Generated ${result.reports.length} Night Audit report(s).`);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  const snapshot = status?.operational_snapshot;
  const exceptions = validation?.exceptions || readiness?.exceptions || [];
  const blocking = exceptions.filter((item) => item.is_blocking);
  const hardBlocking = blocking.filter((item) => item.exception_key !== "frontdesk_expected_arrivals_remaining");
  const warnings = exceptions.filter((item) => !item.is_blocking);
  const financeSummary = validation?.finance_summary;
  const cashierShift = validation?.cashier_shift;

  return (
    <div className="page-grid night-audit-command">
      <PageHeader
        title="Night Audit Command Center"
        subtitle="Daily close, exception control, report package, and business-date rollover."
        metadata={`${propertyCode} • ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">Business Date: {status?.business_date || businessDate}</div>
            <div className="pill">Status: {validation?.audit_status || "loading"}</div>
            <button className="small-btn" onClick={loadStatus}>
              Refresh
            </button>
          </>
        }
      />

      {loading ? <div className="card">Loading night audit status...</div> : null}
      {error ? <div className="error-box">{error}</div> : null}
      {message ? <div className="card">{message}</div> : null}
      {!canRunValidation && !canRunAudit && !canLockDate ? (
        <div className="notice-box">{permissionMessage("Night Audit close controls")}</div>
      ) : null}

      {status ? (
        <>
          <div className="kpi-grid">
            <KpiCard
              label="Audit Status"
              value={validation?.ready_to_run ? "Ready" : "Not Ready"}
            />
            <KpiCard
              label="Remaining Arrivals"
              value={String(snapshot?.arrivals_count ?? 0)}
            />
            <KpiCard
              label="Remaining Departures"
              value={String(snapshot?.departures_count ?? 0)}
            />
            <KpiCard
              label="In-House"
              value={String(snapshot?.in_house_count ?? 0)}
            />
            <KpiCard
              label="No-Shows"
              value={String(snapshot?.no_show_count ?? 0)}
            />
            <KpiCard
              label="Open Folios"
              value={String(financeSummary?.open_folios ?? 0)}
            />
            <KpiCard
              label="Pending Guarantees"
              value={String(financeSummary?.pending_guarantee_reservations ?? 0)}
            />
            <KpiCard
              label="Blocking Issues"
              value={String(blocking.length)}
            />
            <KpiCard
              label="Warnings"
              value={String(warnings.length)}
            />
          </div>

          <div className="workflow-tabs">
            {[
              ["readiness", "Readiness"],
              ["frontdesk", "Front Desk"],
              ["housekeeping", "Housekeeping"],
              ["finance", "Finance"],
              ["cashier", "Cashier"],
              ["exceptions", "Exceptions"],
              ["reports", "Reports"],
              ["run", "Run Audit"],
            ].map(([key, label]) => (
              <button
                key={key}
                className={`tab-btn ${activeTab === key ? "active" : ""}`}
                onClick={() => setActiveTab(key)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>

          {activeTab === "readiness" ? (
          <div className="page-grid two-col">
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Audit Readiness</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Review front office, housekeeping, finance, cashier, and report controls before rolling the date.
              </div>
              <div className="sop-list">
                {(readiness?.checks || []).map((check) => (
                  <div className="sop-item" key={check.key}>
                    <StatusBadge status={check.status} />
                    {check.label}
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <h2 style={{ marginTop: 0 }}>Validation Controls</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Run validation before audit close. Blocking exceptions prevent date rollover.
              </div>
              {canRunValidation ? (
                <button className="primary-btn" onClick={handleRunValidation}>
                  Run Validation
                </button>
              ) : (
                <div className="notice-box">{permissionMessage("Night Audit validation")}</div>
              )}
              <button className="small-btn" onClick={handleGenerateReports} style={{ marginLeft: "10px" }}>
                Generate Reports
              </button>
            </div>
          </div>
          ) : null}

          {["frontdesk", "housekeeping", "finance", "cashier", "exceptions"].includes(activeTab) ? (
            <div className="card">
              <h2 style={{ marginTop: 0 }}>{activeTab === "exceptions" ? "All Exceptions" : `${activeTab[0].toUpperCase()}${activeTab.slice(1)} Audit`}</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Blocking issues must be resolved before Night Audit can run. Warnings may require manager review.
              </div>
              <div className="workflow-list">
                {exceptions
                  .filter((item) => activeTab === "exceptions" || item.department === activeTab)
                  .map((item, index) => (
                    <div className="workflow-row" key={`${item.exception_key}-${index}`}>
                      <div>
                        <strong>{item.message}</strong>
                        <div className="muted">
                          {item.department} / {item.exception_key}
                          {item.related_room_number ? ` / Room ${item.related_room_number}` : ""}
                        </div>
                      </div>
                      <StatusBadge status={item.is_blocking ? "blocked" : "warning"} />
                    </div>
                  ))}
                {exceptions.filter((item) => activeTab === "exceptions" || item.department === activeTab).length === 0 ? (
                  <div className="muted">No exceptions for this area.</div>
                ) : null}
              </div>
            </div>
          ) : null}

          {activeTab === "cashier" ? (
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Cashier Totals</h2>
              <div className="ops-strip">
                <div><span className="ops-label">Cash</span><div className="ops-value">{cashierShift?.cash ?? 0}</div></div>
                <div><span className="ops-label">Card</span><div className="ops-value">{cashierShift?.card ?? 0}</div></div>
                <div><span className="ops-label">Mobile</span><div className="ops-value">{cashierShift?.mobile_money ?? 0}</div></div>
                <div><span className="ops-label">Unassigned</span><div className="ops-value">{cashierShift?.unassigned ?? 0}</div></div>
              </div>
            </div>
          ) : null}

          {activeTab === "reports" ? (
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Reports Package</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Generate Daily Revenue, Trial Balance, Guest Ledger, Deposit Ledger, Payment Ledger, Cashier, Tax, Folio Audit, and movement reports.
              </div>
              <button className="primary-btn" onClick={handleGenerateReports}>Generate Reports</button>
              <button className="small-btn" onClick={() => window.print()} style={{ marginLeft: "10px" }}>Print</button>
            </div>
          ) : null}

          {activeTab === "run" ? (
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Run Night Audit</h2>
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
              {canRunAudit ? (
                <button
                  className="primary-btn"
                  onClick={handleRunAudit}
                  disabled={running || Boolean(hardBlocking.length)}
                  style={{ marginTop: "12px" }}
                >
                  {running ? "Running Audit..." : "Run Night Audit"}
                </button>
              ) : (
                <div className="notice-box">{permissionMessage("Night Audit run")}</div>
              )}
              {hardBlocking.length ? (
                <div className="notice-box">
                  <strong>Run Audit disabled</strong>
                  <span>{hardBlocking.length} blocking issue(s) must be resolved first.</span>
                </div>
              ) : null}
              {blocking.length && !hardBlocking.length ? (
                <div className="notice-box">
                  <strong>No-show processing ready</strong>
                  <span>Night Audit will mark unresolved arrivals as no-show candidates before final validation.</span>
                </div>
              ) : null}
              {lastRun?.ok ? (
                <div className="dashboard-metric-strip compact-four" style={{ marginTop: "16px" }}>
                  <div><span>Room/Tax Postings</span><strong>{lastRun.posting_summary?.posted_transactions ?? 0}</strong></div>
                  <div><span>Duplicate Protected</span><strong>{lastRun.posting_summary?.duplicate_transactions ?? 0}</strong></div>
                  <div><span>No-Shows</span><strong>{lastRun.no_show_summary?.marked_no_show ?? 0}</strong></div>
                  <div><span>Archive</span><strong>#{lastRun.archive_id ?? "-"}</strong></div>
                </div>
              ) : null}
            </div>
          ) : null}

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
                {canLockDate ? (
                  <button className="small-btn" onClick={handleOverrideDate}>
                    Set Date
                  </button>
                ) : (
                  <span className="pill pill-muted">Date control read only</span>
                )}
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
