import {
  LayoutDashboard,
  BookOpen,
  MonitorSmartphone,
  BedDouble,
  Receipt,
  BarChart3,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

export const HOTEL_NAME = "Guzo Guest Assist PMS";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const API_BASE = API_BASE_URL;

export const AUTH_TOKEN =
  import.meta.env.VITE_AUTH_TOKEN || "admin-secret-123";

export const PROPERTY_CODE =
  import.meta.env.VITE_PROPERTY_CODE || "DRE001";

export const PROPERTY_NAME =
  import.meta.env.VITE_PROPERTY_NAME || "Dream Big Hotel";

export const BUSINESS_DATE =
  import.meta.env.VITE_BUSINESS_DATE || "2026-03-06";

export const DEFAULT_PROPERTY_CODE = PROPERTY_CODE;
export const DEFAULT_PROPERTY_NAME = PROPERTY_NAME;
export const DEFAULT_BUSINESS_DATE = BUSINESS_DATE;

export const HOTEL_NAME_BY_PROPERTY: Record<string, string> = {
  DRE001: "Dream Big Hotel",
  NN002: "N&N Luxury Hotel",
};

export const PROPERTY_OPTIONS = [
  { code: "DRE001", name: "Dream Big Hotel" },
  { code: "NN002", name: "N&N Luxury Hotel" },
];

export function getPropertyName(propertyCode?: string) {
  if (!propertyCode) return DEFAULT_PROPERTY_NAME;
  return HOTEL_NAME_BY_PROPERTY[propertyCode] || propertyCode;
}

export type NavItem = {
  path: string;
  label: string;
  icon: LucideIcon;
};

export const NAV_ITEMS: NavItem[] = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/frontdesk", label: "Front Desk", icon: MonitorSmartphone },
  { path: "/reservations", label: "Reservations", icon: BookOpen },
  { path: "/housekeeping", label: "Housekeeping", icon: BedDouble },
  { path: "/finance", label: "Finance", icon: Receipt },
  { path: "/reports", label: "Reports", icon: BarChart3 },
  { path: "/admin", label: "Admin", icon: ShieldCheck },
];