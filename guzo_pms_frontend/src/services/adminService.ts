import { http } from "./http";
import type { HotelProperty } from "../types/pms";

export type AdminOverview = {
  property_code: string;
  business_date: string;
  system_health: string;
  backend_status: string;
  database_status: string;
  frontend_status: string;
  business_date_status: string;
  night_audit_status: string;
  night_audit_blocking: number;
  night_audit_warnings: number;
  active_users: number;
  failed_logins: number;
  open_admin_alerts: number;
  room_count: number;
  report_archive_count: number;
  scheduled_reports_count: number;
  notification_failures: number;
  notification_pending: number;
  roles: string[];
  role_details?: AdminRole[];
  permissions_matrix: Array<Record<string, any>>;
  integrations: Array<Record<string, any>>;
  admin_alerts: Array<Record<string, any>>;
  report_archive: Array<Record<string, any>>;
  scheduled_reports: Array<Record<string, any>>;
  audit_logs: Array<Record<string, any>>;
  notification_outbox: {
    pending: number;
    queued?: number;
    sent_today?: number;
    failed: number;
    last_sent_at?: string | null;
  };
  backup: {
    last_backup_at?: string | null;
    status: string;
  };
};

export type NotificationProcessResult = {
  queued_found: number;
  sent_count: number;
  failed_count: number;
  sent_ids: number[];
  failed: Array<Record<string, unknown>>;
};

export type AdminUser = {
  id: number;
  full_name: string;
  email: string;
  role_key: string;
  property_code?: string | null;
  is_active: boolean;
  last_login_at?: string | null;
  created_at?: string | null;
};

export type AdminRole = {
  role_key: string;
  role_name: string;
  description?: string | null;
  is_system_role?: boolean;
};

export type AdminPermissionRow = {
  role_key: string;
  role_name: string;
  permissions: string[];
};

export type PmsAuditLog = {
  id: number;
  property_code?: string | null;
  user_email?: string | null;
  module?: string | null;
  action?: string | null;
  record_type?: string | null;
  record_id?: string | null;
  old_value?: Record<string, unknown> | null;
  new_value?: Record<string, unknown> | null;
  ip_address?: string | null;
  created_at?: string | null;
};

export type RatePlanConfig = {
  id?: number;
  code: string;
  name: string;
  multiplier: number;
  requires_manager_approval: boolean;
  cancellation_policy?: string | null;
  is_active: boolean;
};

export type RoomTypeRateConfig = {
  id?: number;
  room_type: string;
  base_rate_etb: number;
  currency: string;
  is_active: boolean;
};

export type TaxServiceRuleConfig = {
  id?: number;
  rule_name: string;
  tax_percent: number;
  service_charge_percent: number;
  is_active: boolean;
};

export type SeasonRuleConfig = {
  id?: number;
  rule_name: string;
  start_month: number;
  end_month: number;
  surcharge_percent: number;
  weekend_surcharge_percent: number;
  is_active: boolean;
};

export type DepositPolicyConfig = {
  id?: number;
  rate_code: string;
  deposit_percent: number;
  guarantee_required: boolean;
  policy_text?: string | null;
  is_active: boolean;
};

export type RateConfiguration = {
  property_code: string;
  rate_plans: RatePlanConfig[];
  room_type_rates: RoomTypeRateConfig[];
  tax_service_rules: TaxServiceRuleConfig[];
  season_rules: SeasonRuleConfig[];
  deposit_policies: DepositPolicyConfig[];
};

export type CreateAdminUserPayload = {
  full_name: string;
  email: string;
  role_key: string;
  property_code: string;
  is_active?: boolean;
};

export type PropertySavePayload = HotelProperty;

export type PropertyGoLiveCheck = {
  property_id: number;
  property_code: string;
  status: "green" | "yellow" | "red";
  label: string;
  ready: boolean;
  blockers: string[];
  warnings: string[];
  checks: Record<string, number | boolean>;
};

export async function fetchAdminOverview(
  propertyCode: string,
  businessDate: string
): Promise<AdminOverview> {
  const { data } = await http.get<AdminOverview>("/admin/overview", {
    params: {
      property_code: propertyCode,
      business_date: businessDate,
    },
  });
  return data;
}

export async function fetchProperties(): Promise<HotelProperty[]> {
  const { data } = await http.get<{ properties: HotelProperty[] }>("/properties");
  return data.properties;
}

export async function createAdminProperty(payload: PropertySavePayload): Promise<HotelProperty> {
  const { data } = await http.post<{ property: HotelProperty }>("/admin/properties", payload);
  return data.property;
}

export async function updateAdminProperty(payload: PropertySavePayload): Promise<HotelProperty> {
  if (!payload.id) {
    throw new Error("Property id is required for backend update.");
  }
  const { data } = await http.put<{ property: HotelProperty }>(
    `/admin/properties/${payload.id}`,
    payload
  );
  return data.property;
}

export async function fetchPropertyGoLiveCheck(propertyId: number): Promise<PropertyGoLiveCheck> {
  const { data } = await http.get<PropertyGoLiveCheck>(`/admin/properties/${propertyId}/go-live-check`);
  return data;
}

export async function activateLiveProperty(propertyId: number): Promise<{
  property: HotelProperty;
  go_live_check: PropertyGoLiveCheck;
}> {
  const { data } = await http.post<{
    property: HotelProperty;
    go_live_check: PropertyGoLiveCheck;
  }>(`/admin/properties/${propertyId}/activate-live`);
  return data;
}

export async function seedPropertyDemoRooms(propertyId: number): Promise<{
  status: string;
  property_code: string;
  rooms: Array<{ property_code: string; room_number: string; room_type: string; floor: number }>;
  room_count: number;
}> {
  const { data } = await http.post<{
    status: string;
    property_code: string;
    rooms: Array<{ property_code: string; room_number: string; room_type: string; floor: number }>;
    room_count: number;
  }>(`/admin/properties/${propertyId}/seed-demo-rooms`);
  return data;
}

export async function resetPropertyDemoRooms(propertyId: number): Promise<{
  status: string;
  property_code: string;
  rooms: Array<{ property_code: string; room_number: string; room_type: string; floor: number }>;
  room_count: number;
}> {
  const { data } = await http.post<{
    status: string;
    property_code: string;
    rooms: Array<{ property_code: string; room_number: string; room_type: string; floor: number }>;
    room_count: number;
  }>(`/admin/properties/${propertyId}/reset-demo-rooms`);
  return data;
}

export async function assignAdminToProperty(propertyId: number, userEmail?: string): Promise<{
  status: string;
  property_code: string;
  user_email: string;
}> {
  const { data } = await http.post<{
    status: string;
    property_code: string;
    user_email: string;
  }>(`/admin/properties/${propertyId}/assign-admin`, userEmail ? { user_email: userEmail } : {});
  return data;
}

export async function fetchAdminUsers(propertyCode: string): Promise<AdminUser[]> {
  const { data } = await http.get<{ users: AdminUser[] }>("/admin/users", {
    params: { property_code: propertyCode },
  });
  return data.users;
}

export async function createAdminUser(payload: CreateAdminUserPayload): Promise<AdminUser> {
  const { data } = await http.post<{ user: AdminUser }>("/admin/users", payload);
  return data.user;
}

export async function disableAdminUser(userId: number): Promise<AdminUser> {
  const { data } = await http.post<{ user: AdminUser }>(`/admin/users/${userId}/disable`);
  return data.user;
}

export async function resetAdminUserPassword(userId: number): Promise<{ message: string }> {
  const { data } = await http.post<{ message: string }>(`/admin/users/${userId}/reset-password`);
  return data;
}

export async function fetchAdminRoles(propertyCode: string): Promise<AdminRole[]> {
  const { data } = await http.get<{ roles: AdminRole[] }>("/admin/roles", {
    params: { property_code: propertyCode },
  });
  return data.roles;
}

export async function fetchAdminPermissions(propertyCode: string): Promise<AdminPermissionRow[]> {
  const { data } = await http.get<{ permissions: AdminPermissionRow[] }>("/admin/permissions", {
    params: { property_code: propertyCode },
  });
  return data.permissions;
}

export async function fetchPmsAuditLogs(propertyCode: string): Promise<PmsAuditLog[]> {
  const { data } = await http.get<{ audit_logs: PmsAuditLog[] }>("/admin/audit-logs", {
    params: { property_code: propertyCode },
  });
  return data.audit_logs;
}

export async function fetchRateConfiguration(propertyCode: string): Promise<RateConfiguration> {
  const { data } = await http.get<RateConfiguration>("/admin/rate-configuration", {
    params: { property_code: propertyCode },
  });
  return data;
}

export async function updateRateConfiguration(payload: RateConfiguration): Promise<RateConfiguration> {
  const { data } = await http.put<RateConfiguration>("/admin/rate-configuration", payload);
  return data;
}

export async function processNotificationOutbox(): Promise<NotificationProcessResult> {
  const { data } = await http.post<NotificationProcessResult>("/notifications/process-outbox");
  return data;
}
