import { useEffect, useMemo, useState } from "react";
import { usePmsContext } from "../context/PmsContext";
import {
  fetchDashboardOperationalSummary,
  fetchDailyKpi,
  fetchFrontdeskBookings,
  fetchRoomStatusBoard,
} from "../services/pmsService";
import type {
  DashboardKpi,
  DashboardOperationalSummary,
  FrontdeskBooking,
  RoomStatusItem,
} from "../types/pms";

function bookingStatus(row: FrontdeskBooking) {
  return String(row.booking_status || "").toLowerCase();
}

function percent(value: number, total: number) {
  if (!total) return 0;
  return Math.min(Math.round((value / total) * 100), 100);
}

function countRoomStatus(rooms: RoomStatusItem[], matcher: (value: string) => boolean) {
  return rooms.filter((room) => matcher(String(room.hk_status || "").toLowerCase())).length;
}

function normalizeAuditStatus(summary: DashboardOperationalSummary | null, blockers: number) {
  const rawStatus = String(
    (summary as (DashboardOperationalSummary & { night_audit_status?: string }) | null)
      ?.night_audit_status || ""
  ).toLowerCase();

  if (rawStatus.includes("closed") || rawStatus.includes("completed")) return "CLOSED";
  if (rawStatus.includes("blocked") || blockers > 0) return "BLOCKED";
  if (summary?.night_audit_ready) return "READY";
  return "OPEN";
}

export default function PmsStatusRibbon() {
  const { propertyCode, businessDate, refreshKey } = usePmsContext();
  const [kpi, setKpi] = useState<DashboardKpi | null>(null);
  const [summary, setSummary] = useState<DashboardOperationalSummary | null>(null);
  const [bookings, setBookings] = useState<FrontdeskBooking[]>([]);
  const [rooms, setRooms] = useState<RoomStatusItem[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function loadRibbon() {
      const [kpiResult, summaryResult, bookingsResult, roomsResult] = await Promise.allSettled([
        fetchDailyKpi(propertyCode, businessDate),
        fetchDashboardOperationalSummary(propertyCode, businessDate),
        fetchFrontdeskBookings(propertyCode, businessDate),
        fetchRoomStatusBoard(propertyCode, businessDate),
      ]);

      if (cancelled) return;
      setKpi(kpiResult.status === "fulfilled" ? kpiResult.value : null);
      setSummary(summaryResult.status === "fulfilled" ? summaryResult.value : null);
      setBookings(bookingsResult.status === "fulfilled" ? bookingsResult.value : []);
      setRooms(roomsResult.status === "fulfilled" ? roomsResult.value : []);
    }

    loadRibbon();
    return () => {
      cancelled = true;
    };
  }, [businessDate, propertyCode, refreshKey]);

  const ribbonItems = useMemo(() => {
    const arrivals = summary?.arrivals_today_count ?? bookings.filter((row) => row.check_in_date === businessDate).length;
    const departures = summary?.departures_today_count ?? bookings.filter((row) => row.check_out_date === businessDate).length;
    const occupiedRooms = kpi?.rooms_sold || rooms.filter((room) => room.is_occupied).length;
    const outOfOrder = summary?.out_of_order_count ?? countRoomStatus(rooms, (status) => status.includes("out of order") || status === "out_of_order");
    const outOfService = summary?.out_of_service_count ?? countRoomStatus(rooms, (status) => status.includes("out of service") || status === "out_of_service");
    const availableRooms = Math.max(rooms.length - occupiedRooms - outOfOrder - outOfService, 0);
    const occupancy = percent(occupiedRooms, rooms.length || occupiedRooms);
    const dirtyRooms = summary?.dirty_room_count ?? countRoomStatus(rooms, (status) => status.includes("dirty"));
    const cashierOpen = summary?.open_cashier_shift_count ?? summary?.cashier_shift_open_count ?? 0;
    const auditBlockers =
      summary?.night_audit_blocker_count ??
      bookings.filter((row) => row.check_out_date === businessDate && bookingStatus(row) !== "checked_out").length;
    const nightAuditStatus = normalizeAuditStatus(summary, auditBlockers);

    return [
      { label: "Business Date", value: businessDate, tone: "neutral" },
      { label: "Occupancy %", value: `${occupancy}%`, tone: occupancy > 90 ? "warning" : "success" },
      { label: "Available Rooms", value: availableRooms, tone: availableRooms <= 5 ? "warning" : "success" },
      { label: "Arrivals", value: arrivals, tone: arrivals ? "info" : "neutral" },
      { label: "Departures", value: departures, tone: departures ? "info" : "neutral" },
      {
        label: "Housekeeping Alerts",
        value: dirtyRooms + outOfOrder + outOfService,
        tone: dirtyRooms + outOfOrder + outOfService ? "warning" : "success",
      },
      { label: "Cashier Shifts Open", value: cashierOpen, tone: cashierOpen ? "warning" : "success" },
      {
        label: "Night Audit Status",
        value: nightAuditStatus,
        tone:
          nightAuditStatus === "BLOCKED"
            ? "danger"
            : nightAuditStatus === "READY" || nightAuditStatus === "CLOSED"
              ? "success"
              : "warning",
      },
    ];
  }, [bookings, businessDate, kpi, rooms, summary]);

  return (
    <div className="pms-status-ribbon" aria-label="Hotel operating status">
      {ribbonItems.map((item) => (
        <div key={item.label} className={`pms-status-ribbon-item ${item.tone}`}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}
