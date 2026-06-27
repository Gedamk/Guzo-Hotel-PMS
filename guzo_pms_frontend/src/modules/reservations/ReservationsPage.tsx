import { useEffect, useMemo, useState } from "react";
import PageHeader from "../../components/PageHeader";
import KpiCard from "../../components/KpiCard";
import DataTable from "../../components/DataTable";
import { usePmsContext } from "../../context/PmsContext";
import { fetchFrontdeskBookings } from "../../services/pmsService";
import { getErrorMessage } from "../../services/http";
import {
  applyReservationAction,
  type ReservationWorkflowAction,
} from "../../services/reservationActions";
import type { FrontdeskBooking } from "../../types/pms";

function money(value: number | string | null | undefined) {
  const n = Number(value ?? 0);
  return Number.isFinite(n)
    ? new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(n)
    : "0.00";
}

function statusClass(status: string) {
  const s = String(status || "").toLowerCase();
  if (s === "reserved" || s === "confirmed") return "pill pill-warning";
  if (s === "pending_guarantee" || s === "pending") return "pill pill-warning";
  if (s === "in_house" || s === "checked_in") return "pill pill-success";
  if (s === "checked_out") return "pill pill-muted";
  if (s === "cancelled" || s === "no_show") return "pill pill-danger";
  return "pill";
}

function sourceClass(source: string) {
  const s = String(source || "").toLowerCase();
  if (s.includes("walk")) return "pill pill-success";
  if (s.includes("telegram")) return "pill pill-inspected";
  if (s.includes("ota")) return "pill pill-warning";
  if (s.includes("corporate")) return "pill pill-muted";
  return "pill";
}

function normalizeSource(row: any) {
  return String(
    row.source ||
      row.booking_source ||
      row.channel ||
      row.market_source ||
      "direct"
  ).toLowerCase();
}

function normalizeRoom(row: any) {
  return row.room_number || row.room_no || row.roomNo || row.room_type || "-";
}

function normalizeAmount(row: any) {
  return Number(row.total_amount || row.amount || row.total || 0);
}

function bookingStatus(row: any) {
  return String(row.booking_status || "").toLowerCase();
}

function paymentStatus(row: any) {
  return String(row.payment_status || "pending").toLowerCase();
}

function isInHouse(row: any) {
  const status = bookingStatus(row);
  return status === "in_house" || status === "checked_in";
}

function isClosedReservation(row: any) {
  const status = bookingStatus(row);
  return ["checked_out", "cancelled", "no_show", "no-show"].includes(status);
}

function isOnlineChannel(row: any) {
  const source = normalizeSource(row);
  return (
    source.includes("telegram") ||
    source.includes("chatbot") ||
    source.includes("website") ||
    source.includes("online")
  );
}

function guaranteeStatus(row: any) {
  const status = bookingStatus(row);
  const payment = paymentStatus(row);
  const guaranteedPayments = [
    "paid",
    "authorized",
    "approved",
    "deposit_paid",
    "guaranteed",
    "guarantee_on_file",
    "card_authorized",
  ];
  if (guaranteedPayments.includes(payment)) return "guaranteed";
  if (status === "confirmed" && payment !== "pending") return "guaranteed";
  if (status === "pending_guarantee" || payment === "pending" || payment === "unpaid") {
    return "pending_guarantee";
  }
  return "non_guaranteed";
}

function formatStatus(status: string) {
  return String(status || "").replace(/_/g, " ");
}

function actionLabels(row: any) {
  if (guaranteeStatus(row) === "pending_guarantee") {
    return [
      "Review Guarantee",
      "Send Deposit Link",
      "Record Deposit",
      "Request Card Guarantee",
      "Approve Pay at Hotel",
      "Mark Guaranteed",
      "Hold at Front Desk",
      "Cancel by Deadline",
    ];
  }
  return ["Open", "Send Confirmation", "Add Alert", "Add Trace"];
}

const actionByLabel: Record<string, ReservationWorkflowAction> = {
  "Review Guarantee": "review_guarantee",
  "Send Deposit Link": "send_deposit_link",
  "Record Deposit": "record_deposit",
  "Request Card Guarantee": "request_card_guarantee",
  "Approve Pay at Hotel": "approve_pay_at_hotel",
  "Mark Guaranteed": "mark_guaranteed",
  "Hold at Front Desk": "hold_at_frontdesk",
  "Cancel by Deadline": "cancel_by_deadline",
  Open: "open_reservation",
  "Send Confirmation": "send_confirmation",
  "Add Alert": "add_alert",
  "Add Trace": "add_trace",
};

function handoffStatus(row: any) {
  if (guaranteeStatus(row) === "pending_guarantee") {
    return "Blocked - Guarantee Review Required";
  }
  if (guaranteeStatus(row) === "guaranteed") return "Ready for Front Desk";
  return "Review Before Handoff";
}

function ActionButtons({
  row,
  busy,
  onAction,
}: {
  row: any;
  busy: boolean;
  onAction: (row: any, action: ReservationWorkflowAction, label: string) => void;
}) {
  return (
    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
      {actionLabels(row).map((label, index) => (
        <button
          className={index === 0 ? "primary-btn" : "small-btn"}
          disabled={busy}
          key={label}
          onClick={() => onAction(row, actionByLabel[label], label)}
          type="button"
        >
          {label}
        </button>
      ))}
    </div>
  );
}

export default function ReservationsPage() {
  const { propertyCode, businessDate, refreshKey, refreshData } = usePmsContext();

  const [rows, setRows] = useState<FrontdeskBooking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [selectedReservation, setSelectedReservation] = useState<FrontdeskBooking | null>(null);

  const [statusFilter, setStatusFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [searchText, setSearchText] = useState("");

  async function loadRows() {
    try {
      setLoading(true);
      setError("");
      const data = await fetchFrontdeskBookings(propertyCode, businessDate);
      setRows(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRows();
  }, [propertyCode, businessDate, refreshKey]);

  async function handleReservationAction(
    row: FrontdeskBooking,
    action: ReservationWorkflowAction,
    label: string
  ) {
    try {
      setError("");
      setActionMessage("");
      setBusyAction(`${row.id}-${action}`);
      if (action === "open_reservation") {
        setSelectedReservation(row);
      }
      await applyReservationAction({
        bookingId: row.id,
        propertyCode,
        businessDate,
        action,
        note: `${label} completed from Reservations workspace.`,
      });
      setActionMessage(`${label} completed for ${row.guest_name}.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyAction(null);
    }
  }

  const filteredRows = useMemo(() => {
    return rows.filter((row: any) => {
      const source = normalizeSource(row);
      const room = String(normalizeRoom(row)).toLowerCase();
      const guest = String(row.guest_name || "").toLowerCase();
      const bookingId = String(row.id || "");
      const status = bookingStatus(row);

      const statusOk =
        statusFilter === "all" ? true : status === statusFilter.toLowerCase();

      const sourceOk =
        sourceFilter === "all" ? true : source.includes(sourceFilter.toLowerCase());

      const q = searchText.trim().toLowerCase();
      const searchOk =
        q === ""
          ? true
          : guest.includes(q) || bookingId.includes(q) || room.includes(q);

      return statusOk && sourceOk && searchOk;
    });
  }, [rows, statusFilter, sourceFilter, searchText]);

  const arrivals = useMemo(
    () => filteredRows.filter((row) => row.check_in_date === businessDate && !isClosedReservation(row)),
    [filteredRows, businessDate]
  );

  const expectedArrivals = useMemo(
    () => arrivals.filter((row) => !isInHouse(row)),
    [arrivals]
  );

  const departures = useMemo(
    () => filteredRows.filter((row) => row.check_out_date === businessDate),
    [filteredRows, businessDate]
  );

  const stayovers = useMemo(
    () =>
      filteredRows.filter((row) => {
        return (
          row.check_in_date < businessDate &&
          row.check_out_date > businessDate &&
          isInHouse(row)
        );
      }),
    [filteredRows, businessDate]
  );

  const onlineReservations = useMemo(
    () => filteredRows.filter((row) => isOnlineChannel(row)),
    [filteredRows]
  );

  const waitingGuarantee = useMemo(
    () =>
      filteredRows.filter(
        (row) => guaranteeStatus(row) !== "guaranteed" && !isClosedReservation(row)
      ),
    [filteredRows]
  );

  const guaranteedReservations = useMemo(
    () =>
      filteredRows.filter(
        (row) => guaranteeStatus(row) === "guaranteed" && !isClosedReservation(row)
      ),
    [filteredRows]
  );

  return (
    <div className="page-grid">
      <PageHeader
        title="Reservations"
        subtitle="Reservation control workspace."
        metadata={`${propertyCode} • ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">Online: {onlineReservations.length}</div>
            <div className="pill">Waiting Guarantee: {waitingGuarantee.length}</div>
            <div className="pill">Expected Arrivals: {expectedArrivals.length}</div>
            <div className="pill">Departures: {departures.length}</div>
          </>
        }
      />

      {loading ? (
        <div className="card">Loading reservations workspace...</div>
      ) : (
        <>
          {error ? <div className="error-box">{error}</div> : null}
          {actionMessage ? <div className="card">{actionMessage}</div> : null}
          {selectedReservation ? (
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Reservation Detail</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Guest profile, guarantee status, source, and handoff notes for the selected reservation.
              </div>
              <div className="dashboard-metric-strip">
                <div><span>Guest</span><strong>{selectedReservation.guest_name}</strong></div>
                <div><span>Stay</span><strong>{selectedReservation.check_in_date} to {selectedReservation.check_out_date}</strong></div>
                <div><span>Room</span><strong>{normalizeRoom(selectedReservation)}</strong></div>
                <div><span>Source</span><strong>{normalizeSource(selectedReservation)}</strong></div>
                <div><span>Status</span><strong>{formatStatus(selectedReservation.booking_status)}</strong></div>
                <div><span>Payment</span><strong>{paymentStatus(selectedReservation)}</strong></div>
              </div>
              {selectedReservation.notes ? (
                <div className="muted" style={{ marginTop: "14px" }}>
                  {selectedReservation.notes}
                </div>
              ) : null}
            </div>
          ) : null}

          <div className="kpi-grid">
            <KpiCard label="Total Reservations" value={String(filteredRows.length)} />
            <KpiCard label="Online / Telegram" value={String(onlineReservations.length)} />
            <KpiCard label="Waiting Guarantee" value={String(waitingGuarantee.length)} />
            <KpiCard label="Guaranteed" value={String(guaranteedReservations.length)} />
            <KpiCard label="Arrival Handoff" value={String(expectedArrivals.length)} />
            <KpiCard label="In-House / Stayovers" value={String(stayovers.length)} />
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0 }}>Reservation Filters</h2>
            <div className="muted" style={{ marginBottom: "14px" }}>
              Search and filter bookings by status, source, guest, booking ID, or room number
            </div>

            <div
              style={{
                display: "grid",
                gap: "14px",
                gridTemplateColumns: "1.2fr 1fr 1fr",
              }}
            >
              <div className="field">
                <label>Search</label>
                <input
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  placeholder="Guest name, booking ID, or room"
                />
              </div>

              <div className="field">
                <label>Status</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="all">All Statuses</option>
                  <option value="reserved">reserved</option>
                  <option value="pending_guarantee">pending_guarantee</option>
                  <option value="pending">pending</option>
                  <option value="confirmed">confirmed</option>
                  <option value="in_house">in_house</option>
                  <option value="checked_in">checked_in</option>
                  <option value="checked_out">checked_out</option>
                  <option value="cancelled">cancelled</option>
                  <option value="no_show">no_show</option>
                </select>
              </div>

              <div className="field">
                <label>Source</label>
                <select
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                >
                  <option value="all">All Sources</option>
                  <option value="direct">direct</option>
                  <option value="walk_in">walk_in</option>
                  <option value="ota">ota</option>
                  <option value="corporate">corporate</option>
                  <option value="telegram">telegram</option>
                </select>
              </div>
            </div>
          </div>

          <div className="page-grid two-col">
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Online Reservation Inbox</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Telegram and chatbot bookings enter Reservations first for validation, guarantee review, and confirmation.
              </div>

              <DataTable
                rows={onlineReservations}
                emptyMessage="No online reservations match the selected filters."
                columns={[
                  { key: "id", header: "Booking ID", render: (row: any) => `#${row.id}` },
                  { key: "guest_name", header: "Guest", render: (row: any) => row.guest_name },
                  {
                    key: "dates",
                    header: "Stay",
                    render: (row: any) => `${row.check_in_date} to ${row.check_out_date}`,
                  },
                  { key: "room", header: "Room Type", render: (row: any) => row.room_type || "-" },
                  {
                    key: "guarantee",
                    header: "Guarantee",
                    render: (row: any) => (
                      <span className={statusClass(guaranteeStatus(row))}>
                        {formatStatus(guaranteeStatus(row))}
                      </span>
                    ),
                  },
                  {
                    key: "action",
                    header: "Action Required",
                    render: (row: any) => (
                      <ActionButtons
                        row={row}
                        busy={Boolean(busyAction?.startsWith(`${row.id}-`))}
                        onAction={handleReservationAction}
                      />
                    ),
                  },
                ]}
              />
            </div>

            <div className="card">
              <h2 style={{ marginTop: 0 }}>Guarantee Desk</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Unpaid, pay-at-hotel, and non-guaranteed bookings stay here until deposit, card authorization, or manager approval.
              </div>

              <DataTable
                rows={waitingGuarantee}
                emptyMessage="No reservations are waiting for guarantee."
                columns={[
                  { key: "id", header: "Booking ID", render: (row: any) => `#${row.id}` },
                  { key: "guest_name", header: "Guest", render: (row: any) => row.guest_name },
                  {
                    key: "source",
                    header: "Source",
                    render: (row: any) => {
                      const source = normalizeSource(row);
                      return <span className={sourceClass(source)}>{source}</span>;
                    },
                  },
                  {
                    key: "payment_method",
                    header: "Payment Method",
                    render: (row: any) => row.payment_method || "pending",
                  },
                  {
                    key: "payment_status",
                    header: "Payment",
                    render: (row: any) => (
                      <span className={statusClass(guaranteeStatus(row))}>
                        {paymentStatus(row)}
                      </span>
                    ),
                  },
                  {
                    key: "action",
                    header: "Guarantee Actions",
                    render: (row: any) => (
                      <ActionButtons
                        row={row}
                        busy={Boolean(busyAction?.startsWith(`${row.id}-`))}
                        onAction={handleReservationAction}
                      />
                    ),
                  },
                ]}
              />
            </div>
          </div>

          <div className="page-grid two-col">
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Arrival Handoff</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Confirmed or pending-guarantee reservations arriving today, not yet checked in.
              </div>

              <DataTable
                rows={expectedArrivals}
                emptyMessage="No expected arrivals for this business date."
                columns={[
                  {
                    key: "id",
                    header: "Booking ID",
                    render: (row: any) => `#${row.id}`,
                  },
                  {
                    key: "guest_name",
                    header: "Guest",
                    render: (row: any) => row.guest_name,
                  },
                  {
                    key: "source",
                    header: "Source",
                    render: (row: any) => {
                      const source = normalizeSource(row);
                      return <span className={sourceClass(source)}>{source}</span>;
                    },
                  },
                  {
                    key: "check_in_date",
                    header: "Arrival",
                    render: (row: any) => row.check_in_date,
                  },
                  {
                    key: "room_number",
                    header: "Room",
                    render: (row: any) => normalizeRoom(row),
                  },
                  {
                    key: "guarantee",
                    header: "Guarantee",
                    render: (row: any) => (
                      <span className={statusClass(guaranteeStatus(row))}>
                        {formatStatus(guaranteeStatus(row))}
                      </span>
                    ),
                  },
                  {
                    key: "handoff",
                    header: "Handoff",
                    render: (row: any) => (
                      <span className={statusClass(guaranteeStatus(row))}>
                        {handoffStatus(row)}
                      </span>
                    ),
                  },
                  {
                    key: "status",
                    header: "Status",
                    render: (row: any) => (
                      <span className={statusClass(row.booking_status)}>
                        {row.booking_status}
                      </span>
                    ),
                  },
                  {
                    key: "action",
                    header: "Handoff Actions",
                    render: (row: any) => (
                      <ActionButtons
                        row={row}
                        busy={Boolean(busyAction?.startsWith(`${row.id}-`))}
                        onAction={handleReservationAction}
                      />
                    ),
                  },
                ]}
              />
            </div>

            <div className="card">
              <h2 style={{ marginTop: 0 }}>Departures</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Guests expected to depart on the selected business date
              </div>

              <DataTable
                rows={departures}
                emptyMessage="No departures for this business date."
                columns={[
                  {
                    key: "id",
                    header: "Booking ID",
                    render: (row: any) => `#${row.id}`,
                  },
                  {
                    key: "guest_name",
                    header: "Guest",
                    render: (row: any) => row.guest_name,
                  },
                  {
                    key: "source",
                    header: "Source",
                    render: (row: any) => {
                      const source = normalizeSource(row);
                      return <span className={sourceClass(source)}>{source}</span>;
                    },
                  },
                  {
                    key: "check_out_date",
                    header: "Departure",
                    render: (row: any) => row.check_out_date,
                  },
                  {
                    key: "room_number",
                    header: "Room",
                    render: (row: any) => normalizeRoom(row),
                  },
                  {
                    key: "status",
                    header: "Status",
                    render: (row: any) => (
                      <span className={statusClass(row.booking_status)}>
                        {row.booking_status}
                      </span>
                    ),
                  },
                ]}
              />
            </div>
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0 }}>Reservation Register</h2>
            <div className="muted" style={{ marginBottom: "14px" }}>
              Full reservation list for the selected property and filter context
            </div>

            <DataTable
              rows={filteredRows}
              emptyMessage="No reservations match the selected filters."
              columns={[
                {
                  key: "id",
                  header: "Booking ID",
                  render: (row: any) => `#${row.id}`,
                },
                {
                  key: "guest_name",
                  header: "Guest",
                  render: (row: any) => row.guest_name,
                },
                {
                  key: "source",
                  header: "Source",
                  render: (row: any) => {
                    const source = normalizeSource(row);
                    return <span className={sourceClass(source)}>{source}</span>;
                  },
                },
                {
                  key: "check_in_date",
                  header: "Check-In",
                  render: (row: any) => row.check_in_date,
                },
                {
                  key: "check_out_date",
                  header: "Check-Out",
                  render: (row: any) => row.check_out_date,
                },
                {
                  key: "room_number",
                  header: "Room / Type",
                  render: (row: any) => normalizeRoom(row),
                },
                {
                  key: "guarantee",
                  header: "Guarantee",
                  render: (row: any) => (
                    <span className={statusClass(guaranteeStatus(row))}>
                      {formatStatus(guaranteeStatus(row))}
                    </span>
                  ),
                },
                {
                  key: "booking_status",
                  header: "Status",
                  render: (row: any) => (
                    <span className={statusClass(row.booking_status)}>
                      {row.booking_status}
                    </span>
                  ),
                },
                {
                  key: "payment_status",
                  header: "Payment",
                  render: (row: any) => row.payment_status || "pending",
                },
                {
                  key: "total_amount",
                  header: "Amount",
                  render: (row: any) => money(normalizeAmount(row)),
                },
                {
                  key: "action",
                  header: "Action",
                  render: (row: any) => (
                    <ActionButtons
                      row={row}
                      busy={Boolean(busyAction?.startsWith(`${row.id}-`))}
                      onAction={handleReservationAction}
                    />
                  ),
                },
              ]}
            />
          </div>
        </>
      )}
    </div>
  );
}
