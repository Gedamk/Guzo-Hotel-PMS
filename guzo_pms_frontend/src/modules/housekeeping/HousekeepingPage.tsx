import { useEffect, useMemo, useState } from "react";
import PageHeader from "../../components/PageHeader";
import KpiCard from "../../components/KpiCard";
import DataTable from "../../components/DataTable";
import { usePmsContext } from "../../context/PmsContext";
import { fetchRoomStatusBoard } from "../../services/pmsService";
import { getErrorMessage } from "../../services/http";
import {
  markRoomClean,
  markRoomDirty,
  markRoomOutOfOrder,
  markRoomServiceInProgress,
} from "../../services/housekeepingActions";
import type { RoomStatusItem } from "../../types/pms";

function hkClass(status: string) {
  const s = String(status || "").toLowerCase();
  if (s.includes("inspected")) return "pill pill-inspected";
  if (s.includes("dirty")) return "pill pill-danger";
  if (s.includes("out_of_order") || s.includes("out_of_service") || s.includes("service_in_progress")) return "pill pill-warning";
  if (s.includes("clean")) return "pill pill-success";
  return "pill";
}

export default function HousekeepingPage() {
  const { propertyCode, businessDate, refreshKey, refreshData } = usePmsContext();

  const [rows, setRows] = useState<RoomStatusItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [busyRoomNumber, setBusyRoomNumber] = useState<string | null>(null);

  const [floorFilter, setFloorFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [occupancyFilter, setOccupancyFilter] = useState("all");

  async function loadRows() {
    try {
      setLoading(true);
      setError("");
      const data = await fetchRoomStatusBoard(propertyCode, businessDate);
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

  async function runRoomAction(
    roomNumber: string,
    action: "clean" | "dirty" | "service_in_progress" | "out_of_order"
  ) {
    try {
      setBusyRoomNumber(roomNumber);
      setError("");
      setActionMessage("");

      const payload = {
        roomNumber,
        propertyCode,
        businessDate,
      };

      if (action === "clean") await markRoomClean(payload);
      if (action === "dirty") await markRoomDirty(payload);
      if (action === "service_in_progress") await markRoomServiceInProgress(payload);
      if (action === "out_of_order") await markRoomOutOfOrder(payload);

      setActionMessage(`Room ${roomNumber} updated successfully.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyRoomNumber(null);
    }
  }

  const floors = useMemo(() => {
    return Array.from(new Set(rows.map((row) => row.floor))).sort((a, b) => a - b);
  }, [rows]);

  const filteredRows = useMemo(() => {
    return rows.filter((row) => {
      const floorOk = floorFilter === "all" ? true : String(row.floor) === floorFilter;
      const statusOk = statusFilter === "all" ? true : row.hk_status === statusFilter;
      const occupancyOk =
        occupancyFilter === "all"
          ? true
          : occupancyFilter === "occupied"
          ? row.is_occupied
          : !row.is_occupied;

      return floorOk && statusOk && occupancyOk;
    });
  }, [rows, floorFilter, statusFilter, occupancyFilter]);

  const occupiedRooms = useMemo(
    () => rows.filter((row) => row.is_occupied).length,
    [rows]
  );

  const vacantRooms = useMemo(
    () => rows.filter((row) => !row.is_occupied).length,
    [rows]
  );

  const dirtyRooms = useMemo(
    () => rows.filter((row) => String(row.hk_status).includes("dirty")).length,
    [rows]
  );

  const outOfOrderRooms = useMemo(
    () =>
      rows.filter((row) => {
        const s = String(row.hk_status || "").toLowerCase();
        return s === "out_of_order" || s === "out_of_service" || s === "service_in_progress";
      }).length,
    [rows]
  );

  return (
    <div className="page-grid">
      <PageHeader
        title="Housekeeping"
        subtitle="Room status board."
        metadata={`${propertyCode} • ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">Occupied: {occupiedRooms}</div>
            <div className="pill">Vacant: {vacantRooms}</div>
            <div className="pill">Dirty: {dirtyRooms}</div>
          </>
        }
      />

      {loading ? (
        <div className="card">Loading housekeeping board...</div>
      ) : (
        <>
          {error ? <div className="error-box">{error}</div> : null}
          {actionMessage ? <div className="card">{actionMessage}</div> : null}

          <div className="kpi-grid">
            <KpiCard label="Total Rooms" value={String(rows.length)} />
            <KpiCard label="Occupied Rooms" value={String(occupiedRooms)} />
            <KpiCard label="Vacant Rooms" value={String(vacantRooms)} />
            <KpiCard label="Out of Order" value={String(outOfOrderRooms)} />
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0 }}>Housekeeping Filters</h2>
            <div className="muted" style={{ marginBottom: "14px" }}>
              Filter the room board by floor, housekeeping status, and occupancy
            </div>

            <div className="toolbar-grid">
              <div className="field">
                <label>Floor</label>
                <select
                  value={floorFilter}
                  onChange={(e) => setFloorFilter(e.target.value)}
                >
                  <option value="all">All Floors</option>
                  {floors.map((floor) => (
                    <option key={floor} value={String(floor)}>
                      Floor {floor}
                    </option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label>HK Status</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="all">All Statuses</option>
                  <option value="vacant_clean">vacant_clean</option>
                  <option value="vacant_dirty">vacant_dirty</option>
                  <option value="vacant_inspected">vacant_inspected</option>
                  <option value="occupied_clean">occupied_clean</option>
                  <option value="occupied_dirty">occupied_dirty</option>
                  <option value="out_of_order">out_of_order</option>
                  <option value="out_of_service">out_of_service</option>
                  <option value="service_in_progress">service_in_progress</option>
                  <option value="in_service">in_service</option>
                </select>
              </div>

              <div className="field">
                <label>Occupancy</label>
                <select
                  value={occupancyFilter}
                  onChange={(e) => setOccupancyFilter(e.target.value)}
                >
                  <option value="all">All Rooms</option>
                  <option value="occupied">Occupied Only</option>
                  <option value="vacant">Vacant Only</option>
                </select>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0 }}>Room Status Board</h2>
            <div className="muted" style={{ marginBottom: "14px" }}>
              Operational room readiness for front office and housekeeping coordination
            </div>

            <DataTable
              rows={filteredRows}
              emptyMessage="No rooms match the selected filters."
              columns={[
                {
                  key: "room_number",
                  header: "Room",
                  render: (row) => row.room_number,
                },
                {
                  key: "floor",
                  header: "Floor",
                  render: (row) => row.floor,
                },
                {
                  key: "hk_status",
                  header: "HK Status",
                  render: (row) => (
                    <span className={hkClass(row.hk_status)}>{row.hk_status}</span>
                  ),
                },
                {
                  key: "occupied",
                  header: "Occupied",
                  render: (row) => (row.is_occupied ? "Yes" : "No"),
                },
                {
                  key: "guest",
                  header: "Guest",
                  render: (row) => row.guest_name || "-",
                },
                {
                  key: "stay_dates",
                  header: "Stay Dates",
                  render: (row) =>
                    row.check_in_date && row.check_out_date
                      ? `${row.check_in_date} → ${row.check_out_date}`
                      : "-",
                },
                {
                  key: "actions",
                  header: "Actions",
                  render: (row) => (
                    <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                      <button
                        className="small-btn"
                        disabled={busyRoomNumber === row.room_number}
                        onClick={() => runRoomAction(row.room_number, "clean")}
                      >
                        Clean
                      </button>
                      <button
                        className="small-btn"
                        disabled={busyRoomNumber === row.room_number}
                        onClick={() => runRoomAction(row.room_number, "dirty")}
                      >
                        Dirty
                      </button>
                      <button
                        className="small-btn"
                        disabled={busyRoomNumber === row.room_number}
                        onClick={() => runRoomAction(row.room_number, "service_in_progress")}
                      >
                        Start Cleaning
                      </button>
                      <button
                        className="small-btn"
                        disabled={busyRoomNumber === row.room_number}
                        onClick={() => runRoomAction(row.room_number, "out_of_order")}
                      >
                        OOO
                      </button>
                    </div>
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
