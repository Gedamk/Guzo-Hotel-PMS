import { PMS_USER_EMAIL } from "../config/pms";
import type { UserRole, UserSession } from "../types/pms";
import { loadStoredSession } from "./sessionStorage";

export type PmsPermission =
  | "booking.review_public_request"
  | "booking.reject_public_request"
  | "booking.request_deposit"
  | "booking.convert_public_request"
  | "frontdesk.check_in"
  | "frontdesk.check_out"
  | "frontdesk.room_move"
  | "housekeeping.mark_cleaned"
  | "housekeeping.mark_inspected"
  | "housekeeping.room_status_override"
  | "finance.post_charge"
  | "finance.post_payment"
  | "finance.void_transaction"
  | "finance.transfer_balance"
  | "fnb.create_purchase_order"
  | "fnb.approve_purchase_order"
  | "fnb.receive_goods"
  | "fnb.request_stock"
  | "fnb.issue_stock"
  | "fnb.manage_recipes"
  | "fnb.record_waste"
  | "fnb.stock_count"
  | "fnb.view_reports"
  | "fnb.submit_report"
  | "fnb.finance_review_report"
  | "fnb.approve_report"
  | "night_audit.run_validation"
  | "night_audit.run_audit"
  | "night_audit.override_exception"
  | "night_audit.lock_date"
  | "admin.manage_users";

const ROLE_PERMISSION_MAP: Record<UserRole, PmsPermission[]> = {
  admin: [
    "booking.review_public_request",
    "booking.reject_public_request",
    "booking.request_deposit",
    "booking.convert_public_request",
    "frontdesk.check_in",
    "frontdesk.check_out",
    "frontdesk.room_move",
    "housekeeping.mark_cleaned",
    "housekeeping.mark_inspected",
    "housekeeping.room_status_override",
    "finance.post_charge",
    "finance.post_payment",
    "finance.void_transaction",
    "finance.transfer_balance",
    "fnb.create_purchase_order",
    "fnb.approve_purchase_order",
    "fnb.receive_goods",
    "fnb.request_stock",
    "fnb.issue_stock",
    "fnb.manage_recipes",
    "fnb.record_waste",
    "fnb.stock_count",
    "fnb.view_reports",
    "fnb.submit_report",
    "fnb.finance_review_report",
    "fnb.approve_report",
    "night_audit.run_validation",
    "night_audit.run_audit",
    "night_audit.override_exception",
    "night_audit.lock_date",
    "admin.manage_users",
  ],
  general_manager: [
    "booking.review_public_request",
    "booking.reject_public_request",
    "booking.request_deposit",
    "booking.convert_public_request",
    "frontdesk.check_in",
    "frontdesk.check_out",
    "frontdesk.room_move",
    "housekeeping.mark_cleaned",
    "housekeeping.mark_inspected",
    "housekeeping.room_status_override",
    "finance.post_charge",
    "finance.post_payment",
    "finance.void_transaction",
    "finance.transfer_balance",
    "fnb.create_purchase_order",
    "fnb.approve_purchase_order",
    "fnb.receive_goods",
    "fnb.request_stock",
    "fnb.issue_stock",
    "fnb.manage_recipes",
    "fnb.record_waste",
    "fnb.stock_count",
    "fnb.view_reports",
    "fnb.submit_report",
    "fnb.finance_review_report",
    "fnb.approve_report",
    "night_audit.run_validation",
    "night_audit.run_audit",
    "night_audit.override_exception",
    "night_audit.lock_date",
    "admin.manage_users",
  ],
  reservation_agent: [
    "booking.review_public_request",
    "booking.reject_public_request",
    "booking.request_deposit",
    "booking.convert_public_request",
  ],
  frontdesk: ["frontdesk.check_in", "frontdesk.check_out", "frontdesk.room_move"],
  housekeeping: [
    "housekeeping.mark_cleaned",
    "housekeeping.mark_inspected",
    "housekeeping.room_status_override",
  ],
  finance: ["finance.post_charge", "finance.post_payment"],
  finance_manager: [
    "finance.post_charge",
    "finance.post_payment",
    "finance.void_transaction",
    "finance.transfer_balance",
    "fnb.view_reports",
    "fnb.finance_review_report",
  ],
  night_auditor: [
    "night_audit.run_validation",
    "night_audit.run_audit",
    "night_audit.lock_date",
  ],
  fb_controller: [
    "fnb.create_purchase_order",
    "fnb.approve_purchase_order",
    "fnb.receive_goods",
    "fnb.request_stock",
    "fnb.issue_stock",
    "fnb.manage_recipes",
    "fnb.record_waste",
    "fnb.stock_count",
    "fnb.view_reports",
    "fnb.submit_report",
    "fnb.approve_report",
  ],
  storekeeper: ["fnb.receive_goods", "fnb.issue_stock", "fnb.stock_count", "fnb.record_waste", "fnb.view_reports"],
  chef: ["fnb.request_stock", "fnb.manage_recipes", "fnb.record_waste", "fnb.view_reports", "fnb.submit_report"],
  executive_chef: ["fnb.request_stock", "fnb.manage_recipes", "fnb.record_waste", "fnb.view_reports", "fnb.submit_report", "fnb.approve_report"],
  fnb_manager: [
    "fnb.create_purchase_order",
    "fnb.approve_purchase_order",
    "fnb.receive_goods",
    "fnb.request_stock",
    "fnb.issue_stock",
    "fnb.manage_recipes",
    "fnb.record_waste",
    "fnb.stock_count",
    "fnb.view_reports",
    "fnb.submit_report",
    "fnb.approve_report",
  ],
  purchasing_manager: ["fnb.create_purchase_order", "fnb.approve_purchase_order", "fnb.view_reports"],
  sales_manager: ["booking.review_public_request"],
};

export const ROLE_USER_EMAIL_MAP: Record<UserRole, string> = {
  admin: "admin@guzo.local",
  general_manager: "manager@guzo.local",
  reservation_agent: "reservations@guzo.local",
  frontdesk: "frontdesk@guzo.local",
  housekeeping: "housekeeping@guzo.local",
  finance: "finance@guzo.local",
  finance_manager: "finance.manager@guzo.local",
  night_auditor: "nightaudit@guzo.local",
  fb_controller: PMS_USER_EMAIL,
  storekeeper: "storekeeper@guzo.local",
  chef: "chef@guzo.local",
  executive_chef: "executive.chef@guzo.local",
  fnb_manager: "fnb.manager@guzo.local",
  purchasing_manager: "purchasing@guzo.local",
  sales_manager: "reservations@guzo.local",
};

export function currentSession() {
  return loadStoredSession();
}

export function roleCan(
  permission: PmsPermission,
  session: UserSession | null = currentSession()
) {
  if (!session) return false;
  return ROLE_PERMISSION_MAP[session.role]?.includes(permission) ?? false;
}

export function currentPmsUserEmail() {
  const session = currentSession();
  return session?.email || (session ? ROLE_USER_EMAIL_MAP[session.role] : PMS_USER_EMAIL);
}

export function permissionMessage(label: string) {
  return `${label} requires authorized PMS permission. This view is read-only for your role.`;
}
