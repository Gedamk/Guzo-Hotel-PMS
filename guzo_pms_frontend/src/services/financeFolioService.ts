// src/services/financeFolioService.ts
import { API_BASE, AUTH_TOKEN } from "../config/pms";

export type FolioLine = {
  id: string;
  date: string;
  description: string;
  amount: number;
  currency: string;
  kind: "charge" | "payment";
  category_or_method: string;
  running_balance?: number;
};

export type FolioSummary = {
  balance: number;
  currency: string;
  lines: FolioLine[];
};

export type GetFolioSummaryParams = {
  business_date: string;
  property_code: string;
  booking_id: number;
};

export type PostChargePayload = {
  property_code: string;
  booking_id: number;
  business_date: string;
  category: string;
  description: string;
  amount: number;
  currency: string;
};

export type PostPaymentPayload = {
  property_code: string;
  booking_id: number;
  business_date: string;
  method: string;
  description: string;
  amount: number;
  currency: string;
};

function authHeaders(): Record<string, string> {
  return AUTH_TOKEN ? { Authorization: `Bearer ${AUTH_TOKEN}` } : {};
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers || {}),
    },
  });

  const text = await res.text();
  let data: unknown = null;

  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    // keep text fallback
  }

  if (!res.ok) {
    const detail =
      typeof data === "object" && data !== null && "detail" in data
        ? String((data as { detail?: unknown }).detail ?? "")
        : "";

    throw new Error(detail || text || res.statusText);
  }

  return data as T;
}

export async function apiGetFolioSummary(
  params: GetFolioSummaryParams,
): Promise<FolioSummary> {
  const qs = new URLSearchParams({
    business_date: params.business_date,
    property_code: params.property_code,
    booking_id: String(params.booking_id),
  });

  return await fetchJson<FolioSummary>(
    `${API_BASE}/finance/folio/summary?${qs.toString()}`,
  );
}

export async function apiPostCharge(
  payload: PostChargePayload,
): Promise<{ ok: boolean; charge_id: number }> {
  return await fetchJson<{ ok: boolean; charge_id: number }>(
    `${API_BASE}/finance/folio/post-charge`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function apiPostPayment(
  payload: PostPaymentPayload,
): Promise<{ ok: boolean; payment_id: number }> {
  return await fetchJson<{ ok: boolean; payment_id: number }>(
    `${API_BASE}/finance/folio/post-payment`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}