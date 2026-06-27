import { http } from "./http";

export type NightAuditStatus = {
  property_code: string;
  business_date: string;
  next_business_date: string;
  already_run: boolean;
  last_run: {
    run_id?: number;
    run_at?: string;
    run_by?: string | null;
    status?: string;
    notes?: string | null;
  } | null;
  operational_snapshot: {
    arrivals_count: number;
    departures_count: number;
    in_house_count: number;
    no_show_count: number;
  };
};

export type NightAuditException = {
  exception_key: string;
  department: string;
  severity: string;
  message: string;
  is_blocking: boolean;
  override_allowed: boolean;
  resolved: boolean;
  action?: string | null;
  count?: number | null;
  related_booking_id?: number | null;
  related_folio_id?: number | null;
  related_room_number?: string | null;
};

export type NightAuditValidation = {
  property_code: string;
  business_date: string;
  ready_to_run: boolean;
  audit_status: string;
  blocking_count: number;
  warning_count: number;
  department_counts: Record<string, number>;
  blocking_exceptions: NightAuditException[];
  warning_exceptions: NightAuditException[];
  exceptions: NightAuditException[];
  finance_summary?: Record<string, number>;
  cashier_shift?: Record<string, number>;
};

export type NightAuditReadiness = {
  property_code: string;
  business_date: string;
  ready: boolean;
  audit_status: string;
  blocking_count: number;
  warning_count: number;
  checks: Array<{
    key: string;
    label: string;
    status: string;
  }>;
  exceptions: NightAuditException[];
};

export type NightAuditRunResponse = {
  ok: boolean;
  status: string;
  property_code: string;
  closed_business_date: string;
  next_business_date: string;
  message: string;
  archive_id?: number;
  posting_summary?: {
    in_house_bookings: number;
    posted_transactions: number;
    duplicate_transactions: number;
  };
  no_show_summary?: {
    no_show_candidates: number;
    marked_no_show: number;
    posted_transactions: number;
    duplicate_transactions: number;
  };
};

export async function fetchNightAuditStatus(propertyCode: string) {
  const { data } = await http.get<NightAuditStatus>("/night-audit/status", {
    params: { property_code: propertyCode },
  });
  return data;
}

export async function fetchNightAuditReadiness(
  propertyCode: string,
  businessDate: string
) {
  const { data } = await http.get<NightAuditReadiness>("/night-audit/readiness", {
    params: { property_code: propertyCode, business_date: businessDate },
  });
  return data;
}

export async function fetchNightAuditExceptions(
  propertyCode: string,
  businessDate: string
) {
  const { data } = await http.get<NightAuditValidation>("/night-audit/exceptions", {
    params: { property_code: propertyCode, business_date: businessDate },
  });
  return data;
}

export async function runNightAuditValidation(
  propertyCode: string,
  businessDate: string
) {
  const { data } = await http.post<NightAuditValidation>("/night-audit/run-validation", {
    property_code: propertyCode,
    business_date: businessDate,
  });
  return data;
}

export async function generateNightAuditReports(
  propertyCode: string,
  businessDate: string
) {
  const { data } = await http.post<{
    ok: boolean;
    status: string;
    reports: Array<{ report_type: string; status: string }>;
    ready_to_run: boolean;
    blocking_count: number;
    warning_count: number;
  }>("/night-audit/generate-reports", {
    property_code: propertyCode,
    business_date: businessDate,
  });
  return data;
}

export async function runNightAudit(
  propertyCode: string,
  notes?: string,
  businessDate?: string
) {
  const { data } = await http.post<NightAuditRunResponse>("/night-audit/run", {
    property_code: propertyCode,
    business_date: businessDate || null,
    notes: notes || null,
  });
  return data;
}

export async function overrideBusinessDate(
  propertyCode: string,
  businessDate: string,
  reason?: string
) {
  const { data } = await http.patch("/night-audit/business-date", null, {
    params: {
      property_code: propertyCode,
      business_date: businessDate,
      reason: reason || undefined,
    },
  });
  return data;
}
