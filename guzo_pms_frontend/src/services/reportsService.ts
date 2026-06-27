import { http } from "./http";

export type ReportRegistryItem = {
  report_key: string;
  report_name: string;
  module: string;
  description: string;
  endpoint: string;
  supports_print: boolean;
  supports_csv: boolean;
  supports_pdf: boolean;
  supports_schedule: boolean;
  role_required: string;
};

export type ReportsCommandCenter = {
  property_code: string;
  business_date: string;
  generated_at: string;
  kpis: Record<string, number | string>;
  executive_summary: {
    daily_manager_report: string;
    operations_summary: string;
    night_audit_status: string;
    management_attention: Array<Record<string, any>>;
  };
  frontdesk: Record<string, number>;
  reservations: Record<string, any>;
  housekeeping: Record<string, number>;
  finance: Record<string, any>;
  night_audit: Record<string, any>;
  revenue: Record<string, number>;
  channels: Array<Record<string, any>>;
  booking_hub_channels?: Array<Record<string, any>>;
  exceptions: Array<Record<string, any>>;
  archive: Array<Record<string, any>>;
  scheduled: Array<Record<string, any>>;
  registry: ReportRegistryItem[];
};

export type ArchiveReportPayload = {
  property_code: string;
  business_date: string;
  report_key: string;
  report_name: string;
  report_type?: string;
  status?: string;
  generated_by?: string;
  parameters_json?: Record<string, any>;
  report_payload?: Record<string, any>;
  file_path?: string | null;
};

export type ScheduledReportPayload = {
  property_code: string;
  report_key: string;
  report_name: string;
  recipient_email: string;
  frequency?: string;
  schedule_time?: string;
  is_active?: boolean;
};

export async function fetchReportsCommandCenter(
  propertyCode: string,
  businessDate: string
): Promise<ReportsCommandCenter> {
  const { data } = await http.get<ReportsCommandCenter>("/reports/command-center", {
    params: {
      property_code: propertyCode,
      business_date: businessDate,
    },
  });
  return data;
}

export async function fetchReportRegistry(): Promise<ReportRegistryItem[]> {
  const { data } = await http.get<ReportRegistryItem[]>("/reports/registry");
  return data;
}

export async function archiveReport(payload: ArchiveReportPayload): Promise<{
  ok: boolean;
  archive_id: number;
  generated_at?: string | null;
  message: string;
}> {
  const { data } = await http.post("/reports/archive", payload);
  return data;
}

export async function scheduleReport(payload: ScheduledReportPayload): Promise<{
  ok: boolean;
  schedule_id: number;
  message: string;
}> {
  const { data } = await http.post("/reports/schedule", payload);
  return data;
}

export async function emailReport(
  reportKey: string,
  payload: {
    property_code: string;
    business_date: string;
    recipient_email: string;
    generated_by?: string;
    message?: string;
  }
): Promise<{
  ok: boolean;
  status: string;
  message: string;
}> {
  const { data } = await http.post(`/reports/${reportKey}/email`, payload);
  return data;
}
