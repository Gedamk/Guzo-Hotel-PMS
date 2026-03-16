import { useEffect, useMemo, useState } from "react";
import KpiCard from "../../components/KpiCard";
import PageHeader from "../../components/PageHeader";
import DataTable from "../../components/DataTable";
import { usePmsContext } from "../../context/PmsContext";
import {
  fetchDailyKpi,
  fetchFrontdeskBookings,
  fetchHealth,
  fetchRoomStatusBoard,
  buildDailyManagerReportUrl,
} from "../../services/pmsService";
import { getErrorMessage } from "../../services/http";
import type {
  DashboardKpi,
  FrontdeskBooking,
  HealthResponse,
  RoomStatusItem,
} from "../../types/pms";

function money(value: number) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value || 0);
}

function pillClass(status: string) {
  const s = String(status || "").toLowerCase();
  if (s === "in_house" || s === "checked_in") return "pill pill-success";
  if (s === "checked_out") return "pill pill-muted";
  if (s === "reserved" || s === "confirmed") return "pill pill-warning";
  return "pill";
}

export default function DashboardPage() {
  const { propertyCode, businessDate, refreshKey } = usePmsContext();

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [kpi, setKpi] = useState<DashboardKpi | null>(null);
  const [bookings, setBookings] = useState<FrontdeskBooking[]>([]);
  const [rooms, setRooms] = useState<RoomStatusItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError("");

        const [healthData, kpiData, bookingsData, roomsData] = await Promise.all([
          fetchHealth(),
          fetchDailyKpi(propertyCode, businessDate),
          fetchFrontdeskBookings(propertyCode, businessDate),
          fetchRoomStatusBoard(propertyCode, businessDate),
        ]);

        setHealth(healthData);
        setKpi(kpiData);
        setBookings(bookingsData);
        setRooms(roomsData);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [propertyCode, businessDate, refreshKey]);

  const arrivals = useMemo(
    () => bookings.filter((b) => b.check_in_date === businessDate),
    [bookings, businessDate]
  );

  const departures = useMemo(
    () => bookings.filter((b) => b.check_out_date === businessDate),
    [bookings, businessDate]
  );

  const inHouse = useMemo(
    () =>
      bookings.filter((b) => {
        const s = String(b.booking_status || "").toLowerCase();
        return s === "in_house" || s === "checked_in";
      }),
    [bookings]
  );

  const occupiedRooms = useMemo(
    () => rooms.filter((room) => room.is_occupied).length,
    [rooms]
  );

  const outOfOrderRooms = useMemo(
    () =>
      rooms.filter((room) => {
        const s = String(room.hk_status || "").toLowerCase();
        return s === "out_of_order" || s === "out_of_service";
      }).length,
    [rooms]
  );

  const reportUrl = buildDailyManagerReportUrl(propertyCode, businessDate);

  return (
    <div className="page-grid">
      <PageHeader
        title="Dashboard"
        subtitle={`Property ${propertyCode} • Business Date ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">{health?.service || "guzo-backend"}</div>
            <div className="pill">
              API: {health?.status?.toUpperCase() || "UNKNOWN"}
            </div>
          </>
        }
      />

      {loading ? (
        <div className="card">Loading operational dashboard...</div>
      ) : error ? (
        <div className="error-box">{error}</div>
      ) : (
        <>
          <div className="kpi-grid">
            <KpiCard label="Rooms Sold" value={String(kpi?.rooms_sold ?? 0)} />
            <KpiCard label="Revenue Total" value={money(kpi?.revenue_total ?? 0)} />
            <KpiCard label="ADR" value={money(kpi?.adr ?? 0)} />
            <KpiCard label="RevPAR" value={money(kpi?.revpar ?? 0)} />
          </div>

          <div className="stats-grid">
            <KpiCard label="Arrivals Today" value={String(arrivals.length)} />
            <KpiCard label="Departures Today" value={String(departures.length)} />
            <KpiCard label="In House" value={String(inHouse.length)} />
            <KpiCard label="Out of Order" value={String(outOfOrderRooms)} />
          </div>

          <div className="page-grid two-col">
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Arrivals / Departures</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Daily guest movement for the selected business date
              </div>

              <DataTable
                rows={[...arrivals, ...departures]}
                emptyMessage="No arrivals or departures for this business date."
                columns={[
                  {
                    key: "id",
                    header: "Booking ID",
                    render: (row) => `#${row.id}`,
                  },
                  {
                    key: "guest_name",
                    header: "Guest",
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
                    key: "status",
                    header: "Status",
                    render: (row) => (
                      <span className={pillClass(row.booking_status)}>
                        {row.booking_status}
                      </span>
                    ),
                  },
                ]}
              />
            </div>

            <div className="card">
              <h2 style={{ marginTop: 0 }}>Occupied Rooms Snapshot</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Front office and housekeeping room overview
              </div>

              <div className="kpi-grid" style={{ marginBottom: "14px" }}>
                <KpiCard label="Occupied Rooms" value={String(occupiedRooms)} />
                <KpiCard label="Vacant Rooms" value={String(rooms.length - occupiedRooms)} />
              </div>

              <DataTable
                rows={rooms.filter((r) => r.is_occupied)}
                emptyMessage="No occupied rooms on this business date."
                columns={[
                  {
                    key: "room_number",
                    header: "Room",
                    render: (row) => row.room_number,
                  },
                  {
                    key: "guest_name",
                    header: "Guest",
                    render: (row) => row.guest_name || "-",
                  },
                  {
                    key: "hk_status",
                    header: "HK Status",
                    render: (row) => <span className="pill">{row.hk_status}</span>,
                  },
                  {
                    key: "stay",
                    header: "Stay Dates",
                    render: (row) =>
                      row.check_in_date && row.check_out_date
                        ? `${row.check_in_date} → ${row.check_out_date}`
                        : "-",
                  },
                ]}
              />
            </div>
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0 }}>Manager Actions</h2>
            <div className="muted" style={{ marginBottom: "14px" }}>
              Direct access to the core operational report
            </div>

            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              <a
                href={reportUrl}
                target="_blank"
                rel="noreferrer"
                className="primary-btn"
                style={{ textDecoration: "none", display: "inline-block" }}
              >
                Open Daily Manager PDF
              </a>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
