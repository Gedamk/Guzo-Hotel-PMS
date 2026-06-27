import { useEffect, useMemo, useState } from "react";
import PageHeader from "../../components/PageHeader";
import KpiCard from "../../components/KpiCard";
import DataTable from "../../components/DataTable";
import { HandoffBadge } from "../../components/ui/HandoffBadge";
import { LoadingState } from "../../components/ui/LoadingState";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { usePmsContext } from "../../context/PmsContext";
import { fetchFrontdeskBookings } from "../../services/pmsService";
import { getErrorMessage } from "../../services/http";
import {
  assignRoom,
  checkInGuest,
  checkOutGuest,
  createWalkInBooking,
} from "../../services/frontdeskActions";
import type { FrontdeskBooking } from "../../types/pms";

type WalkInFormState = {
  guestName: string;
  roomNumber: string;
  roomType: string;
  checkInDate: string;
  checkOutDate: string;
  ratePerNightEtb: string;
  totalAmountEtb: string;
  paymentMethod: string;
  amountPaidNowEtb: string;
  notes: string;
};

function defaultWalkInForm(businessDate: string): WalkInFormState {
  return {
    guestName: "",
    roomNumber: "",
    roomType: "Standard",
    checkInDate: businessDate,
    checkOutDate: businessDate,
    ratePerNightEtb: "",
    totalAmountEtb: "",
    paymentMethod: "Cash",
    amountPaidNowEtb: "",
    notes: "",
  };
}

function parseOptionalNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function bookingStatus(row: FrontdeskBooking) {
  return String(row.booking_status || "").toLowerCase();
}

function paymentStatus(row: FrontdeskBooking) {
  const handoff = row as FrontdeskBooking & {
    deposit_status?: string;
    guarantee_status?: string;
  };
  return String(
    row.payment_status || handoff.deposit_status || handoff.guarantee_status || "pending"
  ).toLowerCase();
}

function guaranteeHandoff(row: FrontdeskBooking) {
  const status = paymentStatus(row);
  if (status === "paid" || status === "deposit_paid" || status === "guaranteed") {
    return <HandoffBadge label="Guarantee ready" variant="success" />;
  }
  if (status.includes("request") || status.includes("deposit")) {
    return <HandoffBadge label="Deposit requested" variant="warning" />;
  }
  return <HandoffBadge label="Guarantee review" variant="warning" />;
}

function roomAssignmentHandoff(row: FrontdeskBooking) {
  if (row.room_number) {
    return <HandoffBadge label={`Room ${row.room_number}`} variant="success" />;
  }
  return <HandoffBadge label="Room TBD" variant="warning" />;
}

function readinessHandoff(row: FrontdeskBooking) {
  const readiness = String((row as any).room_readiness || (row as any).hk_status || "").toLowerCase();
  if (readiness.includes("inspect") || readiness === "vacant_clean" || readiness.includes("clean")) {
    return <HandoffBadge label="HK ready" variant="success" />;
  }
  if (row.room_number) {
    return <HandoffBadge label="HK check" variant="warning" />;
  }
  return <HandoffBadge label="Assign first" variant="neutral" />;
}

function isInHouse(row: FrontdeskBooking) {
  return ["in_house", "checked_in"].includes(bookingStatus(row));
}

function isExpectedCheckIn(row: FrontdeskBooking) {
  return ["confirmed", "reserved", "pending", "pending_guarantee"].includes(
    bookingStatus(row)
  );
}

export default function FrontDeskPage() {
  const { propertyCode, businessDate, refreshKey, refreshData } = usePmsContext();

  const [rows, setRows] = useState<FrontdeskBooking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [busyBookingId, setBusyBookingId] = useState<number | null>(null);
  const [roomInputs, setRoomInputs] = useState<Record<number, string>>({});
  const [showWalkIn, setShowWalkIn] = useState(false);
  const [walkInSubmitting, setWalkInSubmitting] = useState(false);
  const [walkInForm, setWalkInForm] = useState<WalkInFormState>(() =>
    defaultWalkInForm(businessDate)
  );

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

  async function handleCheckIn(row: FrontdeskBooking) {
    try {
      setBusyBookingId(row.id);
      setActionMessage("");
      setError("");
      await checkInGuest({
        bookingId: row.id,
        propertyCode,
        businessDate,
      });
      setActionMessage(`Check-in completed for ${row.guest_name}.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyBookingId(null);
    }
  }

  async function handleCheckOut(row: FrontdeskBooking) {
    try {
      setBusyBookingId(row.id);
      setActionMessage("");
      setError("");
      await checkOutGuest({
        bookingId: row.id,
        propertyCode,
        businessDate,
      });
      setActionMessage(`Check-out completed for ${row.guest_name}.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyBookingId(null);
    }
  }

  async function handleAssignRoom(row: FrontdeskBooking) {
    const roomNumber = String(roomInputs[row.id] || "").trim();

    if (!roomNumber) {
      setError(`Enter a room number first for ${row.guest_name}.`);
      return;
    }

    try {
      setBusyBookingId(row.id);
      setActionMessage("");
      setError("");
      await assignRoom({
        bookingId: row.id,
        propertyCode,
        roomNumber,
      });
      setActionMessage(`Room ${roomNumber} assigned to ${row.guest_name}.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyBookingId(null);
    }
  }

  async function handleCreateWalkIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const guestName = walkInForm.guestName.trim();
    if (!guestName) {
      setError("Guest name is required for a walk-in booking.");
      return;
    }

    try {
      setWalkInSubmitting(true);
      setActionMessage("");
      setError("");
      await createWalkInBooking({
        propertyCode,
        guestName,
        checkInDate: walkInForm.checkInDate,
        checkOutDate: walkInForm.checkOutDate,
        roomNumber: walkInForm.roomNumber.trim() || undefined,
        roomType: walkInForm.roomType.trim() || undefined,
        ratePerNightEtb: parseOptionalNumber(walkInForm.ratePerNightEtb),
        totalAmountEtb: parseOptionalNumber(walkInForm.totalAmountEtb),
        paymentMethod: walkInForm.paymentMethod,
        amountPaidNowEtb: parseOptionalNumber(walkInForm.amountPaidNowEtb),
        notes: walkInForm.notes.trim() || undefined,
      });
      setShowWalkIn(false);
      setWalkInForm(defaultWalkInForm(businessDate));
      setActionMessage(`Walk-in booking created for ${guestName}.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setWalkInSubmitting(false);
    }
  }

  const arrivals = useMemo(
    () => rows.filter((row) => row.check_in_date === businessDate),
    [rows, businessDate]
  );

  const expectedCheckIns = useMemo(
    () => arrivals.filter(isExpectedCheckIn),
    [arrivals]
  );

  const checkedInToday = useMemo(
    () => arrivals.filter(isInHouse),
    [arrivals]
  );

  const departures = useMemo(
    () => rows.filter((row) => row.check_out_date === businessDate),
    [rows, businessDate]
  );

  const inHouse = useMemo(
    () => rows.filter(isInHouse),
    [rows]
  );

  const noShows = useMemo(
    () =>
      rows.filter((row) => {
        const status = String(row.booking_status || "").toLowerCase();
        return status === "no_show" || status === "no-show";
      }),
    [rows]
  );

  const walkIns = useMemo(
    () =>
      rows.filter((row) =>
        String(row.channel || row.source || "").toLowerCase().includes("walk")
      ),
    [rows]
  );

  return (
    <div className="page-grid">
      <PageHeader
        title="Front Desk"
        subtitle="Guest movement and room control."
        metadata={`${propertyCode} • ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">Expected Check-ins: {expectedCheckIns.length}</div>
            <div className="pill">Checked-In Today: {checkedInToday.length}</div>
            <div className="pill">Departures: {departures.length}</div>
            <div className="pill">In-House: {inHouse.length}</div>
            <button className="small-btn" onClick={() => setShowWalkIn(true)}>
              New Walk-In
            </button>
          </>
        }
      />

      {showWalkIn ? (
        <div className="card">
          <form className="page-grid" onSubmit={handleCreateWalkIn}>
            <div className="topbar" style={{ padding: 0 }}>
              <div>
                <h2 style={{ margin: 0 }}>Walk-In Booking</h2>
                <div className="muted">
                  Create an In-House guest directly from the Front Desk.
                </div>
              </div>
              <button
                className="small-btn"
                type="button"
                onClick={() => setShowWalkIn(false)}
              >
                Close
              </button>
            </div>

            <div className="form-grid">
              <label>
                Guest Name
                <input
                  value={walkInForm.guestName}
                  onChange={(event) =>
                    setWalkInForm((prev) => ({
                      ...prev,
                      guestName: event.target.value,
                    }))
                  }
                  placeholder="Guest full name"
                  required
                />
              </label>
              <label>
                Room Number
                <input
                  value={walkInForm.roomNumber}
                  onChange={(event) =>
                    setWalkInForm((prev) => ({
                      ...prev,
                      roomNumber: event.target.value,
                    }))
                  }
                  placeholder="Optional"
                />
              </label>
              <label>
                Room Type
                <select
                  value={walkInForm.roomType}
                  onChange={(event) =>
                    setWalkInForm((prev) => ({
                      ...prev,
                      roomType: event.target.value,
                    }))
                  }
                >
                  <option>Standard</option>
                  <option>Deluxe</option>
                  <option>Suite</option>
                  <option>Twin</option>
                </select>
              </label>
              <label>
                Check-In
                <input
                  type="date"
                  value={walkInForm.checkInDate}
                  onChange={(event) =>
                    setWalkInForm((prev) => ({
                      ...prev,
                      checkInDate: event.target.value,
                    }))
                  }
                  required
                />
              </label>
              <label>
                Check-Out
                <input
                  type="date"
                  value={walkInForm.checkOutDate}
                  onChange={(event) =>
                    setWalkInForm((prev) => ({
                      ...prev,
                      checkOutDate: event.target.value,
                    }))
                  }
                  required
                />
              </label>
              <label>
                Rate / Night ETB
                <input
                  inputMode="decimal"
                  value={walkInForm.ratePerNightEtb}
                  onChange={(event) =>
                    setWalkInForm((prev) => ({
                      ...prev,
                      ratePerNightEtb: event.target.value,
                    }))
                  }
                  placeholder="0.00"
                />
              </label>
              <label>
                Total ETB
                <input
                  inputMode="decimal"
                  value={walkInForm.totalAmountEtb}
                  onChange={(event) =>
                    setWalkInForm((prev) => ({
                      ...prev,
                      totalAmountEtb: event.target.value,
                    }))
                  }
                  placeholder="Auto from rate if empty"
                />
              </label>
              <label>
                Payment Method
                <select
                  value={walkInForm.paymentMethod}
                  onChange={(event) =>
                    setWalkInForm((prev) => ({
                      ...prev,
                      paymentMethod: event.target.value,
                    }))
                  }
                >
                  <option>Cash</option>
                  <option>Card</option>
                  <option>Bank Transfer</option>
                  <option>Mobile Money</option>
                  <option>Pay at Check-Out</option>
                </select>
              </label>
              <label>
                Paid Now ETB
                <input
                  inputMode="decimal"
                  value={walkInForm.amountPaidNowEtb}
                  onChange={(event) =>
                    setWalkInForm((prev) => ({
                      ...prev,
                      amountPaidNowEtb: event.target.value,
                    }))
                  }
                  placeholder="0.00"
                />
              </label>
            </div>

            <label>
              Notes
              <textarea
                value={walkInForm.notes}
                onChange={(event) =>
                  setWalkInForm((prev) => ({
                    ...prev,
                    notes: event.target.value,
                  }))
                }
                placeholder="Guest requests, ID notes, billing remarks"
              />
            </label>

            <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
              <button
                className="small-btn"
                type="button"
                onClick={() => setShowWalkIn(false)}
              >
                Cancel
              </button>
              <button className="primary-btn" type="submit" disabled={walkInSubmitting}>
                {walkInSubmitting ? "Creating..." : "Create Walk-In"}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {loading ? (
        <LoadingState label="Loading front desk activity..." />
      ) : (
        <>
          {error ? <div className="error-box">{error}</div> : null}
          {actionMessage ? <div className="card">{actionMessage}</div> : null}

          <div className="kpi-grid">
            <KpiCard label="Total Bookings" value={String(rows.length)} />
            <KpiCard label="Arrivals Today" value={String(arrivals.length)} />
            <KpiCard label="Expected Check-ins" value={String(expectedCheckIns.length)} />
            <KpiCard label="Checked-In Today" value={String(checkedInToday.length)} />
            <KpiCard label="Departures Today" value={String(departures.length)} />
            <KpiCard label="In-House" value={String(inHouse.length)} />
            <KpiCard label="Walk-Ins" value={String(walkIns.length)} />
            <KpiCard label="No-Shows" value={String(noShows.length)} />
          </div>

          <div className="page-grid two-col">
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Expected Check-ins</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Assign a clean room and complete Check-In for guests not yet In-House
              </div>

              <DataTable
                rows={expectedCheckIns}
                emptyMessage="No expected Check-In guests for this business date."
                columns={[
                  {
                    key: "id",
                    header: "Booking ID",
                    render: (row) => `#${row.id}`,
                  },
                  {
                    key: "guest_name",
                    header: "Guest Name",
                    render: (row) => row.guest_name,
                  },
                  {
                    key: "check_in_date",
                    header: "Arrival Date",
                    render: (row) => row.check_in_date,
                  },
                  {
                    key: "room_type",
                    header: "Room Type",
                    render: (row) => row.room_type || "TBD",
                  },
                  {
                    key: "channel",
                    header: "Source",
                    render: (row) => row.source || row.channel || "Direct",
                  },
                  {
                    key: "payment_status",
                    header: "Payment",
                    render: (row) => <StatusBadge status={paymentStatus(row)} />,
                  },
                  {
                    key: "status",
                    header: "Status",
                    render: (row) => <StatusBadge status={row.booking_status} />,
                  },
                  {
                    key: "handoff",
                    header: "PMS Handoff",
                    render: (row) => (
                      <div className="pms-inline-actions">
                        {roomAssignmentHandoff(row)}
                        {guaranteeHandoff(row)}
                        {readinessHandoff(row)}
                      </div>
                    ),
                  },
                  {
                    key: "room_assign",
                    header: "Assign Room",
                    render: (row) => (
                      <div className="pms-assignment-control">
                        <input
                          value={roomInputs[row.id] || ""}
                          onChange={(e) =>
                            setRoomInputs((prev) => ({
                              ...prev,
                              [row.id]: e.target.value,
                            }))
                          }
                          placeholder="Room"
                        />
                        <button
                          className="small-btn"
                          disabled={busyBookingId === row.id}
                          onClick={() => handleAssignRoom(row)}
                        >
                          Assign
                        </button>
                      </div>
                    ),
                  },
                  {
                    key: "action",
                    header: "Check-In",
                    render: (row) => (
                      <button
                        className="small-btn"
                        disabled={busyBookingId === row.id}
                        onClick={() => handleCheckIn(row)}
                      >
                        Check-In
                      </button>
                    ),
                  },
                ]}
              />
            </div>

            <div className="card">
              <h2 style={{ marginTop: 0 }}>Departures</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Complete guest departure and release room control
              </div>

              <DataTable
                rows={departures}
                emptyMessage="No departures for this business date."
                columns={[
                  {
                    key: "id",
                    header: "Booking ID",
                    render: (row) => `#${row.id}`,
                  },
                  {
                    key: "guest_name",
                    header: "Guest Name",
                    render: (row) => row.guest_name,
                  },
                  {
                    key: "check_out_date",
                    header: "Departure Date",
                    render: (row) => row.check_out_date,
                  },
                  {
                    key: "status",
                    header: "Status",
                    render: (row) => <StatusBadge status={row.booking_status} />,
                  },
                  {
                    key: "action",
                    header: "Check-Out",
                    render: (row) => (
                      <button
                        className="small-btn"
                        disabled={busyBookingId === row.id}
                        onClick={() => handleCheckOut(row)}
                      >
                        Check-Out
                      </button>
                    ),
                  },
                ]}
              />
            </div>
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0 }}>In-House Guests</h2>
            <div className="muted" style={{ marginBottom: "14px" }}>
              Live guest stay control for front office operations
            </div>

            <DataTable
              rows={inHouse}
              emptyMessage="No In-House guests for this business date."
              columns={[
                {
                  key: "id",
                  header: "Booking ID",
                  render: (row) => `#${row.id}`,
                },
                {
                  key: "guest_name",
                  header: "Guest Name",
                  render: (row) => row.guest_name,
                },
                {
                  key: "check_in_date",
                  header: "Check-In",
                  render: (row) => row.check_in_date,
                },
                {
                  key: "check_out_date",
                  header: "Check-Out",
                  render: (row) => row.check_out_date,
                },
                {
                  key: "property_code",
                  header: "Property",
                  render: (row) => row.property_code,
                },
                {
                  key: "status",
                  header: "Status",
                  render: (row) => <StatusBadge status={row.booking_status} />,
                },
              ]}
            />
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0 }}>Checked-In Today</h2>
            <div className="muted" style={{ marginBottom: "14px" }}>
              Guests who arrived today and are already in house
            </div>

            <DataTable
              rows={checkedInToday}
              emptyMessage="No guests have checked in today."
              columns={[
                {
                  key: "id",
                  header: "Booking ID",
                  render: (row) => `#${row.id}`,
                },
                {
                  key: "guest_name",
                  header: "Guest Name",
                  render: (row) => row.guest_name,
                },
                {
                  key: "room_number",
                  header: "Room",
                  render: (row) => row.room_number || "Assigned room pending",
                },
                {
                  key: "status",
                  header: "Status",
                  render: (row) => <StatusBadge status={row.booking_status} />,
                },
                {
                  key: "action",
                  header: "Stay Actions",
                  render: (row) => (
                    <button
                      className="small-btn"
                      disabled={busyBookingId === row.id}
                      onClick={() => handleCheckOut(row)}
                    >
                      Check-Out
                    </button>
                  ),
                },
              ]}
            />
          </div>

          <div className="page-grid two-col">
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Front Office SOP</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Desk checklist for consistent arrivals, walk-ins, and departures.
              </div>
              <div className="sop-list">
                <label className="sop-item">
                  <input type="checkbox" /> Confirm guest identity and reservation details.
                </label>
                <label className="sop-item">
                  <input type="checkbox" /> Assign a clean inspected room before key issue.
                </label>
                <label className="sop-item">
                  <input type="checkbox" /> Capture payment guarantee or deposit note.
                </label>
                <label className="sop-item">
                  <input type="checkbox" /> Review open folio balance before checkout.
                </label>
              </div>
            </div>

            <div className="card">
              <h2 style={{ marginTop: 0 }}>Shift Report</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Operational handover snapshot for the current business date.
              </div>
              <DataTable
                rows={[
                  { label: "Arrivals Today", value: arrivals.length },
                  { label: "Expected Check-ins", value: expectedCheckIns.length },
                  { label: "Checked-In Today", value: checkedInToday.length },
                  { label: "Departures", value: departures.length },
                  { label: "In-House", value: inHouse.length },
                  { label: "Walk-Ins", value: walkIns.length },
                  { label: "No-Shows", value: noShows.length },
                ]}
                columns={[
                  {
                    key: "label",
                    header: "Metric",
                    render: (row) => row.label,
                  },
                  {
                    key: "value",
                    header: "Count",
                    render: (row) => row.value,
                  },
                ]}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
