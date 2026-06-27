import type { HotelDepartment, UserRole, UserSession } from "../types/pms";

export type ModulePath =
  | "/dashboard"
  | "/frontdesk"
  | "/reservations"
  | "/housekeeping"
  | "/folio"
  | "/food-costing"
  | "/reports"
  | "/night-audit"
  | "/booking"
  | "/booking/guest"
  | "/guest-profiles"
  | "/guest-feedback"
  | "/booking-assistant"
  | "/agent-harness"
  | "/admin"
  | "/coming-soon";

const COMPATIBILITY_PATHS: Record<string, ModulePath> = {
  "/booking-hub": "/booking",
  "/finance": "/folio",
  "/store-control": "/food-costing",
  "/feedback": "/guest-feedback",
  "/service-recovery": "/guest-feedback",
};

export type LoginRoleOption = {
  role: UserRole;
  department: HotelDepartment;
  label: string;
  description: string;
};

export const LOGIN_ROLE_OPTIONS: LoginRoleOption[] = [
  {
    role: "general_manager",
    department: "executive",
    label: "General Manager",
    description: "Full hotel oversight, KPIs, reports, and operation control.",
  },
  {
    role: "frontdesk",
    department: "frontdesk",
    label: "Front Desk",
    description: "Arrivals, Departures, In-House guests, folio, and room readiness.",
  },
  {
    role: "reservation_agent",
    department: "reservations",
    label: "Reservations",
    description: "Reservation inbox, booking creation, guarantees, and handoff.",
  },
  {
    role: "housekeeping",
    department: "housekeeping",
    label: "Housekeeping",
    description: "Room board, assignments, inspection, DND, and maintenance alerts.",
  },
  {
    role: "finance",
    department: "finance",
    label: "Finance / Cashier",
    description: "Guest folios, payments, cashiering, and revenue reports.",
  },
  {
    role: "finance_manager",
    department: "finance",
    label: "Finance Manager",
    description: "Cost reports, inventory value, variance review, and finance approval.",
  },
  {
    role: "night_auditor",
    department: "night_audit",
    label: "Night Auditor",
    description: "Night audit, balances, departures, reports, and business date close.",
  },
  {
    role: "fb_controller",
    department: "food_beverage",
    label: "F&B Controller",
    description: "Food cost control, stock workflows, cost reports, and finance view.",
  },
  {
    role: "storekeeper",
    department: "food_beverage",
    label: "Storekeeper",
    description: "Receiving, Main Store Inventory, and approved stock issuing.",
  },
  {
    role: "chef",
    department: "food_beverage",
    label: "Chef",
    description: "Store Requisitions and recipe draft preparation.",
  },
  {
    role: "executive_chef",
    department: "food_beverage",
    label: "Executive Chef",
    description: "Recipe approval, kitchen controls, and variance review.",
  },
  {
    role: "fnb_manager",
    department: "food_beverage",
    label: "F&B Manager",
    description: "F&B approvals, reports, purchasing review, and cost control.",
  },
  {
    role: "purchasing_manager",
    department: "food_beverage",
    label: "Purchasing Manager",
    description: "Supplier master, Purchase Orders, and purchasing approvals.",
  },
  {
    role: "sales_manager",
    department: "sales_events",
    label: "Sales & Events",
    description: "Groups, event leads, booking hub, reservations, and reports.",
  },
  {
    role: "admin",
    department: "it_admin",
    label: "System Admin",
    description: "Users, roles, setup, integrations, and all PMS modules.",
  },
];

export const ROLE_MODULE_ACCESS: Record<UserRole, ModulePath[]> = {
  admin: [
    "/dashboard",
    "/frontdesk",
    "/reservations",
    "/housekeeping",
    "/folio",
    "/food-costing",
    "/reports",
    "/night-audit",
    "/booking",
    "/booking/guest",
    "/guest-profiles",
    "/guest-feedback",
    "/booking-assistant",
    "/agent-harness",
    "/admin",
  ],
  general_manager: [
    "/dashboard",
    "/frontdesk",
    "/reservations",
    "/housekeeping",
    "/folio",
    "/food-costing",
    "/reports",
    "/night-audit",
    "/booking",
    "/guest-profiles",
    "/guest-feedback",
    "/booking-assistant",
    "/agent-harness",
    "/admin",
  ],
  reservation_agent: [
    "/dashboard",
    "/reservations",
    "/booking",
    "/booking/guest",
    "/guest-profiles",
    "/booking-assistant",
    "/agent-harness",
    "/frontdesk",
    "/reports",
  ],
  frontdesk: [
    "/dashboard",
    "/frontdesk",
    "/reservations",
    "/housekeeping",
    "/folio",
    "/guest-profiles",
    "/booking-assistant",
    "/agent-harness",
    "/reports",
  ],
  housekeeping: ["/dashboard", "/housekeeping", "/frontdesk", "/guest-profiles", "/agent-harness", "/reports"],
  finance: ["/dashboard", "/folio", "/guest-profiles", "/reports", "/night-audit", "/food-costing"],
  finance_manager: ["/dashboard", "/folio", "/guest-profiles", "/reports", "/night-audit", "/food-costing"],
  night_auditor: [
    "/dashboard",
    "/night-audit",
    "/folio",
    "/frontdesk",
    "/housekeeping",
    "/guest-profiles",
    "/reports",
  ],
  fb_controller: ["/dashboard", "/food-costing", "/folio", "/guest-profiles", "/reports"],
  storekeeper: ["/dashboard", "/food-costing", "/reports"],
  chef: ["/dashboard", "/food-costing", "/reports"],
  executive_chef: ["/dashboard", "/food-costing", "/reports"],
  fnb_manager: ["/dashboard", "/food-costing", "/folio", "/reports", "/night-audit"],
  purchasing_manager: ["/dashboard", "/food-costing", "/reports"],
  sales_manager: [
    "/dashboard",
    "/reservations",
    "/booking",
    "/booking/guest",
    "/guest-profiles",
    "/booking-assistant",
    "/agent-harness",
    "/reports",
  ],
};

export function getRoleLabel(role: UserRole) {
  return LOGIN_ROLE_OPTIONS.find((option) => option.role === role)?.label || role;
}

export function getDefaultPath(session: UserSession | null) {
  if (!session) return "/login";
  return ROLE_MODULE_ACCESS[session.role]?.[0] || "/dashboard";
}

export function canAccessPath(session: UserSession | null, path: string) {
  if (!session) return false;
  if (path.startsWith("/coming-soon")) return true;
  const allowed = ROLE_MODULE_ACCESS[session.role] || [];
  const basePath = path.split(/[?#]/)[0] || path;
  const normalizedPath = COMPATIBILITY_PATHS[basePath] || basePath;
  return allowed.some(
    (modulePath) =>
      normalizedPath === modulePath || normalizedPath.startsWith(`${modulePath}/`)
  );
}
