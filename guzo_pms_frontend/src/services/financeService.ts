import { http } from "./http";

function financeIdempotencyKey(prefix: string): string {
  const value = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}:${value}`;
}

async function api<T>(url: string, options?: RequestInit): Promise<T> {
  const method = String(options?.method || "GET").toLowerCase();
  const body = options?.body ? JSON.parse(String(options.body)) : undefined;
  const { data } = await http.request<T>({
    url,
    method,
    data: body,
    headers: options?.headers as Record<string, string> | undefined,
  });
  return data;
}

export type FolioSummary = {
  booking_id: number;
  property_code: string;
  guest_name?: string;
  room_number?: string | null;
  check_in_date?: string | null;
  check_out_date?: string | null;
  currency?: string;
  charges_total: number;
  payments_total: number;
  balance: number;
  booking_status?: string;
};

export type FolioTransaction = {
  id?: number;
  txn_type: "charge" | "payment" | "refund";
  posting_date?: string;
  description?: string;
  reference?: string | null;
  category?: string | null;
  payment_method?: string | null;
  amount: number;
  currency?: string;
  original_amount?: number;
  original_currency?: string;
  exchange_rate_to_base?: number | null;
  base_amount?: number | null;
  base_currency?: string;
  exchange_rate_source?: string | null;
  exchange_rate_overridden?: boolean;
  exchange_rate_override_reason?: string | null;
  created_at?: string;
};

export type DepositAccount = {
  id: number;
  property_code: string;
  booking_id: number;
  folio_id?: number | null;
  required_amount: number;
  requested_amount: number;
  paid_amount: number;
  remaining_amount: number;
  allocated_amount: number;
  transferred_amount: number;
  refunded_amount: number;
  forfeited_amount: number;
  available_amount: number;
  currency: string;
  refundable: boolean;
  payment_method?: string | null;
  reference?: string | null;
  status: string;
};

export async function fetchDepositAccounts(propertyCode: string, bookingId?: number): Promise<DepositAccount[]> {
  const params = new URLSearchParams({ property_code: propertyCode });
  if (bookingId) params.set("booking_id", String(bookingId));
  return api<DepositAccount[]>(`/finance/deposits?${params.toString()}`);
}

export type PostChargePayload = {
  property_code: string;
  booking_id: number;
  business_date?: string;
  amount: number;
  description: string;
  category?: string;
  reference?: string;
  currency?: string;
  idempotency_key?: string;
};

export type PostPaymentPayload = {
  property_code: string;
  booking_id: number;
  business_date?: string;
  amount: number;
  payment_method: string;
  reference?: string;
  description?: string;
  currency?: string;
  exchange_rate_to_base?: number;
  exchange_rate_source?: string;
  exchange_rate_overridden?: boolean;
  exchange_rate_override_reason?: string;
  idempotency_key?: string;
};

export type CheckoutValidation = {
  booking_id: number;
  property_code: string;
  balance: number;
  can_checkout: boolean;
  checkout_request_date?: string;
  scheduled_check_out_date?: string | null;
  is_early_checkout?: boolean;
  nights_remaining?: number;
  message?: string;
};

export type CashierClosePayload = {
  property_code: string;
  business_date: string;
  cashier_name?: string;
  declared_total?: number;
  actual_cash?: number;
  actual_card?: number;
  actual_bank_transfer?: number;
  actual_mobile_money?: number;
  actual_unassigned?: number;
  manager_approval_reason?: string;
  notes?: string;
};

export type CashierCloseResult = {
  ok: boolean;
  session_id: number;
  property_code: string;
  business_date: string;
  cashier_name: string;
  expected_total: number;
  declared_total: number;
  variance: number;
  unassigned?: number;
  status: string;
};

export type CashierOpenPayload = {
  property_code: string;
  business_date: string;
  cashier_name: string;
  opening_float?: number;
  notes?: string;
};

export type FolioReceipt = {
  receipt_number: string;
  invoice_number: string;
  property_code: string;
  booking_id: number;
  folio_id: number;
  guest_name?: string;
  room_number?: string | null;
  check_in_date?: string | null;
  check_out_date?: string | null;
  charges: Array<Record<string, any>>;
  payments: Array<Record<string, any>>;
  line_items?: Array<Record<string, any>>;
  room_charge_subtotal?: number;
  fnb_other_charge_subtotal?: number;
  service_charge_amount?: number;
  vat_tax_amount?: number;
  tax_percent?: number | null;
  service_charge_percent?: number | null;
  tax_service_posted?: boolean;
  tax_service_warning?: string | null;
  tax_service_charge: number;
  total_charges: number;
  total_payments: number;
  balance: number;
  payment_method?: string | null;
  currency: string;
  folio_status: string;
};

export type CheckoutProcessPayload = {
  property_code: string;
  booking_id: number;
  business_date: string;
  pay_amount?: number;
  pay_method?: string;
  description?: string;
  currency?: string;
  exchange_rate_to_base?: number;
  exchange_rate_source?: string;
  exchange_rate_overridden?: boolean;
  exchange_rate_override_reason?: string;
  close_folio?: boolean;
  mark_booking_checked_out?: boolean;
  idempotency_key?: string;
};

export type CheckoutProcessResult = {
  ok: boolean;
  property_code: string;
  booking_id: number;
  folio_id: number;
  totals: {
    total_charges: string;
    total_payments: string;
    balance: string;
  };
  folio_closed: boolean;
  booking_checked_out: boolean;
  receipt?: {
    receipt_id?: number | null;
    receipt_number: string;
    invoice_number: string;
    currency: string;
    total_charges: string;
    total_payments: string;
    balance: string;
  } | null;
};

export type FinanceControlReport = {
  property_code: string;
  business_date: string;
  finance_dashboard: Record<string, number>;
  daily_revenue: Record<string, number>;
  trial_balance: Record<string, number>;
  guest_ledger: Array<Record<string, any>>;
  deposit_ledger: Array<Record<string, any>>;
  payment_ledger: Array<Record<string, any>>;
  tax_report: Record<string, number>;
  folio_transaction_audit: Array<Record<string, any>>;
  cashier_shift: Record<string, number>;
  duplicate_open_folios?: Array<Record<string, any>>;
  ar_city_ledger?: {
    status: string;
    balance: number;
    message: string;
    rows: Array<Record<string, any>>;
  };
  accounting_lock?: {
    status: string;
    business_date: string;
    locked_by?: string | null;
    locked_at?: string | null;
  };
  finance_exceptions?: Array<Record<string, any>>;
};

export type CashierShift = {
  id: number;
  property_code: string;
  business_date: string;
  cashier_name: string;
  assigned_user_email: string;
  opening_float: number;
  currency: string;
  status: string;
  expected_by_method: Record<string, number>;
  declared_by_method: Record<string, number>;
  expected_total: number;
  declared_total: number;
  variance: number;
  manager_approved_by?: string | null;
  manager_approval_reason?: string | null;
  opened_at?: string;
  closed_at?: string | null;
};

export type ArCompanyAccount = { id:number; property_code:string; company_name:string; account_code:string; billing_contact?:string|null; email?:string|null; phone?:string|null; credit_limit:number; current_balance:number; status:string; payment_terms:number; allow_direct_bill:boolean };
export type ArInvoice = { id:number; invoice_number:string; property_code:string; company_account_id:number; folio_id?:number; booking_id?:number; guest_reference?:string; issue_date:string; due_date:string; subtotal:number; tax:number; total:number; balance_due:number; status:string; ledger_transaction_id?:number };
export type ArAging = { property_code:string; as_of:string; buckets:Record<string,number>; total:number; open_invoice_count:number };

export async function fetchArCompanies(propertyCode:string):Promise<ArCompanyAccount[]> { return api(`/finance/ar/companies?property_code=${encodeURIComponent(propertyCode)}`); }
export async function createArCompany(payload:Record<string,unknown>):Promise<ArCompanyAccount> { return api(`/finance/ar/companies`,{method:"POST",body:JSON.stringify(payload)}); }
export async function fetchArInvoices(propertyCode:string,companyId?:number):Promise<ArInvoice[]> { return api(`/finance/ar/invoices?property_code=${encodeURIComponent(propertyCode)}${companyId?`&company_account_id=${companyId}`:""}`); }
export async function fetchArAging(propertyCode:string,asOf:string):Promise<ArAging> { return api(`/finance/ar/aging?property_code=${encodeURIComponent(propertyCode)}&as_of=${encodeURIComponent(asOf)}`); }
export async function transferFolioToAr(payload:Record<string,unknown>):Promise<ArInvoice> { return api(`/finance/ar/transfers`,{method:"POST",body:JSON.stringify(payload)}); }
export async function receiveArPayment(payload:Record<string,unknown>):Promise<Record<string,any>> { return api(`/finance/ar/payments`,{method:"POST",body:JSON.stringify(payload)}); }
export async function voidArInvoice(invoiceId:number,payload:Record<string,unknown>):Promise<Record<string,any>> { return api(`/finance/ar/invoices/${invoiceId}/void`,{method:"POST",body:JSON.stringify(payload)}); }

export async function fetchCurrentCashierShift(propertyCode: string, businessDate: string): Promise<CashierShift | null> {
  const result = await api<{ shift: CashierShift | null }>(`/finance/cashier/shifts/current?property_code=${encodeURIComponent(propertyCode)}&business_date=${encodeURIComponent(businessDate)}`);
  return result.shift;
}

export async function openControlledCashierShift(payload: CashierOpenPayload): Promise<CashierShift> {
  return api(`/finance/cashier/shifts/open`, { method: "POST", body: JSON.stringify(payload) });
}

export async function declareCashierTotals(shiftId: number, payload: { property_code: string; business_date: string; cash: number; card: number; bank_transfer: number; mobile_money: number; unassigned: number }): Promise<CashierShift> {
  return api(`/finance/cashier/shifts/${shiftId}/declare`, { method: "POST", body: JSON.stringify(payload) });
}

export async function requestCashierVarianceApproval(shiftId: number, payload: { property_code: string; business_date: string; reason: string }): Promise<CashierShift> {
  return api(`/finance/cashier/shifts/${shiftId}/request-approval`, { method: "POST", body: JSON.stringify(payload) });
}

export async function approveCashierVariance(shiftId: number, payload: { property_code: string; business_date: string; reason: string }): Promise<CashierShift> {
  return api(`/finance/cashier/shifts/${shiftId}/approve`, { method: "POST", body: JSON.stringify(payload) });
}

export async function closeControlledCashierShift(shiftId: number, payload: { property_code: string; business_date: string; notes?: string }): Promise<CashierShift> {
  return api(`/finance/cashier/shifts/${shiftId}/close`, { method: "POST", body: JSON.stringify(payload) });
}

export async function fetchFolioSummary(
  propertyCode: string,
  bookingId: number
): Promise<FolioSummary> {
  const url =
    `/finance/folio/summary` +
    `?property_code=${encodeURIComponent(propertyCode)}` +
    `&booking_id=${bookingId}`;

  return api<FolioSummary>(url);
}

export async function fetchFolioTransactions(
  propertyCode: string,
  bookingId: number
): Promise<FolioTransaction[]> {
  const url =
    `/finance/folio/transactions` +
    `?property_code=${encodeURIComponent(propertyCode)}` +
    `&booking_id=${bookingId}`;

  return api<FolioTransaction[]>(url);
}

export async function postCharge(
  payload: PostChargePayload
): Promise<{ ok: boolean; message?: string }> {
  return api<{ ok: boolean; message?: string }>(`/finance/charges`, {
    method: "POST",
    body: JSON.stringify({ ...payload, idempotency_key: payload.idempotency_key || financeIdempotencyKey("charge") }),
  });
}

export async function postPayment(
  payload: PostPaymentPayload
): Promise<{ ok: boolean; message?: string }> {
  return api<{ ok: boolean; message?: string }>(`/finance/payments`, {
    method: "POST",
    body: JSON.stringify({ ...payload, idempotency_key: payload.idempotency_key || financeIdempotencyKey("payment") }),
  });
}

export async function validateCheckout(
  propertyCode: string,
  bookingId: number,
  businessDate?: string
): Promise<CheckoutValidation> {
  const url =
    `/finance/checkout/validate` +
    `?property_code=${encodeURIComponent(propertyCode)}` +
    `&booking_id=${bookingId}` +
    (businessDate ? `&business_date=${encodeURIComponent(businessDate)}` : "");

  return api<CheckoutValidation>(url);
}

export async function fetchFinanceControlReport(
  propertyCode: string,
  businessDate: string
): Promise<FinanceControlReport> {
  const url =
    `/finance/control-report` +
    `?property_code=${encodeURIComponent(propertyCode)}` +
    `&business_date=${encodeURIComponent(businessDate)}`;

  return api<FinanceControlReport>(url);
}

export async function closeCashierSession(
  payload: CashierClosePayload
): Promise<CashierCloseResult> {
  return api<CashierCloseResult>(`/finance/cashier/close`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function openCashierSession(
  payload: CashierOpenPayload
): Promise<{ ok: boolean; session_id: number; status: string; opening_float: number }> {
  return api(`/finance/cashier/open`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function applyTaxServiceCharge(payload: {
  property_code: string;
  booking_id: number;
  business_date: string;
  taxable_amount: number;
  tax_rate?: number;
  service_rate?: number;
  currency?: string;
  idempotency_key?: string;
}): Promise<{ ok: boolean; folio_id: number; transaction_ids: number[]; tax_amount: number; service_amount: number }> {
  return api(`/finance/folio/apply-tax-service`, {
    method: "POST",
    body: JSON.stringify({ ...payload, idempotency_key: payload.idempotency_key || financeIdempotencyKey("tax-service") }),
  });
}

export async function postQuoteChargesToFolio(payload: {
  property_code: string;
  booking_id: number;
  business_date: string;
  room_charge_amount?: number;
  currency?: string;
  idempotency_key?: string;
}): Promise<{
  ok: boolean;
  folio_id: number;
  transaction_ids: number[];
  room_charge: number;
  service_charge: number;
  tax: number;
  currency: string;
}> {
  return api(`/finance/folio/post-quote-charges`, {
    method: "POST",
    body: JSON.stringify({ ...payload, idempotency_key: payload.idempotency_key || financeIdempotencyKey("quote-charge") }),
  });
}

export async function voidFolioTransaction(payload: {
  property_code: string;
  transaction_id: number;
  business_date: string;
  reason: string;
  idempotency_key?: string;
}): Promise<{ ok: boolean; transaction_id: number; reversal_transaction_id: number }> {
  return api(`/finance/folio/void-transaction`, {
    method: "POST",
    body: JSON.stringify({ ...payload, idempotency_key: payload.idempotency_key || financeIdempotencyKey("void") }),
  });
}

export async function postRefund(payload: {
  property_code: string;
  booking_id: number;
  business_date: string;
  amount: number;
  payment_method: string;
  reason: string;
  currency?: string;
  idempotency_key?: string;
}): Promise<{ ok: boolean; refund_id: number }> {
  return api(`/finance/folio/refund`, {
    method: "POST",
    body: JSON.stringify({ ...payload, idempotency_key: payload.idempotency_key || financeIdempotencyKey("refund") }),
  });
}

export async function transferFolioBalance(payload: {
  property_code: string;
  booking_id: number;
  business_date: string;
  billing_account: string;
  reason: string;
  idempotency_key?: string;
}): Promise<{ ok: boolean; folio_id: number; balance: number; billing_account: string; status: string }> {
  return api(`/finance/folio/transfer-balance`, {
    method: "POST",
    body: JSON.stringify({ ...payload, idempotency_key: payload.idempotency_key || financeIdempotencyKey("transfer") }),
  });
}

export async function fetchFolioReceipt(
  propertyCode: string,
  bookingId: number
): Promise<FolioReceipt> {
  const url =
    `/finance/folio/receipt` +
    `?property_code=${encodeURIComponent(propertyCode)}` +
    `&booking_id=${bookingId}`;

  return api<FolioReceipt>(url);
}

export async function processCheckoutSettlement(
  payload: CheckoutProcessPayload
): Promise<CheckoutProcessResult> {
  return api<CheckoutProcessResult>(`/checkout/process`, {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      idempotency_key: payload.idempotency_key || (Number(payload.pay_amount || 0) > 0 ? financeIdempotencyKey("checkout") : undefined),
    }),
  });
}
