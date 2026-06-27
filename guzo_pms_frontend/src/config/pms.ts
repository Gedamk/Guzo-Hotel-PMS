import {
  LayoutDashboard,
  BookOpen,
  MonitorSmartphone,
  BedDouble,
  BarChart3,
  ShieldCheck,
  Bot,
  ChefHat,
  Users,
  WalletCards,
  type LucideIcon,
} from "lucide-react";
import type { HotelProperty } from "../types/pms";

export const HOTEL_NAME = "Guzo PMS";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const API_BASE = API_BASE_URL;

export const AUTH_TOKEN =
  import.meta.env.VITE_AUTH_TOKEN || "";

export const PMS_USER_EMAIL =
  import.meta.env.VITE_PMS_USER_EMAIL || "admin@guzo.local";

export const DEV_AUTH_FALLBACK =
  String(import.meta.env.VITE_DEV_AUTH_FALLBACK ?? import.meta.env.DEV).toLowerCase() === "true";

export const PROPERTY_CODE =
  import.meta.env.VITE_PROPERTY_CODE || "DRE001";

export const PROPERTY_NAME =
  import.meta.env.VITE_PROPERTY_NAME || "Dream Big Hotel";

function getBrowserBusinessDate() {
  const now = new Date();
  const timezoneOffsetMs = now.getTimezoneOffset() * 60 * 1000;
  return new Date(now.getTime() - timezoneOffsetMs).toISOString().slice(0, 10);
}

export const BUSINESS_DATE =
  getBrowserBusinessDate();

export const DEFAULT_PROPERTY_CODE = PROPERTY_CODE;
export const DEFAULT_PROPERTY_NAME = PROPERTY_NAME;
export const DEFAULT_BUSINESS_DATE = BUSINESS_DATE;

export const HOTEL_NAME_BY_PROPERTY: Record<string, string> = {
  DRE001: "Dream Big Hotel",
  NN002: "N&N Hotel",
};

export const DEFAULT_PROPERTY_OPTIONS: HotelProperty[] = [
  {
    code: "DRE001",
    name: "Dream Big Hotel",
    address: "Bole Road",
    city: "Addis Ababa",
    country: "Ethiopia",
    timezone: "Africa/Addis_Ababa",
    currency: "ETB",
    phone: "+251 11 000 0000",
    email: "admin@dreambig.local",
    isActive: true,
    onboardingStatus: "complete",
  },
  {
    code: "NN002",
    name: "N&N Hotel",
    address: "Airport District",
    city: "Addis Ababa",
    country: "Ethiopia",
    timezone: "Africa/Addis_Ababa",
    currency: "ETB",
    phone: "+251 11 000 0001",
    email: "admin@nnhotel.local",
    isActive: true,
    onboardingStatus: "in_progress",
  },
];

export const PROPERTY_OPTIONS = DEFAULT_PROPERTY_OPTIONS;

export function getPropertyName(propertyCode?: string) {
  if (!propertyCode) return DEFAULT_PROPERTY_NAME;
  return HOTEL_NAME_BY_PROPERTY[propertyCode] || propertyCode;
}

export type NavItem = {
  path: string;
  label: string;
  icon: LucideIcon;
  group:
    | "dashboard"
    | "reservations"
    | "frontdesk"
    | "finance"
    | "rooms"
    | "fnb"
    | "profiles"
    | "reports"
    | "admin"
    | "ai";
};

export type PmsNavChild = {
  label: string;
  path: string;
  comingSoon?: boolean;
};

export type PmsNavGroup = {
  key: NavItem["group"];
  label: string;
  path: string;
  icon: LucideIcon;
  activePaths: string[];
  items: PmsNavChild[];
};

function comingSoonPath(label: string) {
  return `/coming-soon?feature=${encodeURIComponent(label)}`;
}

export const PMS_NAV_GROUPS: PmsNavGroup[] = [
  {
    key: "dashboard",
    label: "Dashboard",
    path: "/dashboard",
    icon: LayoutDashboard,
    activePaths: ["/dashboard"],
    items: [],
  },
  {
    key: "reservations",
    label: "Reservations",
    path: "/reservations",
    icon: BookOpen,
    activePaths: ["/reservations", "/booking", "/booking-hub"],
    items: [
      { label: "New Reservation", path: "/reservations/new" },
      { label: "Update Reservation", path: "/reservations/update" },
      { label: "Booking Hub", path: "/booking-hub" },
      { label: "Waitlist", path: "/reservations/waitlist" },
      { label: "Blocks / Group Booking", path: "/reservations/blocks" },
      { label: "Profiles", path: "/reservations/profiles" },
      { label: "Room Plan", path: "/reservations/room-plan" },
      { label: "Floor Plan", path: "/reservations/floor-plan" },
      { label: "Confirmation", path: "/reservations/confirmation" },
      { label: "Registration Cards", path: "/frontdesk/registration-card" },
      { label: "Calendar", path: "/reservations/calendar" },
    ],
  },
  {
    key: "frontdesk",
    label: "Front Desk",
    path: "/frontdesk",
    icon: MonitorSmartphone,
    activePaths: ["/frontdesk"],
    items: [
      { label: "House Status", path: "/frontdesk/house-status" },
      { label: "Arrivals", path: "/frontdesk/arrivals" },
      { label: "Room Assignment", path: "/frontdesk/room-assignment" },
      { label: "Registration Card", path: "/frontdesk/registration-card" },
      { label: "Payment/Auth", path: "/frontdesk/payment-auth" },
      { label: "Queue If Room Not Ready", path: "/frontdesk/queue-rooms" },
      { label: "Check-In", path: "/frontdesk/check-in" },
      { label: "In-House", path: "/frontdesk/in-house" },
      { label: "Folio / Guest Service", path: "/frontdesk/folio-guest-service" },
      { label: "Queue Reservation", path: "/frontdesk/queue-reservation" },
      { label: "Account", path: "/frontdesk/accounts" },
      { label: "Messages", path: "/frontdesk/messages" },
      { label: "Traces", path: "/frontdesk/traces" },
      { label: "Wake-Up Calls", path: "/frontdesk/wake-up-calls" },
      { label: "Departures", path: "/frontdesk/departures" },
      { label: "Walk-In", path: "/frontdesk/walk-in" },
    ],
  },
  {
    key: "finance",
    label: "Cashiering / Finance",
    path: "/finance",
    icon: WalletCards,
    activePaths: ["/finance", "/folio", "/night-audit"],
    items: [
      { label: "Billing / Folio", path: "/folio#guest-ledger" },
      { label: "Payments", path: "/folio#payment-ledger" },
      { label: "Cashier Shift", path: "/folio#payment-ledger" },
      { label: "Deposit", path: "/folio#deposit-ledger" },
      { label: "Refund / Void", path: "/folio#folio-audit" },
      { label: "City Ledger", path: "/folio#city-ledger" },
      { label: "Accounts Receivable", path: "/folio#city-ledger" },
      { label: "Night Audit / End of Day", path: "/night-audit" },
    ],
  },
  {
    key: "rooms",
    label: "Room Management",
    path: "/housekeeping",
    icon: BedDouble,
    activePaths: ["/housekeeping"],
    items: [
      { label: "Housekeeping", path: "/housekeeping#overview" },
      { label: "Room Status", path: "/housekeeping#board" },
      { label: "Maintenance", path: "/housekeeping#maintenance" },
      { label: "Out of Order / Out of Service", path: "/housekeeping#maintenance" },
      { label: "Room Assignment", path: "/frontdesk/room-assignment" },
      { label: "Task Board", path: "/housekeeping#assignments" },
    ],
  },
  {
    key: "fnb",
    label: "F&B Cost Control",
    path: "/food-costing",
    icon: ChefHat,
    activePaths: ["/food-costing", "/store-control"],
    items: [
      { label: "Recipe Costing", path: "/food-costing#recipes" },
      { label: "Menu Costing", path: "/food-costing#menu-engineering" },
      { label: "Store Control", path: "/store-control#store-inventory" },
      { label: "Receiving", path: "/food-costing#receiving" },
      { label: "Issuing", path: "/food-costing#kitchen-requisition" },
      { label: "Inventory Ledger", path: "/food-costing#stock-count" },
      { label: "Purchase Control", path: "/food-costing#purchase-orders" },
    ],
  },
  {
    key: "profiles",
    label: "Profiles",
    path: "/guest-profiles",
    icon: Users,
    activePaths: ["/guest-profiles", "/feedback", "/service-recovery", "/guest-feedback"],
    items: [
      { label: "Guest Profiles", path: "/guest-profiles" },
      { label: "Company Profiles", path: comingSoonPath("Company Profiles"), comingSoon: true },
      { label: "Travel Agent Profiles", path: comingSoonPath("Travel Agent Profiles"), comingSoon: true },
      { label: "Group Profiles", path: comingSoonPath("Group Profiles"), comingSoon: true },
    ],
  },
  {
    key: "reports",
    label: "Reports",
    path: "/reports",
    icon: BarChart3,
    activePaths: ["/reports"],
    items: [
      { label: "Front Office Reports", path: "/reports#front-desk" },
      { label: "Reservation Reports", path: "/reports#reservations" },
      { label: "Cashiering Reports", path: "/reports#finance" },
      { label: "Housekeeping Reports", path: "/reports#housekeeping" },
      { label: "F&B Reports", path: "/reports#revenue" },
      { label: "Audit Reports", path: "/reports#night-audit" },
    ],
  },
  {
    key: "admin",
    label: "Admin / Command Center",
    path: "/admin",
    icon: ShieldCheck,
    activePaths: ["/admin"],
    items: [
      { label: "Users & Roles", path: "/admin#users" },
      { label: "Rate Configuration", path: "/admin#rates" },
      { label: "Property Setup", path: "/admin#property" },
      { label: "Room Setup", path: "/admin#rooms" },
      { label: "Tax / Service Rules", path: "/admin#rates" },
      { label: "Audit Logs", path: "/admin#audit-logs" },
      { label: "System Health", path: "/admin#overview" },
      { label: "Connections / Interfaces", path: comingSoonPath("Connections / Interfaces"), comingSoon: true },
    ],
  },
  {
    key: "ai",
    label: "AI Center",
    path: "/booking-assistant",
    icon: Bot,
    activePaths: ["/booking-assistant", "/agent-harness"],
    items: [
      { label: "Booking Assistant", path: "/booking-assistant" },
      { label: "AI Assistant", path: "/agent-harness" },
      { label: "AI Task Harness", path: "/agent-harness" },
    ],
  },
];

export const NAV_ITEMS: NavItem[] = [
  ...PMS_NAV_GROUPS.map((group) => ({
    path: group.path,
    label: group.label,
    icon: group.icon,
    group: group.key,
  })),
];
