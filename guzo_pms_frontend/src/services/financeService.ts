import { API_BASE, AUTH_TOKEN } from "../config/pms";

const defaultHeaders: Record<string, string> = {
  "Content-Type": "application/json",
  Authorization: `Bearer ${AUTH_TOKEN}`,
};

async function api<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options?.headers as Record<string, string> | undefined),
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }

  return res.json();
}

export type FolioSummary = {
  booking_id: number;
  property_code: string;
  guest_name?: string;
  room_number?: string | null;
  currency?: string;
  charges_total: number;
  payments_total: number;
  balance: number;
  booking_status?: string;
};

export type FolioTransaction = {
  id?: number;
  txn_type: "charge" | "payment";
  posting_date?: string;
  description?: string;
  reference?: string | null;
  category?: string | null;
  payment_method?: string | null;
  amount: number;
  currency?: string;
  created_at?: string;
};

export type PostChargePayload = {
  property_code: string;
  booking_id: number;
  amount: number;
  description: string;
  category?: string;
  reference?: string;
};

export type PostPaymentPayload = {
  property_code: string;
  booking_id: number;
  amount: number;
  payment_method: string;
  reference?: string;
  description?: string;
};

export type CheckoutValidation = {
  booking_id: number;
  property_code: string;
  balance: number;
  can_checkout: boolean;
  message?: string;
};

export async function fetchFolioSummary(
  propertyCode: string,
  bookingId: number
): Promise<FolioSummary> {
  const url =
    `${API_BASE}/finance/folio/summary` +
    `?property_code=${encodeURIComponent(propertyCode)}` +
    `&booking_id=${bookingId}`;

  return api<FolioSummary>(url);
}

export async function fetchFolioTransactions(
  propertyCode: string,
  bookingId: number
): Promise<FolioTransaction[]> {
  const url =
    `${API_BASE}/finance/folio/transactions` +
    `?property_code=${encodeURIComponent(propertyCode)}` +
    `&booking_id=${bookingId}`;

  return api<FolioTransaction[]>(url);
}

export async function postCharge(
  payload: PostChargePayload
): Promise<{ ok: boolean; message?: string }> {
  return api<{ ok: boolean; message?: string }>(`${API_BASE}/finance/charges`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function postPayment(
  payload: PostPaymentPayload
): Promise<{ ok: boolean; message?: string }> {
  return api<{ ok: boolean; message?: string }>(`${API_BASE}/finance/payments`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function validateCheckout(
  propertyCode: string,
  bookingId: number
): Promise<CheckoutValidation> {
  const url =
    `${API_BASE}/finance/checkout/validate` +
    `?property_code=${encodeURIComponent(propertyCode)}` +
    `&booking_id=${bookingId}`;

  return api<CheckoutValidation>(url);
}
