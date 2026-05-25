export type UserSession = {
  username: string;
  role: "admin" | "manager" | "frontdesk" | "housekeeping" | "finance";
};

export type DashboardKpi = {
  property_code: string;
  date: string;
  adr: number;
  revpar: number;
  rooms_sold: number;
  revenue_total: number;
};

export type FrontdeskBooking = {
  id: number;
  guest_name: string;
  check_in_date: string;
  check_out_date: string;
  booking_status: string;
  property_code: string;
  room_number?: string | null;
  total_amount?: number | null;
  source?: string | null;
  channel?: string | null;
};

export type RoomStatusItem = {
  room_number: string;
  property_code: string;
  floor: number;
  hk_status: string;
  business_date: string;
  is_occupied: boolean;
  guest_name: string | null;
  check_in_date: string | null;
  check_out_date: string | null;
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
