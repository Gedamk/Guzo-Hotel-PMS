import { useEffect, useMemo, useState } from "react";
import PageHeader from "../../components/PageHeader";
import KpiCard from "../../components/KpiCard";
import DataTable from "../../components/DataTable";
import { usePmsContext } from "../../context/PmsContext";
import { fetchFrontdeskBookings } from "../../services/pmsService";
import { getErrorMessage } from "../../services/http";
import {
  assignRoom,
  checkInGuest,
  checkOutGuest,
} from "../../services/frontdeskActions";
import type { FrontdeskBooking } from "../../types/pms";

function statusClass(status: string) {
  const s = String(status || "").toLowerCase();
  if (s === "in_house" || s === "checked_in") return "pill pill-success";
  if (s === "checked_out") return "pill pill-muted";
  if (s === "reserved" || s === "confirmed") return "pill pill-warning";
  if (s === "cancelled" || s === "no_show") return "pill pill-danger";
  return "pill";
}

export default function FrontDeskPage() {
  const { propertyCode, businessDate, refreshKey, refreshData } = usePmsContext();

  const [rows, setRows] = useState<FrontdeskBooking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [busyBookingId, setBusyBookingId] = useState<number | null>(null);
  const [roomInputs, setRoomInputs] = useState<Record<number, string>>({});

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

  const arrivals = useMemo(
    () => rows.filter((row) => row.check_in_date === businessDate),
    [rows, businessDate]
  );

  const departures = useMemo(
    () => rows.filter((row) => row.check_out_date === businessDate),
    [rows, businessDate]
  );

  const inHouse = useMemo(
    () =>
      rows.filter((row) => {
        const status = String(row.booking_status || "").toLowerCase();
        return status === "in_house" || status === "checked_in";
      }),
    [rows]
  );

  return (
    <div className="page-grid">
      <PageHeader
        title="Front Desk"
        subtitle={`Guest movement and room control for ${propertyCode} on ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">Arrivals: {arrivals.length}</div>
            <div className="pill">Departures: {departures.length}</div>
            <div className="pill">In House: {inHouse.length}</div>
          </>
        }
      />

      {loading ? (
        <div className="card">Loading front desk activity...</div>
      ) : (
        <>
          {error ? <div className="error-box">{error}</div> : null}
          {actionMessage ? <div className="card">{actionMessage}</div> : null}

          <div className="kpi-grid">
            <KpiCard label="Total Bookings" value={String(rows.length)} />
            <KpiCard label="Arrivals Today" value={String(arrivals.length)} />
            <KpiCard label="Departures Today" value={String(departures.length)} />
            <KpiCard label="In House" value={String(inHouse.length)} />
          </div>

          <div className="page-grid two-col">
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Arrivals</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Assign room and complete check-in for arriving guests
              </div>

              <DataTable
                rows={arrivals}
                emptyMessage="No arrivals for this business date."
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
                    key: "status",
                    header: "Status",
                    render: (row) => (
                      <span className={statusClass(row.booking_status)}>
                        {row.booking_status}
                      </span>
                    ),
                  },
                  {
                    key: "room_assign",
                    header: "Assign Room",
                    render: (row) => (
                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        <input
                          value={roomInputs[row.id] || ""}
                          onChange={(e) =>
                            setRoomInputs((prev) => ({
                              ...prev,
                              [row.id]: e.target.value,
                            }))
                          }
                          placeholder="Room"
                          style={{
                            width: "88px",
                            padding: "8px 10px",
                            background: "#0b1220",
                            color: "white",
                            border: "1px solid var(--line)",
                            borderRadius: "10px",
                          }}
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
                    header: "Check In",
                    render: (row) => (
                      <button
                        className="small-btn"
                        disabled={busyBookingId === row.id}
                        onClick={() => handleCheckIn(row)}
                      >
                        Check In
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
                    render: (row) => (
                      <span className={statusClass(row.booking_status)}>
                        {row.booking_status}
                      </span>
                    ),
                  },
                  {
                    key: "action",
                    header: "Check Out",
                    render: (row) => (
                      <button
                        className="small-btn"
                        disabled={busyBookingId === row.id}
                        onClick={() => handleCheckOut(row)}
                      >
                        Check Out
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
              emptyMessage="No in-house guests for this business date."
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
                  header: "Check In",
                  render: (row) => row.check_in_date,
                },
                {
                  key: "check_out_date",
                  header: "Check Out",
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
                  render: (row) => (
                    <span className={statusClass(row.booking_status)}>
                      {row.booking_status}
                    </span>
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
