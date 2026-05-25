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

export type NightAuditRunResponse = {
  ok: boolean;
  status: string;
  property_code: string;
  closed_business_date: string;
  next_business_date: string;
  message: string;
};

export async function fetchNightAuditStatus(propertyCode: string) {
  const { data } = await http.get<NightAuditStatus>("/night-audit/status", {
    params: { property_code: propertyCode },
  });
  return data;
}

export async function runNightAudit(propertyCode: string, notes?: string) {
  const { data } = await http.post<NightAuditRunResponse>("/night-audit/run", {
    property_code: propertyCode,
    notes: notes || null,
  });
  return data;
}

export async function overrideBusinessDate(
  propertyCode: string,
  businessDate: string
) {
  const { data } = await http.patch("/night-audit/business-date", null, {
    params: {
      property_code: propertyCode,
      business_date: businessDate,
    },
  });
  return data;
}
