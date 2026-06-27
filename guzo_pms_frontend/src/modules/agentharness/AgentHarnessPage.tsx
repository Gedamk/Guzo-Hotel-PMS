import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import {
  BedDouble,
  Bot,
  ClipboardList,
  Hotel,
  Lightbulb,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import PageHeader from "../../components/PageHeader";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { usePmsContext } from "../../context/PmsContext";
import { getRoleLabel } from "../../auth/accessControl";
import { permissionMessage, currentSession } from "../../auth/permissions";
import { getErrorMessage } from "../../services/http";
import {
  runAgentHarnessTask,
  type AgentHarnessResponse,
  type AgentHarnessTaskName,
} from "../../services/agentHarnessService";
import type { UserRole } from "../../types/pms";

type TaskKey =
  | "reservation"
  | "room"
  | "housekeeping"
  | "checkin"
  | "frontdesk"
  | "alerts";

type TaskConfig = {
  key: TaskKey;
  title: string;
  subtitle: string;
  taskName: AgentHarnessTaskName;
  icon: ReactNode;
  allowedRoles: UserRole[];
  readOnly?: boolean;
  suggestionOnly?: boolean;
};

const allAccessRoles: UserRole[] = ["admin", "general_manager"];

const tasks: TaskConfig[] = [
  {
    key: "reservation",
    title: "Reservation Request",
    subtitle: "Create a pending manual-review request for Booking Hub.",
    taskName: "create_reservation_request",
    icon: <Hotel size={22} />,
    allowedRoles: [...allAccessRoles, "reservation_agent", "sales_manager"],
  },
  {
    key: "room",
    title: "Room Assignment Suggestions",
    subtitle: "Suggest clean available rooms without assigning them.",
    taskName: "suggest_room_assignment",
    icon: <BedDouble size={22} />,
    allowedRoles: [...allAccessRoles, "frontdesk", "reservation_agent"],
    suggestionOnly: true,
  },
  {
    key: "housekeeping",
    title: "Housekeeping Task",
    subtitle: "Create a controlled room-status task for housekeeping follow-up.",
    taskName: "create_housekeeping_task",
    icon: <Sparkles size={22} />,
    allowedRoles: [...allAccessRoles, "housekeeping"],
  },
  {
    key: "checkin",
    title: "Check-in Blocker Explanation",
    subtitle: "Explain why a booking cannot be checked in yet.",
    taskName: "explain_check_in_blocked",
    icon: <ShieldAlert size={22} />,
    allowedRoles: [...allAccessRoles, "frontdesk"],
    readOnly: true,
  },
  {
    key: "frontdesk",
    title: "Front Desk Daily Issues",
    subtitle: "Summarize arrivals, departures, no-shows, and room-readiness exceptions.",
    taskName: "summarize_front_desk_issues",
    icon: <ClipboardList size={22} />,
    allowedRoles: [...allAccessRoles, "frontdesk"],
    readOnly: true,
  },
  {
    key: "alerts",
    title: "Manager Alerts Summary",
    subtitle: "Summarize open manager alerts by severity.",
    taskName: "summarize_manager_alerts",
    icon: <Lightbulb size={22} />,
    allowedRoles: allAccessRoles,
    readOnly: true,
  },
];

const initialForms = {
  reservation: {
    guest_name: "",
    guest_email: "",
    guest_phone: "",
    check_in_date: "",
    check_out_date: "",
    room_type: "Standard Room",
    source: "agent_harness",
    adults: "1",
    children: "0",
    special_requests: "",
  },
  room: {
    booking_id: "",
    room_type: "Standard Room",
    check_in_date: "",
  },
  housekeeping: {
    room_number: "",
    task_type: "cleaning",
    priority: "medium",
    assigned_to: "",
    note: "",
  },
  checkin: {
    booking_id: "",
  },
  frontdesk: {},
  alerts: {
    status: "open",
  },
};

function roleCanUseTask(role: UserRole, task: TaskConfig) {
  return task.allowedRoles.includes(role);
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

function ResultList({ value }: { value: unknown }) {
  if (Array.isArray(value)) {
    if (!value.length) return <div className="muted">No records returned.</div>;
    return (
      <div className="agent-result-list">
        {value.map((item, index) => (
          <div className="agent-result-row" key={index}>
            {typeof item === "object" && item !== null ? (
              Object.entries(item as Record<string, unknown>).map(([key, itemValue]) => (
                <div key={key}>
                  <span className="muted">{key.replace(/_/g, " ")}</span>
                  <strong>{stringifyValue(itemValue)}</strong>
                </div>
              ))
            ) : (
              <strong>{stringifyValue(item)}</strong>
            )}
          </div>
        ))}
      </div>
    );
  }

  if (typeof value === "object" && value !== null) {
    return (
      <div className="agent-result-grid">
        {Object.entries(value as Record<string, unknown>).map(([key, itemValue]) => (
          <div className="agent-result-field" key={key}>
            <span>{key.replace(/_/g, " ")}</span>
            {typeof itemValue === "object" && itemValue !== null ? (
              <ResultList value={itemValue} />
            ) : (
              <strong>{stringifyValue(itemValue)}</strong>
            )}
          </div>
        ))}
      </div>
    );
  }

  return <strong>{stringifyValue(value)}</strong>;
}

function ResultCard({ result, suggestionOnly }: { result: AgentHarnessResponse; suggestionOnly?: boolean }) {
  return (
    <div className="agent-result-card">
      <div className="section-heading">
        <div>
          <h3>{result.message}</h3>
          <p className="muted">{result.task_name}</p>
        </div>
        <StatusBadge status={result.status} label={result.status} />
      </div>
      {suggestionOnly ? (
        <div className="notice-box">AI suggestion only. Staff must confirm assignment.</div>
      ) : null}
      <ResultList value={result.data} />
    </div>
  );
}

export default function AgentHarnessPage() {
  const { propertyCode, propertyName, businessDate } = usePmsContext();
  const session = currentSession();
  const role = session?.role;
  const visibleTasks = useMemo(
    () => tasks.filter((task) => role && roleCanUseTask(role, task)),
    [role]
  );
  const [forms, setForms] = useState(initialForms);
  const [results, setResults] = useState<Partial<Record<TaskKey, AgentHarnessResponse>>>({});
  const [busyTask, setBusyTask] = useState<TaskKey | null>(null);
  const [error, setError] = useState("");

  function updateForm<T extends TaskKey>(key: T, field: string, value: string) {
    setForms((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        [field]: value,
      },
    }));
  }

  function buildPayload(task: TaskConfig): Record<string, unknown> {
    if (task.key === "reservation") {
      const form = forms.reservation;
      return {
        ...form,
        adults: Number(form.adults || 1),
        children: Number(form.children || 0),
        special_requests: form.special_requests || null,
      };
    }
    if (task.key === "room") {
      return {
        ...forms.room,
        booking_id: Number(forms.room.booking_id),
      };
    }
    if (task.key === "housekeeping") {
      return {
        ...forms.housekeeping,
        business_date: businessDate,
        assigned_to: forms.housekeeping.assigned_to || null,
        note: forms.housekeeping.note || null,
      };
    }
    if (task.key === "checkin") {
      return {
        booking_id: Number(forms.checkin.booking_id),
        business_date: businessDate,
      };
    }
    if (task.key === "frontdesk") {
      return { business_date: businessDate };
    }
    return { status: forms.alerts.status };
  }

  async function runTask(event: FormEvent, task: TaskConfig) {
    event.preventDefault();
    if (!role || !roleCanUseTask(role, task)) return;
    try {
      setBusyTask(task.key);
      setError("");
      const result = await runAgentHarnessTask(task.taskName, buildPayload(task), propertyCode);
      setResults((prev) => ({ ...prev, [task.key]: result }));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyTask(null);
    }
  }

  function renderFields(task: TaskConfig) {
    if (task.key === "reservation") {
      return (
        <div className="form-grid">
          <Field label="Guest Name" value={forms.reservation.guest_name} onChange={(value) => updateForm("reservation", "guest_name", value)} required />
          <Field label="Email" type="email" value={forms.reservation.guest_email} onChange={(value) => updateForm("reservation", "guest_email", value)} />
          <Field label="Phone" value={forms.reservation.guest_phone} onChange={(value) => updateForm("reservation", "guest_phone", value)} />
          <Field label="Room Type" value={forms.reservation.room_type} onChange={(value) => updateForm("reservation", "room_type", value)} required />
          <Field label="Check-in" type="date" value={forms.reservation.check_in_date} onChange={(value) => updateForm("reservation", "check_in_date", value)} required />
          <Field label="Check-out" type="date" value={forms.reservation.check_out_date} onChange={(value) => updateForm("reservation", "check_out_date", value)} required />
          <Field label="Adults" type="number" value={forms.reservation.adults} onChange={(value) => updateForm("reservation", "adults", value)} />
          <Field label="Children" type="number" value={forms.reservation.children} onChange={(value) => updateForm("reservation", "children", value)} />
          <Field label="Source" value={forms.reservation.source} onChange={(value) => updateForm("reservation", "source", value)} required />
          <label className="field span-2">
            <span>Special Requests</span>
            <textarea value={forms.reservation.special_requests} onChange={(event) => updateForm("reservation", "special_requests", event.target.value)} />
          </label>
        </div>
      );
    }

    if (task.key === "room") {
      return (
        <div className="form-grid">
          <Field label="Booking ID" type="number" value={forms.room.booking_id} onChange={(value) => updateForm("room", "booking_id", value)} required />
          <Field label="Room Type" value={forms.room.room_type} onChange={(value) => updateForm("room", "room_type", value)} required />
          <Field label="Check-in" type="date" value={forms.room.check_in_date} onChange={(value) => updateForm("room", "check_in_date", value)} required />
        </div>
      );
    }

    if (task.key === "housekeeping") {
      return (
        <div className="form-grid">
          <Field label="Room Number" value={forms.housekeeping.room_number} onChange={(value) => updateForm("housekeeping", "room_number", value)} required />
          <label className="field">
            <span>Task Type</span>
            <select value={forms.housekeeping.task_type} onChange={(event) => updateForm("housekeeping", "task_type", event.target.value)}>
              <option value="cleaning">Cleaning</option>
              <option value="clean">Clean</option>
              <option value="inspection">Inspection</option>
              <option value="maintenance">Maintenance</option>
              <option value="out_of_order">Out of Order</option>
            </select>
          </label>
          <label className="field">
            <span>Priority</span>
            <select value={forms.housekeeping.priority} onChange={(event) => updateForm("housekeeping", "priority", event.target.value)}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </label>
          <Field label="Assigned To" value={forms.housekeeping.assigned_to} onChange={(value) => updateForm("housekeeping", "assigned_to", value)} />
          <label className="field span-2">
            <span>Note</span>
            <textarea value={forms.housekeeping.note} onChange={(event) => updateForm("housekeeping", "note", event.target.value)} />
          </label>
        </div>
      );
    }

    if (task.key === "checkin") {
      return (
        <div className="form-grid">
          <Field label="Booking ID" type="number" value={forms.checkin.booking_id} onChange={(value) => updateForm("checkin", "booking_id", value)} required />
        </div>
      );
    }

    if (task.key === "alerts") {
      return (
        <div className="form-grid">
          <label className="field">
            <span>Alert Status</span>
            <select value={forms.alerts.status} onChange={(event) => updateForm("alerts", "status", event.target.value)}>
              <option value="open">Open</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="closed">Closed</option>
            </select>
          </label>
        </div>
      );
    }

    return <div className="muted">Uses property and business date from PMS context.</div>;
  }

  return (
    <div className="page-grid agent-harness-page">
      <PageHeader
        title="AI Assistant / Agent Harness"
        subtitle="Approved automation tasks using PMS permissions, audit logs, and workflow validation."
        metadata={`${propertyCode} • ${propertyName} • ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">{propertyCode}</div>
            <div className="pill">Business Date: {businessDate}</div>
            <div className="pill">Access: {role ? getRoleLabel(role) : "Unknown"}</div>
          </>
        }
      />

      {error ? <div className="error-box">{error}</div> : null}

      {!visibleTasks.length ? (
        <section className="card">
          <div className="section-heading">
            <div>
              <h2>Permission Required</h2>
              <p className="muted">{permissionMessage("Agent Harness")}</p>
            </div>
            <Bot aria-hidden="true" size={28} />
          </div>
        </section>
      ) : (
        <div className="agent-task-grid">
          {tasks.map((task) => {
            const allowed = Boolean(role && roleCanUseTask(role, task));
            if (!allowed) return null;
            return (
              <section className="card agent-task-card" key={task.key}>
                <div className="section-heading">
                  <div>
                    <h2>{task.title}</h2>
                    <p className="muted">{task.subtitle}</p>
                    <div className="agent-badge-row">
                      {task.readOnly ? <span className="pill pill-muted">Read Only</span> : null}
                      {task.suggestionOnly ? <span className="pill pill-warning">Suggestion Only</span> : null}
                    </div>
                  </div>
                  {task.icon}
                </div>

                <form className="page-grid" onSubmit={(event) => runTask(event, task)}>
                  {renderFields(task)}
                  <div className="form-actions sticky-action-row">
                    <button className="primary-btn" type="submit" disabled={busyTask === task.key}>
                      {busyTask === task.key ? "Running..." : "Run Task"}
                    </button>
                  </div>
                </form>

                {results[task.key] ? (
                  <ResultCard result={results[task.key]!} suggestionOnly={task.suggestionOnly} />
                ) : null}
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} required={required} />
    </label>
  );
}
