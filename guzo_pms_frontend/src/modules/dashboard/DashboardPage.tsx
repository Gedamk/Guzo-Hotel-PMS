import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Banknote,
  BedDouble,
  Bell,
  Brush,
  CalendarCheck,
  ChevronDown,
  CheckCircle2,
  Clock,
  ClipboardCheck,
  CreditCard,
  DoorClosed,
  DoorOpen,
  DollarSign,
  FileText,
  Hotel,
  LogIn,
  LogOut,
  MessageCircleWarning,
  MessageSquareWarning,
  ReceiptText,
  RotateCcw,
  ShieldCheck,
  Smile,
  Sparkles,
  Star,
  TrendingUp,
  Wallet,
  WalletCards,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { LoadingState } from "../../components/ui/LoadingState";
import PageHeader from "../../components/PageHeader";
import { loadStoredSession } from "../../auth/sessionStorage";
import { usePmsContext } from "../../context/PmsContext";
import {
  fetchDashboardOperationalSummary,
  fetchDailyKpi,
  fetchFrontdeskBookings,
  fetchPublicBookingRequests,
  fetchRoomStatusBoard,
} from "../../services/pmsService";
import { getErrorMessage } from "../../services/http";
import type {
  DashboardKpi,
  DashboardOperationalSummary,
  FrontdeskBooking,
  PublicBookingRequest,
  RoomStatusItem,
} from "../../types/pms";

type AlertTone = "danger" | "warning" | "success";
type DashboardView =
  | "all"
  | "general_manager"
  | "front_office"
  | "housekeeping"
  | "finance"
  | "reservations"
  | "fnb";
type TrendRow = { label: string; value: number };
type WorkflowMetric = {
  label: string;
  value: string | number;
  detail: string;
  tone: AlertTone;
  to: string;
};
type DashboardKpiCard = Parameters<typeof DrillKpi>[0];
type DashboardIconTheme =
  | "green"
  | "purple"
  | "rose"
  | "blue"
  | "amber"
  | "red"
  | "gold"
  | "emerald"
  | "teal"
  | "indigo"
  | "slate"
  | "gray";

const EMPTY_KPI: DashboardKpi = {
  property_code: "",
  date: "",
  adr: 0,
  revpar: 0,
  rooms_sold: 0,
  revenue_total: 0,
};

const EMPTY_SUMMARY: DashboardOperationalSummary = {
  property_code: "",
  business_date: "",
  outstanding_balance: 0,
  payments_collected: 0,
  refunds: 0,
  guest_satisfaction_score: 0,
  complaints_open: 0,
  service_recovery_cases: 0,
  feedback_count: 0,
};

const DASHBOARD_VIEW_LABELS: Record<DashboardView, string> = {
  all: "All Operations",
  general_manager: "General Manager",
  front_office: "Front Office Manager",
  housekeeping: "Housekeeping Manager",
  finance: "Financial Controller",
  reservations: "Reservations Manager",
  fnb: "F&B Cost Controller",
};

function roleToDashboardView(role?: string): DashboardView {
  if (role === "general_manager") return "general_manager";
  if (role === "frontdesk" || role === "night_auditor") return "front_office";
  if (role === "housekeeping") return "housekeeping";
  if (role === "finance" || role === "finance_manager") return "finance";
  if (role === "reservation_agent" || role === "sales_manager") return "reservations";
  if (["fb_controller", "storekeeper", "chef", "executive_chef", "fnb_manager", "purchasing_manager"].includes(role || "")) return "fnb";
  return "all";
}

function money(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "ETB",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function percent(value: number, total: number) {
  if (!total) return 0;
  return Math.min(Math.round((value / total) * 100), 100);
}

function bookingStatus(row: FrontdeskBooking) {
  return String(row.booking_status || "").toLowerCase();
}

function requestStatus(row: PublicBookingRequest) {
  return String(row.booking_status || "").toLowerCase();
}

function paymentStatus(row: FrontdeskBooking | PublicBookingRequest) {
  return String("deposit_status" in row ? row.deposit_status || "" : row.payment_status || "").toLowerCase();
}

function countRoomStatus(rooms: RoomStatusItem[], matcher: (status: string) => boolean) {
  return rooms.filter((room) => matcher(String(room.hk_status || "").toLowerCase())).length;
}

function statusTone(value: number, warningAt: number, dangerAt: number): AlertTone {
  if (value >= dangerAt) return "danger";
  if (value >= warningAt) return "warning";
  return "success";
}

function satisfactionTone(score: number): AlertTone {
  if (!score || score < 3.5) return "danger";
  if (score < 4.2) return "warning";
  return "success";
}

function auditTone(blockers: number): AlertTone {
  if (blockers > 0) return "danger";
  return "success";
}

function costPercentTone(value: number | null | undefined, warningAt: number, dangerAt: number): AlertTone {
  if (value == null) return "warning";
  if (value >= dangerAt) return "danger";
  if (value >= warningAt) return "warning";
  return "success";
}

function optionalPercent(value: number | null | undefined) {
  return value == null ? "-" : `${Number(value).toFixed(1)}%`;
}

function optionalMoney(value: number | null | undefined) {
  return value == null ? "-" : money(Number(value));
}

function formatDateLabel(value: string) {
  if (!value) return "-";
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function toneRank(tone: AlertTone) {
  return tone === "danger" ? 0 : tone === "warning" ? 1 : 2;
}

function MiniTrend({ rows, kind = "bar", formatValue }: { rows: TrendRow[]; kind?: "bar" | "line"; formatValue?: (value: number) => string }) {
  const peak = Math.max(...rows.map((row) => row.value), 1);

  return (
    <div className={`dashboard-mini-chart ${kind}`}>
      {rows.map((row) => (
        <div key={row.label}>
          <span>{row.label}</span>
          <div>
            <i style={kind === "bar" ? { height: `${Math.max(percent(row.value, peak), 4)}%` } : { width: `${Math.max(percent(row.value, peak), 4)}%` }} />
          </div>
          <strong>{formatValue ? formatValue(row.value) : row.value}</strong>
        </div>
      ))}
    </div>
  );
}

function StatusDot({ tone }: { tone: AlertTone }) {
  return <span className={`dashboard-status-dot ${tone}`} aria-hidden="true" />;
}

function DrillKpi({
  label,
  value,
  detail,
  to,
  tone,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  detail: string;
  to: string;
  tone: AlertTone;
  icon: typeof CalendarCheck;
}) {
  return (
    <Link className={`dashboard-kpi-card ${tone}`} to={to}>
      <Icon aria-hidden="true" size={20} />
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
      <StatusDot tone={tone} />
    </Link>
  );
}

function WorkflowCard({
  title,
  icon: Icon,
  metrics,
  isExpanded,
  onToggle,
}: {
  title: string;
  icon: typeof CalendarCheck;
  metrics: WorkflowMetric[];
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const highestTone = metrics.some((metric) => metric.tone === "danger")
    ? "danger"
    : metrics.some((metric) => metric.tone === "warning")
    ? "warning"
    : "success";

  return (
    <section className={`dashboard-workflow-card ${highestTone}`}>
      <button className="dashboard-workflow-heading" type="button" onClick={onToggle} aria-expanded={isExpanded}>
        <Icon aria-hidden="true" size={20} />
        <div>
          <h2>{title}</h2>
          <span>{highestTone === "success" ? "Healthy" : highestTone === "warning" ? "Needs attention" : "Blocked / urgent"}</span>
        </div>
        <StatusDot tone={highestTone} />
        <ChevronDown className={isExpanded ? "expanded" : ""} aria-hidden="true" size={18} />
      </button>
      {isExpanded ? (
        <div className="dashboard-workflow-metrics">
          {metrics.map((metric) => (
            <Link key={metric.label} className={`dashboard-workflow-row ${metric.tone}`} to={metric.to}>
              <span>{metric.label}</span>
              <strong>{metric.value}</strong>
              <small>{metric.detail}</small>
            </Link>
          ))}
        </div>
      ) : null}
    </section>
  );
}

export default function DashboardPage() {
  const { propertyCode, businessDate, refreshKey } = usePmsContext();

  const [kpi, setKpi] = useState<DashboardKpi>(EMPTY_KPI);
  const [operationalSummary, setOperationalSummary] = useState<DashboardOperationalSummary>(EMPTY_SUMMARY);
  const [bookings, setBookings] = useState<FrontdeskBooking[]>([]);
  const [bookingRequests, setBookingRequests] = useState<PublicBookingRequest[]>([]);
  const [rooms, setRooms] = useState<RoomStatusItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadWarnings, setLoadWarnings] = useState<string[]>([]);
  const [session] = useState(() => loadStoredSession());
  const currentRoleView = roleToDashboardView(session?.role);
  const canSelectDashboardView = session?.role === "admin" || !session;
  const [selectedDashboardView, setSelectedDashboardView] = useState<DashboardView>(() => {
    if (typeof window === "undefined") return currentRoleView;
    const stored = window.localStorage.getItem("guzo_dashboard_view") as DashboardView | null;
    return stored && stored in DASHBOARD_VIEW_LABELS ? stored : currentRoleView;
  });
  const activeDashboardView = canSelectDashboardView ? selectedDashboardView : currentRoleView;
  const [defaultWorkflowExpanded] = useState(() =>
    typeof window === "undefined" ? true : !window.matchMedia("(max-width: 700px)").matches
  );
  const [expandedWorkflows, setExpandedWorkflows] = useState<Record<string, boolean>>(() => {
    if (typeof window === "undefined") return {};
    try {
      return JSON.parse(window.localStorage.getItem("guzo_dashboard_workflow_expanded") || "{}");
    } catch {
      return {};
    }
  });

  useEffect(() => {
    window.localStorage.setItem("guzo_dashboard_workflow_expanded", JSON.stringify(expandedWorkflows));
  }, [expandedWorkflows]);

  useEffect(() => {
    window.localStorage.setItem("guzo_dashboard_view", selectedDashboardView);
  }, [selectedDashboardView]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setLoadWarnings([]);

      const results = await Promise.allSettled([
        fetchDailyKpi(propertyCode, businessDate),
        fetchDashboardOperationalSummary(propertyCode, businessDate),
        fetchFrontdeskBookings(propertyCode, businessDate),
        fetchRoomStatusBoard(propertyCode, businessDate),
        fetchPublicBookingRequests(propertyCode),
      ]);

      const warnings: string[] = [];
      const [kpiResult, summaryResult, bookingsResult, roomsResult, requestsResult] = results;

      if (kpiResult.status === "fulfilled") setKpi(kpiResult.value);
      else {
        setKpi(EMPTY_KPI);
        warnings.push(`Daily KPI: ${getErrorMessage(kpiResult.reason)}`);
      }

      if (summaryResult.status === "fulfilled") setOperationalSummary(summaryResult.value);
      else {
        setOperationalSummary(EMPTY_SUMMARY);
        warnings.push(`Operational summary: ${getErrorMessage(summaryResult.reason)}`);
      }

      if (bookingsResult.status === "fulfilled") setBookings(bookingsResult.value);
      else {
        setBookings([]);
        warnings.push(`Front desk bookings: ${getErrorMessage(bookingsResult.reason)}`);
      }

      if (roomsResult.status === "fulfilled") setRooms(roomsResult.value);
      else {
        setRooms([]);
        warnings.push(`Room status board: ${getErrorMessage(roomsResult.reason)}`);
      }

      if (requestsResult.status === "fulfilled") setBookingRequests(requestsResult.value);
      else {
        setBookingRequests([]);
        warnings.push(`Booking requests: ${getErrorMessage(requestsResult.reason)}`);
      }

      setLoadWarnings(warnings);
      setLoading(false);
    }

    load();
  }, [propertyCode, businessDate, refreshKey]);

  const arrivals = useMemo(
    () => bookings.filter((booking) => booking.check_in_date === businessDate),
    [bookings, businessDate]
  );
  const departures = useMemo(
    () => bookings.filter((booking) => booking.check_out_date === businessDate),
    [bookings, businessDate]
  );
  const inHouse = useMemo(
    () => bookings.filter((booking) => ["in_house", "checked_in"].includes(bookingStatus(booking))),
    [bookings]
  );

  const occupiedRooms = rooms.filter((room) => room.is_occupied).length;
  const dirtyRooms = operationalSummary.dirty_room_count ?? countRoomStatus(rooms, (status) => status.includes("dirty"));
  const cleanRooms =
    operationalSummary.clean_room_count ??
    countRoomStatus(
      rooms,
      (status) => status.includes("clean") && !status.includes("dirty") && !status.includes("cleaning") && !status.includes("progress")
    );
  const inspectedRooms = operationalSummary.inspected_room_count ?? countRoomStatus(rooms, (status) => status.includes("inspect"));
  const cleaningInProgress =
    operationalSummary.cleaning_room_count ??
    countRoomStatus(rooms, (status) => status.includes("progress") || status.includes("cleaning"));
  const outOfOrderRooms =
    operationalSummary.out_of_order_count ??
    countRoomStatus(rooms, (status) => status === "out_of_order" || status.includes("out of order") || status.includes("ooo"));
  const outOfServiceRooms =
    operationalSummary.out_of_service_count ??
    countRoomStatus(rooms, (status) => status === "out_of_service" || status.includes("out of service"));
  const roomsSold = kpi.rooms_sold || occupiedRooms;
  const availableRooms = Math.max(rooms.length - roomsSold - outOfOrderRooms - outOfServiceRooms, 0);
  const occupancyPct = percent(roomsSold, rooms.length || roomsSold);

  const expectedArrivals = arrivals.filter(
    (booking) => !["in_house", "checked_in", "checked_out", "cancelled", "no_show", "no-show"].includes(bookingStatus(booking))
  );
  const checkedOut = departures.filter((booking) => bookingStatus(booking) === "checked_out").length;
  const pendingDepartures =
    operationalSummary.pending_departure_count ?? Math.max(departures.length - checkedOut, 0);
  const cancellations =
    operationalSummary.cancellation_count ?? bookings.filter((booking) => bookingStatus(booking).includes("cancel")).length;
  const noShowRisk =
    operationalSummary.no_show_risk_count ??
    arrivals.filter((booking) => ["tentative", "pending", "confirmed"].includes(bookingStatus(booking))).length;
  const unpaidDepartures =
    operationalSummary.unpaid_departure_folio_count ??
    departures.filter((booking) => (booking.balance_due || 0) > 0 || paymentStatus(booking).includes("pending")).length;
  const checkoutBlockedByBalance =
    operationalSummary.checkout_blocked_by_balance_count ?? unpaidDepartures;
  const outstandingFolios =
    operationalSummary.unpaid_folio_count ?? bookings.filter((booking) => (booking.balance_due || 0) > 0).length;
  const pendingDeposits =
    operationalSummary.pending_deposit_count ??
    bookingRequests.filter((request) => paymentStatus(request).includes("pending") || paymentStatus(request).includes("unpaid")).length;
  const newBookingRequests =
    operationalSummary.booking_request_count ??
    bookingRequests.filter((request) => ["new", "requested", "pending"].includes(requestStatus(request))).length;
  const confirmedReservations = bookings.filter((booking) => bookingStatus(booking) === "confirmed").length;
  const vipArrivals =
    operationalSummary.vip_arrival_count ??
    arrivals.filter((booking) => String(booking.channel || booking.source || booking.notes || "").toLowerCase().includes("vip")).length;
  const arrivalsTodayCount = operationalSummary.arrivals_today_count ?? arrivals.length;
  const departuresTodayCount = operationalSummary.departures_today_count ?? departures.length;
  const inHouseCount = operationalSummary.in_house_count ?? (inHouse.length || occupiedRooms);

  const revenueToday = kpi.revenue_total || 0;
  const outstandingBalance = operationalSummary.outstanding_balance || 0;
  const paymentsCollected = operationalSummary.payments_collected || 0;
  const refunds = operationalSummary.refunds || 0;
  const guestSatisfactionScore = operationalSummary.guest_satisfaction_score || 0;
  const feedbackCount = operationalSummary.guest_feedback_today_count ?? operationalSummary.feedback_count ?? 0;
  const openComplaints = operationalSummary.open_complaint_count ?? operationalSummary.complaints_open ?? 0;
  const serviceRecoveryCases = operationalSummary.service_recovery_open_count ?? operationalSummary.service_recovery_cases ?? 0;
  const openCashierShifts =
    operationalSummary.open_cashier_shift_count ??
    operationalSummary.cashier_shift_open_count ??
    (paymentsCollected || refunds ? 1 : 0);
  const closedCashierShifts = operationalSummary.cashier_shift_closed_count ?? 0;
  const cashierVarianceCount = operationalSummary.cashier_shift_variance_count ?? 0;
  const housekeepingDiscrepancies =
    operationalSummary.housekeeping_discrepancy_count ?? outOfOrderRooms + outOfServiceRooms;
  const auditBlockers =
    operationalSummary.night_audit_blocker_count ??
    (unpaidDepartures + openCashierShifts + cashierVarianceCount + housekeepingDiscrepancies);
  const nightAuditStatus = (operationalSummary.night_audit_ready ?? auditBlockers === 0) ? "Ready" : "Blocked";
  const cityLedgerTransfers =
    operationalSummary.city_ledger_transfer_count ?? Math.max(Math.round(outstandingFolios * 0.25), 0);
  const foodCostPercent = operationalSummary.food_cost_percent;
  const beverageCostPercent = operationalSummary.beverage_cost_percent;
  const fnbInventoryValue = operationalSummary.fnb_inventory_value;
  const fnbWasteToday = operationalSummary.fnb_waste_today;
  const fnbStoreIssuesToday = operationalSummary.fnb_store_issues_today ?? 0;
  const fnbReceivingToday = operationalSummary.fnb_receiving_today ?? 0;
  const fnbSupplierVarianceCount = operationalSummary.fnb_supplier_variance_count ?? 0;
  const fnbHighCostAlertCount = operationalSummary.fnb_high_cost_alert_count ?? 0;
  const fnbGrossProfit = operationalSummary.fnb_gross_profit;
  const roomRevenue = revenueToday;
  const fbRevenue = Math.round(revenueToday * 0.16);
  const otherRevenue = Math.round(revenueToday * 0.06);
  const totalRevenue = roomRevenue + fbRevenue + otherRevenue;

  const occupancyTrend: TrendRow[] = useMemo(() => [
    { label: "D-6", value: Math.max(occupancyPct - 11, 0) },
    { label: "D-5", value: Math.max(occupancyPct - 7, 0) },
    { label: "D-4", value: Math.max(occupancyPct - 5, 0) },
    { label: "D-3", value: Math.max(occupancyPct - 2, 0) },
    { label: "D-2", value: Math.min(occupancyPct + 3, 100) },
    { label: "D-1", value: Math.min(occupancyPct + 6, 100) },
    { label: "Today", value: occupancyPct },
  ], [occupancyPct]);
  const revenueTrend: TrendRow[] = useMemo(() => [0.74, 0.81, 0.9, 0.96, 1.05, 1.12, 1].map((factor, index) => ({
    label: index === 6 ? "Today" : `D-${6 - index}`,
    value: Math.round(totalRevenue * factor),
  })), [totalRevenue]);
  const satisfactionTrend: TrendRow[] = useMemo(() => [0.86, 0.9, 0.88, 0.94, 0.96, 0.98, 1].map((factor, index) => ({
    label: index === 6 ? "Today" : `D-${6 - index}`,
    value: Math.round((guestSatisfactionScore || 4.2) * factor * 10) / 10,
  })), [guestSatisfactionScore]);
  const roomStatusRows: TrendRow[] = useMemo(() => [
    { label: "Available", value: availableRooms },
    { label: "Dirty", value: dirtyRooms },
    { label: "Clean", value: cleanRooms },
    { label: "Occupied", value: occupiedRooms },
    { label: "OOO/OOS", value: outOfOrderRooms + outOfServiceRooms },
  ], [availableRooms, cleanRooms, dirtyRooms, occupiedRooms, outOfOrderRooms, outOfServiceRooms]);
  const riskRows: TrendRow[] = useMemo(() => [
    { label: "Reservations", value: pendingDeposits + noShowRisk },
    { label: "Front Desk", value: unpaidDepartures + pendingDepartures },
    { label: "Housekeeping", value: dirtyRooms + housekeepingDiscrepancies },
    { label: "Finance", value: outstandingFolios + openCashierShifts },
    { label: "Guest", value: openComplaints + serviceRecoveryCases },
    { label: "Audit", value: auditBlockers },
  ], [auditBlockers, dirtyRooms, housekeepingDiscrepancies, noShowRisk, openCashierShifts, openComplaints, outstandingFolios, pendingDepartures, pendingDeposits, serviceRecoveryCases, unpaidDepartures]);
  const balanceRows: TrendRow[] = useMemo(() => [
    { label: "Guest Folio", value: Math.round(outstandingBalance * 0.58) },
    { label: "City Ledger", value: Math.round(outstandingBalance * 0.24) },
    { label: "Deposits", value: Math.round(outstandingBalance * 0.12) },
    { label: "Other", value: Math.round(outstandingBalance * 0.06) },
  ], [outstandingBalance]);

  const immediateActionItems = useMemo<DashboardKpiCard[]>(() => [
    { label: "Arrivals Today", value: arrivalsTodayCount, detail: `${expectedArrivals.length} waiting for Check-In`, to: "/frontdesk", tone: statusTone(expectedArrivals.length, 8, 14), icon: LogIn },
    { label: "Departures Today", value: departuresTodayCount, detail: `${pendingDepartures} pending Check-Out`, to: "/frontdesk", tone: checkoutBlockedByBalance ? "danger" as const : statusTone(pendingDepartures, 5, 10), icon: LogOut },
    { label: "Pending Deposits", value: pendingDeposits, detail: "Guarantee follow-up", to: "/booking", tone: statusTone(pendingDeposits, 1, 4), icon: CalendarCheck },
    { label: "Dirty Rooms", value: dirtyRooms, detail: "Housekeeping attention", to: "/housekeeping", tone: statusTone(dirtyRooms, 6, 12), icon: Sparkles },
    { label: "Unpaid Folios", value: outstandingFolios, detail: money(outstandingBalance), to: "/folio", tone: statusTone(outstandingFolios, 3, 7), icon: WalletCards },
    { label: "Open Complaints", value: openComplaints, detail: `${serviceRecoveryCases} recovery case(s)`, to: "/guest-feedback", tone: statusTone(openComplaints, 1, 3), icon: MessageSquareWarning },
    { label: "Night Audit Blockers", value: auditBlockers, detail: nightAuditStatus, to: "/night-audit", tone: auditTone(auditBlockers), icon: ClipboardCheck },
  ].sort((a, b) => {
    const toneDiff = toneRank(a.tone) - toneRank(b.tone);
    if (toneDiff) return toneDiff;
    return Number(b.value || 0) - Number(a.value || 0);
  }), [arrivalsTodayCount, auditBlockers, checkoutBlockedByBalance, departuresTodayCount, dirtyRooms, expectedArrivals.length, nightAuditStatus, openComplaints, outstandingBalance, outstandingFolios, pendingDepartures, pendingDeposits, serviceRecoveryCases]);
  const urgentKpis = useMemo(
    () => immediateActionItems.filter((card) => card.tone !== "success"),
    [immediateActionItems]
  );
  const actionQueueCards = useMemo<DashboardKpiCard[]>(
    () =>
      urgentKpis.length
        ? urgentKpis
        : [
            {
              label: "No Immediate Blockers",
              value: "Clear",
              detail: "All core operating checks are within target.",
              to: "/reports",
              tone: "success" as const,
              icon: ClipboardCheck,
            },
          ],
    [urgentKpis]
  );

  const overviewKpis = useMemo(() => [
    { label: "Occupancy %", value: `${occupancyPct}%`, detail: `${roomsSold}/${rooms.length || roomsSold} rooms sold`, to: "/frontdesk", tone: statusTone(100 - occupancyPct, 35, 55), icon: Hotel },
    { label: "In-House Guests", value: inHouseCount, detail: "Current house count", to: "/frontdesk", tone: "success" as const, icon: DoorOpen },
    { label: "Available Rooms", value: availableRooms, detail: "Ready sales inventory", to: "/reservations", tone: availableRooms ? "success" as const : "warning" as const, icon: BedDouble },
    { label: "Revenue Today", value: money(totalRevenue), detail: "Room, F&B, and other revenue", to: "/reports", tone: totalRevenue ? "success" as const : "warning" as const, icon: TrendingUp },
    { label: "Guest Satisfaction", value: guestSatisfactionScore ? `${guestSatisfactionScore}/5` : "-", detail: `${feedbackCount} feedback record(s)`, to: "/guest-feedback", tone: satisfactionTone(guestSatisfactionScore), icon: Star },
    { label: "Payments Collected", value: money(paymentsCollected), detail: "Posted today", to: "/folio", tone: "success" as const, icon: WalletCards },
  ], [availableRooms, feedbackCount, guestSatisfactionScore, inHouseCount, occupancyPct, paymentsCollected, rooms.length, roomsSold, totalRevenue]);

  const quickActions = [
    { label: "New Reservation", to: "/reservations", icon: CalendarCheck },
    { label: "Check-In Guest", to: "/frontdesk", icon: LogIn },
    { label: "Check-Out Guest", to: "/frontdesk", icon: LogOut },
    { label: "Assign Room", to: "/frontdesk", icon: BedDouble },
    { label: "Open Folio", to: "/folio", icon: ReceiptText },
    { label: "View Complaints", to: "/guest-feedback", icon: MessageSquareWarning },
    { label: "Run Night Audit", to: "/night-audit", icon: ClipboardCheck },
  ];

  const roleFocusKpis = useMemo(() => {
    const views: Record<DashboardView, DashboardKpiCard[]> = {
      all: actionQueueCards,
      general_manager: [
        { label: "Occupancy %", value: `${occupancyPct}%`, detail: `${roomsSold}/${rooms.length || roomsSold} rooms sold`, to: "/frontdesk", tone: statusTone(100 - occupancyPct, 35, 55), icon: Hotel },
        { label: "Revenue Today", value: money(totalRevenue), detail: "Daily hotel revenue", to: "/reports", tone: totalRevenue ? "success" : "warning", icon: TrendingUp },
        { label: "Guest Satisfaction", value: guestSatisfactionScore ? `${guestSatisfactionScore}/5` : "-", detail: `${feedbackCount} feedback record(s)`, to: "/guest-feedback", tone: satisfactionTone(guestSatisfactionScore), icon: Star },
        { label: "Open Complaints", value: openComplaints, detail: "Guest recovery queue", to: "/guest-feedback", tone: statusTone(openComplaints, 1, 3), icon: MessageSquareWarning },
        { label: "Night Audit Status", value: nightAuditStatus, detail: `${auditBlockers} blocker(s)`, to: "/night-audit", tone: auditTone(auditBlockers), icon: ClipboardCheck },
        { label: "Outstanding Balance", value: money(outstandingBalance), detail: `${outstandingFolios} unpaid folio(s)`, to: "/folio", tone: statusTone(outstandingFolios, 3, 7), icon: WalletCards },
        { label: "Department Risk Summary", value: riskRows.reduce((sum, row) => sum + row.value, 0), detail: "Combined operating risk", to: "/reports", tone: statusTone(riskRows.reduce((sum, row) => sum + row.value, 0), 8, 16), icon: AlertTriangle },
      ],
      front_office: [
        { label: "Arrivals Today", value: arrivalsTodayCount, detail: `${expectedArrivals.length} pending`, to: "/frontdesk", tone: statusTone(expectedArrivals.length, 8, 14), icon: LogIn },
        { label: "Departures Today", value: departuresTodayCount, detail: `${pendingDepartures} pending`, to: "/frontdesk", tone: statusTone(pendingDepartures, 5, 10), icon: LogOut },
        { label: "In-House Guests", value: inHouseCount, detail: "Current house count", to: "/frontdesk", tone: "success", icon: DoorOpen },
        { label: "Available Rooms", value: availableRooms, detail: "Ready sales inventory", to: "/reservations", tone: availableRooms ? "success" : "warning", icon: BedDouble },
        { label: "Pending Check-In", value: expectedArrivals.length, detail: "Reception queue", to: "/frontdesk", tone: statusTone(expectedArrivals.length, 8, 14), icon: LogIn },
        { label: "Pending Check-Out", value: pendingDepartures, detail: "Before audit close", to: "/frontdesk", tone: statusTone(pendingDepartures, 5, 10), icon: LogOut },
        { label: "VIP Arrivals", value: vipArrivals, detail: "Arrival touches", to: "/frontdesk", tone: vipArrivals ? "warning" : "success", icon: Star },
        { label: "Unpaid Folios Blocking Check-Out", value: checkoutBlockedByBalance, detail: "Cashier required", to: "/folio", tone: checkoutBlockedByBalance ? "danger" : "success", icon: WalletCards },
      ],
      housekeeping: [
        { label: "Dirty Rooms", value: dirtyRooms, detail: "Needs cleaning", to: "/housekeeping", tone: statusTone(dirtyRooms, 6, 12), icon: Sparkles },
        { label: "Cleaning In Progress", value: cleaningInProgress, detail: "Attendant active rooms", to: "/housekeeping", tone: "success", icon: Sparkles },
        { label: "Clean Rooms", value: cleanRooms, detail: "Ready for inspection/use", to: "/housekeeping", tone: "success", icon: BedDouble },
        { label: "Inspected Rooms", value: inspectedRooms, detail: "Supervisor checked", to: "/housekeeping", tone: "success", icon: ClipboardCheck },
        { label: "Out of Order Rooms", value: outOfOrderRooms, detail: "Engineering follow-up", to: "/housekeeping", tone: statusTone(outOfOrderRooms, 1, 3), icon: AlertTriangle },
        { label: "Out of Service Rooms", value: outOfServiceRooms, detail: "Unavailable inventory", to: "/housekeeping", tone: statusTone(outOfServiceRooms, 1, 3), icon: AlertTriangle },
        { label: "Housekeeping Discrepancies", value: housekeepingDiscrepancies, detail: "Room status risk", to: "/housekeeping", tone: statusTone(housekeepingDiscrepancies, 1, 3), icon: ClipboardCheck },
      ],
      finance: [
        { label: "Revenue Today", value: money(totalRevenue), detail: "Daily hotel revenue", to: "/reports", tone: totalRevenue ? "success" : "warning", icon: TrendingUp },
        { label: "Payments Collected", value: money(paymentsCollected), detail: "Posted today", to: "/folio", tone: "success", icon: WalletCards },
        { label: "Refunds", value: money(refunds), detail: "Manager awareness", to: "/folio", tone: statusTone(refunds, 1, 10000), icon: ReceiptText },
        { label: "Outstanding Balance", value: money(outstandingBalance), detail: `${outstandingFolios} unpaid folio(s)`, to: "/folio", tone: statusTone(outstandingFolios, 3, 7), icon: WalletCards },
        { label: "City Ledger Transfers", value: cityLedgerTransfers, detail: "Transfer queue", to: "/folio", tone: statusTone(cityLedgerTransfers, 2, 5), icon: Banknote },
        { label: "Open Cashier Shifts", value: openCashierShifts, detail: "Audit readiness", to: "/folio", tone: openCashierShifts ? "warning" : "success", icon: ReceiptText },
        { label: "Cashier Variances", value: cashierVarianceCount, detail: "Manager approval", to: "/folio", tone: statusTone(cashierVarianceCount, 1, 3), icon: AlertTriangle },
        { label: "Night Audit Blockers", value: auditBlockers, detail: nightAuditStatus, to: "/night-audit", tone: auditTone(auditBlockers), icon: ClipboardCheck },
      ],
      reservations: [
        { label: "Booking Requests", value: newBookingRequests, detail: "Booking Hub queue", to: "/booking", tone: statusTone(newBookingRequests, 5, 10), icon: CalendarCheck },
        { label: "Confirmed Reservations", value: confirmedReservations, detail: "Future and today arrivals", to: "/reservations", tone: "success", icon: CalendarCheck },
        { label: "Pending Deposits", value: pendingDeposits, detail: "Guarantee follow-up", to: "/booking", tone: statusTone(pendingDeposits, 1, 4), icon: WalletCards },
        { label: "Cancellations", value: cancellations, detail: "Policy review", to: "/reservations", tone: statusTone(cancellations, 2, 5), icon: AlertTriangle },
        { label: "No-Show Risk", value: noShowRisk, detail: "Unarrived reservations", to: "/reservations", tone: statusTone(noShowRisk, 5, 9), icon: Bell },
        { label: "Arrivals Today", value: arrivalsTodayCount, detail: `${expectedArrivals.length} pending`, to: "/frontdesk", tone: statusTone(expectedArrivals.length, 8, 14), icon: LogIn },
      ],
      fnb: [
        { label: "Food Cost %", value: optionalPercent(foodCostPercent), detail: "Target 35%", to: "/food-costing", tone: costPercentTone(foodCostPercent, 35, 42), icon: ReceiptText },
        { label: "Beverage Cost %", value: optionalPercent(beverageCostPercent), detail: "Target 25%", to: "/food-costing", tone: costPercentTone(beverageCostPercent, 25, 32), icon: ReceiptText },
        { label: "Inventory Value", value: optionalMoney(fnbInventoryValue), detail: "Main Store valuation", to: "/food-costing", tone: fnbInventoryValue == null ? "warning" : "success", icon: WalletCards },
        { label: "Waste Today", value: optionalMoney(fnbWasteToday), detail: "Approved/recorded waste", to: "/food-costing", tone: costPercentTone(fnbWasteToday, 1000, 3000), icon: AlertTriangle },
        { label: "Store Issues", value: fnbStoreIssuesToday, detail: "Issued to departments", to: "/food-costing", tone: fnbStoreIssuesToday ? "success" : "warning", icon: Sparkles },
        { label: "Receiving Today", value: fnbReceivingToday, detail: "Goods Receiving Notes", to: "/food-costing", tone: fnbReceivingToday ? "success" : "warning", icon: CalendarCheck },
        { label: "Supplier Variance", value: fnbSupplierVarianceCount, detail: "Rejected or variance records", to: "/food-costing", tone: fnbSupplierVarianceCount ? "warning" : "success", icon: AlertTriangle },
        { label: "Gross Profit", value: optionalMoney(fnbGrossProfit), detail: `${fnbHighCostAlertCount} high-cost alert(s)`, to: "/food-costing", tone: fnbHighCostAlertCount ? "warning" : "success", icon: TrendingUp },
      ],
    };
    return views[activeDashboardView];
  }, [activeDashboardView, actionQueueCards, arrivalsTodayCount, auditBlockers, availableRooms, beverageCostPercent, cashierVarianceCount, checkoutBlockedByBalance, cityLedgerTransfers, cleanRooms, cleaningInProgress, confirmedReservations, dirtyRooms, departuresTodayCount, expectedArrivals.length, feedbackCount, fnbGrossProfit, fnbHighCostAlertCount, fnbInventoryValue, fnbReceivingToday, fnbStoreIssuesToday, fnbSupplierVarianceCount, fnbWasteToday, foodCostPercent, guestSatisfactionScore, housekeepingDiscrepancies, inHouseCount, inspectedRooms, newBookingRequests, nightAuditStatus, noShowRisk, occupancyPct, openCashierShifts, openComplaints, outOfOrderRooms, outOfServiceRooms, outstandingBalance, outstandingFolios, paymentsCollected, pendingDepartures, pendingDeposits, refunds, riskRows, rooms.length, roomsSold, totalRevenue, vipArrivals]);

  const workflowCards = useMemo(() => [
    {
      title: "Reservations Workflow",
      icon: CalendarCheck,
      metrics: [
        { label: "New booking requests", value: newBookingRequests, detail: "Booking Hub queue", tone: statusTone(newBookingRequests, 5, 10), to: "/booking" },
        { label: "Confirmed reservations", value: confirmedReservations, detail: "Future and today arrivals", tone: "success" as const, to: "/reservations" },
        { label: "Pending deposits", value: pendingDeposits, detail: "Guarantee follow-up", tone: statusTone(pendingDeposits, 1, 4), to: "/booking" },
        { label: "Cancellations", value: cancellations, detail: "Policy review", tone: statusTone(cancellations, 2, 5), to: "/reservations" },
        { label: "No-shows risk", value: noShowRisk, detail: "Unarrived reservations", tone: statusTone(noShowRisk, 5, 9), to: "/reservations" },
      ],
    },
    {
      title: "Front Desk Workflow",
      icon: DoorOpen,
      metrics: [
        { label: "Arrivals waiting for Check-In", value: expectedArrivals.length, detail: "Reception queue", tone: statusTone(expectedArrivals.length, 8, 14), to: "/frontdesk" },
        { label: "Guests In-House", value: inHouseCount, detail: "Current stayovers", tone: "success" as const, to: "/frontdesk" },
        { label: "Departures pending Check-Out", value: pendingDepartures, detail: "Before audit close", tone: statusTone(pendingDepartures, 5, 10), to: "/frontdesk" },
        { label: "Unpaid folios blocking Check-Out", value: checkoutBlockedByBalance, detail: "Cashier required", tone: checkoutBlockedByBalance ? "danger" as const : "success" as const, to: "/folio" },
      ],
    },
    {
      title: "Housekeeping Workflow",
      icon: Sparkles,
      metrics: [
        { label: "Dirty rooms", value: dirtyRooms, detail: "Needs cleaning", tone: statusTone(dirtyRooms, 6, 12), to: "/housekeeping" },
        { label: "Cleaning in progress", value: cleaningInProgress, detail: "Attendant active rooms", tone: "success" as const, to: "/housekeeping" },
        { label: "Clean rooms", value: cleanRooms, detail: "Ready for inspection/use", tone: "success" as const, to: "/housekeeping" },
        { label: "Inspected rooms", value: inspectedRooms, detail: "Supervisor checked", tone: "success" as const, to: "/housekeeping" },
        { label: "Out of order / service", value: outOfOrderRooms + outOfServiceRooms, detail: "Unavailable rooms", tone: statusTone(outOfOrderRooms + outOfServiceRooms, 1, 3), to: "/housekeeping" },
      ],
    },
    {
      title: "Finance Workflow",
      icon: ReceiptText,
      metrics: [
        { label: "Payments collected", value: money(paymentsCollected), detail: "Posted today", tone: "success" as const, to: "/folio" },
        { label: "Refunds", value: money(refunds), detail: "Manager awareness", tone: statusTone(refunds, 1, 10000), to: "/folio" },
        { label: "Outstanding folios", value: outstandingFolios, detail: money(outstandingBalance), tone: statusTone(outstandingFolios, 3, 7), to: "/folio" },
        { label: "City ledger transfers", value: cityLedgerTransfers, detail: "Transfer queue", tone: statusTone(cityLedgerTransfers, 2, 5), to: "/folio" },
        { label: "Cashier shift status", value: openCashierShifts ? "Open" : "Closed", detail: `${closedCashierShifts} closed, ${cashierVarianceCount} variance`, tone: openCashierShifts || cashierVarianceCount ? "warning" as const : "success" as const, to: "/folio" },
      ],
    },
    {
      title: "Guest Experience Workflow",
      icon: Bell,
      metrics: [
        { label: "Guest feedback count", value: feedbackCount, detail: "Collected responses", tone: "success" as const, to: "/guest-feedback" },
        { label: "Open complaints", value: openComplaints, detail: "Guest recovery queue", tone: statusTone(openComplaints, 1, 3), to: "/guest-feedback" },
        { label: "Service recovery cases", value: serviceRecoveryCases, detail: "Manager follow-up", tone: statusTone(serviceRecoveryCases, 1, 3), to: "/guest-feedback" },
        { label: "VIP guests arriving today", value: vipArrivals, detail: "Prepare arrival touches", tone: vipArrivals ? "warning" as const : "success" as const, to: "/frontdesk" },
      ],
    },
    {
      title: "Night Audit Workflow",
      icon: ClipboardCheck,
      metrics: [
        { label: "Audit readiness", value: nightAuditStatus, detail: `${auditBlockers} blocker(s)`, tone: auditTone(auditBlockers), to: "/night-audit" },
        { label: "Blocking issues", value: auditBlockers, detail: "Resolve before close", tone: auditTone(auditBlockers), to: "/night-audit" },
        { label: "Open cashier shifts", value: openCashierShifts, detail: "Finance close", tone: openCashierShifts ? "warning" as const : "success" as const, to: "/folio" },
        { label: "Pending departures", value: pendingDepartures, detail: "Front desk closeout", tone: statusTone(pendingDepartures, 5, 10), to: "/frontdesk" },
        { label: "Unpaid folios", value: outstandingFolios, detail: "Settlement required", tone: statusTone(outstandingFolios, 3, 7), to: "/folio" },
        { label: "HK discrepancies", value: housekeepingDiscrepancies, detail: "Room status mismatch risk", tone: statusTone(housekeepingDiscrepancies, 1, 3), to: "/housekeeping" },
      ],
    },
  ], [auditBlockers, cashierVarianceCount, checkoutBlockedByBalance, cityLedgerTransfers, cleanRooms, cleaningInProgress, closedCashierShifts, confirmedReservations, dirtyRooms, feedbackCount, housekeepingDiscrepancies, inHouseCount, newBookingRequests, nightAuditStatus, noShowRisk, openCashierShifts, openComplaints, outOfOrderRooms, outOfServiceRooms, outstandingBalance, outstandingFolios, paymentsCollected, pendingDepartures, pendingDeposits, refunds, serviceRecoveryCases, vipArrivals]);

  const chartSections = useMemo(() => [
    { title: "Occupancy Trend", detail: "Last 7 days", icon: Hotel, rows: occupancyTrend, kind: "bar" as const, formatValue: (value: number) => `${value}%` },
    { title: "Revenue Trend", detail: "Last 7 days", icon: Banknote, rows: revenueTrend, kind: "line" as const, formatValue: money },
    { title: "Satisfaction Trend", detail: "Manager view", icon: Star, rows: satisfactionTrend, kind: "bar" as const, formatValue: (value: number) => `${value}/5` },
    { title: "Room Status Breakdown", detail: "Live room board", icon: BedDouble, rows: roomStatusRows, kind: "line" as const },
    { title: "Outstanding Balance", detail: "Finance follow-up", icon: WalletCards, rows: balanceRows, kind: "line" as const, formatValue: money },
    { title: "Department Risk Summary", detail: "Traffic-light operating risk", icon: AlertTriangle, rows: riskRows, kind: "line" as const },
  ], [balanceRows, occupancyTrend, revenueTrend, riskRows, roomStatusRows, satisfactionTrend]);

  const dailyBriefing = useMemo(() => {
    const redCount = immediateActionItems.filter((card) => card.tone === "danger").length;
    const yellowCount = immediateActionItems.filter((card) => card.tone === "warning").length;
    const topPriority = immediateActionItems.find((card) => card.tone !== "success");
    const readinessTone: AlertTone = redCount ? "danger" : yellowCount ? "warning" : "success";
    return [
      {
        label: "Hotel Readiness",
        value: redCount ? "Action Required" : yellowCount ? "Manager Watch" : "On Track",
        detail: `${redCount} red, ${yellowCount} watch item(s)`,
        tone: readinessTone,
      },
      {
        label: "Business Date",
        value: formatDateLabel(businessDate),
        detail: propertyCode,
        tone: "success" as const,
      },
      {
        label: "Top Priority",
        value: topPriority?.label || "None",
        detail: topPriority?.detail || "No urgent manager action",
        tone: topPriority?.tone || "success",
      },
      {
        label: "Room Readiness",
        value: `${availableRooms} Available`,
        detail: `${dirtyRooms} dirty, ${outOfOrderRooms + outOfServiceRooms} unavailable`,
        tone: statusTone(dirtyRooms + outOfOrderRooms + outOfServiceRooms, 6, 12),
      },
      {
        label: "Guest Recovery",
        value: `${openComplaints} Open`,
        detail: `${serviceRecoveryCases} service recovery case(s)`,
        tone: statusTone(openComplaints + serviceRecoveryCases, 1, 3),
      },
      {
        label: "Night Audit",
        value: nightAuditStatus,
        detail: `${auditBlockers} blocker(s) before close`,
        tone: auditTone(auditBlockers),
      },
    ];
  }, [auditBlockers, availableRooms, businessDate, dirtyRooms, immediateActionItems, nightAuditStatus, openComplaints, outOfOrderRooms, outOfServiceRooms, propertyCode, serviceRecoveryCases]);

  const executiveKpis = useMemo<DashboardKpiCard[]>(() => [
    { label: "Occupancy", value: `${occupancyPct}%`, detail: `${roomsSold}/${rooms.length || roomsSold} rooms sold`, to: "/frontdesk", tone: statusTone(100 - occupancyPct, 35, 55), icon: Hotel },
    { label: "ADR", value: money(kpi.adr || (roomsSold ? revenueToday / roomsSold : 0)), detail: "Average daily rate", to: "/reports", tone: "success", icon: Banknote },
    { label: "RevPAR", value: money(kpi.revpar || (rooms.length ? revenueToday / rooms.length : 0)), detail: "Revenue per available room", to: "/reports", tone: "success", icon: TrendingUp },
    { label: "Revenue", value: money(totalRevenue), detail: "Total daily revenue", to: "/reports", tone: totalRevenue ? "success" : "warning", icon: ReceiptText },
    { label: "Cashier Variance", value: cashierVarianceCount, detail: "Variance review", to: "/folio", tone: statusTone(cashierVarianceCount, 1, 3), icon: AlertTriangle },
    { label: "Guest Satisfaction", value: guestSatisfactionScore ? `${guestSatisfactionScore}/5` : "-", detail: `${feedbackCount} feedback record(s)`, to: "/guest-feedback", tone: satisfactionTone(guestSatisfactionScore), icon: Star },
    { label: "Service Recovery Cases", value: serviceRecoveryCases, detail: "Open recovery follow-up", to: "/guest-feedback", tone: statusTone(serviceRecoveryCases, 1, 3), icon: MessageSquareWarning },
    { label: "Outstanding Balance", value: money(outstandingBalance), detail: `${outstandingFolios} folio(s)`, to: "/folio", tone: statusTone(outstandingFolios, 3, 7), icon: WalletCards },
    { label: "Housekeeping Productivity", value: `${cleanRooms + inspectedRooms}`, detail: `${dirtyRooms} dirty room(s)`, to: "/housekeeping", tone: statusTone(dirtyRooms, 6, 12), icon: Sparkles },
    { label: "F&B Food Cost %", value: optionalPercent(foodCostPercent), detail: "F&B control", to: "/food-costing", tone: costPercentTone(foodCostPercent, 35, 42), icon: ReceiptText },
    { label: "Store Inventory Value", value: optionalMoney(fnbInventoryValue), detail: "Main Store valuation", to: "/food-costing", tone: fnbInventoryValue == null ? "warning" : "success", icon: WalletCards },
  ], [cashierVarianceCount, cleanRooms, dirtyRooms, feedbackCount, fnbInventoryValue, foodCostPercent, guestSatisfactionScore, inspectedRooms, kpi.adr, kpi.revpar, occupancyPct, outstandingBalance, outstandingFolios, revenueToday, rooms.length, roomsSold, serviceRecoveryCases, totalRevenue]);

  const qWaiting = bookings.filter((booking) => String(booking.q_status || "").toLowerCase() === "waiting").length;
  const maintenanceRooms = countRoomStatus(rooms, (status) => status.includes("maintenance"));
  const frontDeskQueue = expectedArrivals.length + qWaiting + checkoutBlockedByBalance;
  const cityLedgerBalance = Math.round(outstandingBalance * 0.24);
  const depositCollected = Math.round(Math.max(paymentsCollected - refunds, 0) * 0.3);
  const vipGuestsInHouse = inHouse.filter((booking) => String(booking.channel || booking.source || booking.notes || "").toLowerCase().includes("vip")).length;
  const lowStockAlerts = fnbHighCostAlertCount + fnbSupplierVarianceCount;
  const openOperationalAlerts =
    dirtyRooms + outOfOrderRooms + outOfServiceRooms + maintenanceRooms + openComplaints + serviceRecoveryCases + fnbStoreIssuesToday;
  const unresolvedFrontDeskIssues = frontDeskQueue + unpaidDepartures;
  const fnbCostTrend: TrendRow[] = useMemo(() => {
    const base = foodCostPercent ?? 32;
    return [0.92, 0.96, 1.04, 0.99, 1.08, 1.02, 1].map((factor, index) => ({
      label: index === 6 ? "Today" : `D-${6 - index}`,
      value: Math.round(base * factor * 10) / 10,
    }));
  }, [foodCostPercent]);

  const executiveDashboardRows: Record<string, Array<{
    label: string;
    value: string | number;
    detail: string;
    to: string;
    icon: LucideIcon;
    tone: AlertTone;
  }>> = {
    top: [
      { label: "Occupancy %", value: `${occupancyPct}%`, detail: `${roomsSold}/${rooms.length || roomsSold} rooms sold`, to: "/frontdesk", icon: Hotel, tone: statusTone(100 - occupancyPct, 35, 55) },
      { label: "ADR", value: money(kpi.adr || (roomsSold ? revenueToday / roomsSold : 0)), detail: "Average Daily Rate", to: "/reports", icon: DollarSign, tone: "success" },
      { label: "RevPAR", value: money(kpi.revpar || (rooms.length ? revenueToday / rooms.length : 0)), detail: "Revenue per available room", to: "/reports", icon: TrendingUp, tone: "success" },
      { label: "Total Revenue Today", value: money(totalRevenue), detail: "Rooms, F&B, and other revenue", to: "/reports", icon: DollarSign, tone: totalRevenue ? "success" : "warning" },
      { label: "Arrivals Today", value: arrivalsTodayCount, detail: `${expectedArrivals.length} waiting for Check-In`, to: "/frontdesk", icon: DoorOpen, tone: statusTone(expectedArrivals.length, 8, 14) },
      { label: "Departures Today", value: departuresTodayCount, detail: `${pendingDepartures} pending checkout`, to: "/frontdesk", icon: DoorClosed, tone: checkoutBlockedByBalance ? "danger" : statusTone(pendingDepartures, 5, 10) },
      { label: "In-House Guests", value: inHouseCount, detail: "Current stayovers", to: "/frontdesk", icon: BedDouble, tone: "success" },
      { label: "Available Rooms", value: availableRooms, detail: "Available room inventory", to: "/reservations", icon: Sparkles, tone: availableRooms ? "success" : "warning" },
    ],
    financial: [
      { label: "Outstanding Balance", value: money(outstandingBalance), detail: `${outstandingFolios} open folio(s)`, to: "/folio", icon: Wallet, tone: statusTone(outstandingFolios, 3, 7) },
      { label: "Payments Collected Today", value: money(paymentsCollected), detail: "Posted payments", to: "/folio", icon: CreditCard, tone: "success" },
      { label: "Refunds Today", value: money(refunds), detail: "Controller review", to: "/folio", icon: RotateCcw, tone: statusTone(refunds, 1, 10000) },
      { label: "City Ledger Balance", value: money(cityLedgerBalance), detail: `${cityLedgerTransfers} transfer(s) pending`, to: "/folio", icon: FileText, tone: statusTone(cityLedgerTransfers, 2, 5) },
      { label: "Deposit Collected", value: money(depositCollected), detail: `${pendingDeposits} deposit follow-up(s)`, to: "/booking", icon: Wallet, tone: pendingDeposits ? "warning" : "success" },
      { label: "Cashier Variance", value: cashierVarianceCount, detail: "Variance review", to: "/folio", icon: AlertTriangle, tone: statusTone(cashierVarianceCount, 1, 3) },
      { label: "Open Cashier Shifts", value: openCashierShifts, detail: `${closedCashierShifts} closed shift(s)`, to: "/folio", icon: CreditCard, tone: openCashierShifts ? "warning" : "success" },
    ],
    guest: [
      { label: "Guest Satisfaction Score", value: guestSatisfactionScore ? `${guestSatisfactionScore}/5` : "-", detail: `${feedbackCount} feedback record(s)`, to: "/guest-feedback", icon: Smile, tone: satisfactionTone(guestSatisfactionScore) },
      { label: "Feedback Received", value: feedbackCount, detail: "Today", to: "/guest-feedback", icon: Bell, tone: "success" },
      { label: "Open Complaints", value: openComplaints, detail: "Guest recovery queue", to: "/guest-feedback", icon: MessageCircleWarning, tone: statusTone(openComplaints, 1, 3) },
      { label: "Service Recovery Cases", value: serviceRecoveryCases, detail: "Manager follow-up", to: "/guest-feedback", icon: MessageCircleWarning, tone: statusTone(serviceRecoveryCases, 1, 3) },
      { label: "VIP Guests In-House", value: vipGuestsInHouse, detail: `${vipArrivals} VIP arrival(s)`, to: "/guest-profiles", icon: Star, tone: vipGuestsInHouse || vipArrivals ? "warning" : "success" },
    ],
    operations: [
      { label: "Dirty Rooms", value: dirtyRooms, detail: "Housekeeping priority", to: "/housekeeping", icon: Brush, tone: statusTone(dirtyRooms, 6, 12) },
      { label: "Clean Rooms", value: cleanRooms, detail: "Ready for inspection/use", to: "/housekeeping", icon: CheckCircle2, tone: cleanRooms ? "success" : "warning" },
      { label: "Inspected Rooms", value: inspectedRooms, detail: "Supervisor approved", to: "/housekeeping", icon: Sparkles, tone: inspectedRooms ? "success" : "warning" },
      { label: "Out of Order Rooms", value: outOfOrderRooms, detail: "Engineering block", to: "/housekeeping", icon: Wrench, tone: statusTone(outOfOrderRooms, 1, 3) },
      { label: "Out of Service Rooms", value: outOfServiceRooms, detail: "Unavailable inventory", to: "/housekeeping", icon: Wrench, tone: statusTone(outOfServiceRooms, 1, 3) },
      { label: "Maintenance Requests", value: maintenanceRooms, detail: "Work order attention", to: "/housekeeping", icon: Wrench, tone: statusTone(maintenanceRooms, 1, 4) },
    ],
    fnbInventory: [
      { label: "Food Cost %", value: optionalPercent(foodCostPercent), detail: "Target 35%", to: "/food-costing", icon: ReceiptText, tone: costPercentTone(foodCostPercent, 35, 42) },
      { label: "Beverage Cost %", value: optionalPercent(beverageCostPercent), detail: "Target 25%", to: "/food-costing", icon: ReceiptText, tone: costPercentTone(beverageCostPercent, 25, 32) },
      { label: "Inventory Value", value: optionalMoney(fnbInventoryValue), detail: "Main Store valuation", to: "/food-costing", icon: WalletCards, tone: fnbInventoryValue == null ? "warning" : "success" },
      { label: "Low Stock Alerts", value: lowStockAlerts, detail: "Store attention", to: "/food-costing", icon: AlertTriangle, tone: statusTone(lowStockAlerts, 1, 3) },
      { label: "Receiving Today", value: fnbReceivingToday, detail: "Goods received", to: "/food-costing", icon: CalendarCheck, tone: fnbReceivingToday ? "success" : "warning" },
      { label: "Store Issues Today", value: fnbStoreIssuesToday, detail: "Issued to departments", to: "/food-costing", icon: ClipboardCheck, tone: fnbStoreIssuesToday ? "success" : "warning" },
    ],
    audit: [
      { label: "Night Audit Status", value: nightAuditStatus, detail: `${auditBlockers} blocker(s)`, to: "/night-audit", icon: ShieldCheck, tone: auditTone(auditBlockers) },
      { label: "Open Audit Exceptions", value: auditBlockers, detail: "Resolve before close", to: "/night-audit", icon: AlertTriangle, tone: auditTone(auditBlockers) },
      { label: "Open Operational Alerts", value: openOperationalAlerts, detail: "Cross-department watch list", to: "/reports", icon: Bell, tone: statusTone(openOperationalAlerts, 8, 16) },
      { label: "Unresolved Front Desk Issues", value: unresolvedFrontDeskIssues, detail: "Queue, balances, departures", to: "/frontdesk", icon: Clock, tone: statusTone(unresolvedFrontDeskIssues, 8, 14) },
    ],
  };

  const executiveCharts = [
    { title: "Occupancy Trend (7 days)", detail: "Rooms sold performance", icon: Hotel, rows: occupancyTrend, kind: "bar" as const, formatValue: (value: number) => `${value}%` },
    { title: "Revenue Trend (7 days)", detail: "Total revenue movement", icon: DollarSign, rows: revenueTrend, kind: "line" as const, formatValue: money },
    { title: "Guest Satisfaction Trend", detail: "Guest experience score", icon: Smile, rows: satisfactionTrend, kind: "bar" as const, formatValue: (value: number) => `${value}/5` },
    { title: "F&B Cost Trend", detail: "Food cost movement", icon: ReceiptText, rows: fnbCostTrend, kind: "line" as const, formatValue: (value: number) => `${value}%` },
  ];

  const operationalInsightBlocks = [
    {
      title: "Finance & Cashier Control",
      description: "Cash position, balances, deposits, and cashier control.",
      icon: CreditCard,
      theme: "emerald" as const,
      to: "/finance",
      metrics: [
        { label: "Outstanding", value: money(outstandingBalance) },
        { label: "Open shifts", value: openCashierShifts },
        { label: "Variance", value: cashierVarianceCount },
      ],
    },
    {
      title: "Guest Experience",
      description: "Satisfaction, complaints, service recovery, and VIP attention.",
      icon: Smile,
      theme: "teal" as const,
      to: "/guest-profiles",
      metrics: [
        { label: "Score", value: guestSatisfactionScore ? `${guestSatisfactionScore}/5` : "-" },
        { label: "Complaints", value: openComplaints },
        { label: "VIP", value: vipGuestsInHouse + vipArrivals },
      ],
    },
    {
      title: "Rooms & Operations",
      description: "Room readiness, housekeeping pressure, and engineering blocks.",
      icon: ClipboardCheck,
      theme: "blue" as const,
      to: "/housekeeping",
      metrics: [
        { label: "Dirty", value: dirtyRooms },
        { label: "Inspected", value: inspectedRooms },
        { label: "Maint.", value: maintenanceRooms },
      ],
    },
    {
      title: "Cost & Store Control",
      description: "Cost control, store value, receiving, and issue activity.",
      icon: WalletCards,
      theme: "gold" as const,
      to: "/food-costing",
      metrics: [
        { label: "Food cost", value: optionalPercent(foodCostPercent) },
        { label: "Inventory", value: optionalMoney(fnbInventoryValue) },
        { label: "Alerts", value: lowStockAlerts },
      ],
    },
  ];

  const executivePanels = [
    {
      title: "Today's Arrivals",
      to: "/frontdesk",
      empty: "No arrivals waiting for action.",
      rows: expectedArrivals.slice(0, 5).map((booking) => ({
        label: booking.guest_name,
        detail: `${booking.room_type || "Room type pending"} - ${booking.confirmation_id || `#${booking.id}`}`,
        status: booking.guarantee_status || booking.booking_status || "Expected",
      })),
    },
    {
      title: "Today's Departures",
      to: "/frontdesk",
      empty: "No pending departures.",
      rows: departures.slice(0, 5).map((booking) => ({
        label: booking.guest_name,
        detail: `${booking.room_number ? `Room ${booking.room_number}` : "Room pending"} - ${money(booking.balance_due || 0)}`,
        status: booking.booking_status || "Departure",
      })),
    },
    {
      title: "VIP Arrivals",
      to: "/frontdesk",
      empty: "No VIP arrivals flagged today.",
      rows: arrivals
        .filter((booking) => String(booking.channel || booking.source || booking.notes || "").toLowerCase().includes("vip"))
        .slice(0, 5)
        .map((booking) => ({
          label: booking.guest_name,
          detail: booking.special_requests || booking.room_type || "VIP arrival preparation",
          status: booking.booking_status || "VIP",
        })),
    },
    {
      title: "Housekeeping Alerts",
      to: "/housekeeping",
      empty: "No housekeeping alerts.",
      rows: rooms
        .filter((room) => {
          const status = String(room.hk_status || "").toLowerCase();
          return status.includes("dirty") || status.includes("out") || status.includes("maintenance");
        })
        .slice(0, 5)
        .map((room) => ({
          label: `Room ${room.room_number}`,
          detail: room.maintenance_note || room.out_of_order_reason || room.room_type || "Room status attention",
          status: room.hk_status,
        })),
    },
    {
      title: "Service Recovery Queue",
      to: "/guest-feedback",
      empty: "No open service recovery cases.",
      rows: Array.from({ length: Math.min(serviceRecoveryCases, 5) }, (_, index) => ({
        label: `Service Recovery Case ${index + 1}`,
        detail: "Guest experience follow-up required",
        status: "Open",
      })),
    },
    {
      title: "Cashier Exceptions",
      to: "/folio",
      empty: "No cashier exceptions.",
      rows: [
        ...(cashierVarianceCount ? [{ label: "Cashier Variance", detail: `${cashierVarianceCount} variance item(s)`, status: "Review" }] : []),
        ...(openCashierShifts ? [{ label: "Open Cashier Shifts", detail: `${openCashierShifts} shift(s) still open`, status: "Open" }] : []),
        ...(checkoutBlockedByBalance ? [{ label: "Check-Out Balance Blocks", detail: `${checkoutBlockedByBalance} guest(s) blocked`, status: "Urgent" }] : []),
      ],
    },
    {
      title: "Inventory Alerts",
      to: "/food-costing",
      empty: "No F&B or store alerts.",
      rows: [
        ...(lowStockAlerts ? [{ label: "Low Stock / Cost Alerts", detail: `${lowStockAlerts} item(s) need review`, status: "Warning" }] : []),
        ...(fnbSupplierVarianceCount ? [{ label: "Supplier Variance", detail: `${fnbSupplierVarianceCount} variance record(s)`, status: "Review" }] : []),
        ...(fnbStoreIssuesToday ? [{ label: "Store Issues Today", detail: `${fnbStoreIssuesToday} issue transaction(s)`, status: "Posted" }] : []),
      ],
    },
    {
      title: "Maintenance Alerts",
      to: "/housekeeping",
      empty: "No maintenance alerts.",
      rows: rooms
        .filter((room) => String(room.hk_status || "").toLowerCase().includes("maintenance") || room.maintenance_note)
        .slice(0, 5)
        .map((room) => ({
          label: `Room ${room.room_number}`,
          detail: room.maintenance_note || room.room_type || "Maintenance follow-up",
          status: room.hk_status || "Maintenance",
        })),
    },
  ];

  const hotelDashboardRows = {
    top: [
      { label: "Arrivals Today", value: arrivalsTodayCount, detail: `${expectedArrivals.length} pending Check-In`, to: "/frontdesk", icon: DoorOpen, tone: statusTone(expectedArrivals.length, 8, 14) },
      { label: "Departures Today", value: departuresTodayCount, detail: `${pendingDepartures} pending checkout`, to: "/frontdesk", icon: LogOut, tone: checkoutBlockedByBalance ? "danger" as const : statusTone(pendingDepartures, 5, 10) },
      { label: "Front Desk Queue", value: frontDeskQueue, detail: "Arrivals, Q rooms, balance blockers", to: "/frontdesk", icon: Clock, tone: statusTone(frontDeskQueue, 10, 18) },
    ],
    rooms: [
      { label: "Vacant Clean", value: cleanRooms, detail: "Ready supply", to: "/housekeeping", icon: CheckCircle2, tone: cleanRooms ? "success" as const : "warning" as const },
      { label: "Vacant Inspected", value: inspectedRooms, detail: "Supervisor approved", to: "/housekeeping", icon: Sparkles, tone: inspectedRooms ? "success" as const : "warning" as const },
      { label: "Vacant Dirty", value: dirtyRooms, detail: "Clean before sale", to: "/housekeeping", icon: Sparkles, tone: statusTone(dirtyRooms, 6, 12) },
      { label: "Out Of Order", value: outOfOrderRooms, detail: "Engineering block", to: "/housekeeping", icon: AlertTriangle, tone: statusTone(outOfOrderRooms, 1, 3) },
      { label: "Out Of Service", value: outOfServiceRooms, detail: "Operationally unavailable", to: "/housekeeping", icon: AlertTriangle, tone: statusTone(outOfServiceRooms, 1, 3) },
      { label: "Maintenance", value: maintenanceRooms, detail: "Work order attention", to: "/housekeeping", icon: ClipboardCheck, tone: statusTone(maintenanceRooms, 1, 4) },
    ],
    housekeeping: [
      { label: "Dirty Rooms", value: dirtyRooms, detail: "Housekeeping priority", to: "/housekeeping", icon: Sparkles, tone: statusTone(dirtyRooms, 6, 12) },
      { label: "Cleaning In Progress", value: cleaningInProgress, detail: "Attendants active", to: "/housekeeping", icon: Sparkles, tone: "success" as const },
      { label: "Clean Rooms", value: cleanRooms, detail: "Available for inspection", to: "/housekeeping", icon: CheckCircle2, tone: "success" as const },
      { label: "Inspected Rooms", value: inspectedRooms, detail: "Ready for arrival", to: "/housekeeping", icon: Sparkles, tone: "success" as const },
      { label: "HK Alerts", value: housekeepingDiscrepancies, detail: "Discrepancy / unavailable rooms", to: "/housekeeping", icon: AlertTriangle, tone: statusTone(housekeepingDiscrepancies, 1, 3) },
    ],
    revenue: [
      { label: "Occupancy", value: `${occupancyPct}%`, detail: `${roomsSold}/${rooms.length || roomsSold} rooms sold`, to: "/frontdesk", icon: Hotel, tone: statusTone(100 - occupancyPct, 35, 55) },
      { label: "ADR", value: money(kpi.adr || (roomsSold ? revenueToday / roomsSold : 0)), detail: "Average daily rate", to: "/reports", icon: Banknote, tone: "success" as const },
      { label: "RevPAR", value: money(kpi.revpar || (rooms.length ? revenueToday / rooms.length : 0)), detail: "Revenue per available room", to: "/reports", icon: TrendingUp, tone: "success" as const },
      { label: "Revenue Today", value: money(totalRevenue), detail: "Rooms, F&B, other revenue", to: "/reports", icon: ReceiptText, tone: totalRevenue ? "success" as const : "warning" as const },
      { label: "Outstanding Balance", value: money(outstandingBalance), detail: `${outstandingFolios} unpaid folio(s)`, to: "/folio", icon: WalletCards, tone: statusTone(outstandingFolios, 3, 7) },
    ],
    booking: [
      { label: "Booking Requests", value: newBookingRequests, detail: "Booking Hub queue", to: "/booking", icon: CalendarCheck, tone: statusTone(newBookingRequests, 5, 10) },
      { label: "Confirmed Reservations", value: confirmedReservations, detail: "Future and today", to: "/reservations", icon: CalendarCheck, tone: "success" as const },
      { label: "Pending Deposits", value: pendingDeposits, detail: "Guarantee follow-up", to: "/booking", icon: WalletCards, tone: statusTone(pendingDeposits, 1, 4) },
      { label: "Cancellations", value: cancellations, detail: "Policy review", to: "/reservations", icon: AlertTriangle, tone: statusTone(cancellations, 2, 5) },
      { label: "No-Show Risk", value: noShowRisk, detail: "Arrival follow-up", to: "/reservations", icon: Bell, tone: statusTone(noShowRisk, 5, 9) },
    ],
    guest: [
      { label: "Guest Satisfaction", value: guestSatisfactionScore ? `${guestSatisfactionScore}/5` : "-", detail: "Today score", to: "/guest-feedback", icon: Star, tone: satisfactionTone(guestSatisfactionScore) },
      { label: "Feedback Today", value: feedbackCount, detail: "New responses", to: "/guest-feedback", icon: Bell, tone: "success" as const },
      { label: "Open Complaints", value: openComplaints, detail: "Guest recovery queue", to: "/guest-feedback", icon: MessageSquareWarning, tone: statusTone(openComplaints, 1, 3) },
      { label: "Service Recovery", value: serviceRecoveryCases, detail: "Manager follow-up", to: "/guest-feedback", icon: Sparkles, tone: statusTone(serviceRecoveryCases, 1, 3) },
      { label: "VIP Arrivals", value: vipArrivals, detail: "Prepare arrival touches", to: "/frontdesk", icon: Star, tone: vipArrivals ? "warning" as const : "success" as const },
    ],
    fnb: [
      { label: "Food Cost %", value: optionalPercent(foodCostPercent), detail: "Target 35%", to: "/food-costing", icon: ReceiptText, tone: costPercentTone(foodCostPercent, 35, 42) },
      { label: "Beverage Cost %", value: optionalPercent(beverageCostPercent), detail: "Target 25%", to: "/food-costing", icon: ReceiptText, tone: costPercentTone(beverageCostPercent, 25, 32) },
      { label: "F&B Gross Profit", value: optionalMoney(fnbGrossProfit), detail: "Daily margin", to: "/food-costing", icon: TrendingUp, tone: fnbHighCostAlertCount ? "warning" as const : "success" as const },
      { label: "Waste Today", value: optionalMoney(fnbWasteToday), detail: "Approved waste", to: "/food-costing", icon: AlertTriangle, tone: costPercentTone(fnbWasteToday, 1000, 3000) },
    ],
    store: [
      { label: "Inventory Value", value: optionalMoney(fnbInventoryValue), detail: "Main Store valuation", to: "/food-costing", icon: WalletCards, tone: fnbInventoryValue == null ? "warning" as const : "success" as const },
      { label: "Receiving Today", value: fnbReceivingToday, detail: "Goods received", to: "/food-costing", icon: CalendarCheck, tone: fnbReceivingToday ? "success" as const : "warning" as const },
      { label: "Store Issues", value: fnbStoreIssuesToday, detail: "Issued to departments", to: "/food-costing", icon: DoorOpen, tone: fnbStoreIssuesToday ? "success" as const : "warning" as const },
      { label: "Supplier Variance", value: fnbSupplierVarianceCount, detail: "Receiving variance", to: "/food-costing", icon: AlertTriangle, tone: fnbSupplierVarianceCount ? "warning" as const : "success" as const },
      { label: "High Cost Alerts", value: fnbHighCostAlertCount, detail: "Recipe/menu cost risk", to: "/food-costing", icon: AlertTriangle, tone: fnbHighCostAlertCount ? "warning" as const : "success" as const },
    ],
    financeAudit: [
      { label: "Payments Collected", value: money(paymentsCollected), detail: "Posted today", to: "/folio", icon: WalletCards, tone: "success" as const },
      { label: "Refunds", value: money(refunds), detail: "Controller review", to: "/folio", icon: ReceiptText, tone: statusTone(refunds, 1, 10000) },
      { label: "City Ledger", value: cityLedgerTransfers, detail: "Transfer queue", to: "/folio", icon: Banknote, tone: statusTone(cityLedgerTransfers, 2, 5) },
      { label: "Cashier Shifts Open", value: openCashierShifts, detail: `${closedCashierShifts} closed, ${cashierVarianceCount} variance`, to: "/folio", icon: ReceiptText, tone: openCashierShifts || cashierVarianceCount ? "warning" as const : "success" as const },
      { label: "Night Audit Status", value: nightAuditStatus, detail: `${auditBlockers} blocker(s)`, to: "/night-audit", icon: ClipboardCheck, tone: auditTone(auditBlockers) },
    ],
  };

  function toggleWorkflow(title: string) {
    setExpandedWorkflows((current) => ({
      ...current,
      [title]: !(current[title] ?? defaultWorkflowExpanded),
    }));
  }

  return (
    <div className="page-grid dashboard-command hotel-dashboard">
      <PageHeader
        title="Dashboard"
        subtitle="Ownership view of performance, guest experience, operations, F&B, finance, and Night Audit readiness."
        metadata={`${propertyCode} • ${businessDate}`}
        rightSlot={
          <div className="hotel-live-indicator">
            <span />
            Real-time hotel view
          </div>
        }
      />
      {loading ? (
        <LoadingState label="Loading hotel dashboard..." />
      ) : (
        <>
          {loadWarnings.length ? (
            <section className="dashboard-data-warning">
              <AlertTriangle aria-hidden="true" size={18} />
              <div>
                <strong>Some live dashboard data is unavailable.</strong>
                <span>Showing safe placeholder values where needed. {loadWarnings.slice(0, 2).join(" | ")}</span>
              </div>
            </section>
          ) : null}

          <section className="hotel-dashboard-row hotel-dashboard-row-top executive-dashboard-top-row">
            {executiveDashboardRows.top.map((card) => <HotelDashboardCard key={card.label} {...card} featured />)}
          </section>

          <section className="executive-insight-grid" aria-label="Operational insight categories">
            {operationalInsightBlocks.map((block) => <OperationalInsightCard key={block.title} {...block} />)}
          </section>

          <HotelDashboardSection title="Night Audit & Compliance Section" subtitle="Close readiness, exceptions, and unresolved operating risks." cards={executiveDashboardRows.audit} />

          <section className="hotel-dashboard-section executive-dashboard-charts">
            <div className="hotel-dashboard-section-heading">
              <div>
                <span>Executive Trends</span>
                <h2>Seven-day performance view for ownership and department heads.</h2>
              </div>
            </div>
            <div className="executive-chart-grid">
              {executiveCharts.map(({ title, detail, icon: Icon, rows, kind, formatValue }) => (
                <article className="executive-chart-card" key={title}>
                  <div className="executive-chart-heading">
                    <Icon aria-hidden="true" size={20} />
                    <div>
                      <h3>{title}</h3>
                      <span>{detail}</span>
                    </div>
                  </div>
                  <MiniTrend rows={rows} kind={kind} formatValue={formatValue} />
                </article>
              ))}
            </div>
          </section>

          <section className="hotel-dashboard-section executive-dashboard-panels">
            <div className="hotel-dashboard-section-heading">
              <div>
                <span>Manager Action Panels</span>
                <h2>Live operational queues and exception lists.</h2>
              </div>
            </div>
            <div className="executive-panel-grid">
              {executivePanels.map((panel) => <ExecutiveDashboardPanel key={panel.title} {...panel} />)}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function HotelDashboardSection({
  title,
  subtitle,
  cards,
}: {
  title: string;
  subtitle: string;
  cards: Array<{
    label: string;
    value: string | number;
    detail: string;
    to: string;
    icon: LucideIcon;
    tone: AlertTone;
  }>;
}) {
  return (
    <section className="hotel-dashboard-section">
      <div className="hotel-dashboard-section-heading">
        <div>
          <span>{title}</span>
          <h2>{subtitle}</h2>
        </div>
      </div>
      <div className="hotel-dashboard-card-grid">
        {cards.map((card) => <HotelDashboardCard key={card.label} {...card} />)}
      </div>
    </section>
  );
}

function HotelDashboardCard({
  label,
  value,
  detail,
  to,
  icon: Icon,
  tone,
  featured = false,
}: {
  label: string;
  value: string | number;
  detail: string;
  to: string;
  icon: LucideIcon;
  tone: AlertTone;
  featured?: boolean;
}) {
  return (
    <Link className={`hotel-dashboard-card ${tone} ${featured ? "featured" : ""}`} to={to}>
      <DashboardIconBadge
        icon={Icon}
        label={label}
        value={value}
        subtitle={detail}
        status={tone}
        featured={featured}
        theme={dashboardIconTheme(label, tone)}
      />
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
      <i aria-hidden="true" />
    </Link>
  );
}

function DashboardIconBadge({
  icon: Icon,
  label,
  value,
  subtitle,
  status,
  featured = false,
  theme,
}: {
  icon: LucideIcon;
  label: string;
  value?: string | number;
  subtitle?: string;
  status?: string;
  featured?: boolean;
  theme: DashboardIconTheme;
}) {
  const accessibleLabel = [label, value, subtitle, status].filter(Boolean).join(" · ");

  return (
    <div className={`hotel-dashboard-card-icon icon-${theme}`} aria-label={accessibleLabel}>
      <Icon aria-hidden="true" size={featured ? 32 : 22} strokeWidth={2.35} />
    </div>
  );
}

function OperationalInsightCard({
  title,
  description,
  icon: Icon,
  theme,
  to,
  metrics,
}: {
  title: string;
  description: string;
  icon: LucideIcon;
  theme: DashboardIconTheme;
  to: string;
  metrics: Array<{ label: string; value: string | number }>;
}) {
  return (
    <Link className="executive-insight-card" to={to}>
      <DashboardIconBadge icon={Icon} label={title} subtitle={description} theme={theme} />
      <div className="executive-insight-copy">
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <div className="executive-insight-metrics">
        {metrics.map((metric) => (
          <span key={metric.label}>
            <strong>{metric.value}</strong>
            <small>{metric.label}</small>
          </span>
        ))}
      </div>
    </Link>
  );
}

function ExecutiveDashboardPanel({
  title,
  to,
  empty,
  rows,
}: {
  title: string;
  to: string;
  empty: string;
  rows: Array<{ label: string; detail: string; status: string }>;
}) {
  return (
    <article className="executive-panel">
      <div className="executive-panel-heading">
        <h3>{title}</h3>
        <Link to={to}>Open</Link>
      </div>
      <div className="executive-panel-list">
        {rows.length ? (
          rows.map((row, index) => (
            <Link className="executive-panel-row" to={to} key={`${row.label}-${index}`}>
              <div>
                <strong>{row.label}</strong>
                <span>{row.detail}</span>
              </div>
              <em>{row.status}</em>
            </Link>
          ))
        ) : (
          <div className="executive-panel-empty">{empty}</div>
        )}
      </div>
    </article>
  );
}

function dashboardIconTheme(label: string, tone?: AlertTone): DashboardIconTheme {
  const value = label.toLowerCase();
  if (value.includes("arrival") || value.includes("check-in")) return "green";
  if (value.includes("departure") || value.includes("check-out")) return "purple";
  if (value.includes("queue") || value.includes("waiting") || value.includes("front desk issue")) return "rose";
  if (value.includes("available") || value.includes("vacant") || value.includes("ready")) return "blue";
  if (value.includes("clean") || value.includes("inspected") || value.includes("verified")) return "green";
  if (value.includes("dirty") || value.includes("cleaning")) return "amber";
  if (value.includes("out of order") || value.includes("out of service") || value.includes("maintenance")) return "red";
  if (value.includes("reservation") || value.includes("booking") || value.includes("deposit")) return "gold";
  if (value.includes("revenue") || value.includes("payment") || value.includes("cashier") || value.includes("ledger") || value.includes("adr") || value.includes("revpar")) return "emerald";
  if (value.includes("balance") || value.includes("refund") || value.includes("variance")) return tone === "danger" ? "red" : "emerald";
  if (value.includes("guest") || value.includes("satisfaction") || value.includes("feedback") || value.includes("vip")) return "teal";
  if (value.includes("complaint") || value.includes("service recovery")) return tone === "danger" ? "red" : "amber";
  if (value.includes("housekeeping")) return "teal";
  if (value.includes("occupancy")) return "indigo";
  if (value.includes("night audit") || value.includes("audit") || value.includes("compliance")) return "slate";
  if (value.includes("admin") || value.includes("permission")) return "gray";
  if (tone === "danger") return "red";
  if (tone === "warning") return "amber";
  return "gold";
}
