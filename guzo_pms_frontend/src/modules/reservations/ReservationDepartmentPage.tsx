import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  BedDouble,
  Bell,
  BriefcaseBusiness,
  BadgePercent,
  CalendarCheck,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  DoorOpen,
  Edit3,
  Mail,
  MessageCircle,
  MapPinned,
  Send,
  ShieldCheck,
  Sparkles,
  StickyNote,
  Users,
} from "lucide-react";
import PageHeader from "../../components/PageHeader";
import DataTable from "../../components/DataTable";
import { usePmsContext } from "../../context/PmsContext";
import { fetchFrontdeskBookings, fetchRoomStatusBoard } from "../../services/pmsService";
import { getErrorMessage, isBackendUnreachable } from "../../services/http";
import {
  applyReservationAction,
  cancelReservationBlock,
  cancelWaitlistItem,
  convertWaitlistItem,
  createReservationBlock,
  createReservation,
  createWaitlistItem,
  fetchReservationAvailabilityQuote,
  fetchReservationBlocks,
  fetchWaitlist,
  quoteReservationBlock,
  requestReservationBlockDeposit,
  reviewWaitlistItem,
  updateReservationBlock,
  type ReservationBlock,
  type BlockStatus,
  type ReservationAvailabilityQuote,
  type ReservationWaitlistItem,
  type WaitlistStatus,
  type ReservationWorkflowAction,
} from "../../services/reservationActions";
import type { FrontdeskBooking, RoomStatusItem } from "../../types/pms";
import { fetchDepositAccounts, type DepositAccount } from "../../services/financeService";
import { demoFamilyBookings } from "../booking/demoFamilyBookings";

type ReservationTab =
  | "inbox"
  | "search"
  | "guarantee"
  | "handoff"
  | "new"
  | "groups"
  | "profiles"
  | "waitlist"
  | "roomPlan"
  | "floorPlan"
  | "calendar";

type InquiryStatus =
  | "new"
  | "needs_review"
  | "quoted"
  | "waiting_reply"
  | "waiting_deposit"
  | "guaranteed"
  | "confirmed"
  | "converted";

type GuaranteeStatus = "guaranteed" | "pending_guarantee" | "non_guaranteed";

type ReservationInquiry = {
  id: number;
  contact_name: string;
  channel: string;
  request_type: string;
  arrival_date: string;
  departure_date: string;
  room_type: string;
  rooms_requested: number;
  adults: number;
  children: number;
  event_type?: string;
  event_guest_count?: number;
  inquiry_status: InquiryStatus;
  guarantee_status: GuaranteeStatus;
  priority: "normal" | "urgent" | "vip";
  assigned_agent: string;
  last_message: string;
  action_needed: string;
  created_time: string;
};

const tabs: Record<ReservationTab, string> = {
  inbox: "Inbox",
  search: "Reservation Register",
  guarantee: "Guarantee Desk",
  handoff: "Handoff",
  new: "New Reservation",
  groups: "Blocks / Group Booking",
  profiles: "Profiles",
  waitlist: "Waitlist",
  roomPlan: "Room Plan",
  floorPlan: "Floor Plan",
  calendar: "Calendar",
};

const reservationPathToTab: Record<string, ReservationTab> = {
  new: "new",
  update: "search",
  search: "search",
  confirmation: "guarantee",
  guarantee: "guarantee",
  handoff: "handoff",
  blocks: "groups",
  "group-booking": "groups",
  groups: "groups",
  profiles: "profiles",
  profile: "profiles",
  "guest-profiles": "profiles",
  "company-profiles": "profiles",
  "travel-agent-profiles": "profiles",
  waitlist: "waitlist",
  "room-plan": "roomPlan",
  "floor-plan": "floorPlan",
  calendar: "calendar",
};

const reservationTabPath: Record<ReservationTab, string> = {
  inbox: "/reservations",
  search: "/reservations/update",
  guarantee: "/reservations/confirmation",
  handoff: "/reservations/handoff",
  new: "/reservations/new",
  groups: "/reservations/blocks",
  profiles: "/reservations/profiles",
  waitlist: "/reservations/waitlist",
  roomPlan: "/reservations/room-plan",
  floorPlan: "/reservations/floor-plan",
  calendar: "/reservations/calendar",
};

const requestTypeLabels: Record<string, string> = {
  individual_room: "Individual Room",
  group_room: "Group Rooms",
  meeting_room: "Meeting",
  wedding_event: "Wedding",
  party_event: "Party",
  room_plus_event: "Room + Event",
  corporate_booking: "Corporate",
  travel_agent_booking: "Travel Agent",
};

const demoInquiries: ReservationInquiry[] = [
  {
    id: 9101,
    contact_name: "John Kelly Family",
    channel: "Guzo AI Guest Site",
    request_type: "individual_room",
    arrival_date: "2026-06-10",
    departure_date: "2026-06-13",
    room_type: "Deluxe Family Room",
    rooms_requested: 1,
    adults: 2,
    children: 1,
    inquiry_status: "confirmed",
    guarantee_status: "guaranteed",
    priority: "normal",
    assigned_agent: "Booking Desk",
    last_message: demoFamilyBookings[0].confirmationMessage,
    action_needed: "Confirmed AI-site family booking. Handoff to front desk before arrival.",
    created_time: "AI Demo",
  },
  {
    id: 9102,
    contact_name: "Thomas Jefferson Family",
    channel: "Guzo AI Guest Site",
    request_type: "group_room",
    arrival_date: "2026-06-10",
    departure_date: "2026-06-13",
    room_type: "Deluxe Twin + Standard Double",
    rooms_requested: 2,
    adults: 3,
    children: 2,
    inquiry_status: "confirmed",
    guarantee_status: "guaranteed",
    priority: "normal",
    assigned_agent: "Booking Desk",
    last_message: demoFamilyBookings[1].confirmationMessage,
    action_needed: "Confirmed AI-site family multi-room booking. Verify room block 302/303 before arrival.",
    created_time: "AI Demo",
  },
  {
    id: 9001,
    contact_name: "Hana Wedding Party",
    channel: "Website",
    request_type: "room_plus_event",
    arrival_date: "2026-05-26",
    departure_date: "2026-05-28",
    room_type: "Deluxe",
    rooms_requested: 12,
    adults: 24,
    children: 3,
    event_type: "Wedding",
    event_guest_count: 180,
    inquiry_status: "waiting_deposit",
    guarantee_status: "pending_guarantee",
    priority: "urgent",
    assigned_agent: "Reservations",
    last_message: "Bride requested ballroom, airport pickup, and 12 rooms.",
    action_needed: "Confirm deposit deadline and event coordinator.",
    created_time: "09:20",
  },
  {
    id: 9002,
    contact_name: "Alemayehu Trading PLC",
    channel: "Email",
    request_type: "group_room",
    arrival_date: "2026-05-27",
    departure_date: "2026-05-31",
    room_type: "Standard",
    rooms_requested: 15,
    adults: 15,
    children: 0,
    inquiry_status: "quoted",
    guarantee_status: "non_guaranteed",
    priority: "normal",
    assigned_agent: "Sales",
    last_message: "Company requested training room block and direct bill.",
    action_needed: "Manager approval for company guarantee.",
    created_time: "10:05",
  },
  {
    id: 9003,
    contact_name: "Sara Mohammed",
    channel: "Telegram",
    request_type: "individual_room",
    arrival_date: "2026-05-26",
    departure_date: "2026-05-27",
    room_type: "Suite",
    rooms_requested: 1,
    adults: 2,
    children: 1,
    inquiry_status: "new",
    guarantee_status: "pending_guarantee",
    priority: "vip",
    assigned_agent: "Unassigned",
    last_message: "Guest asked for suite, baby cot, and late arrival.",
    action_needed: "Check suite availability and quote deposit.",
    created_time: "10:42",
  },
];

const ratePlans = [
  {
    code: "BAR",
    name: "Best Available Rate",
    segment: "Transient",
    roomType: "Standard Room",
    baseRate: 5200,
    minRate: 4600,
    maxRate: 7200,
    status: "open",
  },
  {
    code: "CORP",
    name: "Corporate Preferred",
    segment: "Corporate",
    roomType: "Deluxe King",
    baseRate: 6100,
    minRate: 5600,
    maxRate: 7600,
    status: "restricted",
  },
  {
    code: "GRP10",
    name: "Group 10+ Rooms",
    segment: "Group",
    roomType: "Standard Room",
    baseRate: 4800,
    minRate: 4300,
    maxRate: 6200,
    status: "manager approval",
  },
];

const corporateContracts = [
  {
    account: "Alemayehu Trading PLC",
    rateCode: "CORP",
    guarantee: "Direct bill pending approval",
    discount: "12%",
    validUntil: "2026-12-31",
  },
  {
    account: "Mekdes Corporate Group",
    rateCode: "GRP10",
    guarantee: "Deposit required",
    discount: "Group ladder",
    validUntil: "2026-09-30",
  },
];

const channelControls = [
  { channel: "Website Chatbot", status: "Open", rateCode: "BAR", allotment: "House availability" },
  { channel: "Telegram Bot", status: "Open", rateCode: "BAR", allotment: "House availability" },
  { channel: "OTA Inbox", status: "Monitor", rateCode: "BAR", allotment: "Manual review" },
];

function money(value: number) {
  return `ETB ${Number(value || 0).toLocaleString("en-US")}`;
}

function addDateDays(value: string, days: number) {
  const date = new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function reservationFallbackKey(kind: "waitlist" | "blocks", propertyCode: string) {
  return `guzo_reservations_${kind}_${propertyCode}`;
}

function readReservationFallback<T>(kind: "waitlist" | "blocks", propertyCode: string): T[] {
  try {
    return JSON.parse(sessionStorage.getItem(reservationFallbackKey(kind, propertyCode)) || "[]") as T[];
  } catch {
    return [];
  }
}

function writeReservationFallback<T>(kind: "waitlist" | "blocks", propertyCode: string, rows: T[]) {
  sessionStorage.setItem(reservationFallbackKey(kind, propertyCode), JSON.stringify(rows));
}

function statusClass(status: string) {
  const s = status.toLowerCase();
  if (s === "guaranteed" || s === "confirmed" || s === "converted") {
    return "pill pill-success";
  }
  if (s === "waiting_deposit" || s === "pending_guarantee" || s === "quoted") {
    return "pill pill-warning";
  }
  if (s === "urgent" || s === "non_guaranteed") return "pill pill-danger";
  if (s === "vip") return "pill pill-inspected";
  return "pill";
}

function sourceClass(source: string) {
  const s = source.toLowerCase();
  if (s.includes("telegram")) return "pill pill-inspected";
  if (s.includes("email")) return "pill pill-warning";
  if (s.includes("walk")) return "pill pill-success";
  if (s.includes("corporate")) return "pill pill-muted";
  return "pill";
}

function normalizeSource(row: FrontdeskBooking) {
  return String(row.source || row.channel || "direct").toLowerCase();
}

function normalizeRoom(row: FrontdeskBooking) {
  return row.room_number || row.room_type || "-";
}

function formatStatus(status: string) {
  return status.replace(/_/g, " ");
}

function bookingStatus(row: FrontdeskBooking) {
  return String(row.booking_status || "").toLowerCase();
}

function paymentStatus(row: FrontdeskBooking) {
  return String(row.payment_status || "pending").toLowerCase();
}

function isInHouse(row: FrontdeskBooking) {
  const status = bookingStatus(row);
  return status === "in_house" || status === "checked_in";
}

function isClosedReservation(row: FrontdeskBooking) {
  return ["checked_out", "cancelled", "no_show", "no-show"].includes(bookingStatus(row));
}

function isPendingGuarantee(row: FrontdeskBooking) {
  return guaranteeFromBooking(row) === "pending_guarantee";
}

function actionButtonLabels(row: FrontdeskBooking) {
  if (isPendingGuarantee(row)) {
    return [
      "Review Guarantee",
      "Send Deposit Link",
      "Approve Pay at Hotel",
      "Hold at Front Desk",
      "Cancel by Deadline",
    ];
  }
  return [
    "Send to Front Desk",
    "Add Arrival Note",
    "Assign Room Preference",
    "Mark VIP",
  ];
}

const bookingActionByLabel: Record<string, ReservationWorkflowAction> = {
  "Open Reservation": "open_reservation",
  "Review Guarantee": "review_guarantee",
  "Send Deposit Link": "send_deposit_link",
  "Record Deposit": "record_deposit",
  "Request Card Guarantee": "request_card_guarantee",
  "Approve Pay at Hotel": "approve_pay_at_hotel",
  "Mark Guaranteed": "mark_guaranteed",
  "Hold at Front Desk": "hold_at_frontdesk",
  "Cancel by Deadline": "cancel_by_deadline",
  "Send to Front Desk": "send_to_frontdesk",
  "Add Arrival Note": "add_arrival_note",
  "Assign Room Preference": "assign_room_preference",
  "Mark VIP": "mark_vip",
  "Add Trace": "add_trace",
};

function handoffStatus(row: FrontdeskBooking) {
  if (isPendingGuarantee(row)) return "Blocked - Guarantee Review Required";
  if (guaranteeFromBooking(row) === "guaranteed") return "Ready for Front Desk";
  return "Review Before Handoff";
}

function guaranteeFromBooking(row: FrontdeskBooking): GuaranteeStatus {
  const payment = paymentStatus(row);
  const status = bookingStatus(row);
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

export default function ReservationDepartmentPage() {
  const { propertyCode, businessDate, refreshKey, refreshData } = usePmsContext();
  const navigate = useNavigate();
  const { section: routeSection } = useParams<{ section?: string }>();

  const [bookings, setBookings] = useState<FrontdeskBooking[]>([]);
  const [rooms, setRooms] = useState<RoomStatusItem[]>([]);
  const [depositAccounts, setDepositAccounts] = useState<DepositAccount[]>([]);
  const [inquiries, setInquiries] = useState<ReservationInquiry[]>(demoInquiries);
  const [selectedInquiryId, setSelectedInquiryId] = useState<number>(demoInquiries[0].id);
  const [activeTab, setActiveTab] = useState<ReservationTab>("inbox");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [availabilityQuote, setAvailabilityQuote] = useState<ReservationAvailabilityQuote | null>(null);
  const [waitlistItems, setWaitlistItems] = useState<ReservationWaitlistItem[]>([]);
  const [reservationBlocks, setReservationBlocks] = useState<ReservationBlock[]>([]);
  const [queueFallbackActive, setQueueFallbackActive] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState<FrontdeskBooking | null>(null);
  const [searchText, setSearchText] = useState("");
  const [channelFilter, setChannelFilter] = useState("all");
  const [newInquiry, setNewInquiry] = useState({
    contactName: "",
    channel: "Phone",
    requestType: "individual_room",
    arrivalDate: businessDate,
    departureDate: addDateDays(businessDate, 1),
    roomType: "Standard",
    roomsRequested: "1",
    adults: "1",
    children: "0",
    message: "",
  });

  useEffect(() => {
    if (!routeSection) {
      setActiveTab("inbox");
      return;
    }
    const nextTab = reservationPathToTab[routeSection];
    if (nextTab) setActiveTab(nextTab);
  }, [routeSection]);

  async function loadBookings() {
    try {
      setLoading(true);
      setError("");
      const [bookingRows, roomRows, depositRows] = await Promise.all([
        fetchFrontdeskBookings(propertyCode, businessDate),
        fetchRoomStatusBoard(propertyCode, businessDate),
        fetchDepositAccounts(propertyCode),
      ]);
      setBookings(bookingRows);
      setRooms(roomRows);
      setDepositAccounts(depositRows);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBookings();
  }, [propertyCode, businessDate, refreshKey]);

  async function loadReservationQueues() {
    try {
      const [waitlistRows, blockRows] = await Promise.all([
        fetchWaitlist(propertyCode),
        fetchReservationBlocks(propertyCode),
      ]);
      setWaitlistItems(waitlistRows);
      setReservationBlocks(blockRows);
      writeReservationFallback("waitlist", propertyCode, waitlistRows);
      writeReservationFallback("blocks", propertyCode, blockRows);
      setQueueFallbackActive(false);
    } catch (err) {
      if (!isBackendUnreachable(err)) {
        setError(getErrorMessage(err));
        return;
      }
      setWaitlistItems(readReservationFallback<ReservationWaitlistItem>("waitlist", propertyCode));
      setReservationBlocks(readReservationFallback<ReservationBlock>("blocks", propertyCode));
      setQueueFallbackActive(true);
    }
  }

  useEffect(() => {
    loadReservationQueues();
  }, [propertyCode, refreshKey]);

  const filteredInquiries = useMemo(() => {
    const q = searchText.trim().toLowerCase();
    return inquiries.filter((item) => {
      const channelOk =
        channelFilter === "all"
          ? true
          : item.channel.toLowerCase() === channelFilter.toLowerCase();
      const searchOk =
        !q ||
        item.contact_name.toLowerCase().includes(q) ||
        item.channel.toLowerCase().includes(q) ||
        item.request_type.toLowerCase().includes(q);
      return channelOk && searchOk;
    });
  }, [inquiries, searchText, channelFilter]);

  const selectedInquiry =
    inquiries.find((item) => item.id === selectedInquiryId) || filteredInquiries[0];

  const arrivalsToday = useMemo(
    () =>
      bookings.filter(
        (row) =>
          row.check_in_date === businessDate &&
          !isInHouse(row) &&
          !isClosedReservation(row)
      ),
    [bookings, businessDate]
  );

  const departuresToday = useMemo(
    () => bookings.filter((row) => row.check_out_date === businessDate && !isClosedReservation(row)),
    [bookings, businessDate]
  );

  const inHouseBookings = useMemo(
    () => bookings.filter((row) => isInHouse(row)),
    [bookings]
  );

  const upcomingArrivals = useMemo(
    () =>
      bookings
        .filter((row) => row.check_in_date > businessDate && !isClosedReservation(row))
        .sort((a, b) => a.check_in_date.localeCompare(b.check_in_date))
        .slice(0, 8),
    [bookings, businessDate]
  );

  const vipGuests = useMemo(
    () =>
      bookings.filter((row) =>
        String(row.notes || row.special_requests || row.source || row.channel || "")
          .toLowerCase()
          .includes("vip")
      ),
    [bookings]
  );

  const unconfirmedReservations = useMemo(
    () =>
      bookings.filter((row) => {
        const status = bookingStatus(row);
        return ["pending", "tentative", "pending_guarantee", "unconfirmed"].includes(status) || isPendingGuarantee(row);
      }),
    [bookings]
  );

  const groupBlockReservations = useMemo(
    () =>
      bookings.filter((row) =>
        String(row.room_type || row.source || row.channel || row.notes || "")
          .toLowerCase()
          .match(/group|block|event|wedding|corporate/)
      ),
    [bookings]
  );

  const expectedRevenue = useMemo(
    () =>
      bookings
        .filter((row) => !isClosedReservation(row))
        .reduce((sum, row) => sum + Number(row.total_amount || row.rate_per_night_etb || 0), 0),
    [bookings]
  );

  const outOfServiceRoomCount = rooms.filter((room) =>
    String(room.hk_status || "").toLowerCase().includes("out")
  ).length;
  const totalRoomBase = rooms.length || Math.max(120, inHouseBookings.length + arrivalsToday.length + 1);
  const sellableRoomBase = Math.max(totalRoomBase - outOfServiceRoomCount, 1);
  const occupancyPct = Math.round((inHouseBookings.length / sellableRoomBase) * 100);
  const waitlistCount =
    waitlistItems.filter((item) => !["converted", "cancelled"].includes(item.status)).length +
    bookings.filter((row) => String(row.q_status || "").toLowerCase() === "waiting").length;
  const availableRooms = Math.max(sellableRoomBase - inHouseBookings.length - arrivalsToday.length, 0);

  const pendingGuaranteeBookings = useMemo(
    () =>
      bookings.filter(
        (row) => guaranteeFromBooking(row) !== "guaranteed" && !isClosedReservation(row)
      ),
    [bookings]
  );

  const groupEventLeads = useMemo(
    () =>
      inquiries.filter((item) =>
        ["group_room", "meeting_room", "wedding_event", "party_event", "room_plus_event"].includes(
          item.request_type
        )
      ),
    [inquiries]
  );

  const waitingDeposit = inquiries.filter(
    (item) =>
      item.guarantee_status === "pending_guarantee" ||
      item.inquiry_status === "waiting_deposit"
  );

  function reservationPayload() {
    const requestType = newInquiry.requestType;
    const source =
      requestType === "corporate_booking"
        ? "corporate"
        : requestType === "travel_agent_booking"
          ? "travel_agent"
          : requestType === "wedding_event" || requestType === "party_event" || requestType === "room_plus_event"
            ? "event"
            : newInquiry.channel;
    return {
      property_code: propertyCode,
      guest_name: newInquiry.contactName.trim() || "New Reservation Guest",
      guest_email: null,
      guest_phone: null,
      check_in_date: newInquiry.arrivalDate,
      check_out_date: newInquiry.departureDate,
      room_type: newInquiry.roomType,
      rooms: Number(newInquiry.roomsRequested || 1),
      adults: Number(newInquiry.adults || 1),
      children: Number(newInquiry.children || 0),
      rate_code: requestType === "group_room" ? "GRP10" : requestType === "corporate_booking" ? "CORP" : "BAR",
      reservation_type: requestType,
      source,
      company_name: requestType === "corporate_booking" ? newInquiry.contactName.trim() : null,
      travel_agent_name: requestType === "travel_agent_booking" ? newInquiry.contactName.trim() : null,
      event_name: requestType.includes("event") ? newInquiry.contactName.trim() : null,
      guarantee_type: Number(newInquiry.roomsRequested || 1) > 1 ? "group_deposit_required" : "deposit_required",
      deposit_required: true,
      special_requests: newInquiry.message || null,
      vip_notes: newInquiry.message.toLowerCase().includes("vip") ? newInquiry.message : null,
      notes: newInquiry.message || null,
    };
  }

  async function handleAvailabilityQuote() {
    try {
      setError("");
      setActionMessage("");
      const payload = reservationPayload();
      const result = await fetchReservationAvailabilityQuote({
        property_code: payload.property_code,
        check_in_date: payload.check_in_date,
        check_out_date: payload.check_out_date,
        room_type: payload.room_type,
        rooms: payload.rooms,
        adults: payload.adults,
        children: payload.children,
        rate_code: payload.rate_code,
      });
      setAvailabilityQuote(result);
      setActionMessage(
        result.availability.is_available
          ? `${result.availability.available_rooms} room(s) available. Quote ${money(result.quote.total_etb)}.`
          : `Not available. ${result.availability.available_rooms} room(s) available for ${result.availability.requested_rooms} requested.`
      );
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function addManualInquiry(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newInquiry.arrivalDate || !newInquiry.departureDate || newInquiry.departureDate <= newInquiry.arrivalDate) {
      setError("Departure date must be after the arrival date.");
      return;
    }
    if (Number(newInquiry.roomsRequested) < 1 || Number(newInquiry.adults) < 1 || Number(newInquiry.children) < 0) {
      setError("Rooms and adults must be at least 1; children cannot be negative.");
      return;
    }
    try {
      setBusyAction("create-reservation");
      setError("");
      setActionMessage("");
      const result = await createReservation(reservationPayload());
      setAvailabilityQuote(result);
      setActionMessage(
        [
          `Reservation ${result.confirmation_id} created and confirmation ${result.guest_notification_status}.`,
          result.duplicate_warnings.length ? `${result.duplicate_warnings.length} possible duplicate warning(s).` : "",
        ]
          .filter(Boolean)
          .join(" ")
      );
      await loadBookings();
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
      setBusyAction(null);
      return;
    }
    const next: ReservationInquiry = {
      id: Date.now(),
      contact_name: newInquiry.contactName.trim() || "New Inquiry",
      channel: newInquiry.channel,
      request_type: newInquiry.requestType,
      arrival_date: newInquiry.arrivalDate,
      departure_date: newInquiry.departureDate,
      room_type: newInquiry.roomType,
      rooms_requested: Number(newInquiry.roomsRequested || 1),
      adults: Number(newInquiry.adults || 1),
      children: Number(newInquiry.children || 0),
      inquiry_status: "new",
      guarantee_status: "pending_guarantee",
      priority: Number(newInquiry.roomsRequested || 1) >= 8 ? "urgent" : "normal",
      assigned_agent: "Reservations",
      last_message: newInquiry.message || "Manual reservation inquiry created.",
      action_needed: "Review availability, quote rate, and confirm guarantee.",
      created_time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setInquiries((prev) => [next, ...prev]);
    setSelectedInquiryId(next.id);
    setActiveTab("inbox");
    setNewInquiry((prev) => ({
      ...prev,
      contactName: "",
      roomsRequested: "1",
      adults: "1",
      children: "0",
      message: "",
    }));
    setBusyAction(null);
  }

  function markGuaranteed(inquiryId: number) {
    setInquiries((prev) =>
      prev.map((item) =>
        item.id === inquiryId
          ? {
              ...item,
              inquiry_status: "guaranteed",
              guarantee_status: "guaranteed",
              action_needed: "Convert to confirmed reservation and send confirmation.",
            }
          : item
      )
    );
  }

  function convertInquiry(inquiryId: number) {
    setInquiries((prev) =>
      prev.map((item) =>
        item.id === inquiryId
          ? {
              ...item,
              inquiry_status: "converted",
              action_needed: "Ready for front desk handoff when arrival date approaches.",
            }
          : item
      )
    );
  }

  function updateInquiryStatus(inquiryId: number, status: InquiryStatus, message: string) {
    setInquiries((prev) =>
      prev.map((item) =>
        item.id === inquiryId
          ? { ...item, inquiry_status: status, action_needed: message }
          : item
      )
    );
    setActionMessage(message);
  }

  async function addInquiryToWaitlist(inquiry: ReservationInquiry) {
    const payload = {
      property_code: propertyCode,
      guest_name: inquiry.contact_name,
      guest_email: null,
      guest_phone: null,
      check_in_date: inquiry.arrival_date,
      check_out_date: inquiry.departure_date,
      room_type: inquiry.room_type,
      rooms: inquiry.rooms_requested,
      adults: inquiry.adults,
      children: inquiry.children,
      rate_code: "BAR",
      source: inquiry.channel,
      notes: inquiry.last_message,
    };
    try {
      const created = await createWaitlistItem(payload);
      setWaitlistItems((rows) => [created, ...rows]);
      updateInquiryStatus(inquiry.id, "waiting_reply", `${inquiry.contact_name} added to the persistent waitlist.`);
      setQueueFallbackActive(false);
    } catch (err) {
      if (!isBackendUnreachable(err)) {
        setError(getErrorMessage(err));
        return;
      }
      const fallback: ReservationWaitlistItem = { ...payload, id: -Date.now(), status: "open" };
      setWaitlistItems((rows) => {
        const next = [fallback, ...rows];
        writeReservationFallback("waitlist", propertyCode, next);
        return next;
      });
      updateInquiryStatus(inquiry.id, "waiting_reply", `${inquiry.contact_name} added to the session waitlist while the backend is unreachable.`);
      setQueueFallbackActive(true);
    }
  }

  async function runWaitlistAction(item: ReservationWaitlistItem, action: "review" | "convert" | "cancel") {
    try {
      const updated = action === "review"
        ? await reviewWaitlistItem(item.id, propertyCode)
        : action === "convert"
          ? await convertWaitlistItem(item.id, propertyCode)
          : await cancelWaitlistItem(item.id, propertyCode, "Cancelled from Reservations Waitlist");
      setWaitlistItems((rows) => rows.map((row) => row.id === item.id ? updated : row));
      setActionMessage(`${item.guest_name}: ${updated.status.replace(/_/g, " ")}.`);
      if (action === "convert") await loadBookings();
    } catch (err) {
      if (!isBackendUnreachable(err)) {
        setError(getErrorMessage(err));
        return;
      }
      const fallbackStatus: WaitlistStatus = action === "cancel" ? "cancelled" : action === "convert" ? "converted" : availableRooms >= item.rooms ? "available" : "open";
      setWaitlistItems((rows) => {
        const next = rows.map((row) => row.id === item.id ? { ...row, status: fallbackStatus } : row);
        writeReservationFallback("waitlist", propertyCode, next);
        return next;
      });
      setQueueFallbackActive(true);
      setActionMessage(`${item.guest_name}: ${fallbackStatus} in session fallback. Reconfirm this action after backend connectivity returns.`);
    }
  }

  async function createBlockFromLead(lead: ReservationInquiry) {
    const payload = {
      property_code: propertyCode,
      block_name: lead.contact_name,
      company_name: lead.contact_name,
      contact_name: lead.contact_name,
      contact_email: null,
      contact_phone: null,
      check_in_date: lead.arrival_date,
      check_out_date: lead.departure_date,
      room_type: lead.room_type,
      rooms: lead.rooms_requested,
      rate_code: "GRP10",
      notes: lead.last_message,
    };
    try {
      const created = await createReservationBlock(payload);
      setReservationBlocks((rows) => [created, ...rows]);
      setActionMessage(`${created.block_name} created as a tentative block.`);
    } catch (err) {
      if (!isBackendUnreachable(err)) {
        setError(getErrorMessage(err));
        return;
      }
      const fallback: ReservationBlock = { ...payload, id: -Date.now(), status: "tentative" };
      setReservationBlocks((rows) => {
        const next = [fallback, ...rows];
        writeReservationFallback("blocks", propertyCode, next);
        return next;
      });
      setQueueFallbackActive(true);
      setActionMessage(`${fallback.block_name} saved to the session fallback.`);
    }
  }

  async function runBlockAction(block: ReservationBlock, action: "quote" | "deposit" | "confirm" | "cancel") {
    try {
      const updated = action === "quote"
        ? await quoteReservationBlock(block.id, propertyCode)
        : action === "deposit"
          ? await requestReservationBlockDeposit(block.id, propertyCode)
          : action === "confirm"
            ? await updateReservationBlock(block.id, propertyCode, { status: "confirmed" })
            : await cancelReservationBlock(block.id, propertyCode, "Cancelled from Reservations Blocks");
      setReservationBlocks((rows) => rows.map((row) => row.id === block.id ? updated : row));
      setActionMessage(`${block.block_name}: ${updated.status.replace(/_/g, " ")}.`);
    } catch (err) {
      if (!isBackendUnreachable(err)) {
        setError(getErrorMessage(err));
        return;
      }
      const fallbackStatus: BlockStatus = action === "quote" ? "quoted" : action === "deposit" ? "deposit_requested" : action === "confirm" ? "confirmed" : "cancelled";
      setReservationBlocks((rows) => {
        const next = rows.map((row) => row.id === block.id ? { ...row, status: fallbackStatus } : row);
        writeReservationFallback("blocks", propertyCode, next);
        return next;
      });
      setQueueFallbackActive(true);
      setActionMessage(`${block.block_name}: ${fallbackStatus.replace(/_/g, " ")} in session fallback.`);
    }
  }

  async function handleBookingAction(
    booking: FrontdeskBooking,
    action: ReservationWorkflowAction,
    label: string
  ) {
    try {
      setError("");
      setActionMessage("");
      setBusyAction(`${booking.id}-${action}`);
      if (action === "open_reservation") {
        setSelectedBooking(booking);
        setActionMessage(`Reservation #${booking.id} opened for ${booking.guest_name}.`);
        return;
      }
      await applyReservationAction({
        bookingId: booking.id,
        propertyCode,
        businessDate,
        action,
        note: `${label} completed from Reservations Department.`,
      });
      setActionMessage(`${label} completed for ${booking.guest_name}.`);
      refreshData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="page-grid reservation-workspace">
      <PageHeader
        title="Reservations"
        subtitle="Sell, confirm, guarantee, and hand off reservations."
        metadata={`${propertyCode} • ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">Inbox: {inquiries.length}</div>
            <div className="pill">Waiting Deposit: {waitingDeposit.length}</div>
            <div className="pill">Arriving Today: {arrivalsToday.length}</div>
          </>
        }
      />

      {loading ? (
        <div className="card">Loading reservation department workspace...</div>
      ) : (
        <>
          {error ? <div className="error-box">{error}</div> : null}
          {actionMessage ? <div className="card">{actionMessage}</div> : null}
          {queueFallbackActive ? (
            <div className="notice-box">Waitlist and block changes are using property-scoped session fallback because the backend is unreachable.</div>
          ) : null}
          {selectedBooking ? (
            <section className="card res-panel">
              <SectionHeader
                icon={<ClipboardList />}
                title="Reservation Detail"
                subtitle="Full reservation profile for review, guarantee decision, trace, and front desk handoff."
              />
              <div className="res-detail-stack">
                <div>
                  <span>Guest</span>
                  <strong>{selectedBooking.guest_name}</strong>
                </div>
                <div>
                  <span>Stay</span>
                  <strong>
                    {selectedBooking.check_in_date} to {selectedBooking.check_out_date}
                  </strong>
                </div>
                <div>
                  <span>Room</span>
                  <strong>{normalizeRoom(selectedBooking)}</strong>
                </div>
                <div>
                  <span>Source</span>
                  <strong>{normalizeSource(selectedBooking)}</strong>
                </div>
                <div>
                  <span>Status</span>
                  <strong>{formatStatus(selectedBooking.booking_status)}</strong>
                </div>
                <div>
                  <span>Payment</span>
                  <strong>{paymentStatus(selectedBooking)}</strong>
                </div>
              </div>
              {selectedBooking.notes ? (
                <div className="res-message-box">
                  <span>Notes</span>
                  <p>{selectedBooking.notes}</p>
                </div>
              ) : null}
              <div className="res-action-row">
                <button
                  className="small-btn"
                  type="button"
                  onClick={() => handleBookingAction(selectedBooking, "send_confirmation", "Send Confirmation")}
                >
                  Send Confirmation
                </button>
                <button
                  className="small-btn"
                  type="button"
                  onClick={() => handleBookingAction(selectedBooking, "add_trace", "Add Trace")}
                >
                  Add Trace
                </button>
                <button className="small-btn" type="button" onClick={() => setSelectedBooking(null)}>
                  Close
                </button>
              </div>
            </section>
          ) : null}

          <div className="res-kpi-grid">
            <ReservationMetric icon={<CalendarCheck />} label="Arrivals Today" value={arrivalsToday.length} />
            <ReservationMetric icon={<DoorOpen />} label="Departures Today" value={departuresToday.length} />
            <ReservationMetric icon={<BedDouble />} label="Occupancy %" value={`${occupancyPct}%`} />
            <ReservationMetric icon={<BadgePercent />} label="Expected Revenue" value={money(expectedRevenue)} />
            <ReservationMetric icon={<ShieldCheck />} label="Pending Confirmations" value={unconfirmedReservations.length + waitingDeposit.length} />
            <ReservationMetric icon={<Users />} label="Waitlist Count" value={waitlistCount} />
          </div>

          <section className="reservation-command-center">
            <div className="reservation-command-main">
              <div className="reservation-action-grid">
                <button type="button" className="reservation-action-card" onClick={() => navigate("/reservations/new")}>
                  <CalendarCheck aria-hidden="true" />
                  <strong>New Reservation</strong>
                  <span>Create and quote a new booking.</span>
                </button>
                <button type="button" className="reservation-action-card" onClick={() => navigate("/reservations/update")}>
                  <Edit3 aria-hidden="true" />
                  <strong>Update Reservation</strong>
                  <span>Open register for changes and notes.</span>
                </button>
                <Link className="reservation-action-card" to="/booking-hub">
                  <MessageCircle aria-hidden="true" />
                  <strong>Booking Hub</strong>
                  <span>Review public and AI booking requests.</span>
                </Link>
                <button type="button" className="reservation-action-card" onClick={() => navigate("/reservations/waitlist")}>
                  <Users aria-hidden="true" />
                  <strong>Waitlist</strong>
                  <span>Review guests waiting for availability.</span>
                </button>
                <button type="button" className="reservation-action-card" onClick={() => navigate("/reservations/blocks")}>
                  <BriefcaseBusiness aria-hidden="true" />
                  <strong>Blocks / Group Booking</strong>
                  <span>Manage corporate, event, and block demand.</span>
                </button>
                <button type="button" className="reservation-action-card" onClick={() => navigate("/reservations/profiles")}>
                  <Users aria-hidden="true" />
                  <strong>Profiles</strong>
                  <span>Open guest and company profiles.</span>
                </button>
                <button type="button" className="reservation-action-card" onClick={() => navigate("/reservations/room-plan")}>
                  <BedDouble aria-hidden="true" />
                  <strong>Room Plan</strong>
                  <span>Review room occupancy and assignment readiness.</span>
                </button>
                <button type="button" className="reservation-action-card" onClick={() => navigate("/reservations/floor-plan")}>
                  <MapPinned aria-hidden="true" />
                  <strong>Floor Plan</strong>
                  <span>Review room inventory grouped by floor.</span>
                </button>
                <button type="button" className="reservation-action-card" onClick={() => navigate("/reservations/confirmation")}>
                  <CheckCircle2 aria-hidden="true" />
                  <strong>Confirmation</strong>
                  <span>Check guarantee and confirmation status.</span>
                </button>
                <Link className="reservation-action-card" to="/frontdesk/registration-card">
                  <ClipboardList aria-hidden="true" />
                  <strong>Registration Cards</strong>
                  <span>Prepare arrival registration cards.</span>
                </Link>
                <button type="button" className="reservation-action-card" onClick={() => navigate("/reservations/calendar")}>
                  <CalendarDays aria-hidden="true" />
                  <strong>Calendar</strong>
                  <span>Open reservation calendar planning.</span>
                </button>
              </div>

              <div className="reservation-center-grid">
                <ReservationListPanel title="Today's Arrivals" rows={arrivalsToday} empty="No arrivals require reservation handoff today." />
                <ReservationListPanel title="Upcoming Arrivals" rows={upcomingArrivals} empty="No upcoming arrivals in the current booking set." />
                <ReservationListPanel title="VIP Guests" rows={vipGuests} empty="No VIP reservations flagged in live data." />
                <ReservationListPanel title="Unconfirmed Reservations" rows={unconfirmedReservations} empty="No unconfirmed reservations need follow-up." />
                <ReservationListPanel title="Group / Block Reservations" rows={groupBlockReservations} empty="No group or block reservations detected." />
              </div>
            </div>

            <aside className="reservation-tools-panel">
              <section className="card res-panel">
                <SectionHeader icon={<BedDouble />} title="Room Availability" subtitle="Safe availability snapshot from current reservations." />
                <div className="reservation-tool-metrics">
                  <div><span>Available</span><strong>{availableRooms}</strong></div>
                  <div><span>In-House</span><strong>{inHouseBookings.length}</strong></div>
                  <div><span>Arrivals</span><strong>{arrivalsToday.length}</strong></div>
                </div>
              </section>

              <section className="card res-panel">
                <SectionHeader icon={<BadgePercent />} title="Rate Quote" subtitle="Quick quote reference using existing rate plans." />
                <div className="reservation-rate-quote">
                  {ratePlans.slice(0, 3).map((plan) => (
                    <div key={plan.code}>
                      <span>{plan.code} | {plan.roomType}</span>
                      <strong>{money(plan.baseRate)}</strong>
                    </div>
                  ))}
                </div>
              </section>

              <section className="card res-panel">
                <SectionHeader icon={<CalendarDays />} title="Calendar" subtitle="Current business date and next arrival focus." />
                <div className="reservation-calendar-card">
                  <strong>{businessDate}</strong>
                  <span>{upcomingArrivals[0]?.check_in_date ? `Next arrival ${upcomingArrivals[0].check_in_date}` : "No future arrivals loaded"}</span>
                </div>
              </section>

              <section className="card res-panel">
                <SectionHeader icon={<StickyNote />} title="Quick Notes" subtitle="Front-office reminders for the reservation desk." />
                <ul className="reservation-quick-notes">
                  <li>Confirm pending deposits before 18:00.</li>
                  <li>Flag VIP and group arrivals for Front Desk handoff.</li>
                  <li>Keep waitlist requests separate from confirmed inventory.</li>
                </ul>
              </section>
            </aside>
          </section>

          <div className="res-tabs">
            {(Object.keys(tabs) as ReservationTab[]).map((tab) => (
              <button
                key={tab}
                className={`tab-btn res-tab-${tab} ${activeTab === tab ? "active" : ""}`}
                onClick={() => navigate(reservationTabPath[tab])}
              >
                {tabs[tab]}
              </button>
            ))}
          </div>

          {activeTab === "inbox" ? (
            <div className="res-inbox-layout">
              <section className="card res-panel res-inbox-card">
                <SectionHeader
                  icon={<Mail />}
                  title="Reservation Inbox"
                  subtitle="Raw demand from email, Telegram, chatbot, website, phone, agent, groups, and events."
                />
                <div className="res-filter-row">
                  <div className="field">
                    <label>Search</label>
                    <input
                      value={searchText}
                      onChange={(event) => setSearchText(event.target.value)}
                      placeholder="Guest, company, channel, request type"
                    />
                  </div>
                  <div className="field">
                    <label>Channel</label>
                    <select
                      value={channelFilter}
                      onChange={(event) => setChannelFilter(event.target.value)}
                    >
                      <option value="all">All Channels</option>
                      <option>Email</option>
                      <option>Telegram</option>
                      <option>Chatbot</option>
                      <option>Website</option>
                      <option>Phone</option>
                      <option>Agent</option>
                    </select>
                  </div>
                </div>

                <DataTable
                  rows={filteredInquiries}
                  emptyMessage="No reservation inquiries match the filters."
                  columns={[
                    {
                      key: "priority",
                      header: "Priority",
                      render: (row) => (
                        <span className={statusClass(row.priority)}>{row.priority}</span>
                      ),
                    },
                    {
                      key: "contact",
                      header: "Guest / Company",
                      render: (row) => (
                        <button
                          className="res-table-link"
                          onClick={() => setSelectedInquiryId(row.id)}
                        >
                          {row.contact_name}
                        </button>
                      ),
                    },
                    {
                      key: "channel",
                      header: "Channel",
                      render: (row) => (
                        <span className={sourceClass(row.channel)}>{row.channel}</span>
                      ),
                    },
                    {
                      key: "type",
                      header: "Request",
                      render: (row) => requestTypeLabels[row.request_type] || row.request_type,
                    },
                    {
                      key: "dates",
                      header: "Dates",
                      render: (row) => `${row.arrival_date} to ${row.departure_date}`,
                    },
                    {
                      key: "rooms",
                      header: "Rooms/Event",
                      render: (row) =>
                        row.event_type
                          ? `${row.event_type}, ${row.rooms_requested} rooms`
                          : `${row.rooms_requested} ${row.room_type}`,
                    },
                    {
                      key: "guarantee",
                      header: "Guarantee",
                      render: (row) => (
                        <span className={statusClass(row.guarantee_status)}>
                          {formatStatus(row.guarantee_status)}
                        </span>
                      ),
                    },
                    {
                      key: "status",
                      header: "Status",
                      render: (row) => (
                        <span className={statusClass(row.inquiry_status)}>
                          {formatStatus(row.inquiry_status)}
                        </span>
                      ),
                    },
                  ]}
                />
              </section>

              <InquiryDrawer
                inquiry={selectedInquiry}
                onMarkGuaranteed={markGuaranteed}
                onConvert={convertInquiry}
                onWaitlist={addInquiryToWaitlist}
              />
            </div>
          ) : null}

          {activeTab === "new" ? (
            <section className="card res-panel">
              <SectionHeader
                icon={<Send />}
                title="Manual Inquiry"
                subtitle="Create an agent, phone, corporate, travel agent, group, or event request before it becomes a booking."
              />
              <form className="res-form-grid" onSubmit={addManualInquiry}>
                <label>
                  Guest / Company
                  <input
                    value={newInquiry.contactName}
                    onChange={(event) =>
                      setNewInquiry((prev) => ({ ...prev, contactName: event.target.value }))
                    }
                    placeholder="Contact name"
                    required
                  />
                </label>
                <label>
                  Channel
                  <select
                    value={newInquiry.channel}
                    onChange={(event) =>
                      setNewInquiry((prev) => ({ ...prev, channel: event.target.value }))
                    }
                  >
                    <option>Email</option>
                    <option>Telegram</option>
                    <option>Chatbot</option>
                    <option>Website</option>
                    <option>Phone</option>
                    <option>Agent</option>
                    <option>Corporate</option>
                    <option>Travel Agent</option>
                  </select>
                </label>
                <label>
                  Request Type
                  <select
                    value={newInquiry.requestType}
                    onChange={(event) =>
                      setNewInquiry((prev) => ({ ...prev, requestType: event.target.value }))
                    }
                  >
                    {Object.entries(requestTypeLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Arrival
                  <input
                    type="date"
                    value={newInquiry.arrivalDate}
                    onChange={(event) =>
                      setNewInquiry((prev) => ({ ...prev, arrivalDate: event.target.value }))
                    }
                  />
                </label>
                <label>
                  Departure
                  <input
                    type="date"
                    value={newInquiry.departureDate}
                    onChange={(event) =>
                      setNewInquiry((prev) => ({ ...prev, departureDate: event.target.value }))
                    }
                  />
                </label>
                <label>
                  Room Type
                  <select
                    value={newInquiry.roomType}
                    onChange={(event) =>
                      setNewInquiry((prev) => ({ ...prev, roomType: event.target.value }))
                    }
                  >
                    <option>Standard</option>
                    <option>Deluxe</option>
                    <option>Suite</option>
                    <option>Twin</option>
                  </select>
                </label>
                <label>
                  Rooms
                  <input
                    inputMode="numeric"
                    value={newInquiry.roomsRequested}
                    onChange={(event) =>
                      setNewInquiry((prev) => ({ ...prev, roomsRequested: event.target.value }))
                    }
                  />
                </label>
                <label>
                  Adults
                  <input
                    inputMode="numeric"
                    value={newInquiry.adults}
                    onChange={(event) =>
                      setNewInquiry((prev) => ({ ...prev, adults: event.target.value }))
                    }
                  />
                </label>
                <label>
                  Children
                  <input
                    inputMode="numeric"
                    value={newInquiry.children}
                    onChange={(event) =>
                      setNewInquiry((prev) => ({ ...prev, children: event.target.value }))
                    }
                  />
                </label>
                <label className="span-3">
                  Message / Request
                  <textarea
                    value={newInquiry.message}
                    onChange={(event) =>
                      setNewInquiry((prev) => ({ ...prev, message: event.target.value }))
                    }
                    placeholder="Guest message, package questions, special requests, billing notes"
                  />
                </label>
                {availabilityQuote ? (
                  <div className="notice-box span-3">
                    <strong>
                      {availabilityQuote.availability.is_available ? "Availability Confirmed" : "Availability Warning"}
                    </strong>
                    <span>
                      {availabilityQuote.availability.available_rooms} available / {availabilityQuote.availability.requested_rooms} requested for {availabilityQuote.availability.room_type}
                    </span>
                    <span>
                      Rate {availabilityQuote.quote.rate_code} - {availabilityQuote.quote.rate_label}: {money(availabilityQuote.quote.total_etb)}
                    </span>
                    <span>
                      Service {money(availabilityQuote.quote.service_charge_etb)} / Tax {money(availabilityQuote.quote.tax_etb)} / Deposit {money(availabilityQuote.quote.deposit_required_etb)}
                    </span>
                    <span>{availabilityQuote.quote.cancellation_policy}</span>
                  </div>
                ) : null}
                <div className="form-actions span-3">
                  <button className="small-btn" type="button" onClick={handleAvailabilityQuote}>
                    Check Availability / Quote
                  </button>
                  <button className="primary-btn" type="submit" disabled={busyAction === "create-reservation"}>
                    {busyAction === "create-reservation" ? "Creating..." : "Create Reservation"}
                  </button>
                </div>
              </form>
            </section>
          ) : null}

          {activeTab === "search" ? (
            <ReservationRegister
              bookings={bookings}
              businessDate={businessDate}
              busyAction={busyAction}
              onBookingAction={handleBookingAction}
            />
          ) : null}

          {activeTab === "groups" ? (
            <BlockDesk
              blocks={reservationBlocks}
              leads={groupEventLeads.filter((item) => item.request_type === "group_room")}
              onCreate={createBlockFromLead}
              onAction={runBlockAction}
            />
          ) : null}

          {activeTab === "profiles" ? (
            <ReservationProfilesDesk
              bookings={bookings}
              inquiries={inquiries}
              businessDate={businessDate}
            />
          ) : null}

          {activeTab === "waitlist" ? (
            <WaitlistDesk
              items={waitlistItems}
              bookings={bookings.filter((row) => String(row.q_status || "").toLowerCase() === "waiting")}
              onAction={runWaitlistAction}
            />
          ) : null}

          {activeTab === "roomPlan" ? <RoomPlanDesk rooms={rooms} mode="room" /> : null}

          {activeTab === "floorPlan" ? <RoomPlanDesk rooms={rooms} mode="floor" /> : null}

          {activeTab === "calendar" ? (
            <ReservationCalendar bookings={bookings} businessDate={businessDate} />
          ) : null}

          {activeTab === "guarantee" ? (
            <GuaranteeDesk
              inquiries={waitingDeposit}
              bookings={pendingGuaranteeBookings}
              deposits={depositAccounts}
              onMarkGuaranteed={markGuaranteed}
              busyAction={busyAction}
              onBookingAction={handleBookingAction}
            />
          ) : null}

          {activeTab === "handoff" ? (
            <HandoffDesk
              arrivals={arrivalsToday}
              inquiries={inquiries.filter((item) => item.inquiry_status === "converted")}
              busyAction={busyAction}
              onBookingAction={handleBookingAction}
            />
          ) : null}
        </>
      )}
    </div>
  );
}

function ReservationListPanel({
  title,
  rows,
  empty,
}: {
  title: string;
  rows: FrontdeskBooking[];
  empty: string;
}) {
  return (
    <section className="card res-panel reservation-list-panel">
      <h3>{title}</h3>
      <div className="reservation-list-stack">
        {rows.length ? (
          rows.slice(0, 5).map((row) => (
            <div key={row.id} className="reservation-list-row">
              <div>
                <strong>{row.guest_name}</strong>
                <span>{row.check_in_date} to {row.check_out_date}</span>
              </div>
              <small>{row.room_number || row.room_type || "Room TBD"}</small>
            </div>
          ))
        ) : (
          <div className="empty-state">{empty}</div>
        )}
      </div>
    </section>
  );
}

function ReservationComingSoonPanel({
  icon,
  title,
  subtitle,
  items,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  items: string[];
}) {
  return (
    <section className="card res-panel reservation-coming-soon-panel">
      <SectionHeader icon={icon} title={title} subtitle={subtitle} />
      <div className="reservation-coming-soon-grid">
        {items.map((item) => (
          <div key={item}>
            <span>{item}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function ReservationProfilesDesk({
  bookings,
  inquiries,
  businessDate,
}: {
  bookings: FrontdeskBooking[];
  inquiries: ReservationInquiry[];
  businessDate: string;
}) {
  const bookingProfiles = bookings.map((booking) => {
    const source = normalizeSource(booking);
    const isCompany =
      /corporate|company|direct bill|group|event|wedding/i.test(
        `${source} ${booking.room_type || ""} ${booking.notes || ""}`
      );
    return {
      id: `booking-${booking.id}`,
      profileName: booking.guest_name,
      profileType: isCompany ? "Company / Group" : "Guest",
      contact: booking.guest_email || source || "Contact pending",
      source,
      stay: `${booking.check_in_date} to ${booking.check_out_date}`,
      value: Number(booking.total_amount || booking.rate_per_night_etb || 0),
      status: booking.booking_status || "open",
      action: booking.check_in_date >= businessDate ? "Prepare arrival profile" : "Review stay history",
    };
  });

  const inquiryProfiles = inquiries.map((inquiry) => ({
    id: `inquiry-${inquiry.id}`,
    profileName: inquiry.contact_name,
    profileType:
      inquiry.request_type.includes("corporate") || inquiry.request_type.includes("group")
        ? "Company / Group"
        : inquiry.request_type.includes("travel_agent")
        ? "Travel Agent"
        : "Guest",
    contact: inquiry.channel,
    source: inquiry.channel,
    stay: `${inquiry.arrival_date} to ${inquiry.departure_date}`,
    value: 0,
    status: inquiry.inquiry_status,
    action: inquiry.action_needed,
  }));

  const profiles = [...bookingProfiles, ...inquiryProfiles];
  const guestCount = profiles.filter((profile) => profile.profileType === "Guest").length;
  const companyCount = profiles.filter((profile) => profile.profileType === "Company / Group").length;
  const travelAgentCount = profiles.filter((profile) => profile.profileType === "Travel Agent").length;
  const profileValue = profiles.reduce((sum, profile) => sum + profile.value, 0);

  return (
    <section className="card res-panel">
      <SectionHeader
        icon={<Users />}
        title="Reservation Profiles"
        subtitle="Guest, company, group, and travel-agent context used by the Reservations desk."
      />
      <div className="res-roadmap-strip">
        <div><span>Guest Profiles</span><strong>{guestCount}</strong></div>
        <div><span>Company / Groups</span><strong>{companyCount}</strong></div>
        <div><span>Travel Agents</span><strong>{travelAgentCount}</strong></div>
        <div><span>Profile Value</span><strong>{money(profileValue)}</strong></div>
      </div>
      <DataTable
        rows={profiles}
        emptyMessage="No reservation profiles are available for this property yet."
        columns={[
          { key: "name", header: "Profile", render: (row) => row.profileName },
          { key: "type", header: "Type", render: (row) => <span className="pill">{row.profileType}</span> },
          { key: "contact", header: "Contact / Channel", render: (row) => row.contact },
          { key: "source", header: "Source", render: (row) => <span className={sourceClass(row.source)}>{row.source}</span> },
          { key: "stay", header: "Stay / Request", render: (row) => row.stay },
          { key: "value", header: "Value", render: (row) => money(row.value) },
          { key: "status", header: "Status", render: (row) => <span className={statusClass(row.status)}>{formatStatus(row.status)}</span> },
          { key: "action", header: "Reservation Action", render: (row) => row.action },
        ]}
      />
      <div className="res-action-row" style={{ marginTop: "14px" }}>
        <Link className="small-btn" to="/guest-profiles">
          Open Guest 360
        </Link>
        <Link className="small-btn" to="/guest-feedback">
          Open Feedback / Recovery
        </Link>
      </div>
    </section>
  );
}

function WaitlistDesk({
  items,
  bookings,
  onAction,
}: {
  items: ReservationWaitlistItem[];
  bookings: FrontdeskBooking[];
  onAction: (item: ReservationWaitlistItem, action: "review" | "convert" | "cancel") => void;
}) {
  return (
    <section className="card res-panel">
      <SectionHeader
        icon={<Users />}
        title="Waitlist"
        subtitle="Guests waiting for room availability, ordered for reservation follow-up."
      />
      <div className="reservation-waitlist-grid">
        {items.map((item) => (
          <article className="reservation-waitlist-card" key={item.id}>
            <div>
              <strong>{item.guest_name}</strong>
              <span className={statusClass(item.status)}>{formatStatus(item.status)}</span>
            </div>
            <p>{item.check_in_date} to {item.check_out_date}</p>
            <p>{item.rooms} {item.room_type} room(s) · {item.adults + item.children} guest(s)</p>
            <small>{item.notes || `${item.source} waitlist request`}</small>
            <div className="res-action-row">
              <button
                className="primary-btn"
                type="button"
                disabled={["converted", "cancelled"].includes(item.status)}
                onClick={() => onAction(item, "review")}
              >
                Review Availability
              </button>
              <button
                className="small-btn"
                type="button"
                disabled={item.status !== "available"}
                onClick={() => onAction(item, "convert")}
              >
                Convert
              </button>
              <button
                className="small-btn"
                type="button"
                disabled={["converted", "cancelled"].includes(item.status)}
                onClick={() => onAction(item, "cancel")}
              >
                Cancel
              </button>
            </div>
          </article>
        ))}
        {bookings.map((booking) => (
          <article className="reservation-waitlist-card" key={`booking-${booking.id}`}>
            <div>
              <strong>{booking.guest_name}</strong>
              <span className="pill pill-warning">PMS queue</span>
            </div>
            <p>{booking.check_in_date} to {booking.check_out_date}</p>
            <p>{booking.room_type || "Room type pending"}</p>
            <small>Booking #{booking.id} is waiting for room readiness or inventory release.</small>
          </article>
        ))}
        {!items.length && !bookings.length ? (
          <div className="empty-state">No guests are currently waiting for availability.</div>
        ) : null}
      </div>
    </section>
  );
}

function RoomPlanDesk({ rooms, mode }: { rooms: RoomStatusItem[]; mode: "room" | "floor" }) {
  const sortedRooms = [...rooms].sort(
    (a, b) => a.floor - b.floor || a.room_number.localeCompare(b.room_number, undefined, { numeric: true })
  );
  const floors = Array.from(new Set(sortedRooms.map((room) => room.floor)));
  const content = mode === "floor" ? floors : [null];

  return (
    <section className="card res-panel">
      <SectionHeader
        icon={mode === "floor" ? <MapPinned /> : <BedDouble />}
        title={mode === "floor" ? "Floor Plan" : "Room Plan"}
        subtitle={mode === "floor" ? "Room inventory grouped by hotel floor." : "Live room occupancy and reservation-assignment readiness."}
      />
      {content.map((floor) => {
        const floorRooms = floor === null ? sortedRooms : sortedRooms.filter((room) => room.floor === floor);
        return (
          <div className="reservation-floor-group" key={floor ?? "all"}>
            {floor !== null ? <h3>Floor {floor}</h3> : null}
            <div className="reservation-room-plan-grid">
              {floorRooms.map((room) => {
                const status = room.is_occupied ? "occupied" : String(room.hk_status || "unknown").replace(/_/g, " ");
                return (
                  <article className={`reservation-room-card ${room.is_occupied ? "occupied" : "available"}`} key={room.room_number}>
                    <div>
                      <strong>{room.room_number}</strong>
                      <span className={room.is_occupied ? "pill pill-warning" : "pill pill-success"}>{status}</span>
                    </div>
                    <span>{room.room_type || "Standard Room"}</span>
                    <small>{room.guest_name || (room.is_occupied ? "Occupied" : "Available for assignment")}</small>
                  </article>
                );
              })}
            </div>
          </div>
        );
      })}
      {!rooms.length ? <div className="empty-state">No room-plan data is available for this property.</div> : null}
    </section>
  );
}

function ReservationCalendar({ bookings, businessDate }: { bookings: FrontdeskBooking[]; businessDate: string }) {
  const calendarDates = Array.from(
    new Set([businessDate, ...bookings.flatMap((booking) => [booking.check_in_date, booking.check_out_date])])
  )
    .filter(Boolean)
    .sort()
    .slice(0, 21);

  return (
    <section className="card res-panel">
      <SectionHeader
        icon={<CalendarDays />}
        title="Reservation Calendar"
        subtitle="Arrival, departure, and in-house demand by operating date."
      />
      <div className="reservation-calendar-grid">
        {calendarDates.map((date) => {
          const arrivals = bookings.filter((booking) => booking.check_in_date === date);
          const departures = bookings.filter((booking) => booking.check_out_date === date);
          const inHouse = bookings.filter((booking) => booking.check_in_date <= date && booking.check_out_date > date && !isClosedReservation(booking));
          return (
            <article className={date === businessDate ? "today" : ""} key={date}>
              <div>
                <strong>{date}</strong>
                {date === businessDate ? <span className="pill pill-success">Business Date</span> : null}
              </div>
              <dl>
                <div><dt>Arrivals</dt><dd>{arrivals.length}</dd></div>
                <div><dt>Departures</dt><dd>{departures.length}</dd></div>
                <div><dt>In House</dt><dd>{inHouse.length}</dd></div>
              </dl>
              <small>{arrivals.slice(0, 3).map((booking) => booking.guest_name).join(", ") || "No arrivals"}</small>
            </article>
          );
        })}
      </div>
      {!calendarDates.length ? <div className="empty-state">No reservation dates are available.</div> : null}
    </section>
  );
}

function ReservationMetric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
}) {
  return (
    <div className="res-metric">
      <div className="res-metric-icon">{icon}</div>
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
    <div className="section-heading res-section-heading">
      <div>
        <div className="res-title-row">
          <span>{icon}</span>
          <h2>{title}</h2>
        </div>
        <p className="muted">{subtitle}</p>
      </div>
    </div>
  );
}

function InquiryDrawer({
  inquiry,
  onMarkGuaranteed,
  onConvert,
  onWaitlist,
}: {
  inquiry?: ReservationInquiry;
  onMarkGuaranteed: (id: number) => void;
  onConvert: (id: number) => void;
  onWaitlist: (inquiry: ReservationInquiry) => void;
}) {
  if (!inquiry) {
    return <aside className="card res-drawer res-inquiry-detail-card">Select an inquiry to review.</aside>;
  }

  return (
    <aside className="card res-drawer res-inquiry-detail-card">
      <SectionHeader
        icon={<ClipboardList />}
        title="Inquiry Detail"
        subtitle="Availability, quote, internal note, and handoff preparation."
      />
      <div className="res-detail-stack">
        <div>
          <span>Contact</span>
          <strong>{inquiry.contact_name}</strong>
        </div>
        <div>
          <span>Request Type</span>
          <strong>{requestTypeLabels[inquiry.request_type] || inquiry.request_type}</strong>
        </div>
        <div>
          <span>Stay / Event</span>
          <strong>
            {inquiry.arrival_date} to {inquiry.departure_date}
          </strong>
        </div>
        <div>
          <span>Guests</span>
          <strong>
            {inquiry.adults} adults, {inquiry.children} children
          </strong>
        </div>
      </div>
      <div className="res-message-box">
        <span>Last Message</span>
        <p>{inquiry.last_message}</p>
      </div>
      <div className="res-message-box">
        <span>Suggested Reply</span>
        <p>
          Thank you for your request. We are checking availability for{" "}
          {inquiry.rooms_requested} {inquiry.room_type} room(s). To guarantee the
          reservation, please confirm the deposit or approved guarantee method.
        </p>
      </div>
      <div className="res-action-row">
        <button className="small-btn" onClick={() => onWaitlist(inquiry)}>
          Add to Waitlist
        </button>
        <button className="small-btn" onClick={() => onMarkGuaranteed(inquiry.id)}>
          Mark Guaranteed
        </button>
        <button
          className="primary-btn res-convert-btn"
          onClick={() => onConvert(inquiry.id)}
        >
          Convert / Handoff
        </button>
      </div>
    </aside>
  );
}

function ReservationRegister({
  bookings,
  businessDate,
  busyAction,
  onBookingAction,
}: {
  bookings: FrontdeskBooking[];
  businessDate: string;
  busyAction: string | null;
  onBookingAction: (
    booking: FrontdeskBooking,
    action: ReservationWorkflowAction,
    label: string
  ) => void;
}) {
  return (
    <section className="card res-panel">
      <SectionHeader
        icon={<CalendarCheck />}
        title="Reservation Search"
        subtitle="Confirmed and active bookings already in PMS, separate from raw inbox demand."
      />
      <DataTable
        rows={bookings}
        emptyMessage="No bookings found."
        columns={[
          { key: "id", header: "Booking ID", render: (row) => `#${row.id}` },
          { key: "guest", header: "Guest", render: (row) => row.guest_name },
          {
            key: "source",
            header: "Source",
            render: (row) => (
              <span className={sourceClass(normalizeSource(row))}>
                {normalizeSource(row)}
              </span>
            ),
          },
          { key: "arrival", header: "Arrival", render: (row) => row.check_in_date },
          { key: "departure", header: "Departure", render: (row) => row.check_out_date },
          { key: "room", header: "Room", render: (row) => normalizeRoom(row) },
          {
            key: "guarantee",
            header: "Guarantee",
            render: (row) => (
              <span className={statusClass(guaranteeFromBooking(row))}>
                {formatStatus(guaranteeFromBooking(row))}
              </span>
            ),
          },
          {
            key: "handoff",
            header: "Handoff",
            render: (row) =>
              row.check_in_date === businessDate ? (
                <span className="pill pill-warning">front desk today</span>
              ) : (
                <span className="pill">future</span>
              ),
          },
          {
            key: "actions",
            header: "Actions",
            render: (row) => (
              <div className="res-action-row">
                <button
                  className="small-btn"
                  disabled={Boolean(busyAction?.startsWith(`${row.id}-`))}
                  onClick={() => onBookingAction(row, "open_reservation", "Open Reservation")}
                  type="button"
                >
                  Open
                </button>
                <button
                  className="small-btn"
                  disabled={Boolean(busyAction?.startsWith(`${row.id}-`))}
                  onClick={() => onBookingAction(row, "send_confirmation", "Send Confirmation")}
                  type="button"
                >
                  Confirm
                </button>
              </div>
            ),
          },
        ]}
      />
    </section>
  );
}

function RateManagementDesk() {
  return (
    <section className="card res-panel">
      <SectionHeader
        icon={<BadgePercent />}
        title="Rate Management"
        subtitle="Version 1 revenue optimization lives inside Reservations: rate codes, seasonal controls, and manager approval rules."
      />
      <DataTable
        rows={ratePlans}
        columns={[
          { key: "code", header: "Rate Code", render: (row) => row.code },
          { key: "name", header: "Name", render: (row) => row.name },
          { key: "segment", header: "Segment", render: (row) => row.segment },
          { key: "roomType", header: "Room Type", render: (row) => row.roomType },
          { key: "baseRate", header: "Base Rate", render: (row) => money(row.baseRate) },
          { key: "range", header: "Allowed Range", render: (row) => `${money(row.minRate)} - ${money(row.maxRate)}` },
          { key: "status", header: "Control", render: (row) => <span className="pill pill-warning">{row.status}</span> },
        ]}
      />
      <div className="res-roadmap-strip">
        <div><span>Version 1</span><strong>Rate Management</strong></div>
        <div><span>Version 2</span><strong>Advanced Rate Rules</strong></div>
        <div><span>Version 3</span><strong>Dedicated Revenue Management</strong></div>
      </div>
    </section>
  );
}

function CorporateContractsDesk() {
  return (
    <section className="card res-panel">
      <SectionHeader
        icon={<BriefcaseBusiness />}
        title="Corporate Contracts"
        subtitle="Preferred accounts, direct-bill rules, negotiated rates, and group/corporate guarantees."
      />
      <DataTable
        rows={corporateContracts}
        columns={[
          { key: "account", header: "Account", render: (row) => row.account },
          { key: "rateCode", header: "Rate Code", render: (row) => row.rateCode },
          { key: "discount", header: "Discount", render: (row) => row.discount },
          { key: "guarantee", header: "Guarantee", render: (row) => row.guarantee },
          { key: "validUntil", header: "Valid Until", render: (row) => row.validUntil },
        ]}
      />
    </section>
  );
}

function ChannelControlDesk() {
  return (
    <section className="card res-panel">
      <SectionHeader
        icon={<MessageCircle />}
        title="OTA / Channel Controls"
        subtitle="Channel availability, rate-code mapping, and booking-source review before a future standalone revenue module."
      />
      <DataTable
        rows={channelControls}
        columns={[
          { key: "channel", header: "Channel", render: (row) => row.channel },
          { key: "status", header: "Status", render: (row) => <span className="pill pill-success">{row.status}</span> },
          { key: "rateCode", header: "Rate Code", render: (row) => row.rateCode },
          { key: "allotment", header: "Allotment", render: (row) => row.allotment },
        ]}
      />
    </section>
  );
}

function BlockDesk({
  blocks,
  leads,
  onCreate,
  onAction,
}: {
  blocks: ReservationBlock[];
  leads: ReservationInquiry[];
  onCreate: (lead: ReservationInquiry) => void;
  onAction: (block: ReservationBlock, action: "quote" | "deposit" | "confirm" | "cancel") => void;
}) {
  const persistedNames = new Set(blocks.map((block) => block.block_name.toLowerCase()));
  return (
    <section className="card res-panel">
      <SectionHeader
        icon={<Users />}
        title="Blocks / Group Booking"
        subtitle="Persistent group inventory blocks, quotes, deposits, and confirmation status."
      />
      <div className="res-lead-grid">
        {blocks.map((block) => (
          <article className="res-lead-card" key={block.id}>
            <div>
              <strong>{block.block_name}</strong>
              <span className={statusClass(block.status)}>{formatStatus(block.status)}</span>
            </div>
            <p>{block.check_in_date} to {block.check_out_date} · {block.rooms} {block.room_type} room(s)</p>
            <div className="res-mini-grid">
              <span>{block.company_name || block.contact_name}</span>
              <span>{block.quoted_amount ? money(Number(block.quoted_amount)) : "Not quoted"}</span>
              <span>{block.deposit_amount ? `${money(Number(block.deposit_amount))} deposit` : "No deposit request"}</span>
            </div>
            <div className="res-action-row">
              <button className="primary-btn" type="button" disabled={["cancelled", "confirmed"].includes(block.status)} onClick={() => onAction(block, "quote")}>Quote</button>
              <button className="small-btn" type="button" disabled={!['quoted', 'deposit_requested'].includes(block.status)} onClick={() => onAction(block, "deposit")}>Request Deposit</button>
              <button className="small-btn" type="button" disabled={block.status !== "deposit_requested"} onClick={() => onAction(block, "confirm")}>Confirm</button>
              <button className="small-btn" type="button" disabled={block.status === "cancelled"} onClick={() => onAction(block, "cancel")}>Cancel</button>
            </div>
          </article>
        ))}
        {leads.filter((lead) => !persistedNames.has(lead.contact_name.toLowerCase())).map((lead) => (
          <article className="res-lead-card" key={`lead-${lead.id}`}>
            <div><strong>{lead.contact_name}</strong><span className="pill">Inbox lead</span></div>
            <p>{lead.last_message}</p>
            <div className="res-mini-grid"><span>{lead.rooms_requested} rooms</span><span>{lead.arrival_date}</span><span>{lead.assigned_agent}</span></div>
            <button className="primary-btn" type="button" onClick={() => onCreate(lead)}>Create Tentative Block</button>
          </article>
        ))}
        {!blocks.length && !leads.length ? <div className="empty-state">No group blocks or leads found.</div> : null}
      </div>
    </section>
  );
}

function LeadBoard({
  title,
  icon,
  leads,
  onUpdate,
}: {
  title: string;
  icon: React.ReactNode;
  leads: ReservationInquiry[];
  onUpdate?: (id: number, status: InquiryStatus, message: string) => void;
}) {
  return (
    <section className="card res-panel">
      <SectionHeader
        icon={icon}
        title={title}
        subtitle="Track room blocks, billing instructions, deposits, contracts, and coordinator ownership."
      />
      <div className="res-lead-grid">
        {leads.length ? (
          leads.map((lead) => (
            <div className="res-lead-card" key={lead.id}>
              <div>
                <strong>{lead.contact_name}</strong>
                <span>{requestTypeLabels[lead.request_type]}</span>
              </div>
              <span className={statusClass(lead.guarantee_status)}>
                {formatStatus(lead.guarantee_status)}
              </span>
              <p>{lead.last_message}</p>
              <div className="res-mini-grid">
                <span>{lead.rooms_requested} rooms</span>
                <span>{lead.event_guest_count || lead.adults} guests</span>
                <span>{lead.assigned_agent}</span>
              </div>
              {onUpdate ? (
                <div className="res-action-row">
                  <button
                    className="primary-btn"
                    type="button"
                    onClick={() => onUpdate(lead.id, "quoted", `${lead.contact_name} block moved to quote review.`)}
                  >
                    Review Block
                  </button>
                  <button
                    className="small-btn"
                    type="button"
                    onClick={() => onUpdate(lead.id, "waiting_deposit", `${lead.contact_name} block is awaiting deposit.`)}
                  >
                    Request Deposit
                  </button>
                </div>
              ) : null}
            </div>
          ))
        ) : (
          <div className="muted">No leads in this queue.</div>
        )}
      </div>
    </section>
  );
}

function GuaranteeDesk({
  inquiries,
  bookings,
  deposits,
  onMarkGuaranteed,
  busyAction,
  onBookingAction,
}: {
  inquiries: ReservationInquiry[];
  bookings: FrontdeskBooking[];
  deposits: DepositAccount[];
  onMarkGuaranteed: (id: number) => void;
  busyAction: string | null;
  onBookingAction: (
    booking: FrontdeskBooking,
    action: ReservationWorkflowAction,
    label: string
  ) => void;
}) {
  return (
    <section className="card res-panel">
      <SectionHeader
        icon={<ShieldCheck />}
        title="Guarantee Desk"
        subtitle="Pending deposits, non-guaranteed reservations, expiring holds, and manager-approved guarantees."
      />
      <div className="res-guarantee-grid">
        {inquiries.map((item) => (
          <div className="res-guarantee-card" key={item.id}>
            <strong>{item.contact_name}</strong>
            <span className={statusClass(item.guarantee_status)}>
              {formatStatus(item.guarantee_status)}
            </span>
            <p>{item.action_needed}</p>
            <button className="small-btn" onClick={() => onMarkGuaranteed(item.id)}>
              Mark Guaranteed
            </button>
          </div>
        ))}
        {bookings.map((booking) => (
          <div className="res-guarantee-card" key={`booking-${booking.id}`}>
            <strong>{booking.guest_name}</strong>
            <span className={statusClass(guaranteeFromBooking(booking))}>
              {formatStatus(guaranteeFromBooking(booking))}
            </span>
            <p>
              Payment {paymentStatus(booking)}. Review deposit, card, company
              guarantee, or manager-approved pay-at-hotel before Check-In.
            </p>
            {deposits.find((deposit) => deposit.booking_id === booking.id) ? (() => {
              const deposit = deposits.find((item) => item.booking_id === booking.id)!;
              return (
                <p>
                  Requested {money(Number(deposit.requested_amount))}; paid {money(Number(deposit.paid_amount))};
                  remaining {money(Number(deposit.remaining_amount))}; allocated {money(Number(deposit.allocated_amount))}.
                  {" "}{deposit.refundable ? "Refundable" : "Non-refundable"}; {deposit.payment_method || "method pending"};
                  reference {deposit.reference || "pending"}; status {formatStatus(deposit.status)}.
                </p>
              );
            })() : null}
            <span className="pill">Booking #{booking.id}</span>
            <div className="res-action-row">
              {[
                "Open Reservation",
                "Send Deposit Link",
                "Record Deposit",
                "Request Card Guarantee",
                "Approve Pay at Hotel",
                "Mark Guaranteed",
                "Hold at Front Desk",
                "Add Trace",
                "Cancel by Deadline",
              ].map((label, index) => (
                <button
                  className={index === 0 ? "primary-btn" : "small-btn"}
                  disabled={Boolean(busyAction?.startsWith(`${booking.id}-`))}
                  key={label}
                  onClick={() =>
                    onBookingAction(booking, bookingActionByLabel[label], label)
                  }
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function HandoffDesk({
  arrivals,
  inquiries,
  busyAction,
  onBookingAction,
}: {
  arrivals: FrontdeskBooking[];
  inquiries: ReservationInquiry[];
  busyAction: string | null;
  onBookingAction: (
    booking: FrontdeskBooking,
    action: ReservationWorkflowAction,
    label: string
  ) => void;
}) {
  return (
    <section className="card res-panel">
      <SectionHeader
        icon={<Sparkles />}
        title="Handoff to Front Desk"
        subtitle="Clean arrival data, VIP notes, guarantee warnings, and group/event alerts."
      />
      <div className="res-handoff-grid">
        {arrivals.map((arrival) => (
          <div className="res-handoff-card" key={arrival.id}>
            <strong>{arrival.guest_name}</strong>
            <span className={statusClass(guaranteeFromBooking(arrival))}>
              {formatStatus(guaranteeFromBooking(arrival))}
            </span>
            <p>
              Arrival today. Room type {arrival.room_type || "pending"}, room{" "}
              {arrival.room_number || "not assigned"}.
            </p>
            <div className="res-message-box">
              <span>Handoff Status</span>
              <p>{handoffStatus(arrival)}</p>
            </div>
            <div className="res-action-row">
              {actionButtonLabels(arrival).map((label, index) => (
                <button
                  className={index === 0 ? "primary-btn" : "small-btn"}
                  disabled={Boolean(busyAction?.startsWith(`${arrival.id}-`))}
                  key={label}
                  onClick={() =>
                    onBookingAction(arrival, bookingActionByLabel[label], label)
                  }
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ))}
        {inquiries.map((inquiry) => (
          <div className="res-handoff-card" key={inquiry.id}>
            <strong>{inquiry.contact_name}</strong>
            <span className={statusClass(inquiry.priority)}>{inquiry.priority}</span>
            <p>{inquiry.action_needed}</p>
            <span className="pill pill-inspected">
              {requestTypeLabels[inquiry.request_type]}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
