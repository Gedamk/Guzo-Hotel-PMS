import { useEffect, useMemo, useState } from "react";
import PageHeader from "../../components/PageHeader";
import KpiCard from "../../components/KpiCard";
import DataTable from "../../components/DataTable";
import { usePmsContext } from "../../context/PmsContext";
import { fetchFrontdeskBookings } from "../../services/pmsService";
import { getErrorMessage } from "../../services/http";
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
  if (s === "in_house" || s === "checked_in") return "pill pill-success";
  if (s === "checked_out") return "pill pill-muted";
  if (s === "cancelled" || s === "no_show") return "pill pill-danger";
  return "pill";
}

function sourceClass(source: string) {
  const s = String(source || "").toLowerCase();
  if (s === "walk_in") return "pill pill-success";
  if (s === "telegram") return "pill pill-inspected";
  if (s === "ota") return "pill pill-warning";
  if (s === "corporate") return "pill pill-muted";
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
  return row.room_number || row.room_no || row.roomNo || "-";
}

function normalizeAmount(row: any) {
  return Number(row.total_amount || row.amount || row.total || 0);
}

export default function ReservationsPage() {
  const { propertyCode, businessDate, refreshKey } = usePmsContext();

  const [rows, setRows] = useState<FrontdeskBooking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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

  const filteredRows = useMemo(() => {
    return rows.filter((row: any) => {
      const source = normalizeSource(row);
      const room = String(normalizeRoom(row)).toLowerCase();
      const guest = String(row.guest_name || "").toLowerCase();
      const bookingId = String(row.id || "");
      const status = String(row.booking_status || "").toLowerCase();

      const statusOk =
        statusFilter === "all" ? true : status === statusFilter.toLowerCase();

      const sourceOk =
        sourceFilter === "all" ? true : source === sourceFilter.toLowerCase();

      const q = searchText.trim().toLowerCase();
      const searchOk =
        q === ""
          ? true
          : guest.includes(q) || bookingId.includes(q) || room.includes(q);

      return statusOk && sourceOk && searchOk;
    });
  }, [rows, statusFilter, sourceFilter, searchText]);

  const arrivals = useMemo(
    () => filteredRows.filter((row) => row.check_in_date === businessDate),
    [filteredRows, businessDate]
  );

  const departures = useMemo(
    () => filteredRows.filter((row) => row.check_out_date === businessDate),
    [filteredRows, businessDate]
  );

  const stayovers = useMemo(
    () =>
      filteredRows.filter((row) => {
        const status = String(row.booking_status || "").toLowerCase();
        return (
          row.check_in_date < businessDate &&
          row.check_out_date > businessDate &&
          (status === "in_house" || status === "checked_in")
        );
      }),
    [filteredRows, businessDate]
  );

  return (
    <div className="page-grid">
      <PageHeader
        title="Reservations"
        subtitle={`Reservation control workspace for ${propertyCode} on ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">Arrivals: {arrivals.length}</div>
            <div className="pill">Departures: {departures.length}</div>
            <div className="pill">Stayovers: {stayovers.length}</div>
          </>
        }
      />

      {loading ? (
        <div className="card">Loading reservations workspace...</div>
      ) : (
        <>
          {error ? <div className="error-box">{error}</div> : null}

          <div className="kpi-grid">
            <KpiCard label="Total Reservations" value={String(filteredRows.length)} />
            <KpiCard label="Arrivals Today" value={String(arrivals.length)} />
            <KpiCard label="Departures Today" value={String(departures.length)} />
            <KpiCard label="Stayovers" value={String(stayovers.length)} />
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
              <h2 style={{ marginTop: 0 }}>Arrivals</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Guests expected to arrive on the selected business date
              </div>

              <DataTable
                rows={arrivals}
                emptyMessage="No arrivals for this business date."
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
                  header: "Check In",
                  render: (row: any) => row.check_in_date,
                },
                {
                  key: "check_out_date",
                  header: "Check Out",
                  render: (row: any) => row.check_out_date,
                },
                {
                  key: "room_number",
                  header: "Room",
                  render: (row: any) => normalizeRoom(row),
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
                  key: "total_amount",
                  header: "Amount",
                  render: (row: any) => money(normalizeAmount(row)),
                },
              ]}
            />
          </div>
        </>
      )}
    </div>
  );
}
