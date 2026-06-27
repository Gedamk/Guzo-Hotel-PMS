import { useEffect, useMemo, useState, type FormEvent } from "react";
import { MessageSquareText } from "lucide-react";
import PageHeader from "../../components/PageHeader";
import DataTable from "../../components/DataTable";
import KpiCard from "../../components/KpiCard";
import { LoadingState } from "../../components/ui/LoadingState";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { usePmsContext } from "../../context/PmsContext";
import {
  createGuestFeedback,
  fetchGuestFeedback,
  markGuestFeedbackServiceRecovery,
  updateGuestFeedbackStatus,
} from "../../services/pmsService";
import { getErrorMessage } from "../../services/http";
import type { GuestFeedback } from "../../types/pms";

type FeedbackForm = {
  guest_name: string;
  booking_id: string;
  rating: string;
  feedback_source: string;
  comment: string;
};

type RecoveryForm = {
  assigned_to: string;
  priority: string;
  recovery_action: string;
  follow_up_date: string;
  resolution_notes: string;
  guest_contacted: boolean;
  compensation_offered: string;
};

const defaultForm: FeedbackForm = {
  guest_name: "",
  booking_id: "",
  rating: "5",
  feedback_source: "front_desk",
  comment: "",
};

const defaultRecoveryForm: RecoveryForm = {
  assigned_to: "",
  priority: "medium",
  recovery_action: "",
  follow_up_date: "",
  resolution_notes: "",
  guest_contacted: false,
  compensation_offered: "none",
};

function formatDate(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function feedbackLabel(status: string) {
  const labels: Record<string, string> = {
    new: "New",
    reviewed: "Reviewed",
    service_recovery: "Service Recovery",
    closed: "Closed",
  };
  return labels[status] || status;
}

export default function GuestFeedbackPage() {
  const { propertyCode, propertyName, businessDate, refreshKey, refreshData } = usePmsContext();
  const [rows, setRows] = useState<GuestFeedback[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [form, setForm] = useState<FeedbackForm>(defaultForm);
  const [selectedRecovery, setSelectedRecovery] = useState<GuestFeedback | null>(null);
  const [recoveryForm, setRecoveryForm] = useState<RecoveryForm>(defaultRecoveryForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadFeedback() {
    try {
      setLoading(true);
      setError("");
      const data = await fetchGuestFeedback(
        propertyCode,
        statusFilter === "all" ? undefined : statusFilter
      );
      setRows(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFeedback();
  }, [propertyCode, statusFilter, refreshKey]);

  const stats = useMemo(() => {
    const open = rows.filter((row) => ["new", "reviewed"].includes(String(row.status))).length;
    const recovery = rows.filter((row) => row.status === "service_recovery").length;
    const closed = rows.filter((row) => row.status === "closed").length;
    const rated = rows.filter((row) => Number(row.rating || 0) > 0);
    const average = rated.length
      ? rated.reduce((sum, row) => sum + Number(row.rating || 0), 0) / rated.length
      : 0;
    return { open, recovery, closed, average };
  }, [rows]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    const rating = Number(form.rating || 0);
    if (!form.guest_name.trim()) {
      setError("Guest name is required.");
      return;
    }
    if (rating < 0 || rating > 5) {
      setError("Rating must be between 0 and 5.");
      return;
    }

    try {
      setSaving(true);
      await createGuestFeedback({
        property_code: propertyCode,
        booking_id: form.booking_id ? Number(form.booking_id) : null,
        guest_name: form.guest_name.trim(),
        rating,
        feedback_source: form.feedback_source,
        comment: form.comment.trim() || null,
        status: "new",
      });
      setForm(defaultForm);
      setMessage("Guest feedback added. Dashboard satisfaction will update automatically.");
      await loadFeedback();
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  function openRecovery(row: GuestFeedback) {
    setSelectedRecovery(row);
    setRecoveryForm({
      assigned_to: row.assigned_to || "",
      priority: row.priority || "medium",
      recovery_action: row.recovery_action || "",
      follow_up_date: row.follow_up_date || "",
      resolution_notes: row.resolution_notes || "",
      guest_contacted: Boolean(row.guest_contacted),
      compensation_offered: row.compensation_offered || "none",
    });
  }

  async function submitServiceRecovery(event: FormEvent) {
    event.preventDefault();
    if (!selectedRecovery) return;
    try {
      setBusyId(selectedRecovery.id);
      setError("");
      setMessage("");
      await markGuestFeedbackServiceRecovery(selectedRecovery.id, propertyCode, {
        assigned_to: recoveryForm.assigned_to.trim() || null,
        priority: recoveryForm.priority,
        recovery_action: recoveryForm.recovery_action.trim() || null,
        follow_up_date: recoveryForm.follow_up_date || null,
        resolution_notes: recoveryForm.resolution_notes.trim() || null,
        guest_contacted: recoveryForm.guest_contacted,
        compensation_offered: recoveryForm.compensation_offered,
      });
      setSelectedRecovery(null);
      setRecoveryForm(defaultRecoveryForm);
      setMessage("Service recovery case updated.");
      await loadFeedback();
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  async function runAction(row: GuestFeedback, action: "reviewed" | "closed") {
    try {
      setBusyId(row.id);
      setError("");
      setMessage("");
      await updateGuestFeedbackStatus(
        row.id,
        action,
        propertyCode,
        `Marked ${action} from Guest Feedback Inbox`
      );
      setMessage(`Feedback marked ${feedbackLabel(action).toLowerCase()}.`);
      await loadFeedback();
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page-grid guest-feedback-command">
      <PageHeader
        title="Guest Feedback Inbox"
        subtitle="Guest satisfaction, complaints, and service recovery workflow."
        metadata={`${propertyCode} • ${propertyName} • ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">{propertyCode}</div>
            <div className="pill">Business Date: {businessDate}</div>
            <button className="small-btn" type="button" onClick={loadFeedback}>Refresh</button>
          </>
        }
      />

      {loading ? (
        <LoadingState label="Loading guest feedback..." />
      ) : (
        <>
          {error ? <div className="error-box">{error}</div> : null}
          {message ? <div className="notice-box">{message}</div> : null}

          <div className="kpi-grid">
            <KpiCard label="Feedback Records" value={String(rows.length)} />
            <KpiCard label="Average Rating" value={stats.average ? `${stats.average.toFixed(2)}/5` : "No feedback"} />
            <KpiCard label="Open Feedback" value={String(stats.open)} />
            <KpiCard label="Service Recovery" value={String(stats.recovery)} />
            <KpiCard label="Closed" value={String(stats.closed)} />
          </div>

          <section className="page-grid two-col">
            <div className="card">
              <div className="section-heading">
                <div>
                  <h2>Add Feedback</h2>
                  <p className="muted">Capture guest reviews, complaints, surveys, chatbot sentiment, or service recovery notes.</p>
                </div>
                <MessageSquareText aria-hidden="true" size={24} />
              </div>

              <form className="page-grid" onSubmit={handleCreate}>
                <div className="form-grid">
                  <label className="field">
                    <span>Guest Name</span>
                    <input
                      value={form.guest_name}
                      onChange={(event) => setForm((prev) => ({ ...prev, guest_name: event.target.value }))}
                      required
                    />
                  </label>
                  <label className="field">
                    <span>Booking ID</span>
                    <input
                      type="number"
                      min="1"
                      value={form.booking_id}
                      onChange={(event) => setForm((prev) => ({ ...prev, booking_id: event.target.value }))}
                    />
                  </label>
                  <label className="field">
                    <span>Rating</span>
                    <input
                      type="number"
                      min="0"
                      max="5"
                      step="0.1"
                      value={form.rating}
                      onChange={(event) => setForm((prev) => ({ ...prev, rating: event.target.value }))}
                    />
                  </label>
                  <label className="field">
                    <span>Source</span>
                    <select
                      value={form.feedback_source}
                      onChange={(event) => setForm((prev) => ({ ...prev, feedback_source: event.target.value }))}
                    >
                      <option value="front_desk">Front Desk</option>
                      <option value="post_stay_survey">Post-Stay Survey</option>
                      <option value="chatbot">Chatbot</option>
                      <option value="email">Email</option>
                      <option value="phone">Phone</option>
                      <option value="manager">Manager</option>
                    </select>
                  </label>
                  <label className="field span-2">
                    <span>Comment</span>
                    <textarea
                      value={form.comment}
                      onChange={(event) => setForm((prev) => ({ ...prev, comment: event.target.value }))}
                    />
                  </label>
                </div>
                <div className="form-actions">
                  <button className="primary-btn" type="submit" disabled={saving}>
                    {saving ? "Saving..." : "Add Feedback"}
                  </button>
                </div>
              </form>
            </div>

            <div className="card">
              <div className="section-heading">
                <div>
                  <h2>Workflow</h2>
                  <p className="muted">Feedback moves from intake to review, service recovery when needed, and closure.</p>
                </div>
              </div>
              <div className="workflow-list">
                {["Add feedback", "Review by supervisor", "Mark service recovery when required", "Close after resolution", "Dashboard updates automatically"].map((step, index) => (
                  <div className="workflow-row" key={step}>
                    <strong>{index + 1}. {step}</strong>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {selectedRecovery ? (
            <section className="card">
              <div className="section-heading">
                <div>
                  <h2>Service Recovery Case</h2>
                  <p className="muted">
                    {selectedRecovery.guest_name || "Guest"} · {selectedRecovery.rating ? `${selectedRecovery.rating}/5` : "No rating"}
                  </p>
                </div>
                <button className="small-btn" type="button" onClick={() => setSelectedRecovery(null)}>Cancel</button>
              </div>
              <form className="page-grid" onSubmit={submitServiceRecovery}>
                <div className="form-grid">
                  <label className="field">
                    <span>Assigned To</span>
                    <input
                      value={recoveryForm.assigned_to}
                      onChange={(event) => setRecoveryForm((prev) => ({ ...prev, assigned_to: event.target.value }))}
                    />
                  </label>
                  <label className="field">
                    <span>Priority</span>
                    <select
                      value={recoveryForm.priority}
                      onChange={(event) => setRecoveryForm((prev) => ({ ...prev, priority: event.target.value }))}
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="urgent">Urgent</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>Follow-up Date</span>
                    <input
                      type="date"
                      value={recoveryForm.follow_up_date}
                      onChange={(event) => setRecoveryForm((prev) => ({ ...prev, follow_up_date: event.target.value }))}
                    />
                  </label>
                  <label className="field">
                    <span>Compensation</span>
                    <select
                      value={recoveryForm.compensation_offered}
                      onChange={(event) => setRecoveryForm((prev) => ({ ...prev, compensation_offered: event.target.value }))}
                    >
                      <option value="none">None</option>
                      <option value="discount">Discount</option>
                      <option value="upgrade">Upgrade</option>
                      <option value="refund">Refund</option>
                      <option value="amenity">Amenity</option>
                    </select>
                  </label>
                  <label className="field span-2">
                    <span>Recovery Action</span>
                    <textarea
                      value={recoveryForm.recovery_action}
                      onChange={(event) => setRecoveryForm((prev) => ({ ...prev, recovery_action: event.target.value }))}
                    />
                  </label>
                  <label className="field span-2">
                    <span>Resolution Notes</span>
                    <textarea
                      value={recoveryForm.resolution_notes}
                      onChange={(event) => setRecoveryForm((prev) => ({ ...prev, resolution_notes: event.target.value }))}
                    />
                  </label>
                  <label className="field">
                    <span>Guest Contacted</span>
                    <select
                      value={recoveryForm.guest_contacted ? "yes" : "no"}
                      onChange={(event) => setRecoveryForm((prev) => ({ ...prev, guest_contacted: event.target.value === "yes" }))}
                    >
                      <option value="no">No</option>
                      <option value="yes">Yes</option>
                    </select>
                  </label>
                </div>
                <div className="form-actions">
                  <button className="primary-btn" type="submit" disabled={busyId === selectedRecovery.id}>
                    {busyId === selectedRecovery.id ? "Saving..." : "Save Service Recovery"}
                  </button>
                </div>
              </form>
            </section>
          ) : null}

          <section className="card">
            <div className="section-heading">
              <div>
                <h2>Feedback List</h2>
                <p className="muted">Review guest experience records and update status.</p>
              </div>
              <label className="field compact-field">
                <span>Status</span>
                <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                  <option value="all">All</option>
                  <option value="new">New</option>
                  <option value="reviewed">Reviewed</option>
                  <option value="service_recovery">Service Recovery</option>
                  <option value="closed">Closed</option>
                </select>
              </label>
            </div>

            <DataTable
              rows={rows}
              emptyMessage="No guest feedback found."
              columns={[
                { key: "guest", header: "Guest", render: (row) => <strong>{row.guest_name || "Guest"}</strong> },
                { key: "rating", header: "Rating", render: (row) => (row.rating ? `${row.rating}/5` : "-") },
                { key: "source", header: "Source", render: (row) => row.feedback_source || "-" },
                {
                  key: "recovery",
                  header: "Recovery",
                  render: (row) => (
                    <div>
                      <strong>{row.assigned_to || "-"}</strong>
                      <div className="muted">{row.priority || "medium"} · {row.compensation_offered || "none"}</div>
                    </div>
                  ),
                },
                { key: "comment", header: "Comment", render: (row) => row.comment || "-" },
                {
                  key: "status",
                  header: "Status",
                  render: (row) => <StatusBadge status={row.status} label={feedbackLabel(row.status)} />,
                },
                { key: "created", header: "Created", render: (row) => formatDate(row.created_at) },
                {
                  key: "actions",
                  header: "Actions",
                  render: (row) => (
                    <div className="table-actions">
                      <button className="small-btn" disabled={busyId === row.id || row.status === "reviewed"} onClick={() => runAction(row, "reviewed")}>Review</button>
                      <button className="small-btn" disabled={busyId === row.id} onClick={() => openRecovery(row)}>Service Recovery</button>
                      <button className="small-btn" disabled={busyId === row.id || row.status === "closed"} onClick={() => runAction(row, "closed")}>Close</button>
                    </div>
                  ),
                },
              ]}
            />
          </section>
        </>
      )}
    </div>
  );
}
