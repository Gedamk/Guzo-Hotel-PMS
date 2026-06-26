import {
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type FormEvent,
  type ReactNode,
  type SetStateAction,
} from "react";
import {
  AlertTriangle,
  BedDouble,
  CalendarCheck,
  ClipboardList,
  DoorOpen,
  KeyRound,
  ReceiptText,
  Sparkles,
  UserCheck,
  Users,
} from "lucide-react";
import PageHeader from "../../components/PageHeader";
import DataTable from "../../components/DataTable";
import { usePmsContext } from "../../context/PmsContext";
import {
  fetchFrontdeskBookings,
  fetchRoomStatusBoard,
} from "../../services/pmsService";
import { getErrorMessage } from "../../services/http";
import {
  assignRoom,
  addLateCheckoutNote,
  checkInGuest,
  checkOutGuest,
  createWalkInBooking,
  extendStay,
  markEarlyDeparture,
  moveGuestRoom,
} from "../../services/frontdeskActions";
import {
  fetchFolioReceipt,
  postQuoteChargesToFolio,
  validateCheckout,
  type FolioReceipt,
} from "../../services/financeService";
import type { FrontdeskBooking, RoomStatusItem } from "../../types/pms";
import { permissionMessage, roleCan } from "../../auth/permissions";

type FrontDeskTab =
  | "shift"
  | "houseStatus"
  | "arrivals"
  | "qReservations"
  | "departures"
  | "inHouse"
  | "walkIn"
  | "assignment"
  | "roomPlan"
  | "floorPlan"
  | "registration"
  | "reports"
  | "exceptions";

type FrontDeskOperation =
  | "shift"
  | "arrivals"
  | "expectedCheckIns"
  | "checkedIn"
  | "departures"
  | "checkedOut"
  | "inHouse"
  | "noShows"
  | "walkIns"
  | "assignment"
  | "exceptions";

type WalkInFormState = {
  guestName: string;
  adults: string;
  children: string;
  isVip: boolean;
  documentType: string;
  documentNumber: string;
  email: string;
  phone: string;
  purposeOfVisit: string;
  roomNumber: string;
  roomType: string;
  checkInDate: string;
  checkOutDate: string;
  currency: string;
  ratePerNightEtb: string;
  totalAmountEtb: string;
  discountAmount: string;
  extraBedCharge: string;
  taxPercent: string;
  customTaxPercent: string;
  serviceChargePercent: string;
  customServiceChargePercent: string;
  vatPercent: string;
  customVatPercent: string;
  downpaymentAmount: string;
  paymentMethod: string;
  amountPaidNowEtb: string;
  notes: string;
};

type ArrivalFilterState = {
  arrivalDate: string;
  search: string;
  roomType: string;
  roomNumber: string;
  vip: string;
  groupBlock: string;
  assignment: string;
  status: string;
  payment: string;
  readiness: string;
};

type RoomCandidateFilterState = {
  search: string;
  roomType: string;
  floor: string;
  housekeeping: string;
};

type QReservationState = {
  startedAt: string;
  priority: "normal" | "vip" | "urgent";
  notes: string;
};

type ManualAuthorizationState = {
  amount: number;
  code: string;
  authorizedBy: string;
  authorizedAt: string;
  type: "card" | "cash" | "offline";
  notes: string;
};

const tabLabels: Record<FrontDeskTab, string> = {
  shift: "Shift Start",
  houseStatus: "House Status",
  arrivals: "Arrivals",
  qReservations: "Q Reservations",
  departures: "Departures",
  inHouse: "In House",
  walkIn: "Walk-In",
  assignment: "Room Assignment",
  roomPlan: "Room Plan",
  floorPlan: "Floor Plan",
  registration: "Registration Cards",
  reports: "Reports",
  exceptions: "Exceptions",
};

const operationLabels: Record<FrontDeskOperation, string> = {
  shift: "Shift Start",
  arrivals: "Arrivals Prep",
  expectedCheckIns: "Expected Check-ins",
  checkedIn: "Checked In",
  departures: "Departures",
  checkedOut: "Checked Out",
  inHouse: "In House",
  noShows: "No-Shows",
  walkIns: "Walk-Ins",
  assignment: "Room Assignment",
  exceptions: "Exceptions",
};

const purposeOptions = [
  "Vacation",
  "Meeting",
  "Wedding",
  "Business",
  "Education",
  "Conference",
  "Medical",
  "Family Visit",
  "Relocation",
  "Other",
];

const hotelRoomTypes = [
  "Single Room",
  "Double Room",
  "Twin Room",
  "Queen Room",
  "King Room",
  "Standard Room",
  "Deluxe Room",
  "Superior Room",
  "Executive Room",
  "Family Room",
  "Connecting Rooms",
  "Accessible Room",
  "Suite",
  "Junior Suite",
  "Executive Suite",
  "Presidential Suite",
  "Villa / Bungalow",
  "Dormitory / Shared Room",
];

const chargePercentOptions = ["0", "5", "7", "8", "10", "12", "15", "18", "custom"];

function defaultWalkInForm(businessDate: string): WalkInFormState {
  return {
    guestName: "",
    adults: "1",
    children: "0",
    isVip: false,
    documentType: "Passport",
    documentNumber: "",
    email: "",
    phone: "",
    purposeOfVisit: "Vacation",
    roomNumber: "",
    roomType: "Standard Room",
    checkInDate: businessDate,
    checkOutDate: businessDate,
    currency: "ETB",
    ratePerNightEtb: "",
    totalAmountEtb: "",
    discountAmount: "",
    extraBedCharge: "",
    taxPercent: "0",
    customTaxPercent: "",
    serviceChargePercent: "10",
    customServiceChargePercent: "",
    vatPercent: "15",
    customVatPercent: "",
    downpaymentAmount: "",
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

function statusClass(status: string) {
  const s = String(status || "").toLowerCase();
  if (s === "in_house" || s === "checked_in") return "pill pill-success";
  if (s === "checked_out") return "pill pill-muted";
  if (s === "reserved" || s === "confirmed") return "pill pill-warning";
  if (s === "cancelled" || s === "no_show" || s === "no-show") {
    return "pill pill-danger";
  }
  return "pill";
}

function roomReady(room?: RoomStatusItem) {
  if (!room) return false;
  const status = String(room.hk_status || "").toLowerCase();
  return !room.is_occupied && (status.includes("clean") || status.includes("inspected"));
}

function roomBlocked(room?: RoomStatusItem) {
  const status = String(room?.hk_status || "").toLowerCase();
  return status.includes("out") || status.includes("ooo") || status.includes("order");
}

function normalizeRoomNumber(value?: string | null) {
  return String(value || "").trim();
}

function bookingBalance(row: FrontdeskBooking) {
  return Number(row.balance_due ?? row.total_amount ?? 0);
}

function bookingIsVip(row: FrontdeskBooking) {
  return String(row.channel || row.source || row.notes || row.special_requests || "")
    .toLowerCase()
    .includes("vip");
}

function money(value: number, currency = "ETB") {
  return `${currency} ${Number(value || 0).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function countNights(checkInDate: string, checkOutDate: string) {
  const start = new Date(`${checkInDate}T00:00:00`);
  const end = new Date(`${checkOutDate}T00:00:00`);
  const diff = Math.round((end.getTime() - start.getTime()) / 86400000);
  return Math.max(diff || 1, 1);
}

function parseMoneyFromNotes(notes: string | null | undefined, label: string) {
  const match = String(notes || "").match(new RegExp(`${label}:\\s*([0-9,.]+)`, "i"));
  if (!match) return 0;
  return Number(match[1].replace(/,/g, "")) || 0;
}

function folioReceipt(row: FrontdeskBooking, businessDate: string) {
  const nights = countNights(row.check_in_date, row.check_out_date);
  const total = bookingBalance(row);
  const rate = Number(row.rate_per_night_etb || 0) || (nights ? total / nights : total);
  const downpayment = parseMoneyFromNotes(row.notes, "Downpayment");
  const paidNow = parseMoneyFromNotes(row.notes, "Amount Paid Now");
  const roomSubtotal = rate * nights;
  const postedCharges = total || roomSubtotal;
  const dueNow = Math.max(postedCharges - downpayment - paidNow, 0);

  return {
    businessDate,
    nights,
    rate,
    roomSubtotal,
    postedCharges,
    downpayment,
    paidNow,
    dueNow,
  };
}

function selectedPercent(selected: string, custom: string) {
  if (selected === "custom") return parseOptionalNumber(custom) || 0;
  return parseOptionalNumber(selected) || 0;
}

function totalGuests(form: WalkInFormState) {
  return (parseOptionalNumber(form.adults) || 0) + (parseOptionalNumber(form.children) || 0);
}

function walkInReceiptTotals(form: WalkInFormState) {
  const nights = countNights(form.checkInDate, form.checkOutDate);
  const rate = parseOptionalNumber(form.ratePerNightEtb) || 0;
  const roomSubtotal = rate * nights;
  const discount = parseOptionalNumber(form.discountAmount) || 0;
  const guests = totalGuests(form);
  const extraGuestCount = Math.max(guests - 5, 0);
  const extraBedCharge = extraGuestCount * (parseOptionalNumber(form.extraBedCharge) || 0);
  const taxableBase = Math.max(roomSubtotal - discount + extraBedCharge, 0);
  const taxPercent = selectedPercent(form.taxPercent, form.customTaxPercent);
  const serviceChargePercent = selectedPercent(
    form.serviceChargePercent,
    form.customServiceChargePercent
  );
  const vatPercent = selectedPercent(form.vatPercent, form.customVatPercent);
  const tax = taxableBase * (taxPercent / 100);
  const serviceCharge = taxableBase * (serviceChargePercent / 100);
  const vat = taxableBase * (vatPercent / 100);
  const explicitTotal = parseOptionalNumber(form.totalAmountEtb);
  const total =
    explicitTotal ??
    Math.max(taxableBase + tax + serviceCharge + vat, 0);
  const downpayment = parseOptionalNumber(form.downpaymentAmount) || 0;
  const paidNow = parseOptionalNumber(form.amountPaidNowEtb) || 0;
  return {
    nights,
    guests,
    extraGuestCount,
    roomSubtotal,
    discount,
    extraBedCharge,
    taxableBase,
    taxPercent,
    serviceChargePercent,
    vatPercent,
    tax,
    serviceCharge,
    vat,
    total,
    downpayment,
    paidNow,
    balanceDue: Math.max(total - downpayment - paidNow, 0),
  };
}

export default function FrontDeskCommandCenter() {
  const { propertyCode, businessDate, refreshKey, refreshData } = usePmsContext();

  const [rows, setRows] = useState<FrontdeskBooking[]>([]);
  const [rooms, setRooms] = useState<RoomStatusItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [busyBookingId, setBusyBookingId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<FrontDeskTab>("arrivals");
  const [activeOperation, setActiveOperation] = useState<FrontDeskOperation>("arrivals");
  const [selectedFolio, setSelectedFolio] = useState<FrontdeskBooking | null>(null);
  const [roomInputs, setRoomInputs] = useState<Record<number, string>>({});
  const [showWalkIn, setShowWalkIn] = useState(false);
  const [walkInSubmitting, setWalkInSubmitting] = useState(false);
  const [arrivalFilters, setArrivalFilters] = useState<ArrivalFilterState>(() => ({
    arrivalDate: businessDate,
    search: "",
    roomType: "",
    roomNumber: "",
    vip: "all",
    groupBlock: "",
    assignment: "all",
    status: "",
    payment: "",
    readiness: "all",
  }));
  const [roomCandidateFilters, setRoomCandidateFilters] = useState<RoomCandidateFilterState>({
    search: "",
    roomType: "",
    floor: "",
    housekeeping: "ready",
  });
  const [qReservations, setQReservations] = useState<Record<number, QReservationState>>({});
  const [registrationGenerated, setRegistrationGenerated] = useState<Record<number, string>>({});
  const [manualAuthorizations, setManualAuthorizations] = useState<Record<number, ManualAuthorizationState>>({});
  const [upsellDecisions, setUpsellDecisions] = useState<Record<number, "accepted" | "declined">>({});
  const [selectedRegistrationCard, setSelectedRegistrationCard] = useState<FrontdeskBooking | null>(null);
  const canCheckIn = roleCan("frontdesk.check_in");
  const canCheckOut = roleCan("frontdesk.check_out");
  const canAssignRoom = roleCan("frontdesk.room_move");
  const canUseFrontDeskActions = canCheckIn || canCheckOut || canAssignRoom;
  const [walkInForm, setWalkInForm] = useState<WalkInFormState>(() =>
    defaultWalkInForm(businessDate)
  );

  async function loadBoard() {
    try {
      setLoading(true);
      setError("");
      const [bookingRows, roomRows] = await Promise.all([
        fetchFrontdeskBookings(propertyCode, businessDate),
        fetchRoomStatusBoard(propertyCode, businessDate),
      ]);
      setRows(bookingRows);
      setRooms(roomRows);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBoard();
  }, [propertyCode, businessDate, refreshKey]);

  useEffect(() => {
    setWalkInForm((prev) => ({
      ...prev,
      checkInDate: prev.checkInDate || businessDate,
      checkOutDate: prev.checkOutDate || businessDate,
    }));
    setArrivalFilters((prev) => ({
      ...prev,
      arrivalDate: prev.arrivalDate || businessDate,
    }));
  }, [businessDate]);

  const roomByNumber = useMemo(() => {
    const map = new Map<string, RoomStatusItem>();
    rooms.forEach((room) => map.set(normalizeRoomNumber(room.room_number), room));
    return map;
  }, [rooms]);

  const cleanRooms = useMemo(
    () =>
      rooms
        .filter(roomReady)
        .sort((a, b) =>
          normalizeRoomNumber(a.room_number).localeCompare(
            normalizeRoomNumber(b.room_number),
            undefined,
            { numeric: true }
          )
        ),
    [rooms]
  );

  const dirtyRooms = useMemo(
    () =>
      rooms.filter((room) =>
        String(room.hk_status || "").toLowerCase().includes("dirty")
      ),
    [rooms]
  );

  const outOfOrderRooms = useMemo(() => rooms.filter(roomBlocked), [rooms]);

  const inspectedRooms = useMemo(
    () => rooms.filter((room) => String(room.hk_status || "").toLowerCase().includes("inspect")),
    [rooms]
  );

  const occupiedRooms = useMemo(() => rooms.filter((room) => room.is_occupied), [rooms]);

  const outOfServiceRooms = useMemo(
    () => rooms.filter((room) => String(room.hk_status || "").toLowerCase().includes("out_of_service")),
    [rooms]
  );

  const arrivals = useMemo(
    () => rows.filter((row) => row.check_in_date === businessDate),
    [rows, businessDate]
  );

  const expectedCheckIns = useMemo(
    () =>
      arrivals.filter((row) => {
        const status = String(row.booking_status || "").toLowerCase();
        return !["in_house", "checked_in", "checked_out", "cancelled", "no_show", "no-show"].includes(status);
      }),
    [arrivals]
  );

  const checkedIn = useMemo(
    () =>
      arrivals.filter((row) => {
        const status = String(row.booking_status || "").toLowerCase();
        return status === "in_house" || status === "checked_in";
      }),
    [arrivals]
  );

  const departures = useMemo(
    () => rows.filter((row) => row.check_out_date === businessDate),
    [rows, businessDate]
  );

  const checkedOut = useMemo(
    () =>
      departures.filter((row) => String(row.booking_status || "").toLowerCase() === "checked_out"),
    [departures]
  );

  const inHouse = useMemo(
    () =>
      rows.filter((row) => {
        const status = String(row.booking_status || "").toLowerCase();
        return status === "in_house" || status === "checked_in";
      }),
    [rows]
  );

  const stayovers = useMemo(
    () => inHouse.filter((row) => row.check_in_date < businessDate && row.check_out_date > businessDate),
    [businessDate, inHouse]
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

  const unassignedArrivals = useMemo(
    () => expectedCheckIns.filter((row) => !normalizeRoomNumber(row.room_number)),
    [expectedCheckIns]
  );

  const qRows = useMemo(
    () => rows.filter((row) => qReservations[row.id]),
    [qReservations, rows]
  );

  const filteredArrivals = useMemo(() => {
    const needle = arrivalFilters.search.trim().toLowerCase();
    return rows.filter((row) => {
      if (arrivalFilters.arrivalDate && row.check_in_date !== arrivalFilters.arrivalDate) return false;
      const roomNumber = normalizeRoomNumber(row.room_number);
      const status = String(row.booking_status || "").toLowerCase();
      const payment = String(row.payment_status || row.guarantee_status || "").toLowerCase();
      const text = [
        row.guest_name,
        row.confirmation_id,
        row.room_type,
        row.room_number,
        row.source,
        row.channel,
        row.notes,
        row.special_requests,
      ].join(" ").toLowerCase();
      if (needle && !text.includes(needle)) return false;
      if (arrivalFilters.roomType && displayRoomType(row) !== arrivalFilters.roomType) return false;
      if (arrivalFilters.roomNumber && roomNumber !== arrivalFilters.roomNumber.trim()) return false;
      if (arrivalFilters.vip === "vip" && !isVipBooking(row)) return false;
      if (arrivalFilters.vip === "non_vip" && isVipBooking(row)) return false;
      if (arrivalFilters.groupBlock && !text.includes(arrivalFilters.groupBlock.toLowerCase())) return false;
      if (arrivalFilters.assignment === "assigned" && !roomNumber) return false;
      if (arrivalFilters.assignment === "unassigned" && roomNumber) return false;
      if (arrivalFilters.status && !status.includes(arrivalFilters.status.toLowerCase())) return false;
      if (arrivalFilters.payment && !payment.includes(arrivalFilters.payment.toLowerCase())) return false;
      if (arrivalFilters.readiness !== "all") {
        const readiness = checkInReadiness(row);
        const hasBlockers = readiness.blockers.length > 0;
        if (arrivalFilters.readiness === "ready" && hasBlockers) return false;
        if (arrivalFilters.readiness === "blocked" && !hasBlockers) return false;
        if (arrivalFilters.readiness === "payment" && !readiness.blockers.concat(readiness.warnings).some((item) => item.toLowerCase().includes("payment") || item.toLowerCase().includes("authorization"))) return false;
        if (arrivalFilters.readiness === "room" && !readiness.blockers.concat(readiness.warnings).some((item) => item.toLowerCase().includes("room"))) return false;
      }
      return true;
    });
  }, [arrivalFilters, rows, roomByNumber]);

  const assignedArrivals = useMemo(
    () => expectedCheckIns.filter((row) => normalizeRoomNumber(row.room_number)),
    [expectedCheckIns]
  );

  const roomCandidates = useMemo(() => {
    const needle = roomCandidateFilters.search.trim().toLowerCase();
    return rooms
      .filter((room) => {
        const roomText = [
          room.room_number,
          room.room_type,
          room.floor,
          room.hk_status,
          room.maintenance_note,
          room.out_of_order_reason,
        ].join(" ").toLowerCase();
        const hk = String(room.hk_status || "").toLowerCase();
        if (needle && !roomText.includes(needle)) return false;
        if (roomCandidateFilters.roomType && room.room_type !== roomCandidateFilters.roomType) return false;
        if (roomCandidateFilters.floor && String(room.floor) !== roomCandidateFilters.floor) return false;
        if (roomCandidateFilters.housekeeping === "ready" && !roomReady(room)) return false;
        if (roomCandidateFilters.housekeeping === "dirty" && !hk.includes("dirty")) return false;
        if (roomCandidateFilters.housekeeping === "blocked" && !roomBlocked(room)) return false;
        if (roomCandidateFilters.housekeeping === "occupied" && !room.is_occupied) return false;
        return true;
      })
      .sort((a, b) =>
        normalizeRoomNumber(a.room_number).localeCompare(
          normalizeRoomNumber(b.room_number),
          undefined,
          { numeric: true }
        )
      );
  }, [roomCandidateFilters, rooms]);

  const projectedRoomRevenue = useMemo(
    () =>
      [...expectedCheckIns, ...inHouse].reduce(
        (sum, row) => sum + Number(row.rate_per_night_etb || row.total_amount || 0),
        0
      ),
    [expectedCheckIns, inHouse]
  );

  const houseStatusMetrics = useMemo(() => {
    const sellableRooms = Math.max(rooms.length - outOfOrderRooms.length - outOfServiceRooms.length, 0);
    const occupiedCount = occupiedRooms.length || inHouse.length;
    const availableTonight = Math.max(sellableRooms - occupiedCount - expectedCheckIns.length, 0);
    const occupancyPct = sellableRooms ? Math.round((occupiedCount / sellableRooms) * 100) : 0;
    const adr = occupiedCount ? projectedRoomRevenue / occupiedCount : 0;
    return [
      { label: "Total Physical Rooms", value: rooms.length, note: "Configured room inventory" },
      { label: "Available Tonight", value: availableTonight, note: "Sellable rooms after occupancy and arrivals" },
      { label: "Occupied Rooms", value: occupiedCount, note: "Current in-house / occupied rooms" },
      { label: "Occupancy %", value: `${occupancyPct}%`, note: "Current operational occupancy" },
      { label: "Expected Arrivals", value: expectedCheckIns.length, note: "Due to arrive today" },
      { label: "Arrivals Checked In", value: checkedIn.length, note: "Completed check-ins today" },
      { label: "Expected Departures", value: departures.length, note: "Due out today" },
      { label: "Stayovers", value: stayovers.length, note: "In-house past today" },
      { label: "Out of Order", value: outOfOrderRooms.length, note: "Not sellable" },
      { label: "Out of Service", value: outOfServiceRooms.length, note: "Operationally unavailable" },
      { label: "Dirty Rooms", value: dirtyRooms.length, note: "Housekeeping required" },
      { label: "Clean Rooms", value: cleanRooms.length, note: "Clean or inspected supply" },
      { label: "Inspected Rooms", value: inspectedRooms.length, note: "Preferred for check-in" },
      { label: "Rooms on Q", value: qRows.length, note: "Guests waiting for room readiness" },
      { label: "Projected Room Revenue", value: money(projectedRoomRevenue), note: "Arrival and in-house room value" },
      { label: "ADR", value: money(adr), note: "Average daily rate estimate" },
    ];
  }, [checkedIn.length, cleanRooms.length, departures.length, dirtyRooms.length, expectedCheckIns.length, inHouse.length, inspectedRooms.length, occupiedRooms.length, outOfOrderRooms.length, outOfServiceRooms.length, projectedRoomRevenue, qRows.length, rooms.length, stayovers.length]);

  const roomNotReadyArrivals = useMemo(
    () =>
      expectedCheckIns.filter((row) => {
        const roomNumber = normalizeRoomNumber(row.room_number);
        if (!roomNumber) return false;
        return !roomReady(roomByNumber.get(roomNumber));
      }),
    [expectedCheckIns, roomByNumber]
  );

  const inHouseRoomStatusExceptions = useMemo(
    () =>
      inHouse.filter((row) => {
        const roomNumber = normalizeRoomNumber(row.room_number);
        if (!roomNumber) return false;
        return !roomReady(roomByNumber.get(roomNumber));
      }),
    [inHouse, roomByNumber]
  );

  const balanceReview = useMemo(
    () => [...departures, ...inHouse].filter((row) => bookingBalance(row) > 0),
    [departures, inHouse]
  );

  const suggestedRooms = useMemo(() => {
    const map = new Map<number, string>();
    expectedCheckIns.forEach((row, index) => {
      if (normalizeRoomNumber(row.room_number)) return;
      const suggestion = cleanRooms[index % Math.max(cleanRooms.length, 1)];
      if (suggestion) map.set(row.id, suggestion.room_number);
    });
    return map;
  }, [expectedCheckIns, cleanRooms]);

  function getSuggestedRoom(row: FrontdeskBooking) {
    if (normalizeRoomNumber(row.room_number)) return normalizeRoomNumber(row.room_number);
    return suggestedRooms.get(row.id) || cleanRooms[0]?.room_number || "";
  }

  function displayRoomType(row: FrontdeskBooking) {
    const directRoomType = String(row.room_type || "").trim();
    if (directRoomType) return directRoomType;
    const assignedRoom = roomByNumber.get(normalizeRoomNumber(row.room_number));
    return assignedRoom?.room_type || "Standard Room";
  }

  function isVipBooking(row: FrontdeskBooking) {
    return bookingIsVip(row);
  }

  function hasPaymentGuarantee(row: FrontdeskBooking) {
    const guarantee = String(row.guarantee_status || row.payment_status || row.payment_method || "").toLowerCase();
    return ["paid", "deposit", "guarantee", "card", "authorized", "approved"].some((token) => guarantee.includes(token));
  }

  function isNoPost(row: FrontdeskBooking) {
    const payment = String(row.payment_method || row.payment_status || "").toLowerCase();
    return payment.includes("cash") || payment.includes("check") || payment.includes("no post") || !hasPaymentGuarantee(row);
  }

  function checkInReadiness(row: FrontdeskBooking) {
    const blockers: string[] = [];
    const warnings: string[] = [];
    const status = String(row.booking_status || "").toLowerCase();
    const roomNumber = normalizeRoomNumber(row.room_number || getSuggestedRoom(row));
    const assignedRoom = roomByNumber.get(roomNumber);
    const hkStatus = String(assignedRoom?.hk_status || row.housekeeping_status || "").toLowerCase();

    if (row.check_in_date !== businessDate) warnings.push("Arrival is not on the selected business date.");
    if (!roomNumber) blockers.push("Needs Room Assignment");
    if (status.includes("cancel") || status.includes("no_show") || status.includes("no-show")) blockers.push("Reservation is cancelled or no-show.");
    if (hkStatus.includes("dirty")) blockers.push("Room Dirty");
    if (hkStatus.includes("out")) blockers.push("Manager Override Required");
    if (roomNumber && hkStatus.includes("clean") && !hkStatus.includes("inspect")) warnings.push("Room Not Inspected");
    if (roomNumber && !hkStatus.includes("clean") && !hkStatus.includes("inspect")) warnings.push("Room Not Inspected");
    if (!row.payment_method && !manualAuthorizations[row.id]) warnings.push("Payment Required");
    if (!hasPaymentGuarantee(row)) warnings.push("Payment Required");
    if (!manualAuthorizations[row.id] && !hasPaymentGuarantee(row)) warnings.push("Authorization Required");
    if (!registrationGenerated[row.id]) warnings.push("Registration Card Pending");
    if (!row.guest_email && !String(row.notes || "").toLowerCase().includes("profile")) warnings.push("Guest profile contact needs review.");
    if (isVipBooking(row)) warnings.push("VIP/special request review required.");
    if (row.notes || row.special_requests) warnings.push("Comments and alerts must be reviewed.");

    return { blockers, warnings };
  }

  function operationalBadges(row: FrontdeskBooking) {
    const status = String(row.booking_status || "").toLowerCase();
    const paymentStatus = String(row.payment_status || "pending").toLowerCase();
    const roomNumber = normalizeRoomNumber(row.room_number);
    const assignedRoom = roomByNumber.get(roomNumber);
    const badges: Array<{ label: string; className: string }> = [];

    if (!roomNumber && expectedCheckIns.some((arrival) => arrival.id === row.id)) {
      badges.push({ label: "Room TBD", className: "pill pill-warning" });
      badges.push({ label: "Assignment Required Before Check-in", className: "pill pill-danger" });
    }

    if (roomNumber && assignedRoom && !roomReady(assignedRoom)) {
      badges.push({ label: "Room Not Ready", className: "pill pill-danger" });
    }

    if (status === "pending_guarantee" || paymentStatus === "pending") {
      badges.push({ label: "Guarantee / Deposit Review", className: "pill pill-warning" });
    }

    if (paymentStatus === "deposit_paid" || paymentStatus === "guaranteed" || paymentStatus === "paid") {
      badges.push({ label: "Guaranteed", className: "pill pill-success" });
    }

    if (qReservations[row.id]) badges.push({ label: "On Q", className: "pill pill-warning" });
    if (isVipBooking(row)) badges.push({ label: "VIP", className: "pill pill-warning" });
    if (isNoPost(row)) badges.push({ label: "No Post", className: "pill pill-danger" });
    if (String(row.notes || row.special_requests || "").toLowerCase().includes("route")) {
      badges.push({ label: "Routed", className: "pill pill-success" });
    }
    if (manualAuthorizations[row.id]) {
      badges.push({ label: "Authorized", className: "pill pill-success" });
    } else if (!hasPaymentGuarantee(row)) {
      badges.push({ label: "Authorization Required", className: "pill pill-warning" });
    }

    return badges;
  }

  function selectOperation(operation: FrontDeskOperation) {
    setActiveOperation(operation);
    if (operation === "arrivals" || operation === "expectedCheckIns" || operation === "checkedIn") {
      setActiveTab("arrivals");
      return;
    }
    if (operation === "departures" || operation === "checkedOut") {
      setActiveTab("departures");
      return;
    }
    if (operation === "inHouse") {
      setActiveTab("inHouse");
      return;
    }
    if (operation === "walkIns") {
      setActiveTab("walkIn");
      return;
    }
    if (operation === "assignment") {
      setActiveTab("assignment");
      return;
    }
    if (operation === "exceptions" || operation === "noShows") {
      setActiveTab("exceptions");
      return;
    }
    setActiveTab("shift");
  }

  async function assignSpecificRoom(row: FrontdeskBooking, roomNumber: string) {
    if (!roomNumber) {
      setError(`Enter or select a room number first for ${row.guest_name}.`);
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

  async function handleAssignRoom(row: FrontdeskBooking) {
    await assignSpecificRoom(row, String(roomInputs[row.id] || "").trim());
  }

  async function handleAssignSuggested(row: FrontdeskBooking) {
    await assignSpecificRoom(row, getSuggestedRoom(row));
  }

  async function handleAutoAssignAll() {
    if (!canAssignRoom) {
      setError(permissionMessage("Auto room assignment"));
      return;
    }
    const assignable = unassignedArrivals
      .map((row) => ({ row, roomNumber: getSuggestedRoom(row) }))
      .filter((item) => item.roomNumber);
    if (!assignable.length) {
      setActionMessage("No unassigned arrivals with clean/inspected room suggestions.");
      return;
    }
    for (const item of assignable) {
      await assignSpecificRoom(item.row, item.roomNumber);
    }
    setActionMessage(`Auto-assigned ${assignable.length} arrival room(s).`);
  }

  async function handleUnassignRoom(row: FrontdeskBooking) {
    if (!canAssignRoom) {
      setError(permissionMessage("Room unassignment"));
      return;
    }
    setRoomInputs((current) => ({ ...current, [row.id]: "" }));
    setActionMessage(`Room unassignment for ${row.guest_name} is prepared. Use Assign Room to save a new room when selected.`);
  }

  async function handleExchangeRooms() {
    if (!canAssignRoom) {
      setError(permissionMessage("Room exchange"));
      return;
    }
    const firstId = Number(window.prompt("First booking ID to exchange"));
    const secondId = Number(window.prompt("Second booking ID to exchange"));
    const first = rows.find((row) => row.id === firstId);
    const second = rows.find((row) => row.id === secondId);
    if (!first || !second) {
      setError("Both booking IDs must match visible front desk bookings.");
      return;
    }
    const firstRoom = normalizeRoomNumber(first.room_number);
    const secondRoom = normalizeRoomNumber(second.room_number);
    if (!firstRoom || !secondRoom) {
      setError("Both bookings need assigned rooms before exchange.");
      return;
    }
    await assignSpecificRoom(first, secondRoom);
    await assignSpecificRoom(second, firstRoom);
    setActionMessage(`Exchanged rooms for ${first.guest_name} and ${second.guest_name}.`);
  }

  function handlePlaceOnQ(row: FrontdeskBooking) {
    setQReservations((current) => ({
      ...current,
      [row.id]: {
        startedAt: new Date().toISOString(),
        priority: isVipBooking(row) ? "vip" : "normal",
        notes: `Waiting for ${displayRoomType(row)} readiness.`,
      },
    }));
    setActionMessage(`${row.guest_name} placed on Q. Housekeeping should prioritize room readiness.`);
  }

  function handleRemoveFromQ(row: FrontdeskBooking) {
    setQReservations((current) => {
      const next = { ...current };
      delete next[row.id];
      return next;
    });
    setActionMessage(`${row.guest_name} removed from Q.`);
  }

  function handleGenerateRegistrationCard(row: FrontdeskBooking) {
    setRegistrationGenerated((current) => ({ ...current, [row.id]: new Date().toISOString() }));
    setSelectedRegistrationCard(row);
    setActionMessage(`Registration card generated for ${row.guest_name}.`);
  }

  function handleBatchRegistrationCards() {
    const timestamp = new Date().toISOString();
    const next = { ...registrationGenerated };
    filteredArrivals.forEach((row) => {
      next[row.id] = timestamp;
    });
    setRegistrationGenerated(next);
    setActionMessage(`Generated ${filteredArrivals.length} registration card(s) for selected arrivals.`);
  }

  function handleManualAuthorization(row: FrontdeskBooking) {
    const amount = Number(window.prompt("Authorization amount", String(Math.max(bookingBalance(row), Number(row.rate_per_night_etb || 0)) || 0)));
    if (!Number.isFinite(amount) || amount <= 0) return;
    const code = window.prompt("Approval code / manual reference", "MANUAL-AUTH") || "MANUAL-AUTH";
    setManualAuthorizations((current) => ({
      ...current,
      [row.id]: {
        amount,
        code,
        authorizedBy: "Front Desk",
        authorizedAt: new Date().toISOString(),
        type: String(row.payment_method || "").toLowerCase().includes("cash") ? "cash" : "offline",
        notes: "Manual/offline front desk authorization recorded.",
      },
    }));
    setActionMessage(`Manual authorization recorded for ${row.guest_name}.`);
  }

  function handleUpsell(row: FrontdeskBooking, accepted: boolean) {
    setUpsellDecisions((current) => ({ ...current, [row.id]: accepted ? "accepted" : "declined" }));
    setActionMessage(`${row.guest_name} ${accepted ? "accepted" : "declined"} the check-in upsell offer.`);
  }

  async function handleCheckIn(row: FrontdeskBooking) {
    const status = String(row.booking_status || "").toLowerCase();
    if (status === "in_house" || status === "checked_in") {
      setError(`${row.guest_name} is already in house. Use Open Folio, Room Move, or Check Out.`);
      return;
    }

    const roomNumber = normalizeRoomNumber(row.room_number || getSuggestedRoom(row));
    const assignedRoom = roomByNumber.get(roomNumber);

    if (!roomNumber) {
      setError(`Assign a clean room before checking in ${row.guest_name}.`);
      return;
    }

    if (assignedRoom && !roomReady(assignedRoom)) {
      setError(
        `Room ${roomNumber} is not ready. Check-in is blocked until housekeeping marks it clean or inspected.`
      );
      return;
    }

    const readiness = checkInReadiness(row);
    if (readiness.blockers.length) {
      setError(`Check-in blocked: ${readiness.blockers.join(" ")}`);
      return;
    }

    try {
      setBusyBookingId(row.id);
      setActionMessage("");
      setError("");
      if (!normalizeRoomNumber(row.room_number)) {
        await assignRoom({
          bookingId: row.id,
          propertyCode,
          roomNumber,
        });
      }
      await checkInGuest({
        bookingId: row.id,
        propertyCode,
        businessDate,
      });
      setActionMessage(`Check-in completed for ${row.guest_name}. Folio is ready.`);
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

      const validation = await validateCheckout(propertyCode, row.id, businessDate);
      if (!validation.can_checkout) {
        setError(
          validation.message ||
            `Checkout blocked. Folio balance is ${validation.balance.toFixed(2)}.`
        );
        return;
      }

      await checkOutGuest({
        bookingId: row.id,
        propertyCode,
        businessDate,
      });
      setActionMessage(
        `Check-out completed for ${row.guest_name}. Housekeeping can clean room ${
          row.room_number || ""
        }.`.trim()
      );
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyBookingId(null);
    }
  }

  async function handleRoomMove(row: FrontdeskBooking) {
    const suggested = cleanRooms.find(
      (room) => normalizeRoomNumber(room.room_number) !== normalizeRoomNumber(row.room_number)
    )?.room_number;
    const roomNumber = window.prompt(
      `Move ${row.guest_name} to which clean/inspected room?`,
      suggested || ""
    );
    if (!roomNumber?.trim()) return;

    try {
      setBusyBookingId(row.id);
      setActionMessage("");
      setError("");
      await moveGuestRoom({
        bookingId: row.id,
        propertyCode,
        businessDate,
        roomNumber: roomNumber.trim(),
        note: "Room move from Front Desk Command Center",
      });
      setActionMessage(`${row.guest_name} moved to room ${roomNumber.trim()}.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyBookingId(null);
    }
  }

  async function handleExtendStay(row: FrontdeskBooking) {
    const current = new Date(`${row.check_out_date}T00:00:00`);
    current.setDate(current.getDate() + 1);
    const nextDate = current.toISOString().slice(0, 10);
    const checkOutDate = window.prompt(`Extend ${row.guest_name} to which check-out date?`, nextDate);
    if (!checkOutDate?.trim()) return;

    try {
      setBusyBookingId(row.id);
      setActionMessage("");
      setError("");
      await extendStay({
        bookingId: row.id,
        propertyCode,
        businessDate,
        checkOutDate: checkOutDate.trim(),
        note: "Stay extended from Front Desk Command Center",
      });
      setActionMessage(`${row.guest_name} extended to ${checkOutDate.trim()}.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyBookingId(null);
    }
  }

  async function handleEarlyDeparture(row: FrontdeskBooking) {
    const note = window.prompt(
      `Early departure note for ${row.guest_name}`,
      "Guest requested early departure; folio review required."
    );
    if (note === null) return;

    try {
      setBusyBookingId(row.id);
      setActionMessage("");
      setError("");
      await markEarlyDeparture({
        bookingId: row.id,
        propertyCode,
        businessDate,
        note,
      });
      setActionMessage(`${row.guest_name} marked for early departure today.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyBookingId(null);
    }
  }

  async function handleLateCheckoutNote(row: FrontdeskBooking) {
    const note = window.prompt(
      `Late checkout note for ${row.guest_name}`,
      "Late checkout requested; review payment, room status, and next arrival impact."
    );
    if (note === null) return;

    try {
      setBusyBookingId(row.id);
      setActionMessage("");
      setError("");
      await addLateCheckoutNote({
        bookingId: row.id,
        propertyCode,
        businessDate,
        note,
      });
      setActionMessage(`Late checkout note added for ${row.guest_name}.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyBookingId(null);
    }
  }

  async function handleCreateWalkIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const guestName = walkInForm.guestName.trim();
    if (!guestName) {
      setError("Guest name is required for a walk-in booking.");
      return;
    }

    const selectedRoom = walkInForm.roomNumber.trim() || cleanRooms[0]?.room_number || "";
    const receiptTotals = walkInReceiptTotals(walkInForm);

    try {
      setWalkInSubmitting(true);
      setActionMessage("");
      setError("");
      await createWalkInBooking({
        propertyCode,
        guestName,
        adults: parseOptionalNumber(walkInForm.adults),
        children: parseOptionalNumber(walkInForm.children),
        isVip: walkInForm.isVip,
        documentType: walkInForm.documentType,
        documentNumber: walkInForm.documentNumber.trim() || undefined,
        email: walkInForm.email.trim() || undefined,
        phone: walkInForm.phone.trim() || undefined,
        purposeOfVisit: walkInForm.purposeOfVisit.trim() || undefined,
        checkInDate: walkInForm.checkInDate,
        checkOutDate: walkInForm.checkOutDate,
        roomNumber: selectedRoom || undefined,
        roomType: walkInForm.roomType.trim() || undefined,
        currency: walkInForm.currency,
        ratePerNightEtb: parseOptionalNumber(walkInForm.ratePerNightEtb),
        totalAmountEtb: parseOptionalNumber(walkInForm.totalAmountEtb),
        discountAmount: parseOptionalNumber(walkInForm.discountAmount),
        extraBedCharge: receiptTotals.extraBedCharge,
        taxPercent: receiptTotals.taxPercent,
        taxAmount: receiptTotals.tax,
        serviceChargePercent: receiptTotals.serviceChargePercent,
        serviceChargeAmount: receiptTotals.serviceCharge,
        vatPercent: receiptTotals.vatPercent,
        vatAmount: receiptTotals.vat,
        downpaymentAmount: parseOptionalNumber(walkInForm.downpaymentAmount),
        paymentMethod: walkInForm.paymentMethod,
        amountPaidNowEtb: parseOptionalNumber(walkInForm.amountPaidNowEtb),
        notes: walkInForm.notes.trim() || undefined,
      });
      setShowWalkIn(false);
      setWalkInForm(defaultWalkInForm(businessDate));
      setActionMessage(
        `Walk-in booking created for ${guestName}${selectedRoom ? ` in room ${selectedRoom}` : ""}.`
      );
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setWalkInSubmitting(false);
    }
  }

  const attentionItems = [
    {
      label: "Unassigned arrivals",
      value: unassignedArrivals.length,
      tone: unassignedArrivals.length ? "warning" : "success",
    },
    {
      label: "Rooms not ready",
      value: roomNotReadyArrivals.length + inHouseRoomStatusExceptions.length,
      tone: roomNotReadyArrivals.length + inHouseRoomStatusExceptions.length ? "danger" : "success",
    },
    {
      label: "Balance review",
      value: balanceReview.length,
      tone: balanceReview.length ? "warning" : "success",
    },
    {
      label: "Out of order",
      value: outOfOrderRooms.length,
      tone: outOfOrderRooms.length ? "danger" : "success",
    },
  ];

  const sellableRooms = Math.max(rooms.length - outOfOrderRooms.length - outOfServiceRooms.length, 0);
  const occupancyPercent = sellableRooms
    ? Math.round(((occupiedRooms.length || inHouse.length) / sellableRooms) * 100)
    : 0;
  const summaryCards = [
    {
      label: "Expected Arrivals",
      value: expectedCheckIns.length,
      note: "Due today",
      tone: expectedCheckIns.length ? "info" : "neutral",
      tab: "arrivals" as FrontDeskTab,
    },
    {
      label: "Checked In",
      value: checkedIn.length,
      note: "Arrived today",
      tone: "success",
      tab: "arrivals" as FrontDeskTab,
    },
    {
      label: "Rooms Ready",
      value: cleanRooms.length,
      note: "Clean or inspected",
      tone: cleanRooms.length ? "success" : "warning",
      tab: "houseStatus" as FrontDeskTab,
    },
    {
      label: "Rooms Dirty",
      value: dirtyRooms.length,
      note: "Needs housekeeping",
      tone: dirtyRooms.length ? "warning" : "success",
      tab: "houseStatus" as FrontDeskTab,
    },
    {
      label: "Rooms on Q",
      value: qRows.length,
      note: "Waiting guests",
      tone: qRows.length ? "warning" : "neutral",
      tab: "qReservations" as FrontDeskTab,
    },
    {
      label: "Occupancy",
      value: `${occupancyPercent}%`,
      note: `${occupiedRooms.length || inHouse.length} occupied`,
      tone: occupancyPercent > 85 ? "warning" : "info",
      tab: "houseStatus" as FrontDeskTab,
    },
    {
      label: "Departures",
      value: departures.length,
      note: "Due out today",
      tone: departures.length ? "info" : "neutral",
      tab: "departures" as FrontDeskTab,
    },
    {
      label: "OOO / OOS",
      value: outOfOrderRooms.length + outOfServiceRooms.length,
      note: "Not sellable",
      tone: outOfOrderRooms.length + outOfServiceRooms.length ? "danger" : "success",
      tab: "houseStatus" as FrontDeskTab,
    },
  ];

  const guestActionColumns = [
    {
      key: "id",
      header: "Conf #",
      render: (row: FrontdeskBooking) => row.confirmation_id || `#${row.id}`,
    },
    {
      key: "guest_name",
      header: "Guest",
      render: (row: FrontdeskBooking) => (
        <div className="fd-guest-cell">
          <strong>{row.guest_name}</strong>
          <span>{displayRoomType(row)}</span>
          {row.special_requests || row.notes ? (
            <span>{String(row.special_requests || row.notes).slice(0, 90)}</span>
          ) : null}
        </div>
      ),
    },
    {
      key: "room",
      header: "Room",
      render: (row: FrontdeskBooking) => {
        const roomNumber = normalizeRoomNumber(row.room_number);
        const assignedRoom = roomByNumber.get(roomNumber);
        return roomNumber ? (
          <div className="fd-ops-badge-stack">
            <span className="fd-room-chip">{roomNumber}</span>
            <span className="pill">{row.housekeeping_status || assignedRoom?.hk_status || "HK pending"}</span>
            {operationalBadges(row)
              .filter((badge) => badge.label === "Room Not Ready")
              .map((badge) => (
                <span className={badge.className} key={badge.label}>{badge.label}</span>
              ))}
          </div>
        ) : (
          <div className="fd-ops-badge-stack">
            <span className="fd-suggested-room">Suggest {getSuggestedRoom(row) || "TBD"}</span>
            <span className="pill pill-warning">Room TBD</span>
          </div>
        );
      },
    },
    {
      key: "status",
      header: "Status",
      render: (row: FrontdeskBooking) => (
        <div className="fd-ops-badge-stack">
          <span className={statusClass(row.booking_status)}>{row.booking_status}</span>
          <span className="pill">{row.guarantee_status || row.payment_status || "pending"}</span>
          <span className={bookingBalance(row) > 0 ? "pill pill-warning" : "pill pill-success"}>
            {money(bookingBalance(row))}
          </span>
          {operationalBadges(row)
            .filter((badge) => badge.label !== "Room Not Ready" && badge.label !== "Room TBD")
            .map((badge) => (
              <span className={badge.className} key={badge.label}>{badge.label}</span>
            ))}
        </div>
      ),
    },
  ];

  const operationRowsByType: Record<FrontDeskOperation, FrontdeskBooking[]> = {
    shift: [...expectedCheckIns, ...checkedIn, ...departures, ...inHouse],
    arrivals: expectedCheckIns,
    expectedCheckIns,
    checkedIn,
    departures,
    checkedOut,
    inHouse,
    noShows,
    walkIns,
    assignment: unassignedArrivals,
    exceptions: [
      ...unassignedArrivals,
      ...roomNotReadyArrivals,
      ...inHouseRoomStatusExceptions,
      ...balanceReview,
      ...noShows,
    ],
  };

  const tabOrder: FrontDeskTab[] = [
    "arrivals",
    "houseStatus",
    "qReservations",
    "assignment",
    "roomPlan",
    "floorPlan",
    "registration",
    "walkIn",
    "inHouse",
    "departures",
    "reports",
    "exceptions",
  ];

  const visibleTabs = tabOrder.filter((tab) => {
    if (tab === "walkIn") return canCheckIn;
    if (tab === "assignment") return canAssignRoom;
    return true;
  });

  return (
    <div className="page-grid frontdesk-command frontdesk-command-center">
      <PageHeader
        title="Front Desk Command Center"
        subtitle={`Arrival, room readiness, check-in, queue, and guest movement control | ${propertyCode} | ${businessDate}`}
        rightSlot={
          <div className="frontdesk-header-actions">
            <span className="pill pill-success">Live Data</span>
            <span className="pill pill-success">{cleanRooms.length} Rooms Ready</span>
            <span className={expectedCheckIns.length ? "pill pill-warning" : "pill pill-muted"}>
              {expectedCheckIns.length} Arrivals Pending
            </span>
            <span className={qRows.length ? "pill pill-warning" : "pill pill-muted"}>
              {qRows.length} Q Waiting
            </span>
            {canCheckIn ? (
              <button
                className="primary-btn fd-icon-btn fd-walkin-btn"
                onClick={() => {
                  selectOperation("walkIns");
                  setActiveTab("walkIn");
                  setShowWalkIn(true);
                }}
              >
                <DoorOpen size={15} />
                New Walk-In
              </button>
            ) : (
              <span className="pill pill-muted">Read Only</span>
            )}
          </div>
        }
      />

      {loading ? (
        <div className="card">Loading front desk command center...</div>
      ) : (
        <>
          {error ? <div className="error-box">{error}</div> : null}
          {actionMessage ? <div className="notice-box">{actionMessage}</div> : null}
          {!canUseFrontDeskActions ? (
            <div className="notice-box">
              {permissionMessage("Front Desk operational actions")}
            </div>
          ) : null}
          {selectedFolio ? (
            <FolioReceiptModal
              row={selectedFolio}
              businessDate={businessDate}
              propertyCode={propertyCode}
              roomType={displayRoomType(selectedFolio)}
              onClose={() => setSelectedFolio(null)}
            />
          ) : null}
          {selectedRegistrationCard ? (
            <RegistrationCardModal
              row={selectedRegistrationCard}
              businessDate={businessDate}
              propertyCode={propertyCode}
              roomType={displayRoomType(selectedRegistrationCard)}
              authorization={manualAuthorizations[selectedRegistrationCard.id]}
              generatedAt={registrationGenerated[selectedRegistrationCard.id]}
              onClose={() => setSelectedRegistrationCard(null)}
            />
          ) : null}

          <div className="frontdesk-summary-grid fd-kpi-strip fd-operation-strip">
            {summaryCards.map((card) => {
              return (
                <button
                  key={card.label}
                  type="button"
                  className={`frontdesk-status-card fd-metric ${card.tone} ${activeTab === card.tab ? "active" : ""}`}
                  onClick={() => {
                    setActiveTab(card.tab);
                    const operationByCard: Partial<Record<FrontDeskTab, FrontDeskOperation>> = {
                      arrivals: "arrivals",
                      houseStatus: "shift",
                      qReservations: "arrivals",
                      departures: "departures",
                    };
                    setActiveOperation(operationByCard[card.tab] || "shift");
                  }}
                >
                  <span>{card.label}</span>
                  <strong>{card.value}</strong>
                  <small>{card.note}</small>
                </button>
              );
            })}
          </div>

          <div className="frontdesk-workflow-tabs fd-tabs">
            {visibleTabs.map((tab) => (
              <button
                key={tab}
                className={`tab-btn ${activeTab === tab ? "active" : ""}`}
                onClick={() => {
                  const operationByTab: Record<FrontDeskTab, FrontDeskOperation> = {
                    shift: "shift",
                    houseStatus: "shift",
                    arrivals: "arrivals",
                    qReservations: "arrivals",
                    departures: "departures",
                    inHouse: "inHouse",
                    walkIn: "walkIns",
                    assignment: "assignment",
                    roomPlan: "assignment",
                    floorPlan: "assignment",
                    registration: "arrivals",
                    reports: "shift",
                    exceptions: "exceptions",
                  };
                  setActiveOperation(operationByTab[tab]);
                  setActiveTab(tab);
                }}
              >
                {tabLabels[tab]}
              </button>
            ))}
          </div>

          {activeTab === "houseStatus" ? (
            <section className="card fd-workflow-card">
              <SectionTitle
                icon={<ClipboardList />}
                title="House Status"
                subtitle="Arrival-day hotel condition before check-in, room assignment, Q, and night audit handoff."
              />
              <div className="fd-house-status-grid">
                {houseStatusMetrics.map((metric) => (
                  <div className="fd-house-status-card" key={metric.label}>
                    <span>{metric.label}</span>
                    <strong>{metric.value}</strong>
                    <small>{metric.note}</small>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {activeTab === "shift" ? (
            <div className="page-grid two-col">
              <section className="card fd-workflow-card fd-shift-start-card">
                <SectionTitle
                  icon={<ClipboardList />}
                  title="Shift Start Dashboard"
                  subtitle="The first scan for arrivals, rooms, payments, and handover risk."
                />
                <div className="fd-attention-grid">
                  {attentionItems.map((item) => (
                    <div className={`fd-attention-card ${item.tone}`} key={item.label}>
                      <span>{item.label}</span>
                      <strong>{item.value}</strong>
                    </div>
                  ))}
                </div>
                <div className="sop-list fd-checklist">
                  <label className="sop-item">
                    <input type="checkbox" /> Review VIP, notes, and special requests.
                  </label>
                  <label className="sop-item">
                    <input type="checkbox" /> Assign clean rooms for today arrivals.
                  </label>
                  <label className="sop-item">
                    <input type="checkbox" /> Prioritize dirty arrival rooms with housekeeping.
                  </label>
                  <label className="sop-item">
                    <input type="checkbox" /> Review open balances before departures.
                  </label>
                </div>
              </section>

              <section className="card fd-workflow-card fd-room-readiness-card">
                <SectionTitle
                  icon={<BedDouble />}
                  title="Room Readiness"
                  subtitle="Clean-room supply and problem rooms for immediate room control."
                />
                <div className="fd-readiness-grid">
                  <RoomStack title="Ready Rooms" rooms={cleanRooms.slice(0, 8)} />
                  <RoomStack title="Dirty Rooms" rooms={dirtyRooms.slice(0, 8)} />
                  <RoomStack title="Out of Order" rooms={outOfOrderRooms.slice(0, 8)} />
                </div>
              </section>
            </div>
          ) : null}

          {activeTab === "arrivals" ? (
            <section className="card fd-workflow-card frontdesk-arrivals-table">
              <SectionTitle
                icon={<UserCheck />}
                title="Arrivals Preparation"
                subtitle="Search arrivals, pre-block rooms, review registration, authorize payment, and complete check-in."
              />
              <ArrivalFilters
                filters={arrivalFilters}
                setFilters={setArrivalFilters}
                roomTypes={Array.from(new Set(rows.map(displayRoomType))).sort()}
              />
              <DataTable
                rows={filteredArrivals}
                emptyMessage="No expected check-ins for this business date."
                columns={[
                  {
                    key: "guest",
                    header: "Guest",
                    render: (row: FrontdeskBooking) => (
                      <div className="fd-guest-cell">
                        <strong>{row.guest_name}</strong>
                        <span>{row.source || row.channel || "Reservation"}</span>
                      </div>
                    ),
                  },
                  {
                    key: "confirmation",
                    header: "Confirmation",
                    render: (row: FrontdeskBooking) => row.confirmation_id || `#${row.id}`,
                  },
                  {
                    key: "dates",
                    header: "Stay Dates",
                    render: (row: FrontdeskBooking) => (
                      <div className="fd-guest-cell">
                        <span>{row.check_in_date} to {row.check_out_date}</span>
                        <span>{countNights(row.check_in_date, row.check_out_date)} night(s)</span>
                        <span>{(row as any).adults ?? "-"} adult(s) / {(row as any).children ?? "-"} child(ren)</span>
                      </div>
                    ),
                  },
                  {
                    key: "roomType",
                    header: "Room Type",
                    render: (row: FrontdeskBooking) => displayRoomType(row),
                  },
                  {
                    key: "room",
                    header: "Room",
                    render: (row: FrontdeskBooking) => {
                      const roomNumber = normalizeRoomNumber(row.room_number);
                      return roomNumber ? (
                        <span className="pill pill-success">{roomNumber}</span>
                      ) : (
                        <span className="pill pill-warning">Unassigned</span>
                      );
                    },
                  },
                  {
                    key: "roomStatus",
                    header: "Room Status",
                    render: (row: FrontdeskBooking) => {
                      const roomNumber = normalizeRoomNumber(row.room_number);
                      const assignedRoom = roomByNumber.get(roomNumber);
                      const hk = row.housekeeping_status || assignedRoom?.hk_status || "HK pending";
                      const hkLower = String(hk).toLowerCase();
                      const cls = hkLower.includes("dirty") || hkLower.includes("out")
                        ? "pill pill-danger"
                        : hkLower.includes("clean") || hkLower.includes("inspect")
                          ? "pill pill-success"
                          : "pill pill-warning";
                      return <span className={cls}>{hk}</span>;
                    },
                  },
                  {
                    key: "readiness",
                    header: "Readiness",
                    render: (row: FrontdeskBooking) => {
                      const readiness = checkInReadiness(row);
                      return (
                        <div className="fd-ops-badge-stack">
                          {readiness.blockers.length ? <span className="pill pill-danger">Blocked</span> : <span className="pill pill-success">Ready to Check In</span>}
                          {readiness.blockers.slice(0, 2).map((blocker) => (
                            <span className="pill pill-danger" key={blocker}>{blocker}</span>
                          ))}
                          {!readiness.blockers.length && readiness.warnings.slice(0, 1).map((warning) => (
                            <span className="pill pill-warning" key={warning}>{warning}</span>
                          ))}
                        </div>
                      );
                    },
                  },
                  {
                    key: "payment",
                    header: "Payment / Authorization",
                    render: (row: FrontdeskBooking) => (
                      <div className="fd-ops-badge-stack">
                        <span className={bookingBalance(row) > 0 ? "pill pill-warning" : "pill pill-success"}>
                          {money(bookingBalance(row), row.currency || "ETB")}
                        </span>
                        <span className={manualAuthorizations[row.id] ? "pill pill-success" : "pill pill-warning"}>
                          {manualAuthorizations[row.id] ? "Authorized" : row.guarantee_status || row.payment_status || "Authorization Required"}
                        </span>
                      </div>
                    ),
                  },
                  {
                    key: "alerts",
                    header: "VIP / Alerts",
                    render: (row: FrontdeskBooking) => (
                      <div className="fd-ops-badge-stack">
                        {bookingIsVip(row) ? <span className="pill pill-warning">VIP</span> : <span className="pill pill-muted">Standard</span>}
                        {operationalBadges(row)
                          .filter((badge) => ["No Post", "Routed", "On Q"].includes(badge.label))
                          .map((badge) => (
                            <span className={badge.className} key={badge.label}>{badge.label}</span>
                          ))}
                        {row.special_requests || row.notes ? <span className="pill">Alerts</span> : null}
                      </div>
                    ),
                  },
                  {
                    key: "action",
                    header: "Actions",
                    render: (row: FrontdeskBooking) => (
                      <div className="frontdesk-action-group fd-inline-actions">
                        {canAssignRoom ? (
                          <div className="frontdesk-assign-control">
                            <input
                              value={roomInputs[row.id] || ""}
                              onChange={(event) =>
                                setRoomInputs((prev) => ({
                                  ...prev,
                                  [row.id]: event.target.value,
                                }))
                              }
                              placeholder={getSuggestedRoom(row) || "Room"}
                            />
                            <button
                              className="small-btn"
                              disabled={busyBookingId === row.id}
                              onClick={() => handleAssignRoom(row)}
                            >
                              Assign
                            </button>
                          </div>
                        ) : null}
                        <button className="small-btn" type="button" onClick={() => setSelectedFolio(row)}>
                          View
                        </button>
                        <button className="small-btn" type="button" onClick={() => window.location.assign(`/guest-profiles?guest=${encodeURIComponent(row.guest_name)}`)}>
                          Profile
                        </button>
                        <button className="small-btn" type="button" onClick={() => handleGenerateRegistrationCard(row)}>
                          Reg Card
                        </button>
                        <button className="small-btn" type="button" onClick={() => setSelectedFolio(row)}>
                          Routing/Folio
                        </button>
                        <button className="small-btn" type="button" onClick={() => handleManualAuthorization(row)}>
                          Authorize
                        </button>
                        <button className="small-btn" type="button" onClick={() => handlePlaceOnQ(row)}>
                          Place on Q
                        </button>
                        <button className="small-btn" type="button" onClick={() => handleUpsell(row, true)}>
                          Upsell
                        </button>
                        {canCheckIn ? (
                          <button
                            className="primary-btn fd-gold-action"
                            disabled={busyBookingId === row.id}
                            onClick={() => handleCheckIn(row)}
                          >
                            Check In
                          </button>
                        ) : null}
                        {!canAssignRoom && !canCheckIn ? <span className="pill pill-muted">Read Only</span> : null}
                      </div>
                    ),
                  },
                ]}
              />
              <ArrivalSupportPanels
                rows={filteredArrivals}
                cleanRooms={cleanRooms}
                qReservations={qReservations}
                authorizations={manualAuthorizations}
                upsellDecisions={upsellDecisions}
                onUpsell={handleUpsell}
              />
            </section>
          ) : null}

          {activeTab === "qReservations" ? (
            <section className="card fd-workflow-card frontdesk-q-panel">
              <SectionTitle
                icon={<Sparkles />}
                title="Q Reservations"
                subtitle="Early arrivals waiting for room readiness. Q is not check-in; it is a guest waiting state."
              />
              <DataTable
                rows={qRows}
                emptyMessage="No guests are waiting on Q."
                columns={[
                  {
                    key: "guest",
                    header: "Guest",
                    render: (row: FrontdeskBooking) => (
                      <div className="fd-guest-cell">
                        <strong>{row.guest_name}</strong>
                        <span>{row.confirmation_id || `#${row.id}`}</span>
                      </div>
                    ),
                  },
                  {
                    key: "roomType",
                    header: "Room Type Requested",
                    render: (row: FrontdeskBooking) => displayRoomType(row),
                  },
                  {
                    key: "room",
                    header: "Assigned Room",
                    render: (row: FrontdeskBooking) => normalizeRoomNumber(row.room_number) || "Unassigned",
                  },
                  {
                    key: "hk",
                    header: "Housekeeping",
                    render: (row: FrontdeskBooking) => {
                      const room = roomByNumber.get(normalizeRoomNumber(row.room_number));
                      const hk = row.housekeeping_status || room?.hk_status || "HK pending";
                      return <span className={roomReady(room) ? "pill pill-success" : roomBlocked(room) ? "pill pill-danger" : "pill pill-warning"}>{hk}</span>;
                    },
                  },
                  {
                    key: "wait",
                    header: "Waiting",
                    render: (row: FrontdeskBooking) => {
                      const q = qReservations[row.id];
                      const minutes = q ? Math.max(Math.round((Date.now() - new Date(q.startedAt).getTime()) / 60000), 0) : 0;
                      return <span className={minutes > 30 ? "pill pill-danger" : minutes > 10 ? "pill pill-warning" : "pill"}>{minutes} min</span>;
                    },
                  },
                  {
                    key: "priority",
                    header: "Priority / VIP",
                    render: (row: FrontdeskBooking) => {
                      const priority = qReservations[row.id]?.priority || "normal";
                      return (
                        <div className="fd-ops-badge-stack">
                          <span className={priority === "urgent" || priority === "vip" ? "pill pill-warning" : "pill"}>{priority}</span>
                          {bookingIsVip(row) ? <span className="pill pill-warning">VIP</span> : null}
                        </div>
                      );
                    },
                  },
                  {
                    key: "actions",
                    header: "Actions",
                    render: (row: FrontdeskBooking) => (
                      <div className="frontdesk-action-group fd-inline-actions">
                        <button className="small-btn" type="button" onClick={() => setSelectedFolio(row)}>Open Reservation</button>
                        <button className="small-btn" type="button" onClick={() => handleAssignSuggested(row)}>Assign Ready Room</button>
                        {canCheckIn ? <button className="primary-btn fd-gold-action" type="button" onClick={() => handleCheckIn(row)}>Check In</button> : null}
                        <button className="small-btn" type="button" onClick={() => handleRemoveFromQ(row)}>Remove from Q</button>
                      </div>
                    ),
                  },
                ]}
              />
            </section>
          ) : null}

          {activeTab === "departures" ? (
            <section className="card fd-workflow-card">
              <SectionTitle
                icon={<ReceiptText />}
                title="Departure Control"
                subtitle="Open folio, confirm payment, then release room to housekeeping."
              />
              <DataTable
                rows={departures}
                emptyMessage="No departures for this business date."
                columns={[
                  ...guestActionColumns,
                  {
                    key: "balance",
                    header: "Balance",
                    render: (row: FrontdeskBooking) =>
                      money(bookingBalance(row), row.currency || "ETB"),
                  },
                  {
                    key: "action",
                    header: "Action",
                    render: (row: FrontdeskBooking) => (
                      <div className="fd-inline-actions">
                        <button className="small-btn" type="button" onClick={() => setSelectedFolio(row)}>
                          Open Folio
                        </button>
                        {canAssignRoom ? (
                          <button
                            className="small-btn"
                            type="button"
                            disabled={busyBookingId === row.id}
                            onClick={() => handleRoomMove(row)}
                          >
                            Room Move
                          </button>
                        ) : null}
                        {canCheckOut ? (
                          <>
                            <button
                              className="small-btn"
                              type="button"
                              disabled={busyBookingId === row.id}
                              onClick={() => handleEarlyDeparture(row)}
                            >
                              Early Departure
                            </button>
                            <button
                              className="small-btn"
                              type="button"
                              disabled={busyBookingId === row.id}
                              onClick={() => handleLateCheckoutNote(row)}
                            >
                              Late Checkout Note
                            </button>
                          </>
                        ) : null}
                        {canCheckOut ? (
                          <button
                            className="primary-btn fd-gold-action"
                            disabled={busyBookingId === row.id}
                            onClick={() => handleCheckOut(row)}
                          >
                            Check Out
                          </button>
                        ) : null}
                      </div>
                    ),
                  },
                ]}
              />
            </section>
          ) : null}

          {activeTab === "inHouse" ? (
            <section className="card fd-workflow-card">
              <SectionTitle
                icon={<KeyRound />}
                title="Guest Stay Panel"
                subtitle="In-house guests with folio, payment, extension, and departure actions."
              />
              <DataTable
                rows={inHouse}
                emptyMessage="No in-house guests for this business date."
                columns={[
                  ...guestActionColumns,
                  {
                    key: "dates",
                    header: "Stay",
                    render: (row: FrontdeskBooking) =>
                      `${row.check_in_date} to ${row.check_out_date}`,
                  },
                  {
                    key: "action",
                    header: "Quick Actions",
                    render: (row: FrontdeskBooking) => (
                      <div className="fd-inline-actions">
                        <button className="small-btn" type="button" onClick={() => setSelectedFolio(row)}>
                          Folio
                        </button>
                        {canAssignRoom ? (
                          <button
                            className="small-btn"
                            type="button"
                            disabled={busyBookingId === row.id}
                            onClick={() => handleRoomMove(row)}
                          >
                            Room Move
                          </button>
                        ) : null}
                        {canCheckOut ? (
                          <>
                            <button className="small-btn" type="button" onClick={() => setSelectedFolio(row)}>
                              Payment
                            </button>
                            <button
                              className="small-btn"
                              type="button"
                              disabled={busyBookingId === row.id}
                              onClick={() => handleExtendStay(row)}
                            >
                              Extend Stay
                            </button>
                            <button
                              className="small-btn"
                              type="button"
                              disabled={busyBookingId === row.id}
                              onClick={() => handleEarlyDeparture(row)}
                            >
                              Early Departure
                            </button>
                            <button
                              className="small-btn"
                              type="button"
                              disabled={busyBookingId === row.id}
                              onClick={() => handleLateCheckoutNote(row)}
                            >
                              Late Checkout Note
                            </button>
                            <button
                              className="primary-btn fd-gold-action"
                              disabled={busyBookingId === row.id}
                              onClick={() => handleCheckOut(row)}
                            >
                              Check Out
                            </button>
                          </>
                        ) : null}
                      </div>
                    ),
                  },
                ]}
              />
            </section>
          ) : null}

          {activeTab === "walkIn" ? (
            <section className="card fd-workflow-card">
              <SectionTitle
                icon={<DoorOpen />}
                title="Fast Walk-In"
                subtitle="Create the guest, assign a clean room, and prepare folio from one screen."
              />
              {canCheckIn ? (
                <button
                  className="primary-btn fd-icon-btn fd-walkin-btn"
                  onClick={() => setShowWalkIn(true)}
                >
                  <DoorOpen size={15} />
                  New Walk-In
                </button>
              ) : (
                <div className="notice-box">{permissionMessage("Walk-in creation")}</div>
              )}
              {showWalkIn && canCheckIn ? (
                <WalkInForm
                  form={walkInForm}
                  setForm={setWalkInForm}
                  cleanRooms={cleanRooms}
                  submitting={walkInSubmitting}
                  onSubmit={handleCreateWalkIn}
                  onCancel={() => setShowWalkIn(false)}
                />
              ) : null}
            </section>
          ) : null}

          {activeTab === "assignment" ? (
            <section className="card fd-workflow-card frontdesk-room-assignment">
              <SectionTitle
                icon={<BedDouble />}
                title="Room Assignment / Pre-Block"
                subtitle="Pre-block arrivals, auto-assign inspected rooms, and manage room exchange before check-in."
              />
              <div className="fd-inline-actions frontdesk-panel-actions">
                <button className="primary-btn fd-gold-action" type="button" onClick={handleAutoAssignAll}>Auto Assign</button>
                <button className="small-btn" type="button" onClick={handleExchangeRooms}>Exchange Room</button>
              </div>
              <div className="frontdesk-assignment-layout">
                <div className="frontdesk-assignment-panel">
                  <h3>Unassigned Arrivals</h3>
                  <div className="fd-assignment-grid">
                    {unassignedArrivals.length ? (
                      unassignedArrivals.map((row) => (
                        <div className="fd-assignment-card" key={row.id}>
                          <div>
                            <strong>{row.guest_name}</strong>
                            <span>{displayRoomType(row)} | {row.confirmation_id || `#${row.id}`}</span>
                          </div>
                          <span className="fd-suggested-room">
                            Suggested {getSuggestedRoom(row) || "TBD"}
                          </span>
                          {row.special_requests || row.notes ? <span className="pill pill-warning">Guest preference / alert</span> : null}
                          {canAssignRoom ? (
                            <div className="fd-inline-actions">
                              <button
                                className="primary-btn"
                                disabled={busyBookingId === row.id || !getSuggestedRoom(row)}
                                onClick={() => handleAssignSuggested(row)}
                              >
                                Assign Room
                              </button>
                              <button className="small-btn" type="button" onClick={() => handlePlaceOnQ(row)}>
                                Place on Q
                              </button>
                            </div>
                          ) : (
                            <span className="pill pill-muted">Read Only</span>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="muted">All expected check-ins have room assignments.</div>
                    )}
                  </div>
                </div>
                <div className="frontdesk-assignment-panel">
                  <h3>Assigned Arrivals</h3>
                  <div className="frontdesk-room-candidate-list">
                    {assignedArrivals.slice(0, 10).map((row) => (
                      <div className="frontdesk-room-candidate" key={`assigned-${row.id}`}>
                        <div>
                          <strong>{row.guest_name}</strong>
                          <span>{row.room_number} | {displayRoomType(row)}</span>
                        </div>
                        <div className="fd-inline-actions">
                          <button className="small-btn" type="button" onClick={() => handleUnassignRoom(row)}>
                            Unassign
                          </button>
                          <button className="small-btn" type="button" onClick={() => handlePlaceOnQ(row)}>
                            Q
                          </button>
                        </div>
                      </div>
                    ))}
                    {!assignedArrivals.length ? <p className="muted">No assigned arrivals in the current business date.</p> : null}
                  </div>
                </div>
                <div className="frontdesk-assignment-panel frontdesk-assignment-wide">
                  <h3>Available Room Candidates</h3>
                  <RoomCandidateFilters
                    filters={roomCandidateFilters}
                    setFilters={setRoomCandidateFilters}
                    roomTypes={Array.from(new Set(rooms.map((room) => room.room_type || "Room"))).sort()}
                    floors={Array.from(new Set(rooms.map((room) => String(room.floor)))).sort((a, b) => Number(a) - Number(b))}
                  />
                  <div className="frontdesk-room-candidate-list">
                    {roomCandidates.slice(0, 16).map((room) => (
                      <div className="frontdesk-room-candidate" key={`candidate-${room.room_number}`}>
                        <div>
                          <strong>{room.room_number}</strong>
                          <span>{room.room_type || "Room"} | Floor {room.floor}</span>
                          <small>{room.is_occupied ? "Occupied / pre-blocked" : "Available"} {room.out_of_order_reason ? `| ${room.out_of_order_reason}` : ""}</small>
                        </div>
                        <span className={roomReady(room) ? "pill pill-success" : roomBlocked(room) ? "pill pill-danger" : "pill pill-warning"}>
                          {room.hk_status}
                        </span>
                      </div>
                    ))}
                    {!roomCandidates.length ? <p className="muted">No rooms match the selected candidate filters.</p> : null}
                  </div>
                </div>
              </div>
            </section>
          ) : null}

          {activeTab === "roomPlan" ? (
            <section className="card fd-workflow-card frontdesk-room-plan">
              <SectionTitle
                icon={<BedDouble />}
                title="Room Plan"
                subtitle="Planning table by room, date, assignment, VIP indicator, and room readiness."
              />
              <RoomPlan rows={rows} rooms={rooms} businessDate={businessDate} roomByNumber={roomByNumber} />
            </section>
          ) : null}

          {activeTab === "floorPlan" ? (
            <section className="card fd-workflow-card frontdesk-floor-plan">
              <SectionTitle
                icon={<BedDouble />}
                title="Floor Plan"
                subtitle="Simplified floor view for room readiness, pre-blocking, in-house status, and arrival attention."
              />
              <FloorPlan
                rooms={rooms}
                rows={rows}
                businessDate={businessDate}
                qReservations={qReservations}
                onAssign={(booking, room) => assignSpecificRoom(booking, room.room_number)}
                onCheckIn={handleCheckIn}
              />
            </section>
          ) : null}

          {activeTab === "registration" ? (
            <section className="card fd-workflow-card frontdesk-registration-cards">
              <SectionTitle
                icon={<ClipboardList />}
                title="Registration Card Workflow"
                subtitle="Generate single or batch registration-card previews for arrivals."
              />
              <div className="frontdesk-registration-tools">
                <div>
                  <span>Selected arrival date</span>
                  <strong>{arrivalFilters.arrivalDate || businessDate}</strong>
                </div>
                <div>
                  <span>Current filter</span>
                  <strong>
                    {arrivalFilters.vip !== "all" ? arrivalFilters.vip : "All arrivals"} |{" "}
                    {arrivalFilters.assignment !== "all" ? arrivalFilters.assignment : "assigned and unassigned"}
                  </strong>
                </div>
                <div>
                  <span>Preview type</span>
                  <strong>HTML print-ready preview</strong>
                </div>
              </div>
              <div className="fd-inline-actions frontdesk-panel-actions">
                <button className="primary-btn fd-gold-action" type="button" onClick={handleBatchRegistrationCards}>
                  Batch Generate Selected Arrivals
                </button>
              </div>
              <DataTable
                rows={filteredArrivals}
                emptyMessage="No arrival registration cards for the current filter."
                columns={[
                  ...guestActionColumns,
                  {
                    key: "generated",
                    header: "Generated",
                    render: (row: FrontdeskBooking) => registrationGenerated[row.id] ? new Date(registrationGenerated[row.id]).toLocaleString() : "Pending",
                  },
                  {
                    key: "card",
                    header: "Card",
                    render: (row: FrontdeskBooking) => (
                      <button className="small-btn" type="button" onClick={() => handleGenerateRegistrationCard(row)}>
                        Print/View Reg Card
                      </button>
                    ),
                  },
                ]}
              />
            </section>
          ) : null}

          {activeTab === "reports" ? (
            <section className="card fd-workflow-card">
              <SectionTitle
                icon={<ClipboardList />}
                title="Front Desk Reports"
                subtitle="Export-ready operating views for arrivals, Q, assignments, house status, and room readiness."
              />
              <FrontDeskReports
                arrivals={filteredArrivals}
                qRows={qRows}
                inHouse={inHouse}
                rooms={rooms}
                unassignedArrivals={unassignedArrivals}
                dirtyRooms={dirtyRooms}
                cleanRooms={cleanRooms}
                inspectedRooms={inspectedRooms}
                outOfOrderRooms={outOfOrderRooms}
                walkIns={walkIns}
                noShows={noShows}
              />
            </section>
          ) : null}

          {activeTab === "exceptions" ? (
            <section className="card fd-workflow-card">
              <SectionTitle
                icon={<AlertTriangle />}
                title="Operational Exceptions"
                subtitle="Items that need human confirmation or department follow-up."
              />
              <div className="fd-exception-grid">
                <ExceptionList title="Unassigned Arrivals" rows={unassignedArrivals} />
                <ExceptionList title="Arrival Rooms Not Ready" rows={roomNotReadyArrivals} />
                <ExceptionList title="In-House Room Status Review" rows={inHouseRoomStatusExceptions} />
                <ExceptionList title="Balance Review" rows={balanceReview} />
                <ExceptionList title="No-Shows" rows={noShows} />
              </div>
            </section>
          ) : null}

          <section className="card fd-workflow-card fd-shift-handover-card">
            <SectionTitle
              icon={<ClipboardList />}
              title="Shift Handover"
              subtitle="Summary for the next agent or manager review."
            />
            <div className="shift-grid">
              <div className="shift-card">
                <span>Remaining arrivals</span>
                <strong>{expectedCheckIns.length}</strong>
              </div>
              <div className="shift-card">
                <span>Departures not checked out</span>
                <strong>
                  {
                    departures.filter(
                      (row) => String(row.booking_status).toLowerCase() !== "checked_out"
                    ).length
                  }
                </strong>
              </div>
              <div className="shift-card">
                <span>Dirty rooms</span>
                <strong>{dirtyRooms.length}</strong>
              </div>
              <div className="shift-card">
                <span>Manual follow-up</span>
                <strong>{attentionItems.reduce((sum, item) => sum + item.value, 0)}</strong>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function FolioReceiptModal({
  row,
  businessDate,
  propertyCode,
  roomType,
  onClose,
}: {
  row: FrontdeskBooking;
  businessDate: string;
  propertyCode: string;
  roomType: string;
  onClose: () => void;
}) {
  const fallbackReceipt = folioReceipt(row, businessDate);
  const [receipt, setReceipt] = useState<FolioReceipt | null>(null);
  const [receiptError, setReceiptError] = useState("");
  const [postingQuote, setPostingQuote] = useState(false);
  const [postingMessage, setPostingMessage] = useState("");

  async function loadReceipt() {
    setReceiptError("");
    const result = await fetchFolioReceipt(propertyCode, row.id);
    setReceipt(result);
    return result;
  }

  useEffect(() => {
    let cancelled = false;
    setReceiptError("");
    fetchFolioReceipt(propertyCode, row.id)
      .then((result) => {
        if (!cancelled) setReceipt(result);
      })
      .catch((error) => {
        if (!cancelled) {
          setReceiptError(error instanceof Error ? error.message : "Unable to load folio receipt.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [propertyCode, row.id]);

  const currency = receipt?.currency || row.currency || "ETB";
  const lineItems = receipt?.line_items || [];
  const hasPostedFolioActivity = lineItems.length > 0 || Number(receipt?.total_charges || 0) > 0 || Number(receipt?.total_payments || 0) > 0;
  const displayRoomSubtotal = hasPostedFolioActivity
    ? Number(receipt?.room_charge_subtotal || 0)
    : fallbackReceipt.roomSubtotal;
  const displayFnbOther = hasPostedFolioActivity ? Number(receipt?.fnb_other_charge_subtotal || 0) : 0;
  const displayServiceCharge = hasPostedFolioActivity ? Number(receipt?.service_charge_amount || 0) : 0;
  const displayVatTax = hasPostedFolioActivity ? Number(receipt?.vat_tax_amount || 0) : 0;
  const displayTotalCharges = hasPostedFolioActivity
    ? Number(receipt?.total_charges || 0)
    : fallbackReceipt.postedCharges;
  const displayPayments = hasPostedFolioActivity
    ? Number(receipt?.total_payments || 0)
    : fallbackReceipt.paidNow + fallbackReceipt.downpayment;
  const displayBalance = hasPostedFolioActivity
    ? Number(receipt?.balance || 0)
    : fallbackReceipt.dueNow;
  const canPostQuoteCharges =
    !hasPostedFolioActivity &&
    fallbackReceipt.postedCharges > 0 &&
    roleCan("finance.post_charge") &&
    !postingQuote;
  const foreignPayments =
    receipt?.payments?.filter((payment) => payment.base_amount != null && payment.original_currency !== payment.base_currency) || [];

  async function handlePostQuoteCharges() {
    const confirmed = window.confirm(
      "This will create official folio transactions for this guest."
    );
    if (!confirmed) return;
    try {
      setPostingQuote(true);
      setPostingMessage("");
      setReceiptError("");
      const result = await postQuoteChargesToFolio({
        property_code: propertyCode,
        booking_id: row.id,
        business_date: businessDate,
        room_charge_amount: fallbackReceipt.roomSubtotal,
        currency,
      });
      await loadReceipt();
      setPostingMessage(
        `Posted room ${result.currency} ${result.room_charge.toFixed(2)}, service ${result.currency} ${result.service_charge.toFixed(2)}, tax ${result.currency} ${result.tax.toFixed(2)}.`
      );
    } catch (error) {
      setReceiptError(getErrorMessage(error));
    } finally {
      setPostingQuote(false);
    }
  }

  return (
    <div className="fd-folio-overlay">
      <section className="fd-folio-receipt" id={`folio-receipt-${row.id}`}>
        <div className="fd-folio-toolbar">
          <button className="small-btn" type="button" onClick={onClose}>
            Close
          </button>
          <button className="primary-btn fd-gold-action" type="button" onClick={() => window.print()}>
            Print Receipt
          </button>
        </div>
        <div className="fd-folio-header">
          <div>
            <div className="eyebrow">Guzo PMS Guest Folio</div>
            <h2>Dream Big Hotel</h2>
            <span>{propertyCode} | Business Date {businessDate}</span>
          </div>
          <div>
            <strong>Booking #{row.id}</strong>
            <span>{row.confirmation_id || "Confirmation pending"}</span>
          </div>
        </div>

        <div className="fd-folio-guest-grid">
          <div><span>Guest</span><strong>{row.guest_name}</strong></div>
          <div><span>Room</span><strong>{row.room_number || "Unassigned"}</strong></div>
          <div><span>Room Type</span><strong>{roomType}</strong></div>
          <div><span>Status</span><strong>{row.booking_status}</strong></div>
          <div><span>Arrival</span><strong>{row.check_in_date}</strong></div>
          <div><span>Departure</span><strong>{row.check_out_date}</strong></div>
        </div>

        <div className="fd-folio-lines">
          <span>Nights Stayed / Reserved</span>
          <strong>{fallbackReceipt.nights}</strong>
          <span>Rate per Night</span>
          <strong>{money(fallbackReceipt.rate, currency)}</strong>
          <span>Room subtotal</span>
          <strong>{money(displayRoomSubtotal, currency)}</strong>
          <span>F&B / other subtotal</span>
          <strong>{money(displayFnbOther, currency)}</strong>
          <span>Service charge</span>
          <strong>
            {money(displayServiceCharge, currency)}
            {receipt?.service_charge_percent != null ? ` (${Number(receipt.service_charge_percent) * 100}%)` : ""}
          </strong>
          <span>VAT / tax</span>
          <strong>
            {money(displayVatTax, currency)}
            {receipt?.tax_percent != null ? ` (${Number(receipt.tax_percent) * 100}%)` : ""}
          </strong>
          <span>Total charges</span>
          <strong>{money(displayTotalCharges, currency)}</strong>
          <span>Payments</span>
          <strong>{money(displayPayments, currency)}</strong>
          <span>Balance due</span>
          <strong>{money(displayBalance, currency)}</strong>
        </div>

        {!hasPostedFolioActivity || receipt?.tax_service_posted === false || receiptError ? (
          <div className="notice-box" style={{ marginTop: "14px" }}>
            {!hasPostedFolioActivity
              ? "No posted folio transactions yet. Showing reservation quote values until charges, tax, service, and payments are posted."
              : receipt?.tax_service_warning || receiptError || "Tax/service not posted."}
          </div>
        ) : null}

        {canPostQuoteCharges ? (
          <div className="fd-folio-total">
            <span>Make quote official</span>
            <button
              className="primary-btn fd-gold-action"
              type="button"
              onClick={handlePostQuoteCharges}
            >
              Post Room Charge + Tax/Service
            </button>
          </div>
        ) : null}

        {postingMessage ? (
          <div className="notice-box" style={{ marginTop: "14px" }}>{postingMessage}</div>
        ) : null}

        {foreignPayments.length ? (
          <div className="fd-folio-total">
            <span>Foreign currency paid</span>
            <strong>
              {foreignPayments
                .map((payment) =>
                  `${payment.original_currency} ${Number(payment.original_amount || 0).toFixed(2)} @ ${payment.exchange_rate_to_base} = ${payment.base_currency} ${Number(payment.base_amount || 0).toFixed(2)}`
                )
                .join("; ")}
            </strong>
          </div>
        ) : null}

        {lineItems.length ? (
          <div className="fd-folio-line-items">
            <strong>Line items</strong>
            <table className="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Category</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((item: any) => (
                  <tr key={item.id}>
                    <td data-label="Date">{item.date || "-"}</td>
                    <td data-label="Description">{item.description || "-"}</td>
                    <td data-label="Category">{item.category || item.txn_type || "-"}</td>
                    <td data-label="Amount">{money(item.amount, item.currency || currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        <div className="fd-folio-footer">
          <span>Front Desk Cycle: verify identity, review stay, settle folio, check out, release room to housekeeping.</span>
          <span>Printed receipt is system-generated and based on booking id #{row.id}.</span>
        </div>
      </section>
    </div>
  );
}

function RegistrationCardModal({
  row,
  businessDate,
  propertyCode,
  roomType,
  authorization,
  generatedAt,
  onClose,
}: {
  row: FrontdeskBooking;
  businessDate: string;
  propertyCode: string;
  roomType: string;
  authorization?: ManualAuthorizationState;
  generatedAt?: string;
  onClose: () => void;
}) {
  const currency = row.currency || "ETB";
  const stayNights = countNights(row.check_in_date, row.check_out_date);

  return (
    <div className="fd-folio-overlay">
      <section className="fd-folio-receipt fd-registration-card">
        <div className="fd-folio-toolbar">
          <button className="small-btn" type="button" onClick={onClose}>
            Close
          </button>
          <button className="primary-btn fd-gold-action" type="button" onClick={() => window.print()}>
            Print Registration Card
          </button>
        </div>
        <div className="fd-folio-header">
          <div>
            <div className="eyebrow">Guzo PMS Registration Card</div>
            <h2>Dream Big Hotel</h2>
            <span>{propertyCode} | Business Date {businessDate}</span>
          </div>
          <div>
            <strong>Booking #{row.id}</strong>
            <span>{generatedAt ? new Date(generatedAt).toLocaleString() : "Generated now"}</span>
          </div>
        </div>

        <div className="fd-folio-guest-grid">
          <div><span>Guest Name</span><strong>{row.guest_name}</strong></div>
          <div><span>Confirmation</span><strong>{row.confirmation_id || "Pending"}</strong></div>
          <div><span>Room</span><strong>{row.room_number || "To be assigned"}</strong></div>
          <div><span>Room Type</span><strong>{roomType}</strong></div>
          <div><span>Arrival</span><strong>{row.check_in_date}</strong></div>
          <div><span>Departure</span><strong>{row.check_out_date}</strong></div>
          <div><span>Nights</span><strong>{stayNights}</strong></div>
          <div><span>Status</span><strong>{row.booking_status}</strong></div>
        </div>

        <div className="fd-folio-lines">
          <span>Rate / Total</span>
          <strong>{money(Number(row.rate_per_night_etb || row.total_amount || 0), currency)}</strong>
          <span>Payment Method</span>
          <strong>{row.payment_method || "Review at desk"}</strong>
          <span>Guarantee Status</span>
          <strong>{row.guarantee_status || row.payment_status || "Pending review"}</strong>
          <span>Manual Authorization</span>
          <strong>
            {authorization
              ? `${money(authorization.amount, currency)} | ${authorization.code}`
              : "Not recorded"}
          </strong>
          <span>Guest Notes</span>
          <strong>{row.special_requests || row.notes || "No special request recorded"}</strong>
        </div>

        <div className="fd-registration-signature">
          <div>
            <span>Guest Signature</span>
            <strong />
          </div>
          <div>
            <span>Front Desk Agent</span>
            <strong />
          </div>
          <div>
            <span>Date / Time</span>
            <strong>{new Date().toLocaleString()}</strong>
          </div>
        </div>

        <div className="fd-folio-footer">
          <span>Guest confirms the stay dates, room/rate information, identification review, and hotel house rules.</span>
          <span>Registration cards are generated from live reservation data and should be filed according to property policy.</span>
        </div>
      </section>
    </div>
  );
}

function ArrivalFilters({
  filters,
  setFilters,
  roomTypes,
}: {
  filters: ArrivalFilterState;
  setFilters: Dispatch<SetStateAction<ArrivalFilterState>>;
  roomTypes: string[];
}) {
  function update(field: keyof ArrivalFilterState, value: string) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  return (
    <div className="fd-filter-grid">
      <label>
        Arrival Date
        <input
          type="date"
          value={filters.arrivalDate}
          onChange={(event) => update("arrivalDate", event.target.value)}
        />
      </label>
      <label>
        Search Guest / Confirmation
        <input
          value={filters.search}
          onChange={(event) => update("search", event.target.value)}
          placeholder="Guest, room, channel, note"
        />
      </label>
      <label>
        Room Type
        <select value={filters.roomType} onChange={(event) => update("roomType", event.target.value)}>
          <option value="">All room types</option>
          {roomTypes.map((roomType) => (
            <option key={roomType} value={roomType}>
              {roomType}
            </option>
          ))}
        </select>
      </label>
      <label>
        Room Number
        <input
          value={filters.roomNumber}
          onChange={(event) => update("roomNumber", event.target.value)}
          placeholder="101"
        />
      </label>
      <label>
        Guest Priority
        <select value={filters.vip} onChange={(event) => update("vip", event.target.value)}>
          <option value="all">All guests</option>
          <option value="vip">VIP only</option>
          <option value="non_vip">Non-VIP</option>
        </select>
      </label>
      <label>
        Group / Block
        <input
          value={filters.groupBlock}
          onChange={(event) => update("groupBlock", event.target.value)}
          placeholder="Group, block, company"
        />
      </label>
      <label>
        Assignment
        <select value={filters.assignment} onChange={(event) => update("assignment", event.target.value)}>
          <option value="all">All assignments</option>
          <option value="assigned">Assigned</option>
          <option value="unassigned">Unassigned</option>
        </select>
      </label>
      <label>
        Readiness
        <select value={filters.readiness} onChange={(event) => update("readiness", event.target.value)}>
          <option value="all">All readiness</option>
          <option value="ready">Ready to Check In</option>
          <option value="blocked">Blocked / issue</option>
          <option value="room">Room readiness issue</option>
          <option value="payment">Payment / authorization issue</option>
        </select>
      </label>
      <label>
        Status
        <input
          value={filters.status}
          onChange={(event) => update("status", event.target.value)}
          placeholder="confirmed"
        />
      </label>
      <label>
        Payment
        <input
          value={filters.payment}
          onChange={(event) => update("payment", event.target.value)}
          placeholder="deposit, card, paid"
        />
      </label>
    </div>
  );
}

function RoomCandidateFilters({
  filters,
  setFilters,
  roomTypes,
  floors,
}: {
  filters: RoomCandidateFilterState;
  setFilters: Dispatch<SetStateAction<RoomCandidateFilterState>>;
  roomTypes: string[];
  floors: string[];
}) {
  function update(field: keyof RoomCandidateFilterState, value: string) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  return (
    <div className="frontdesk-room-candidate-filters">
      <label>
        Search Room
        <input
          value={filters.search}
          onChange={(event) => update("search", event.target.value)}
          placeholder="Room, feature, note"
        />
      </label>
      <label>
        Room Type
        <select value={filters.roomType} onChange={(event) => update("roomType", event.target.value)}>
          <option value="">All room types</option>
          {roomTypes.map((roomType) => (
            <option key={roomType} value={roomType}>{roomType}</option>
          ))}
        </select>
      </label>
      <label>
        Floor
        <select value={filters.floor} onChange={(event) => update("floor", event.target.value)}>
          <option value="">All floors</option>
          {floors.map((floor) => (
            <option key={floor} value={floor}>Floor {floor}</option>
          ))}
        </select>
      </label>
      <label>
        Status
        <select value={filters.housekeeping} onChange={(event) => update("housekeeping", event.target.value)}>
          <option value="ready">Clean / inspected</option>
          <option value="all">All rooms</option>
          <option value="dirty">Dirty</option>
          <option value="blocked">OOO / OOS</option>
          <option value="occupied">Occupied / pre-blocked</option>
        </select>
      </label>
    </div>
  );
}

function ArrivalSupportPanels({
  rows,
  cleanRooms,
  qReservations,
  authorizations,
  upsellDecisions,
  onUpsell,
}: {
  rows: FrontdeskBooking[];
  cleanRooms: RoomStatusItem[];
  qReservations: Record<number, QReservationState>;
  authorizations: Record<number, ManualAuthorizationState>;
  upsellDecisions: Record<number, "accepted" | "declined">;
  onUpsell: (row: FrontdeskBooking, accepted: boolean) => void;
}) {
  const authorizationRequired = rows.filter((row) => !authorizations[row.id] && bookingBalance(row) > 0);
  const routedOrNoPost = rows.filter((row) =>
    String(row.notes || row.special_requests || row.payment_method || "")
      .toLowerCase()
      .match(/route|no post|cash|company/)
  );
  const vipRows = rows.filter(bookingIsVip);

  return (
    <div className="fd-support-grid">
      <div className="fd-support-card">
        <h3>Credit Authorization</h3>
        <strong>{authorizationRequired.length}</strong>
        <span>arrival(s) need card, cash, or offline approval before check-in.</span>
      </div>
      <div className="fd-support-card">
        <h3>Routing / No Post</h3>
        <strong>{routedOrNoPost.length}</strong>
        <span>folio routing, company billing, or no-post notes need front desk review.</span>
      </div>
      <div className="fd-support-card">
        <h3>Room Key Readiness</h3>
        <strong>{cleanRooms.length}</strong>
        <span>clean or inspected rooms available for key cutting and check-in.</span>
      </div>
      <div className="fd-support-card">
        <h3>Q / VIP Attention</h3>
        <strong>{Object.keys(qReservations).length + vipRows.length}</strong>
        <span>waiting or VIP guests should be prioritized with housekeeping.</span>
      </div>
      <div className="fd-support-card fd-support-wide">
        <h3>Upsell at Check-In</h3>
        <div className="fd-upsell-list">
          {rows.slice(0, 5).map((row) => (
            <div className="fd-upsell-row" key={`upsell-${row.id}`}>
              <div>
                <strong>{row.guest_name}</strong>
                <span>{row.room_type || "Standard Room"} to Deluxe / Suite candidate</span>
              </div>
              <span className="pill">{upsellDecisions[row.id] || "Offer ETB 1,200/night"}</span>
              <button className="small-btn" type="button" onClick={() => onUpsell(row, true)}>
                Accept
              </button>
              <button className="small-btn" type="button" onClick={() => onUpsell(row, false)}>
                Decline
              </button>
            </div>
          ))}
          {!rows.length ? <p className="muted">No arrivals in the current filter.</p> : null}
        </div>
      </div>
    </div>
  );
}

function RoomPlan({
  rows,
  rooms,
  businessDate,
  roomByNumber,
}: {
  rows: FrontdeskBooking[];
  rooms: RoomStatusItem[];
  businessDate: string;
  roomByNumber: Map<string, RoomStatusItem>;
}) {
  const planRows = rooms
    .slice()
    .sort((a, b) =>
      normalizeRoomNumber(a.room_number).localeCompare(normalizeRoomNumber(b.room_number), undefined, {
        numeric: true,
      })
    )
    .map((room) => {
      const assigned = rows.find((row) => normalizeRoomNumber(row.room_number) === normalizeRoomNumber(room.room_number));
      const arrival = rows.find(
        (row) =>
          row.check_in_date === businessDate &&
          normalizeRoomNumber(row.room_number) === normalizeRoomNumber(room.room_number)
      );
      return { room, assigned, arrival };
    });

  return (
    <div className="fd-room-plan-grid">
      <table className="table">
        <thead>
          <tr>
            <th>Room</th>
            <th>Type</th>
            <th>Floor</th>
            <th>Housekeeping</th>
            <th>Guest / Assignment</th>
            <th>VIP</th>
            <th>Stay</th>
            <th>Readiness</th>
          </tr>
        </thead>
        <tbody>
          {planRows.map(({ room, assigned, arrival }) => {
            const roomRecord = roomByNumber.get(normalizeRoomNumber(room.room_number));
            return (
              <tr key={`room-plan-${room.room_number}`}>
                <td data-label="Room">{room.room_number}</td>
                <td data-label="Type">{room.room_type || assigned?.room_type || "Standard Room"}</td>
                <td data-label="Floor">{room.floor}</td>
                <td data-label="Housekeeping"><span className={statusClass(room.hk_status)}>{room.hk_status}</span></td>
                <td data-label="Guest">{assigned?.guest_name || "Available"}</td>
                <td data-label="VIP">{assigned && bookingIsVip(assigned) ? "VIP" : "-"}</td>
                <td data-label="Stay">{assigned ? `${assigned.check_in_date} to ${assigned.check_out_date}` : "-"}</td>
                <td data-label="Readiness">
                  <span className={roomReady(roomRecord) ? "pill pill-success" : roomBlocked(roomRecord) ? "pill pill-danger" : "pill pill-warning"}>
                    {arrival ? "Arrival Room" : roomReady(roomRecord) ? "Ready" : "Review"}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function FloorPlan({
  rooms,
  rows,
  businessDate,
  qReservations,
  onAssign,
  onCheckIn,
}: {
  rooms: RoomStatusItem[];
  rows: FrontdeskBooking[];
  businessDate: string;
  qReservations: Record<number, QReservationState>;
  onAssign: (booking: FrontdeskBooking, room: RoomStatusItem) => void | Promise<void>;
  onCheckIn: (booking: FrontdeskBooking) => void | Promise<void>;
}) {
  const floors = Array.from(new Set(rooms.map((room) => room.floor))).sort((a, b) => a - b);
  const unassignedArrivals = rows.filter(
    (row) => row.check_in_date === businessDate && !normalizeRoomNumber(row.room_number)
  );

  return (
    <div className="fd-floor-plan">
      {floors.map((floor) => {
        const floorRooms = rooms
          .filter((room) => room.floor === floor)
          .sort((a, b) =>
            normalizeRoomNumber(a.room_number).localeCompare(normalizeRoomNumber(b.room_number), undefined, {
              numeric: true,
            })
          );
        return (
          <section className="fd-floor-section" key={`floor-${floor}`}>
            <h3>Floor {floor}</h3>
            <div className="fd-floor-grid">
              {floorRooms.map((room) => {
                const assigned = rows.find((row) => normalizeRoomNumber(row.room_number) === normalizeRoomNumber(room.room_number));
                const waiting = assigned ? qReservations[assigned.id] : undefined;
                const suggestedArrival = !assigned && roomReady(room) ? unassignedArrivals[0] : undefined;
                return (
                  <div
                    className={`fd-floor-room ${roomReady(room) ? "ready" : roomBlocked(room) ? "blocked" : "review"}`}
                    key={`floor-room-${room.room_number}`}
                  >
                    <div>
                      <strong>{room.room_number}</strong>
                      <span>{room.room_type || "Room"}</span>
                    </div>
                    <span>{room.hk_status}</span>
                    <small>{assigned?.guest_name || (suggestedArrival ? `Suggest ${suggestedArrival.guest_name}` : "Available")}</small>
                    {waiting ? <span className="pill pill-warning">On Q</span> : null}
                    <div className="fd-inline-actions">
                      {suggestedArrival ? (
                        <button className="small-btn" type="button" onClick={() => onAssign(suggestedArrival, room)}>
                          Assign
                        </button>
                      ) : null}
                      {assigned && assigned.check_in_date === businessDate ? (
                        <button className="small-btn" type="button" onClick={() => onCheckIn(assigned)}>
                          Check In
                        </button>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function FrontDeskReports({
  arrivals,
  qRows,
  inHouse,
  rooms,
  unassignedArrivals,
  dirtyRooms,
  cleanRooms,
  inspectedRooms,
  outOfOrderRooms,
  walkIns,
  noShows,
}: {
  arrivals: FrontdeskBooking[];
  qRows: FrontdeskBooking[];
  inHouse: FrontdeskBooking[];
  rooms: RoomStatusItem[];
  unassignedArrivals: FrontdeskBooking[];
  dirtyRooms: RoomStatusItem[];
  cleanRooms: RoomStatusItem[];
  inspectedRooms: RoomStatusItem[];
  outOfOrderRooms: RoomStatusItem[];
  walkIns: FrontdeskBooking[];
  noShows: FrontdeskBooking[];
}) {
  const reportGroups = [
    {
      group: "Arrival Reports",
      items: [
        { title: "Arrival List", value: arrivals.length, detail: "Expected arrivals and filtered check-in worklist" },
        { title: "VIP Arrivals", value: arrivals.filter(bookingIsVip).length, detail: "Guests needing manager/front office attention" },
        { title: "Unassigned Arrivals", value: unassignedArrivals.length, detail: "Rooms must be assigned before check-in" },
        { title: "Walk-In Report", value: walkIns.length, detail: "Direct desk bookings" },
      ],
    },
    {
      group: "Room Status Reports",
      items: [
        { title: "Room Status", value: rooms.length, detail: "Total physical room board" },
        { title: "Dirty Rooms", value: dirtyRooms.length, detail: "Housekeeping priority list" },
        { title: "Clean / Inspected", value: cleanRooms.length + inspectedRooms.length, detail: "Ready-room supply" },
        { title: "Out of Order", value: outOfOrderRooms.length, detail: "Non-sellable rooms" },
      ],
    },
    {
      group: "In-House Reports",
      items: [
        { title: "In-House List", value: inHouse.length, detail: "Current guest stay panel" },
      ],
    },
    {
      group: "Queue Reports",
      items: [
        { title: "Q Reservations", value: qRows.length, detail: "Waiting guests not yet checked in" },
      ],
    },
    {
      group: "Exception Reports",
      items: [
        { title: "No-Show Report", value: noShows.length, detail: "Reservations requiring follow-up" },
      ],
    },
  ];

  return (
    <div className="frontdesk-report-launcher">
      {reportGroups.map((group) => (
        <section className="frontdesk-report-group" key={group.group}>
          <h3>{group.group}</h3>
          <div className="fd-report-grid">
            {group.items.map((card) => (
              <div className="fd-report-card" key={card.title}>
                <span>{card.title}</span>
                <strong>{card.value}</strong>
                <small>{card.detail}</small>
                <button className="small-btn" type="button">
                  Preview
                </button>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function SectionTitle({
  icon,
  title,
  subtitle,
}: {
  icon: ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="section-heading fd-section-heading">
      <div>
        <div className="fd-title-row">
          <span>{icon}</span>
          <h2>{title}</h2>
        </div>
        <p className="muted">{subtitle}</p>
      </div>
    </div>
  );
}

function RoomStack({ title, rooms }: { title: string; rooms: RoomStatusItem[] }) {
  return (
    <div className="fd-room-stack">
      <span>{title}</span>
      <div>
        {rooms.length ? (
          rooms.map((room) => (
            <span className="fd-room-chip" key={room.room_number}>
              {room.room_number}
            </span>
          ))
        ) : (
          <span className="muted">None</span>
        )}
      </div>
    </div>
  );
}

function ExceptionList({
  title,
  rows,
}: {
  title: string;
  rows: FrontdeskBooking[];
}) {
  return (
    <div className="fd-exception-list">
      <h3>{title}</h3>
      {rows.length ? (
        rows.slice(0, 6).map((row) => (
          <div className="fd-exception-row" key={`${title}-${row.id}`}>
            <div>
              <strong>{row.guest_name}</strong>
              <span>#{row.id}</span>
            </div>
            <span className={statusClass(row.booking_status)}>{row.booking_status}</span>
          </div>
        ))
      ) : (
        <p className="muted">No exceptions.</p>
      )}
    </div>
  );
}

function WalkInForm({
  form,
  setForm,
  cleanRooms,
  submitting,
  onSubmit,
  onCancel,
}: {
  form: WalkInFormState;
  setForm: Dispatch<SetStateAction<WalkInFormState>>;
  cleanRooms: RoomStatusItem[];
  submitting: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
}) {
  const receipt = walkInReceiptTotals(form);
  const currency = form.currency || "ETB";

  return (
    <form className="fd-walkin-form" onSubmit={onSubmit}>
      <div className="fd-form-section span-3">
        <h3>Guest Profile</h3>
        <div className="fd-form-grid">
          <label>
            Guest Name
            <input
              value={form.guestName}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, guestName: event.target.value }))
              }
              placeholder="Guest full name"
              required
            />
          </label>
          <label>
            Adults
            <input
              inputMode="numeric"
              value={form.adults}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, adults: event.target.value }))
              }
            />
          </label>
          <label>
            Children Under 18
            <input
              inputMode="numeric"
              value={form.children}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, children: event.target.value }))
              }
            />
          </label>
          <label>
            Passport / ID
            <select
              value={form.documentType}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, documentType: event.target.value }))
              }
            >
              <option>Passport</option>
              <option>National ID</option>
              <option>Driver License</option>
              <option>Residence ID</option>
            </select>
          </label>
          <label>
            Document Number
            <input
              value={form.documentNumber}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, documentNumber: event.target.value }))
              }
              placeholder="Passport or ID number"
            />
          </label>
          <label>
            Email
            <input
              type="email"
              value={form.email}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, email: event.target.value }))
              }
              placeholder="guest@email.com"
            />
          </label>
          <label>
            Phone Number
            <input
              value={form.phone}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, phone: event.target.value }))
              }
              placeholder="+251..."
            />
          </label>
          <label>
            Purpose of Visit
            <select
              value={form.purposeOfVisit}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, purposeOfVisit: event.target.value }))
              }
            >
              {purposeOptions.map((purpose) => (
                <option key={purpose}>{purpose}</option>
              ))}
            </select>
          </label>
          <label className="fd-toggle-field">
            <input
              type="checkbox"
              checked={form.isVip}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, isVip: event.target.checked }))
              }
            />
            VIP Guest
          </label>
        </div>
      </div>

      <div className="fd-form-section span-3">
        <h3>Stay Details</h3>
        <div className="fd-form-grid">
          <label>
            Room Number
            <input
              list="walkin-clean-room-options"
              value={form.roomNumber}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, roomNumber: event.target.value }))
              }
              placeholder="Leave blank for auto suggestion or enter manually"
            />
            <datalist id="walkin-clean-room-options">
              {cleanRooms.map((room) => (
                <option key={room.room_number} value={room.room_number}>
                  {room.room_number} - clean / inspected
                </option>
              ))}
            </datalist>
          </label>
          <label>
            Room Type
            <select
              value={form.roomType}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, roomType: event.target.value }))
              }
            >
              {hotelRoomTypes.map((roomType) => (
                <option key={roomType}>{roomType}</option>
              ))}
            </select>
          </label>
          <label>
            Check In
            <input
              type="date"
              value={form.checkInDate}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, checkInDate: event.target.value }))
              }
              required
            />
          </label>
          <label>
            Check Out
            <input
              type="date"
              value={form.checkOutDate}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, checkOutDate: event.target.value }))
              }
              required
            />
          </label>
          <div className="fd-occupancy-guide span-3">
            <strong>{receipt.guests || 0} total guests</strong>
            <span>
              Family setup supports up to 5 guests: 1 king, 1 queen, and 1
              standard or sofa bed for one person.
            </span>
            {receipt.extraGuestCount > 0 ? (
              <span className="pill pill-warning">
                {receipt.extraGuestCount} extra guest(s) need extra bed charge
              </span>
            ) : (
              <span className="pill">No extra bed needed</span>
            )}
          </div>
        </div>
      </div>

      <div className="fd-form-section span-3">
        <h3>Payment and Receipt</h3>
        <div className="fd-form-grid">
          <label>
            Currency
            <select
              value={form.currency}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, currency: event.target.value }))
              }
            >
              <option>ETB</option>
              <option>USD</option>
              <option>EUR</option>
              <option>GBP</option>
              <option>AED</option>
            </select>
          </label>
          <label>
            Rack Rate / Night
            <input
              inputMode="decimal"
              value={form.ratePerNightEtb}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, ratePerNightEtb: event.target.value }))
              }
              placeholder="0.00"
            />
          </label>
          <label>
            Extra Bed Charge
            <input
              inputMode="decimal"
              value={form.extraBedCharge}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, extraBedCharge: event.target.value }))
              }
              placeholder="Per extra guest"
            />
          </label>
          <label>
            Discount
            <input
              inputMode="decimal"
              value={form.discountAmount}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, discountAmount: event.target.value }))
              }
              placeholder="0.00"
            />
          </label>
          <label>
            Tax %
            <select
              value={form.taxPercent}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, taxPercent: event.target.value }))
              }
            >
              {chargePercentOptions.map((percent) => (
                <option key={percent} value={percent}>
                  {percent === "custom" ? "Add custom" : `${percent}%`}
                </option>
              ))}
            </select>
          </label>
          {form.taxPercent === "custom" ? (
            <label>
              Custom Tax %
              <input
                inputMode="decimal"
                value={form.customTaxPercent}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, customTaxPercent: event.target.value }))
                }
                placeholder="0"
              />
            </label>
          ) : null}
          <label>
            Service Charge %
            <select
              value={form.serviceChargePercent}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  serviceChargePercent: event.target.value,
                }))
              }
            >
              {chargePercentOptions.map((percent) => (
                <option key={percent} value={percent}>
                  {percent === "custom" ? "Add custom" : `${percent}%`}
                </option>
              ))}
            </select>
          </label>
          {form.serviceChargePercent === "custom" ? (
            <label>
              Custom Service %
              <input
                inputMode="decimal"
                value={form.customServiceChargePercent}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    customServiceChargePercent: event.target.value,
                  }))
                }
                placeholder="0"
              />
            </label>
          ) : null}
          <label>
            VAT %
            <select
              value={form.vatPercent}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, vatPercent: event.target.value }))
              }
            >
              {chargePercentOptions.map((percent) => (
                <option key={percent} value={percent}>
                  {percent === "custom" ? "Add custom" : `${percent}%`}
                </option>
              ))}
            </select>
          </label>
          {form.vatPercent === "custom" ? (
            <label>
              Custom VAT %
              <input
                inputMode="decimal"
                value={form.customVatPercent}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, customVatPercent: event.target.value }))
                }
                placeholder="0"
              />
            </label>
          ) : null}
          <label>
            Downpayment
            <input
              inputMode="decimal"
              value={form.downpaymentAmount}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, downpaymentAmount: event.target.value }))
              }
              placeholder="0.00"
            />
          </label>
          <label>
            Paid Now
            <input
              inputMode="decimal"
              value={form.amountPaidNowEtb}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, amountPaidNowEtb: event.target.value }))
              }
              placeholder="0.00"
            />
          </label>
          <label>
            Payment Method
            <select
              value={form.paymentMethod}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, paymentMethod: event.target.value }))
              }
            >
              <option>Cash</option>
              <option>Card</option>
              <option>Bank Transfer</option>
              <option>Mobile Money</option>
              <option>Pay at Checkout</option>
            </select>
          </label>
          <label>
            Override Total
            <input
              inputMode="decimal"
              value={form.totalAmountEtb}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, totalAmountEtb: event.target.value }))
              }
              placeholder="Auto calculated"
            />
          </label>
        </div>
      </div>

      <div className="fd-receipt-preview span-3">
        <div className="fd-receipt-header">
          <div>
            <strong>Guzo PMS Receipt Preview</strong>
            <span>
              {form.guestName || "Guest name"} | {form.roomNumber || "Auto room"} |{" "}
              {receipt.guests} guest(s)
            </span>
          </div>
          <span className="pill pill-success">{currency}</span>
        </div>
        <div className="fd-receipt-lines">
          <span>Nights</span>
          <strong>{receipt.nights}</strong>
          <span>Room Subtotal</span>
          <strong>{currency} {receipt.roomSubtotal.toFixed(2)}</strong>
          <span>Discount</span>
          <strong>- {currency} {receipt.discount.toFixed(2)}</strong>
          <span>Extra Bed Charge</span>
          <strong>{currency} {receipt.extraBedCharge.toFixed(2)}</strong>
          <span>Tax ({receipt.taxPercent}%)</span>
          <strong>{currency} {receipt.tax.toFixed(2)}</strong>
          <span>Service Charge ({receipt.serviceChargePercent}%)</span>
          <strong>{currency} {receipt.serviceCharge.toFixed(2)}</strong>
          <span>VAT ({receipt.vatPercent}%)</span>
          <strong>{currency} {receipt.vat.toFixed(2)}</strong>
          <span>Downpayment</span>
          <strong>- {currency} {receipt.downpayment.toFixed(2)}</strong>
          <span>Paid Now</span>
          <strong>- {currency} {receipt.paidNow.toFixed(2)}</strong>
        </div>
        <div className="fd-receipt-total">
          <span>Total</span>
          <strong>{currency} {receipt.total.toFixed(2)}</strong>
          <span>Balance Due</span>
          <strong>{currency} {receipt.balanceDue.toFixed(2)}</strong>
        </div>
      </div>

      <label className="span-3">
        Notes
        <textarea
          value={form.notes}
          onChange={(event) =>
            setForm((prev) => ({ ...prev, notes: event.target.value }))
          }
          placeholder="Guest requests, ID notes, billing remarks"
        />
      </label>
      <div className="form-actions span-3">
        <button className="small-btn" type="button" onClick={onCancel}>
          Cancel
        </button>
        <button className="primary-btn" type="submit" disabled={submitting}>
          {submitting ? "Creating..." : "Create Walk-In"}
        </button>
      </div>
    </form>
  );
}
