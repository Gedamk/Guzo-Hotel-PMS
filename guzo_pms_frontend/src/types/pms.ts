export type UserSession = {
  username: string;
  email?: string;
  full_name?: string;
  avatar_url?: string;
  role: UserRole;
  role_key?: string;
  department: HotelDepartment;
  property_code?: string;
  property_codes?: string[];
  access_token?: string;
  expires_at?: string;
};

export type HotelDepartment =
  | "executive"
  | "reservations"
  | "frontdesk"
  | "housekeeping"
  | "finance"
  | "night_audit"
  | "food_beverage"
  | "sales_events"
  | "it_admin";

export type UserRole =
  | "admin"
  | "general_manager"
  | "reservation_agent"
  | "frontdesk"
  | "housekeeping"
  | "finance"
  | "finance_manager"
  | "night_auditor"
  | "fb_controller"
  | "storekeeper"
  | "chef"
  | "executive_chef"
  | "fnb_manager"
  | "purchasing_manager"
  | "sales_manager";

export type DashboardKpi = {
  property_code: string;
  date: string;
  adr: number;
  revpar: number;
  rooms_sold: number;
  revenue_total: number;
};

export type DashboardOperationalSummary = {
  property_code: string;
  business_date: string;
  outstanding_balance: number;
  payments_collected: number;
  refunds: number;
  guest_satisfaction_score: number;
  complaints_open: number;
  service_recovery_cases: number;
  feedback_count: number;
  cashier_shift_open_count?: number;
  cashier_shift_closed_count?: number;
  cashier_shift_variance_count?: number;
  city_ledger_transfer_count?: number;
  unpaid_folio_count?: number;
  checkout_blocked_by_balance_count?: number;
  night_audit_ready?: boolean;
  night_audit_blocker_count?: number;
  pending_departure_count?: number;
  open_cashier_shift_count?: number;
  housekeeping_discrepancy_count?: number;
  unpaid_departure_folio_count?: number;
  dirty_room_count?: number;
  cleaning_room_count?: number;
  clean_room_count?: number;
  inspected_room_count?: number;
  out_of_order_count?: number;
  out_of_service_count?: number;
  open_complaint_count?: number;
  service_recovery_open_count?: number;
  guest_feedback_today_count?: number;
  vip_arrival_count?: number;
  arrivals_today_count?: number;
  departures_today_count?: number;
  in_house_count?: number;
  pending_deposit_count?: number;
  booking_request_count?: number;
  cancellation_count?: number;
  no_show_risk_count?: number;
  food_cost_percent?: number | null;
  beverage_cost_percent?: number | null;
  fnb_inventory_value?: number | null;
  fnb_waste_today?: number | null;
  fnb_store_issues_today?: number;
  fnb_receiving_today?: number;
  fnb_supplier_variance_count?: number;
  fnb_high_cost_alert_count?: number;
  fnb_daily_sales?: number | null;
  fnb_gross_profit?: number | null;
};

export type GlobalSearchResult = {
  id: string;
  module: string;
  title: string;
  subtitle: string;
  status?: string | null;
  target_route: string;
  record_type: string;
  record_id: string;
};

export type GlobalSearchGroup = {
  key: string;
  label: string;
  results: GlobalSearchResult[];
};

export type GlobalSearchResponse = {
  query: string;
  groups: GlobalSearchGroup[];
};

export type GuestFeedback = {
  id: number;
  property_code: string;
  booking_id?: number | null;
  guest_name?: string | null;
  rating?: number | null;
  feedback_source?: string | null;
  comment?: string | null;
  status: "new" | "reviewed" | "service_recovery" | "closed" | string;
  created_at?: string | null;
  assigned_to?: string | null;
  priority?: string | null;
  recovery_action?: string | null;
  follow_up_date?: string | null;
  resolution_notes?: string | null;
  guest_contacted?: boolean | null;
  compensation_offered?: string | null;
};

export type GuestFeedbackCreate = {
  property_code: string;
  booking_id?: number | null;
  guest_name?: string | null;
  rating?: number | null;
  feedback_source: string;
  comment?: string | null;
  status?: string;
  assigned_to?: string | null;
  priority?: string;
  recovery_action?: string | null;
  follow_up_date?: string | null;
  resolution_notes?: string | null;
  guest_contacted?: boolean;
  compensation_offered?: string;
};

export type GuestServiceRecoveryUpdate = {
  assigned_to?: string | null;
  priority: string;
  recovery_action?: string | null;
  follow_up_date?: string | null;
  resolution_notes?: string | null;
  guest_contacted: boolean;
  compensation_offered: string;
};

export type FrontdeskBooking = {
  id: number;
  confirmation_id?: string | null;
  guest_name: string;
  guest_email?: string | null;
  check_in_date: string;
  check_out_date: string;
  booking_status: string;
  property_code: string;
  room_number?: string | null;
  room_type?: string | null;
  currency?: string | null;
  total_amount?: number | null;
  rate_per_night_etb?: number | null;
  payment_method?: string | null;
  payment_status?: string | null;
  notes?: string | null;
  source?: string | null;
  channel?: string | null;
  balance_due?: number | null;
  guarantee_status?: string | null;
  housekeeping_status?: string | null;
  special_requests?: string | null;
  q_status?: string | null;
  q_started_at?: string | null;
  q_priority?: string | null;
  q_notes?: string | null;
  q_removed_at?: string | null;
  q_removed_by?: string | null;
  registration_card_generated_at?: string | null;
  registration_card_generated_by?: string | null;
  registration_card_signed?: boolean | null;
  registration_card_signed_at?: string | null;
  registration_card_notes?: string | null;
  authorization_status?: string | null;
  authorization_amount?: number | null;
  authorization_type?: string | null;
  authorization_code?: string | null;
  authorization_notes?: string | null;
  authorization_recorded_by?: string | null;
  authorization_recorded_at?: string | null;
  upsell_offered?: boolean | null;
  upsell_accepted?: boolean | null;
  upsell_declined?: boolean | null;
  upsell_from_room_type?: string | null;
  upsell_to_room_type?: string | null;
  upsell_amount_per_night?: number | null;
  upsell_total_amount?: number | null;
  upsell_recorded_by?: string | null;
  upsell_recorded_at?: string | null;
};

export type PublicBookingRequest = {
  id: number;
  property_code: string;
  source: string;
  channel?: string | null;
  guest_name: string;
  guest_phone?: string | null;
  guest_email?: string | null;
  check_in_date: string;
  check_out_date: string;
  adults: number;
  children: number;
  room_type?: string | null;
  reservation_type: string;
  booking_status: string;
  guarantee_type: string;
  deposit_status: string;
  special_requests?: string | null;
  notes?: string | null;
  converted_booking_id?: number | null;
  converted_at?: string | null;
  converted_by?: string | null;
  confirmation_id?: string | null;
  guest_notification_status?: string | null;
  deposit_payment_link?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type RoomStatusItem = {
  room_number: string;
  property_code: string;
  room_type?: string | null;
  floor: number;
  hk_status: string;
  business_date: string;
  is_occupied: boolean;
  guest_name: string | null;
  check_in_date: string | null;
  check_out_date: string | null;
  assigned_to?: string | null;
  maintenance_note?: string | null;
  out_of_order_reason?: string | null;
  lost_item_note?: string | null;
  inspected_by?: string | null;
  inspected_at?: string | null;
};

export type FrontDeskServiceRecordType =
  | "guest_message"
  | "trace"
  | "wake_up_call"
  | "task_history";

export type FrontDeskServiceRecordStatus =
  | "open"
  | "in_progress"
  | "completed"
  | "cancelled";

export type FrontDeskServiceRecordPriority =
  | "low"
  | "normal"
  | "high"
  | "urgent";

export type FrontDeskServiceRecord = {
  id: number;
  record_type: FrontDeskServiceRecordType | string;
  property_code: string;
  booking_id?: number | null;
  reservation_reference?: string | null;
  guest_name?: string | null;
  room_number?: string | null;
  status: FrontDeskServiceRecordStatus | string;
  status_label: string;
  priority: FrontDeskServiceRecordPriority | string;
  assigned_to?: string | null;
  created_by: string;
  created_at: string;
  completed_at?: string | null;
  notes?: string | null;
  task_key?: string | null;
  title?: string | null;
  scheduled_for?: string | null;
  updated_at?: string | null;
};

export type FrontDeskServiceRecordPayload = {
  record_type: FrontDeskServiceRecordType;
  property_code: string;
  booking_id?: number | null;
  reservation_reference?: string | null;
  guest_name?: string | null;
  room_number?: string | null;
  status?: FrontDeskServiceRecordStatus;
  priority?: FrontDeskServiceRecordPriority;
  assigned_to?: string | null;
  notes?: string | null;
  task_key?: string | null;
  title?: string | null;
  scheduled_for?: string | null;
};

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

export type PmsContextState = {
  propertyCode: string;
  businessDate: string;
};

export type HotelProperty = {
  id?: number;
  name: string;
  code: string;
  address: string;
  city: string;
  country: string;
  timezone: string;
  currency: string;
  phone: string;
  email: string;
  isActive: boolean;
  onboardingStatus?: "not_started" | "in_progress" | "complete";
};
