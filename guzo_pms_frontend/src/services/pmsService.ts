import { API_BASE_URL, BUSINESS_DATE, PROPERTY_CODE } from "../config/pms";
import { http } from "./http";
import type {
  DashboardKpi,
  FrontdeskBooking,
  HealthResponse,
  RoomStatusItem,
} from "../types/pms";

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await http.get<HealthResponse>("/health");
  return data;
}

export async function fetchDailyKpi(
  propertyCode = PROPERTY_CODE,
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

export async function fetchFrontdeskBookings(
  propertyCode = PROPERTY_CODE,
  date = BUSINESS_DATE
): Promise<FrontdeskBooking[]> {
  const { data } = await http.get<FrontdeskBooking[]>("/frontdesk/bookings", {
    params: {
      scope: "today",
      date,
    },
  });
  return data.filter(
    (row) => !propertyCode || row.property_code === propertyCode
  );
}

export async function fetchRoomStatusBoard(
  propertyCode = PROPERTY_CODE,
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

export function buildDailyManagerReportUrl(
  propertyCode = PROPERTY_CODE,
  date = BUSINESS_DATE
): string {
  const url = new URL("/reports/daily-manager", API_BASE_URL);
  url.searchParams.set("property_code", propertyCode);
  url.searchParams.set("business_date", date);
  return url.toString();
}
