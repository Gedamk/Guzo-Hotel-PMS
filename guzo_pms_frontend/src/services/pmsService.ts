import { API_BASE_URL, BUSINESS_DATE } from "../config/pms";
import { http } from "./http";
import type {
  DashboardKpi,
  DashboardOperationalSummary,
  FrontdeskBooking,
  GlobalSearchResponse,
  GuestFeedback,
  GuestFeedbackCreate,
  GuestServiceRecoveryUpdate,
  HealthResponse,
  PublicBookingRequest,
  RoomStatusItem,
} from "../types/pms";

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await http.get<HealthResponse>("/health");
  return data;
}

export async function fetchDailyKpi(
  propertyCode: string,
  date = BUSINESS_DATE
): Promise<DashboardKpi> {
  const { data } = await http.get<DashboardKpi>("/kpi/kpi/daily", {
    params: {
      property_code: propertyCode,
      date,
    },
  });
  return data;
}

export async function fetchDashboardOperationalSummary(
  propertyCode: string,
  date = BUSINESS_DATE
): Promise<DashboardOperationalSummary> {
  const { data } = await http.get<DashboardOperationalSummary>("/dashboard/operational-summary", {
    params: {
      property_code: propertyCode,
      business_date: date,
    },
  });
  return data;
}

export async function fetchGlobalSearch(
  query: string,
  propertyCode: string
): Promise<GlobalSearchResponse> {
  const { data } = await http.get<GlobalSearchResponse>("/search/global", {
    params: {
      q: query,
      property_code: propertyCode,
    },
  });
  return data;
}

export async function fetchFrontdeskBookings(
  propertyCode: string,
  date = BUSINESS_DATE
): Promise<FrontdeskBooking[]> {
  const { data } = await http.get<FrontdeskBooking[]>("/frontdesk/bookings", {
    params: {
      scope: "today",
      date,
      property: propertyCode,
    },
  });
  return data;
}

export async function fetchPublicBookingRequests(
  propertyCode: string
): Promise<PublicBookingRequest[]> {
  const { data } = await http.get<PublicBookingRequest[]>("/booking-hub/public-requests", {
    params: {
      property_code: propertyCode,
    },
  });
  return data;
}

export async function updatePublicBookingRequestStatus(
  requestId: number,
  status: string,
  propertyCode: string,
  notes?: string
): Promise<PublicBookingRequest> {
  const { data } = await http.patch<PublicBookingRequest>(
    `/booking-hub/public-requests/${requestId}/status`,
    {
      status,
      notes,
    },
    { params: { property_code: propertyCode } }
  );
  return data;
}

export async function convertPublicBookingRequest(
  requestId: number,
  payload: {
    total_amount_etb: number;
    rate_per_night_etb?: number;
    room_type?: string | null;
    payment_status?: string;
    notes?: string;
  },
  propertyCode: string
): Promise<{ ok: boolean; booking_id: number; confirmation_id: string; message: string }> {
  const { data } = await http.post(
    `/booking-hub/public-requests/${requestId}/convert`,
    payload,
    { params: { property_code: propertyCode } }
  );
  return data;
}

export async function fetchRoomStatusBoard(
  propertyCode: string,
  date = BUSINESS_DATE
): Promise<RoomStatusItem[]> {
  const { data } = await http.get<RoomStatusItem[]>("/rooms/status-board", {
    params: {
      property_code: propertyCode,
      date,
    },
  });
  return data;
}

export async function fetchGuestFeedback(
  propertyCode: string,
  statusFilter?: string
): Promise<GuestFeedback[]> {
  const { data } = await http.get<GuestFeedback[]>("/guest-feedback", {
    params: {
      property_code: propertyCode,
      status_filter: statusFilter || undefined,
    },
  });
  return data;
}

export async function createGuestFeedback(
  payload: GuestFeedbackCreate
): Promise<GuestFeedback> {
  const { data } = await http.post<GuestFeedback>("/guest-feedback", payload);
  return data;
}

export async function updateGuestFeedbackStatus(
  feedbackId: number,
  status: "reviewed" | "closed" | "service_recovery",
  propertyCode: string,
  note?: string
): Promise<GuestFeedback> {
  const { data } = await http.patch<GuestFeedback>(`/guest-feedback/${feedbackId}/status`, {
    status,
    note,
  }, { params: { property_code: propertyCode } });
  return data;
}

export async function markGuestFeedbackServiceRecovery(
  feedbackId: number,
  propertyCode: string,
  payload?: GuestServiceRecoveryUpdate
): Promise<GuestFeedback> {
  const { data } = await http.patch<GuestFeedback>(`/guest-feedback/${feedbackId}/service-recovery`, payload || {}, {
    params: { property_code: propertyCode },
  });
  return data;
}

export function buildDailyManagerReportUrl(
  propertyCode: string,
  date = BUSINESS_DATE
): string {
  const url = new URL("/reports/daily-manager", API_BASE_URL);
  url.searchParams.set("property_code", propertyCode);
  url.searchParams.set("business_date", date);
  return url.toString();
}
