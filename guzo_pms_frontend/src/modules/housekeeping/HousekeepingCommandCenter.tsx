import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  AlertTriangle,
  BedDouble,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  Hammer,
  Hotel,
  PackageSearch,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  UserCheck,
  Users,
} from "lucide-react";
import PageHeader from "../../components/PageHeader";
import DataTable from "../../components/DataTable";
import { LoadingState } from "../../components/ui/LoadingState";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { usePmsContext } from "../../context/PmsContext";
import { fetchRoomStatusBoard } from "../../services/pmsService";
import { getErrorMessage } from "../../services/http";
import {
  assignRoomAttendant,
  markRoomClean,
  markRoomDirty,
  markRoomInspected,
  markRoomMaintenance,
  markRoomOutOfOrder,
  markRoomOutOfService,
  markRoomServiceInProgress,
} from "../../services/housekeepingActions";
import type { RoomStatusItem } from "../../types/pms";
import { permissionMessage, roleCan } from "../../auth/permissions";

type HkTab =
  | "overview"
  | "board"
  | "assignments"
  | "inspections"
  | "maintenance"
  | "dnd"
  | "publicAreas"
  | "reports";

type RoomAction =
  | "clean"
  | "dirty"
  | "inspected"
  | "service_in_progress"
  | "out_of_order"
  | "out_of_service"
  | "maintenance";

type Attendant = {
  name: string;
  section: string;
  rooms: string[];
};

const tabs: Record<HkTab, string> = {
  overview: "Overview",
  board: "Room Board",
  assignments: "Assignments",
  inspections: "Inspections",
  maintenance: "Maintenance",
  dnd: "DND / Refused",
  publicAreas: "Public Areas",
  reports: "Reports",
};

const hkTabByHash: Record<string, HkTab> = {
  overview: "overview",
  housekeeping: "overview",
  board: "board",
  "room-status": "board",
  assignments: "assignments",
  "task-board": "assignments",
  inspections: "inspections",
  maintenance: "maintenance",
  "out-of-order": "maintenance",
  "out-of-service": "maintenance",
  dnd: "dnd",
  "public-areas": "publicAreas",
  reports: "reports",
};

const attendants: Attendant[] = [
  { name: "Hana", section: "Floors 2-3", rooms: ["201", "202", "203", "301"] },
  { name: "Sara", section: "Floors 4-5", rooms: ["401", "402", "403"] },
  { name: "Abebe", section: "Suites / VIP", rooms: ["501", "502"] },
];

const publicAreaTasks = [
  { area: "Lobby", task: "Mop floor and polish front desk counter", frequency: "Every 2 hours", owner: "Dawit", status: "In Progress" },
  { area: "Public Restroom", task: "Clean and restock supplies", frequency: "Hourly", owner: "Hana", status: "Pending" },
  { area: "Elevator", task: "Polish panels and check mirrors", frequency: "3 times daily", owner: "Sara", status: "Done" },
  { area: "Meeting Room", task: "Reset chairs and inspect AV table", frequency: "Before event", owner: "Abebe", status: "Pending" },
];

const inspectionChecklist = [
  "Bedroom: bed made, dust removed, floor clean",
  "Bathroom: toilet, shower, sink, mirror, towels",
  "Amenities: soap, shampoo, tissue, water, coffee",
  "Equipment: TV, lights, AC, phone, safe",
  "Safety: door lock, smoke detector, emergency info",
  "Final: odor, temperature, presentation",
];

function normalizeStatus(status: string, occupied: boolean) {
  const s = String(status || "").toLowerCase();
  if (s.includes("out_of_order") || s.includes("out of order")) return "out_of_order";
  if (s.includes("out_of_service") || s.includes("out of service")) return "out_of_service";
  if (s.includes("service_in_progress") || s.includes("service in progress")) return "service_in_progress";
  if (s.includes("maintenance")) return "maintenance";
  if (s.includes("in_service") || s.includes("in service")) return "in_service";
  if (s.includes("inspect") || s.includes("ready")) return "vacant_inspected";
  if (s.includes("dirty")) return occupied ? "occupied_dirty" : "vacant_dirty";
  if (s.includes("clean")) return occupied ? "occupied_clean" : "vacant_clean";
  return occupied ? "occupied_dirty" : "vacant_dirty";
}

function friendlyStatus(status: string, occupied: boolean) {
  const normalized = normalizeStatus(status, occupied);
  const labels: Record<string, string> = {
    vacant_dirty: "Vacant Dirty",
    vacant_clean: "Vacant Clean",
    vacant_inspected: "Inspected / Ready",
    occupied_dirty: "Occupied Dirty",
    occupied_clean: "Occupied Clean",
    out_of_order: "Out of Order",
    out_of_service: "Out of Service",
    maintenance: "Maintenance",
    service_in_progress: "Cleaning in Progress",
    in_service: "In Service / Usable",
  };
  return labels[normalized] || normalized;
}

function taskCredit(room: RoomStatusItem) {
  const status = normalizeStatus(room.hk_status, room.is_occupied);
  if (status === "vacant_dirty") return 2;
  if (status === "occupied_dirty") return 1;
  if (status.includes("out")) return 3;
  if (String(room.guest_name || "").toLowerCase().includes("vip")) return 4;
  return 1;
}

function priorityLabel(room: RoomStatusItem, businessDate: string) {
  const status = normalizeStatus(room.hk_status, room.is_occupied);
  if (status.includes("out")) return "Maintenance";
  if (String(room.guest_name || "").toLowerCase().includes("vip")) return "VIP Arrival";
  if (room.check_in_date === businessDate && !room.is_occupied) return "Arrival Today";
  if (room.check_out_date === businessDate) return "Due Out";
  if (room.is_occupied && room.check_out_date && room.check_out_date > businessDate) return "Stayover";
  if (status === "vacant_dirty") return "Check-Out Clean";
  return "Normal";
}

function priorityClass(priority: string) {
  if (["Arrival Today", "Due Out", "Maintenance", "VIP Arrival"].includes(priority)) return "pill pill-warning";
  if (priority === "Check-Out Clean") return "pill pill-danger";
  if (priority === "Stayover") return "pill pill-inspected";
  return "pill";
}

export default function HousekeepingCommandCenter() {
  const location = useLocation();
  const { propertyCode, businessDate, refreshKey, refreshData } = usePmsContext();

  const [rooms, setRooms] = useState<RoomStatusItem[]>([]);
  const [activeTab, setActiveTab] = useState<HkTab>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [busyRoomNumber, setBusyRoomNumber] = useState<string | null>(null);
  const canMarkCleaned = roleCan("housekeeping.mark_cleaned");
  const canMarkInspected = roleCan("housekeeping.mark_inspected");
  const canOverrideRoomStatus = roleCan("housekeeping.room_status_override");
  const canUseHousekeepingActions =
    canMarkCleaned || canMarkInspected || canOverrideRoomStatus;
  const [floorFilter, setFloorFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedRoom, setSelectedRoom] = useState<RoomStatusItem | null>(null);

  useEffect(() => {
    const hashKey = location.hash.replace(/^#/, "");
    const tab = hkTabByHash[hashKey];
    if (tab) setActiveTab(tab);
  }, [location.hash]);

  async function loadRooms() {
    try {
      setLoading(true);
      setError("");
      const data = await fetchRoomStatusBoard(propertyCode, businessDate);
      setRooms(data);
      setSelectedRoom((current) => current || data[0] || null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRooms();
  }, [propertyCode, businessDate, refreshKey]);

  async function runRoomAction(roomNumber: string, action: RoomAction) {
    try {
      setBusyRoomNumber(roomNumber);
      setError("");
      setActionMessage("");
      const note =
        action === "out_of_order"
          ? window.prompt("Out of Order reason", "Maintenance issue requires engineering follow-up.") || undefined
          : action === "out_of_service"
          ? window.prompt("Out of Service reason", "Room unavailable for operational reason.") || undefined
          : action === "maintenance"
          ? window.prompt("Maintenance issue note", "Maintenance issue reported by Housekeeping.") || undefined
          : undefined;
      const payload = {
        roomNumber,
        propertyCode,
        businessDate,
        note,
        maintenanceNote: action === "maintenance" ? note : undefined,
        outOfOrderReason: action === "out_of_order" || action === "out_of_service" ? note : undefined,
      };

      if (action === "clean") await markRoomClean(payload);
      if (action === "dirty") await markRoomDirty(payload);
      if (action === "inspected") await markRoomInspected(payload);
      if (action === "service_in_progress") await markRoomServiceInProgress(payload);
      if (action === "out_of_order") await markRoomOutOfOrder(payload);
      if (action === "out_of_service") await markRoomOutOfService(payload);
      if (action === "maintenance") await markRoomMaintenance(payload);

      setActionMessage(`Room ${roomNumber} updated successfully.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyRoomNumber(null);
    }
  }

  async function assignAttendant(roomNumber: string, current?: string | null) {
    const assignedTo = window.prompt("Assign room to housekeeper", current || attendants[0]?.name || "");
    if (!assignedTo?.trim()) return;
    try {
      setBusyRoomNumber(roomNumber);
      setError("");
      setActionMessage("");
      await assignRoomAttendant({
        roomNumber,
        propertyCode,
        businessDate,
        assignedTo: assignedTo.trim(),
        note: "Assigned from Housekeeping Command Center",
      });
      setActionMessage(`Room ${roomNumber} assigned to ${assignedTo.trim()}.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyRoomNumber(null);
    }
  }

  const floors = useMemo(
    () => Array.from(new Set(rooms.map((room) => room.floor))).sort((a, b) => a - b),
    [rooms]
  );

  const counts = useMemo(() => {
    const count = (key: string) =>
      rooms.filter((room) => normalizeStatus(room.hk_status, room.is_occupied) === key)
        .length;
    return {
      total: rooms.length,
      vacantDirty: count("vacant_dirty"),
      vacantClean: count("vacant_clean"),
      ready: count("vacant_inspected"),
      occupiedDirty: count("occupied_dirty"),
      occupiedClean: count("occupied_clean"),
      out: rooms.filter((room) => normalizeStatus(room.hk_status, room.is_occupied).includes("out")).length,
      maintenance: count("maintenance"),
      serviceInProgress: count("service_in_progress"),
      arrivalsNoInspected: rooms.filter(
        (room) =>
          room.check_in_date === businessDate &&
          !["vacant_inspected"].includes(
            normalizeStatus(room.hk_status, room.is_occupied)
          )
      ).length,
      dirtyOccupied: count("occupied_dirty"),
      dueOut: rooms.filter((room) => room.check_out_date === businessDate).length,
      stayover: rooms.filter(
        (room) =>
          room.is_occupied &&
          room.check_in_date &&
          room.check_out_date &&
          room.check_in_date < businessDate &&
          room.check_out_date > businessDate
      ).length,
    };
  }, [rooms, businessDate]);

  const priorityRooms = useMemo(
    () =>
      rooms
        .filter((room) =>
          ["Arrival Today", "Due Out", "Check-Out Clean", "Maintenance"].includes(
            priorityLabel(room, businessDate)
          )
        )
        .slice(0, 8),
    [rooms, businessDate]
  );

  const filteredRooms = useMemo(() => {
    return rooms.filter((room) => {
      const floorOk = floorFilter === "all" || String(room.floor) === floorFilter;
      const normalized = normalizeStatus(room.hk_status, room.is_occupied);
      const statusOk = statusFilter === "all" || normalized === statusFilter;
      return floorOk && statusOk;
    });
  }, [rooms, floorFilter, statusFilter]);

  const inspectionQueue = rooms.filter((room) =>
    ["vacant_clean", "vacant_inspected"].includes(
      normalizeStatus(room.hk_status, room.is_occupied)
    )
  );
  const maintenanceRooms = rooms.filter((room) =>
    normalizeStatus(room.hk_status, room.is_occupied).includes("out") ||
    ["maintenance", "service_in_progress"].includes(
      normalizeStatus(room.hk_status, room.is_occupied)
    )
  );
  const dndRows = rooms.filter((_, index) => index % 9 === 0 && rooms.length > 5).slice(0, 5);

  return (
    <div className="page-grid housekeeping-command">
      <PageHeader
        title="Housekeeping"
        subtitle="Room lifecycle, attendant assignments, inspections, and front desk readiness."
        metadata={`${propertyCode} • ${businessDate}`}
        rightSlot={
          <>
            <button className="small-btn hk-icon-btn" onClick={loadRooms}>
              <RefreshCw size={15} />
              Refresh
            </button>
            <div className="pill">Business Date: {businessDate}</div>
            <div className="pill">Ready: {counts.ready}</div>
          </>
        }
      />

      {loading ? (
        <LoadingState label="Loading housekeeping command center..." />
      ) : (
        <>
          {error ? <div className="error-box">{error}</div> : null}
          {actionMessage ? <div className="notice-box">{actionMessage}</div> : null}
          {!canUseHousekeepingActions ? (
            <div className="notice-box">{permissionMessage("Housekeeping room-status actions")}</div>
          ) : null}

          <div className="hk-kpi-grid">
            <HkMetric icon={<Hotel />} label="Total Rooms" value={counts.total} />
            <HkMetric icon={<AlertTriangle />} label="Vacant Dirty" value={counts.vacantDirty} />
            <HkMetric icon={<Sparkles />} label="Vacant Clean" value={counts.vacantClean} />
            <HkMetric icon={<ShieldCheck />} label="Inspected Ready" value={counts.ready} />
            <HkMetric icon={<BedDouble />} label="Occupied Dirty" value={counts.occupiedDirty} />
            <HkMetric icon={<CheckCircle2 />} label="Occupied Clean" value={counts.occupiedClean} />
            <HkMetric icon={<Hammer />} label="Out of Order" value={counts.out} />
            <HkMetric icon={<Hammer />} label="Maintenance" value={counts.maintenance} />
            <HkMetric icon={<Sparkles />} label="Cleaning" value={counts.serviceInProgress} />
            <HkMetric icon={<AlertTriangle />} label="Arrival Exceptions" value={counts.arrivalsNoInspected} />
          </div>

          <div className="hk-tabs">
            {(Object.keys(tabs) as HkTab[]).map((tab) => (
              <button
                key={tab}
                className={`tab-btn ${activeTab === tab ? "active" : ""}`}
                onClick={() => setActiveTab(tab)}
              >
                {tabs[tab]}
              </button>
            ))}
          </div>

          {activeTab === "overview" ? (
            <div className="page-grid two-col">
              <section className="card hk-panel hk-morning-card">
                <SectionHeader
                  icon={<ClipboardList />}
                  title="Daily Housekeeping Dashboard"
                  subtitle="Morning briefing after night audit: priorities, readiness, and risks."
                />
                <div className="hk-summary-grid">
                  <SummaryTile label="Total Rooms" value={counts.total} />
                  <SummaryTile label="Vacant Dirty" value={counts.vacantDirty} />
                  <SummaryTile label="Vacant Clean" value={counts.vacantClean} />
                  <SummaryTile label="Inspected / Ready" value={counts.ready} />
                  <SummaryTile label="Occupied Dirty" value={counts.occupiedDirty} />
                  <SummaryTile label="Occupied Clean" value={counts.occupiedClean} />
                  <SummaryTile label="Out of Order" value={counts.out} />
                  <SummaryTile label="Maintenance" value={counts.maintenance} />
                  <SummaryTile label="Cleaning" value={counts.serviceInProgress} />
                  <SummaryTile label="Arrival Exceptions" value={counts.arrivalsNoInspected} />
                  <SummaryTile label="Dirty Occupied" value={counts.dirtyOccupied} />
                  <SummaryTile label="Due Out" value={counts.dueOut} />
                  <SummaryTile label="Stayovers" value={counts.stayover} />
                </div>
                <div className="hk-sop-list">
                  <label><input type="checkbox" /> Review arrivals and assigned rooms.</label>
                  <label><input type="checkbox" /> Prioritize VIP, early Check-In, and back-to-back rooms.</label>
                  <label><input type="checkbox" /> Assign dirty departures by floor and workload credits.</label>
                  <label><input type="checkbox" /> Review maintenance, DND, refused service, and front desk alerts.</label>
                </div>
              </section>

              <section className="card hk-panel hk-priority-card">
                <SectionHeader
                  icon={<UserCheck />}
                  title="Priority Queue"
                  subtitle="Rooms housekeeping should handle first for front desk readiness."
                />
                <div className="hk-priority-list">
                  {priorityRooms.length ? (
                    priorityRooms.map((room) => (
                      <button
                        key={room.room_number}
                        className="hk-priority-row"
                        onClick={() => {
                          setSelectedRoom(room);
                          setActiveTab("board");
                        }}
                      >
                        <strong>{room.room_number}</strong>
                        <span>{friendlyStatus(room.hk_status, room.is_occupied)}</span>
                        <span className={priorityClass(priorityLabel(room, businessDate))}>
                          {priorityLabel(room, businessDate)}
                        </span>
                      </button>
                    ))
                  ) : (
                    <div className="muted">No urgent priority rooms.</div>
                  )}
                </div>
              </section>
            </div>
          ) : null}

          {activeTab === "board" ? (
            <section className="card hk-panel">
              <SectionHeader
                icon={<BedDouble />}
                title="Room Status Board"
                subtitle="Opera-style room lifecycle board: dirty, assigned, cleaned, inspected, ready."
              />
              <div className="hk-filter-row">
                <div className="field">
                  <label>Floor</label>
                  <select value={floorFilter} onChange={(event) => setFloorFilter(event.target.value)}>
                    <option value="all">All Floors</option>
                    {floors.map((floor) => (
                      <option key={floor} value={String(floor)}>Floor {floor}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label>Status</label>
                  <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                    <option value="all">All Statuses</option>
                    <option value="vacant_dirty">Vacant Dirty</option>
                    <option value="vacant_clean">Vacant Clean</option>
                    <option value="vacant_inspected">Inspected / Ready</option>
                    <option value="occupied_dirty">Occupied Dirty</option>
                    <option value="occupied_clean">Occupied Clean</option>
                    <option value="out_of_order">Out of Order</option>
                    <option value="out_of_service">Out of Service</option>
                    <option value="maintenance">Maintenance</option>
                    <option value="service_in_progress">Cleaning in Progress</option>
                    <option value="in_service">In Service / Usable</option>
                  </select>
                </div>
              </div>
              <DataTable
                rows={filteredRooms}
                emptyMessage="No rooms match the selected filters."
                columns={[
                  { key: "room", header: "Room", render: (room) => <strong>{room.room_number}</strong> },
                  { key: "type", header: "Type", render: (room) => room.room_type || "Standard Room" },
                  { key: "floor", header: "Floor", render: (room) => room.floor },
                  { key: "occupancy", header: "Occupancy", render: (room) => (room.is_occupied ? "Occupied" : "Vacant") },
                  { key: "guest", header: "Guest", render: (room) => room.guest_name || "-" },
                  { key: "assigned", header: "Attendant", render: (room) => room.assigned_to || "-" },
                  {
                    key: "status",
                    header: "Status",
                    render: (room) => (
                      <StatusBadge
                        status={normalizeStatus(room.hk_status, room.is_occupied)}
                        label={friendlyStatus(room.hk_status, room.is_occupied)}
                      />
                    ),
                  },
                  {
                    key: "priority",
                    header: "Priority",
                    render: (room) => (
                      <span className={priorityClass(priorityLabel(room, businessDate))}>
                        {priorityLabel(room, businessDate)}
                      </span>
                    ),
                  },
                  {
                    key: "actions",
                    header: "Action",
                    render: (room) => (
                      <RoomActions
                        room={room}
                        busyRoomNumber={busyRoomNumber}
                        runRoomAction={runRoomAction}
                        selectRoom={() => setSelectedRoom(room)}
                        canMarkCleaned={canMarkCleaned}
                        canMarkInspected={canMarkInspected}
                        canOverrideRoomStatus={canOverrideRoomStatus}
                        assignAttendant={assignAttendant}
                      />
                    ),
                  },
                ]}
              />
            </section>
          ) : null}

          {activeTab === "assignments" ? (
            <section className="card hk-panel">
              <SectionHeader
                icon={<Users />}
                title="Attendant Assignments"
                subtitle="Assign by floor, room type, priority, and workload credits."
              />
              <div className="hk-assignment-grid">
                {attendants.map((attendant) => {
                  const assigned = rooms.filter((room) => attendant.rooms.includes(room.room_number));
                  const credits = assigned.reduce((sum, room) => sum + taskCredit(room), 0);
                  return (
                    <div className="hk-attendant-card" key={attendant.name}>
                      <div>
                        <strong>{attendant.name}</strong>
                        <span>{attendant.section}</span>
                      </div>
                      <div className="hk-room-chip-row">
                        {attendant.rooms.map((room) => <span className="hk-room-chip" key={room}>{room}</span>)}
                      </div>
                      <div className="hk-credit-row">
                        <span>Assigned</span><strong>{assigned.length}</strong>
                        <span>Credits</span><strong>{credits}</strong>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          ) : null}

          {activeTab === "inspections" ? (
            <section className="card hk-panel">
              <SectionHeader
                icon={<ClipboardCheck />}
                title="Supervisor Inspection Queue"
                subtitle="Cleaned rooms require supervisor approval before front desk can check in."
              />
              <div className="hk-inspection-layout">
                <div className="hk-inspection-list">
                  {inspectionQueue.map((room) => (
                    <button className="hk-priority-row" key={room.room_number} onClick={() => setSelectedRoom(room)}>
                      <strong>{room.room_number}</strong>
                      <span>{friendlyStatus(room.hk_status, room.is_occupied)}</span>
                      <span className="pill pill-warning">Inspect</span>
                    </button>
                  ))}
                </div>
                <div className="hk-checklist-card">
                  <h3>Inspection Checklist</h3>
                  {inspectionChecklist.map((item) => (
                    <label key={item}><input type="checkbox" /> {item}</label>
                  ))}
                  <div className="hk-action-row">
                    {canOverrideRoomStatus ? (
                      <button className="small-btn" disabled={!selectedRoom}>Fail Inspection</button>
                    ) : null}
                    {canMarkInspected ? (
                      <button
                        className="primary-btn"
                        disabled={!selectedRoom || busyRoomNumber === selectedRoom.room_number}
                        onClick={() => selectedRoom && runRoomAction(selectedRoom.room_number, "inspected")}
                      >
                        Mark Inspected
                      </button>
                    ) : (
                      <span className="pill pill-muted">Read Only</span>
                    )}
                  </div>
                </div>
              </div>
            </section>
          ) : null}

          {activeTab === "maintenance" ? (
            <IssueBoard
              title="Maintenance Issues"
              icon={<Hammer />}
              rows={maintenanceRooms}
              emptyText="No out-of-order or out-of-service rooms."
              businessDate={businessDate}
            />
          ) : null}

          {activeTab === "dnd" ? (
            <IssueBoard
              title="DND / Refused Service"
              icon={<AlertTriangle />}
              rows={dndRows}
              emptyText="No DND or refused-service records."
              businessDate={businessDate}
            />
          ) : null}

          {activeTab === "publicAreas" ? (
            <section className="card hk-panel">
              <SectionHeader
                icon={<PackageSearch />}
                title="Public Areas and Deep Cleaning"
                subtitle="Lobby, restrooms, elevators, meeting rooms, and recurring project cleaning."
              />
              <DataTable
                rows={publicAreaTasks}
                columns={[
                  { key: "area", header: "Area", render: (row) => row.area },
                  { key: "task", header: "Task", render: (row) => row.task },
                  { key: "frequency", header: "Frequency", render: (row) => row.frequency },
                  { key: "owner", header: "Assigned To", render: (row) => row.owner },
                  { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
                ]}
              />
            </section>
          ) : null}

          {activeTab === "reports" ? (
            <section className="card hk-panel">
              <SectionHeader
                icon={<CheckCircle2 />}
                title="Daily Housekeeping Report"
                subtitle="Manager summary for cleaned, inspected, pending, DND, maintenance, and productivity."
              />
              <div className="hk-report-grid">
                <SummaryTile label="Rooms Cleaned" value={counts.vacantClean + counts.occupiedClean} />
                <SummaryTile label="Rooms Inspected" value={counts.ready} />
                <SummaryTile label="Rooms Pending" value={counts.vacantDirty + counts.occupiedDirty} />
                <SummaryTile label="Maintenance" value={counts.out} />
                <SummaryTile label="Lost & Found" value={2} />
                <SummaryTile label="Late Rooms" value={Math.max(counts.vacantDirty - 2, 0)} />
              </div>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}

function HkMetric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="hk-metric">
      <div className="hk-metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function SectionHeader({
  icon,
  title,
  subtitle,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="section-heading hk-section-heading">
      <div>
        <div className="hk-title-row">
          <span>{icon}</span>
          <h2>{title}</h2>
        </div>
        <p className="muted">{subtitle}</p>
      </div>
    </div>
  );
}

function SummaryTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="hk-summary-tile">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RoomActions({
  room,
  busyRoomNumber,
  runRoomAction,
  selectRoom,
  canMarkCleaned,
  canMarkInspected,
  canOverrideRoomStatus,
  assignAttendant,
}: {
  room: RoomStatusItem;
  busyRoomNumber: string | null;
  runRoomAction: (roomNumber: string, action: RoomAction) => void;
  selectRoom: () => void;
  canMarkCleaned: boolean;
  canMarkInspected: boolean;
  canOverrideRoomStatus: boolean;
  assignAttendant: (roomNumber: string, current?: string | null) => void;
}) {
  const busy = busyRoomNumber === room.room_number;
  return (
    <div className="hk-action-row">
      <button className="small-btn hk-status-action hk-action-view" onClick={selectRoom}>View</button>
      {canOverrideRoomStatus ? (
        <button className="small-btn hk-status-action hk-action-view" disabled={busy} onClick={() => assignAttendant(room.room_number, room.assigned_to)}>Assign</button>
      ) : null}
      {canMarkCleaned ? (
        <button className="small-btn hk-status-action hk-action-start" disabled={busy} onClick={() => runRoomAction(room.room_number, "service_in_progress")}>Start</button>
      ) : null}
      {canMarkCleaned ? (
        <button className="small-btn hk-status-action hk-action-cleaned" disabled={busy} onClick={() => runRoomAction(room.room_number, "clean")}>Cleaned</button>
      ) : null}
      {canMarkInspected ? (
        <button className="small-btn hk-status-action hk-action-inspected" disabled={busy} onClick={() => runRoomAction(room.room_number, "inspected")}>Inspected</button>
      ) : null}
      {canOverrideRoomStatus ? (
        <>
          <button className="small-btn hk-status-action hk-action-ooo" disabled={busy} title="Out of Order" aria-label="Mark room out of order" onClick={() => runRoomAction(room.room_number, "out_of_order")}>OOO</button>
          <button className="small-btn hk-status-action hk-action-oos" disabled={busy} title="Out of Service" aria-label="Mark room out of service" onClick={() => runRoomAction(room.room_number, "out_of_service")}>OOS</button>
          <button className="small-btn hk-status-action hk-action-maint" disabled={busy} title="Maintenance" aria-label="Mark room for maintenance" onClick={() => runRoomAction(room.room_number, "maintenance")}>Maint.</button>
        </>
      ) : null}
      {canMarkCleaned ? (
        <button className="small-btn hk-status-action hk-action-dirty" disabled={busy} onClick={() => runRoomAction(room.room_number, "dirty")}>Dirty</button>
      ) : null}
      {!canMarkCleaned && !canMarkInspected && !canOverrideRoomStatus ? (
        <span className="pill pill-muted">Read Only</span>
      ) : null}
    </div>
  );
}

function IssueBoard({
  title,
  icon,
  rows,
  emptyText,
  businessDate,
}: {
  title: string;
  icon: React.ReactNode;
  rows: RoomStatusItem[];
  emptyText: string;
  businessDate: string;
}) {
  return (
    <section className="card hk-panel">
      <SectionHeader icon={icon} title={title} subtitle="Logged room issues for supervisor follow-up and front desk visibility." />
      <div className="hk-issue-grid">
        {rows.length ? (
          rows.map((room) => (
            <div className="hk-issue-card" key={room.room_number}>
              <strong>Room {room.room_number}</strong>
              <span>{friendlyStatus(room.hk_status, room.is_occupied)}</span>
              <p>
                {priorityLabel(room, businessDate)}. Supervisor should add note,
                retry time, work order, or manager follow-up.
              </p>
              <div className="hk-action-row">
                <button className="small-btn">Add Note</button>
                <button className="small-btn">Work Order</button>
              </div>
            </div>
          ))
        ) : (
          <div className="muted">{emptyText}</div>
        )}
      </div>
    </section>
  );
}
