import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import PageHeader from "../../components/PageHeader";
import KpiCard from "../../components/KpiCard";
import DataTable from "../../components/DataTable";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { permissionMessage, roleCan } from "../../auth/permissions";
import { usePmsContext } from "../../context/PmsContext";
import { getErrorMessage } from "../../services/http";
import { fetchFrontdeskBookings } from "../../services/pmsService";
import {
  fetchFolioSummary,
  fetchFolioTransactions,
  fetchFinanceControlReport,
  fetchDepositAccounts,
  applyTaxServiceCharge,
  closeControlledCashierShift,
  declareCashierTotals,
  fetchCurrentCashierShift,
  fetchFolioReceipt,
  openControlledCashierShift,
  requestCashierVarianceApproval,
  approveCashierVariance,
  postCharge,
  postPayment,
  postRefund,
  processCheckoutSettlement,
  transferFolioBalance,
  validateCheckout,
  voidFolioTransaction,
  type CheckoutProcessResult,
  type FinanceControlReport,
  type DepositAccount,
  type CashierShift,
  type ArCompanyAccount,
  type ArInvoice,
  type ArAging,
  fetchArCompanies,
  createArCompany,
  fetchArInvoices,
  fetchArAging,
  transferFolioToAr,
  receiveArPayment,
  type FolioReceipt,
  type FolioSummary,
  type FolioTransaction,
} from "../../services/financeService";
import type { FrontdeskBooking } from "../../types/pms";

type FinanceTab =
  | "daily_revenue"
  | "trial_balance"
  | "guest_ledger"
  | "deposit_ledger"
  | "payment_ledger"
  | "tax_report"
  | "folio_audit"
  | "ar_city_ledger"
  | "reports_export"
  | "night_audit";

const financeTabs: Record<FinanceTab, string> = {
  daily_revenue: "Daily Revenue",
  trial_balance: "Trial Balance",
  guest_ledger: "Guest Ledger",
  deposit_ledger: "Deposit / Guarantee",
  payment_ledger: "Payment Ledger / Cashier",
  tax_report: "Tax Report",
  folio_audit: "Folio Audit",
  ar_city_ledger: "A/R City Ledger",
  reports_export: "Reports & Export",
  night_audit: "Night Audit Finance",
};

const financeTabByHash: Record<string, FinanceTab> = {
  "daily-revenue": "daily_revenue",
  "trial-balance": "trial_balance",
  "guest-ledger": "guest_ledger",
  "billing-folio": "guest_ledger",
  "deposit-ledger": "deposit_ledger",
  deposit: "deposit_ledger",
  "payment-ledger": "payment_ledger",
  payments: "payment_ledger",
  cashier: "payment_ledger",
  "tax-report": "tax_report",
  "folio-audit": "folio_audit",
  "refund-void": "folio_audit",
  "city-ledger": "ar_city_ledger",
  "accounts-receivable": "ar_city_ledger",
  export: "reports_export",
  "night-audit": "night_audit",
};

function money(v: number | string | null | undefined) {
  const n = Number(v ?? 0);
  return Number.isFinite(n) ? n.toFixed(2) : "0.00";
}

function currencyAmount(currency: string | null | undefined, value: number | string | null | undefined) {
  return `${currency || "ETB"} ${money(value)}`;
}

function dayDiff(start: string, end: string) {
  const startDate = new Date(`${start}T00:00:00`);
  const endDate = new Date(`${end}T00:00:00`);
  const diffMs = endDate.getTime() - startDate.getTime();
  return Math.max(Math.round(diffMs / 86_400_000), 0);
}

function depositActionBadge(row: any) {
  const action = String(row.deposit_action || "").toLowerCase();
  const folioStatus = String(row.folio_status || "").toLowerCase();
  const paymentStatus = String(row.payment_status || "").toLowerCase();
  if (paymentStatus === "deposit_paid" || paymentStatus === "paid") {
    return <StatusBadge status="deposit_paid" />;
  }
  if (action === "deposit expected") return <StatusBadge status="pending" label="Deposit Expected" />;
  if (folioStatus === "folio_prepared") return <StatusBadge status="confirmed" label="Folio Prepared" />;
  return <StatusBadge status="open" label="Review" />;
}

function folioStatusBadge(row: any) {
  const status = String(row.folio_status || "").toLowerCase();
  if (status === "folio_prepared") return <StatusBadge status="confirmed" label="Folio Prepared" />;
  if (status === "pending_request_not_converted") return <StatusBadge status="pending_request" />;
  return <StatusBadge status="pending" label="Folio Pending" />;
}

export default function FinanceDashboard() {
  const location = useLocation();
  const { propertyCode, businessDate, refreshKey } = usePmsContext();

  const [bookingId, setBookingId] = useState<number>(0);
  const [bookings, setBookings] = useState<FrontdeskBooking[]>([]);
  const [summary, setSummary] = useState<FolioSummary | null>(null);
  const [transactions, setTransactions] = useState<FolioTransaction[]>([]);
  const [controlReport, setControlReport] = useState<FinanceControlReport | null>(null);
  const [depositAccounts, setDepositAccounts] = useState<DepositAccount[]>([]);
  const [cashierShift, setCashierShift] = useState<CashierShift | null>(null);
  const [arCompanies, setArCompanies] = useState<ArCompanyAccount[]>([]);
  const [arInvoices, setArInvoices] = useState<ArInvoice[]>([]);
  const [arAging, setArAging] = useState<ArAging | null>(null);
  const [arCompanyId, setArCompanyId] = useState<number>(0);
  const [arCompanyName, setArCompanyName] = useState("");
  const [arAccountCode, setArAccountCode] = useState("");
  const [arCreditLimit, setArCreditLimit] = useState("0");
  const [arPaymentAmount, setArPaymentAmount] = useState("");
  const [activeTab, setActiveTab] = useState<FinanceTab>("daily_revenue");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const canPostCharge = roleCan("finance.post_charge");
  const canPostPayment = roleCan("finance.post_payment");
  const canApproveAccounting = roleCan("finance.void_transaction");
  const canTransferBalance = roleCan("finance.transfer_balance");

  const [chargeAmount, setChargeAmount] = useState("");
  const [chargeDescription, setChargeDescription] = useState("");
  const [chargeCategory, setChargeCategory] = useState("fnb");

  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [paymentReference, setPaymentReference] = useState("");
  const [paymentExchangeRate, setPaymentExchangeRate] = useState("");
  const [checkoutPaymentAmount, setCheckoutPaymentAmount] = useState("");
  const [checkoutPaymentMethod, setCheckoutPaymentMethod] = useState("cash");
  const [checkoutExchangeRate, setCheckoutExchangeRate] = useState("");
  const [checkoutResult, setCheckoutResult] = useState<CheckoutProcessResult | null>(null);
  const [receipt, setReceipt] = useState<FolioReceipt | null>(null);
  const [cashierName, setCashierName] = useState("manager");
  const [openingFloat, setOpeningFloat] = useState("0");
  const [actualCash, setActualCash] = useState("");
  const [actualCard, setActualCard] = useState("");
  const [actualBank, setActualBank] = useState("");
  const [actualMobile, setActualMobile] = useState("");
  const [actualUnassigned, setActualUnassigned] = useState("");
  const [varianceReason, setVarianceReason] = useState("");

  useEffect(() => {
    const hashKey = location.hash.replace(/^#/, "");
    const tab = financeTabByHash[hashKey];
    if (tab) setActiveTab(tab);
  }, [location.hash]);
  const selectedBooking = bookings.find((booking) => booking.id === bookingId);
  const scheduledCheckoutDate =
    summary?.check_out_date || selectedBooking?.check_out_date || null;
  const activeCurrency = summary?.currency || selectedBooking?.currency || "ETB";
  const baseCurrency = "ETB";
  const requiresExchangeRate = activeCurrency !== baseCurrency;
  const paymentBaseEstimate =
    requiresExchangeRate && paymentAmount && paymentExchangeRate
      ? Number(paymentAmount) * Number(paymentExchangeRate)
      : Number(paymentAmount || 0);
  const checkoutBaseEstimate =
    requiresExchangeRate && checkoutPaymentAmount && checkoutExchangeRate
      ? Number(checkoutPaymentAmount) * Number(checkoutExchangeRate)
      : Number(checkoutPaymentAmount || 0);
  const isEarlyCheckout =
    Boolean(scheduledCheckoutDate) && businessDate < String(scheduledCheckoutDate);
  const nightsRemaining = scheduledCheckoutDate
    ? dayDiff(businessDate, scheduledCheckoutDate)
    : 0;

  async function loadData() {
    if (!bookingId || bookingId <= 0) {
      setError("Choose a booking before loading a folio.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setActionMessage("");

      const [folio, txns] = await Promise.all([
        fetchFolioSummary(propertyCode, bookingId),
        fetchFolioTransactions(propertyCode, bookingId),
      ]);

      setSummary(folio);
      setTransactions(txns);
      setCheckoutPaymentAmount(String(Math.max(Number(folio.balance || 0), 0)));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function loadControlReport() {
    try {
      setError("");
      const [report, deposits, shift, companies, invoices, aging] = await Promise.all([
        fetchFinanceControlReport(propertyCode, businessDate),
        fetchDepositAccounts(propertyCode),
        fetchCurrentCashierShift(propertyCode, businessDate),
        fetchArCompanies(propertyCode),
        fetchArInvoices(propertyCode),
        fetchArAging(propertyCode, businessDate),
      ]);
      setControlReport(report);
      setDepositAccounts(deposits);
      setCashierShift(shift);
      setArCompanies(companies); setArInvoices(invoices); setArAging(aging);
      setArCompanyId((current) => current && companies.some((item) => item.id===current) ? current : companies[0]?.id || 0);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  useEffect(() => {
    async function loadBookings() {
      try {
        const rows = await fetchFrontdeskBookings(propertyCode, businessDate);
        setBookings(rows);
        setBookingId((current) => {
          if (current > 0 && rows.some((row) => row.id === current)) return current;
          return rows[0]?.id ?? 0;
        });
      } catch (err) {
        setError(getErrorMessage(err));
      }
    }

    loadBookings();
    loadControlReport();
  }, [propertyCode, businessDate, refreshKey]);

  useEffect(() => {
    if (bookingId > 0) loadData();
  }, [bookingId]);

  async function handlePostCharge() {
    try {
      setError("");
      setActionMessage("");

      await postCharge({
        property_code: propertyCode,
        booking_id: bookingId,
        business_date: businessDate,
        amount: Number(chargeAmount),
        description: chargeDescription,
        category: chargeCategory,
        currency: activeCurrency,
      });

      setChargeAmount("");
      setChargeDescription("");
      setActionMessage("Charge posted successfully.");
      await loadData();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handlePostPayment() {
    try {
      setError("");
      setActionMessage("");

      await postPayment({
        property_code: propertyCode,
        booking_id: bookingId,
        business_date: businessDate,
        amount: Number(paymentAmount),
        payment_method: paymentMethod,
        reference: paymentReference,
        currency: activeCurrency,
        exchange_rate_to_base: requiresExchangeRate ? Number(paymentExchangeRate) : 1,
        exchange_rate_source: requiresExchangeRate ? "manual_front_desk" : "same_currency",
      });

      setPaymentAmount("");
      setPaymentReference("");
      setPaymentExchangeRate("");
      setActionMessage("Payment posted successfully.");
      await loadData();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleValidateCheckout() {
    try {
      setError("");
      setActionMessage("");

      const result = await validateCheckout(propertyCode, bookingId, businessDate);
      setActionMessage(
        [
          result.can_checkout
            ? `Check-Out allowed. Balance: ${activeCurrency} ${money(result.balance)}`
            : `Check-Out blocked. Balance: ${activeCurrency} ${money(result.balance)}. ${result.message || ""}`,
          result.is_early_checkout
            ? `Early Check-Out: scheduled departure is ${result.scheduled_check_out_date}; ${result.nights_remaining || 0} night(s) remain.`
            : "",
        ]
          .filter(Boolean)
          .join(" ")
      );
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleProcessCheckout() {
    try {
      setError("");
      setActionMessage("");
      setReceipt(null);
      setCheckoutResult(null);

      const result = await processCheckoutSettlement({
        property_code: propertyCode,
        booking_id: bookingId,
        business_date: businessDate,
        pay_amount: Number(checkoutPaymentAmount || 0),
        pay_method: checkoutPaymentMethod,
        description: "Check-Out settlement",
        currency: activeCurrency,
        exchange_rate_to_base: requiresExchangeRate ? Number(checkoutExchangeRate) : 1,
        exchange_rate_source: requiresExchangeRate ? "manual_checkout" : "same_currency",
        close_folio: true,
        mark_booking_checked_out: true,
      });

      setCheckoutResult(result);
      setActionMessage(
        result.receipt
          ? `Check-Out completed. Receipt ${result.receipt.receipt_number}, invoice ${result.receipt.invoice_number} queued for guest notification.`
          : "Check-Out completed."
      );
      await Promise.all([loadData(), loadControlReport()]);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  function handlePrintReport() {
    window.print();
  }

  async function handleCloseCashierShift() {
    try {
      setError("");
      setActionMessage("");
      if (!cashierShift) throw new Error("Open a cashier shift first.");
      const result = await closeControlledCashierShift(cashierShift.id, { property_code: propertyCode, business_date: businessDate, notes: `Closed from Finance & Accounting Command Center for ${activeTab}` });
      setActionMessage(
        `Cashier shift #${result.id} closed. Expected ${activeCurrency} ${money(result.expected_total)}, declared ${activeCurrency} ${money(result.declared_total)}, variance ${activeCurrency} ${money(result.variance)}.`
      );
      await loadControlReport();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleOpenCashierShift() {
    try {
      setError("");
      setActionMessage("");
      const result = await openControlledCashierShift({
        property_code: propertyCode,
        business_date: businessDate,
        cashier_name: cashierName || "cashier",
        opening_float: Number(openingFloat || 0),
        notes: "Opened from Finance & Accounting Command Center",
      });
      setActionMessage(`Cashier shift #${result.id} opened with float ${activeCurrency} ${money(result.opening_float)}.`);
      await loadControlReport();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleDeclareCashierTotals() {
    try {
      if (!cashierShift) throw new Error("Open a cashier shift first.");
      const result = await declareCashierTotals(cashierShift.id, { property_code: propertyCode, business_date: businessDate, cash: Number(actualCash || 0), card: Number(actualCard || 0), bank_transfer: Number(actualBank || 0), mobile_money: Number(actualMobile || 0), unassigned: Number(actualUnassigned || 0) });
      setCashierShift(result);
      setActionMessage(`Totals declared. Variance ${activeCurrency} ${money(result.variance)}.`);
    } catch (err) { setError(getErrorMessage(err)); }
  }

  async function handleRequestVarianceApproval() {
    try {
      if (!cashierShift) throw new Error("No current cashier shift.");
      const result = await requestCashierVarianceApproval(cashierShift.id, { property_code: propertyCode, business_date: businessDate, reason: varianceReason });
      setCashierShift(result);
      setActionMessage("Variance approval requested.");
    } catch (err) { setError(getErrorMessage(err)); }
  }

  async function handleApproveVariance() {
    try {
      if (!cashierShift) throw new Error("No current cashier shift.");
      const result = await approveCashierVariance(cashierShift.id, { property_code: propertyCode, business_date: businessDate, reason: varianceReason });
      setCashierShift(result);
      setActionMessage("Variance approved.");
    } catch (err) { setError(getErrorMessage(err)); }
  }

  async function handleCreateArCompany() {
    try { const created=await createArCompany({property_code:propertyCode,company_name:arCompanyName,account_code:arAccountCode,credit_limit:Number(arCreditLimit||0),payment_terms:30,status:"active",allow_direct_bill:true}); setActionMessage(`City Ledger account ${created.account_code} created.`); setArCompanyName("");setArAccountCode("");await loadControlReport(); } catch(err){setError(getErrorMessage(err));}
  }

  async function handleArTransfer() {
    try { if(!bookingId||!arCompanyId) throw new Error("Select a folio and company account."); const result=await transferFolioToAr({property_code:propertyCode,booking_id:bookingId,company_account_id:arCompanyId,business_date:businessDate,tax:0,manager_override_reason:"Finance-approved City Ledger transfer",idempotency_key:`ar-ui-${propertyCode}-${bookingId}-${Date.now()}`}); setActionMessage(`AR invoice ${result.invoice_number} issued.`);await Promise.all([loadData(),loadControlReport()]); } catch(err){setError(getErrorMessage(err));}
  }

  async function handleArPayment() {
    try { if(!arCompanyId) throw new Error("Select a company account."); const result=await receiveArPayment({property_code:propertyCode,company_account_id:arCompanyId,business_date:businessDate,amount:Number(arPaymentAmount),currency:baseCurrency,payment_method:"bank_transfer",channel:"back_office",idempotency_key:`ar-pay-ui-${Date.now()}`});setActionMessage(`AR payment posted. Allocated ${money(result.allocated_amount)}, unapplied ${money(result.unapplied_amount)}.`);setArPaymentAmount("");await loadControlReport(); } catch(err){setError(getErrorMessage(err));}
  }

  async function handleApplyTaxService() {
    try {
      setError("");
      setActionMessage("");
      const result = await applyTaxServiceCharge({
        property_code: propertyCode,
        booking_id: bookingId,
        business_date: businessDate,
        taxable_amount: Number(summary?.charges_total || 0),
        tax_rate: 0.15,
        service_rate: 0.1,
        currency: activeCurrency,
      });
      setActionMessage(
        `Tax/service posted. Tax ${activeCurrency} ${money(result.tax_amount)}, service ${activeCurrency} ${money(result.service_amount)}.`
      );
      await Promise.all([loadData(), loadControlReport()]);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleLoadReceipt() {
    try {
      setError("");
      setActionMessage("");
      const result = await fetchFolioReceipt(propertyCode, bookingId);
      setReceipt(result);
      setActionMessage(`Receipt ${result.receipt_number} loaded.`);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleVoidTransaction(transactionId: number) {
    const reason = window.prompt("Manager void reason");
    if (!reason) return;
    try {
      setError("");
      setActionMessage("");
      const result = await voidFolioTransaction({
        property_code: propertyCode,
        transaction_id: transactionId,
        business_date: businessDate,
        reason,
      });
      setActionMessage(`Transaction #${transactionId} voided with reversal #${result.reversal_transaction_id}.`);
      await Promise.all([loadData(), loadControlReport()]);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleRefund() {
    const amount = window.prompt("Refund amount");
    if (!amount) return;
    const reason = window.prompt("Manager refund reason");
    if (!reason) return;
    try {
      setError("");
      setActionMessage("");
      const result = await postRefund({
        property_code: propertyCode,
        booking_id: bookingId,
        business_date: businessDate,
        amount: Number(amount),
        payment_method: checkoutPaymentMethod,
        reason,
        currency: activeCurrency,
      });
      setActionMessage(`Refund #${result.refund_id} posted.`);
      await Promise.all([loadData(), loadControlReport()]);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleTransferBalance() {
    const billingAccount = window.prompt("Approved billing / city ledger account");
    if (!billingAccount) return;
    const reason = window.prompt("Manager transfer reason");
    if (!reason) return;
    try {
      setError("");
      setActionMessage("");
      const result = await transferFolioBalance({
        property_code: propertyCode,
        booking_id: bookingId,
        business_date: businessDate,
        billing_account: billingAccount,
        reason,
      });
      setActionMessage(
        `Balance ${money(result.balance)} transferred to ${result.billing_account}.`
      );
      await Promise.all([loadData(), loadControlReport()]);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  function handleExportCsv() {
    const payload =
      activeTab === "daily_revenue"
        ? controlReport?.daily_revenue
        : activeTab === "trial_balance"
          ? controlReport?.trial_balance
          : activeTab === "tax_report"
            ? controlReport?.tax_report
            : activeTab === "guest_ledger"
              ? controlReport?.guest_ledger
              : activeTab === "deposit_ledger"
                ? controlReport?.deposit_ledger
                : activeTab === "payment_ledger"
                  ? controlReport?.payment_ledger
                  : activeTab === "folio_audit"
                    ? controlReport?.folio_transaction_audit
                    : {};

    const escapeCsv = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const csv =
      Array.isArray(payload) && payload.length > 0
        ? [
            Object.keys(payload[0]).map(escapeCsv).join(","),
            ...payload.map((row) => Object.values(row).map(escapeCsv).join(",")),
          ].join("\n")
        : [
            "metric,value",
            ...Object.entries(payload || {}).map(([key, value]) =>
              [key, value].map(escapeCsv).join(",")
            ),
          ].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${propertyCode}-${activeTab}-${businessDate}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="page-grid finance-command">
      <PageHeader
        title="Finance"
        subtitle="Daily revenue, ledgers, cashier, tax, and night-audit finance control."
        metadata={`${propertyCode} • ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">Property: {propertyCode}</div>
            <div className="pill">Business Date: {businessDate}</div>
            <div className="pill">Status: {controlReport?.accounting_lock?.status || "open"}</div>
          </>
        }
      />

      {error ? <div className="error-box">{error}</div> : null}
      {actionMessage ? <div className="card">{actionMessage}</div> : null}
      {!canPostCharge && !canPostPayment ? (
        <div className="notice-box">{permissionMessage("Finance posting actions")}</div>
      ) : null}
      {isEarlyCheckout ? (
        <div className="notice-box">
          <strong>Early Check-Out request</strong>
          <span>
            {summary?.guest_name || selectedBooking?.guest_name || "Selected guest"} is
            completing Check-Out on {businessDate}, before the scheduled departure date of{" "}
            {scheduledCheckoutDate}. {nightsRemaining} night(s) remain.
          </span>
        </div>
      ) : null}

      <div className="card">
        <div className="section-heading">
          <div>
            <h2>Report Toolbar</h2>
            <div className="muted">
              Currency {activeCurrency}. Draft reports stay editable until Night Audit locks the business date.
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button className="small-btn" onClick={loadControlReport}>Refresh</button>
            <button className="small-btn" onClick={handlePrintReport}>Print</button>
            <button className="small-btn" onClick={handleExportCsv}>Export CSV</button>
            <button className="small-btn" onClick={() => setActionMessage("PDF export will use the locked report package after Night Audit.")}>Export PDF</button>
            <button className="small-btn" onClick={() => setActionMessage("Manager email queued for the selected finance report.")}>Email Manager</button>
            <button className="small-btn" onClick={handleCloseCashierShift}>Close Cashier Shift</button>
            <button className="small-btn" onClick={() => setActionMessage("Finance lock is controlled by Night Audit close.")}>Lock Report</button>
          </div>
        </div>
      </div>

      <div className="workflow-tabs">
        {(Object.keys(financeTabs) as FinanceTab[]).map((tab) => (
          <button
            className={`tab-btn ${activeTab === tab ? "active" : ""}`}
            key={tab}
            onClick={() => setActiveTab(tab)}
            type="button"
          >
            {financeTabs[tab]}
          </button>
        ))}
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Folio Lookup</h2>
        <div className="muted" style={{ marginBottom: "14px" }}>
          Load folio summary, transactions, and Check-Out validation
        </div>

        <div className="toolbar-grid">
          <div className="field">
            <label>Booking ID</label>
            <select
              value={bookingId || ""}
              onChange={(e) => setBookingId(Number(e.target.value))}
            >
              <option value="">Choose booking</option>
              {bookings.map((booking) => (
                <option key={booking.id} value={booking.id}>
                  #{booking.id} - {booking.guest_name} - {booking.booking_status}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label>Manual Booking ID</label>
            <input
              type="number"
              value={bookingId || ""}
              onChange={(e) => setBookingId(Number(e.target.value))}
              placeholder="Enter booking ID"
            />
          </div>

          <div className="field" style={{ alignSelf: "end" }}>
            <button className="primary-btn" onClick={loadData} disabled={!bookingId}>
              Load Folio
            </button>
          </div>

          <div className="field" style={{ alignSelf: "end" }}>
            <button className="small-btn" onClick={handleValidateCheckout} disabled={!bookingId}>
              Validate Check-Out
            </button>
          </div>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard label="Charges Total" value={money(summary?.charges_total)} />
        <KpiCard label="Payments Total" value={money(summary?.payments_total)} />
        <KpiCard label="Balance" value={money(summary?.balance)} />
        <KpiCard
          label="Scheduled Check-Out"
          value={scheduledCheckoutDate || "-"}
          helpText={isEarlyCheckout ? "Early Check-Out" : "Normal departure"}
        />
      </div>

      <div className="card">
        <div className="section-heading">
          <div>
            <h2>Folio Lifecycle Control</h2>
            <div className="muted">
              Open folio, post charges/payments, apply tax/service, issue receipt, and route approved balances.
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button className="small-btn" onClick={loadData} disabled={!bookingId}>Open / Refresh Folio</button>
            {canPostCharge ? (
              <button className="small-btn" onClick={handleApplyTaxService} disabled={!bookingId || !summary?.charges_total}>
                Apply Tax + Service
              </button>
            ) : null}
            <button className="small-btn" onClick={handleLoadReceipt} disabled={!bookingId}>Receipt / Invoice</button>
            {canApproveAccounting ? (
              <button className="small-btn" onClick={handleRefund} disabled={!bookingId}>Manager Refund</button>
            ) : null}
            {canTransferBalance ? (
              <button className="small-btn" onClick={handleTransferBalance} disabled={!bookingId || !summary?.balance}>
                Transfer to City Ledger
              </button>
            ) : null}
          </div>
        </div>

        {!canApproveAccounting ? (
          <div className="notice-box" style={{ marginTop: "14px" }}>
            {permissionMessage("Refunds, voids, and balance transfers")}
          </div>
        ) : null}

        {receipt ? (
          <div className="notice-box" style={{ marginTop: "14px" }}>
            <strong>Receipt / Invoice</strong>
            <span>Guest: {receipt.guest_name || "-"}</span>
            <span>Receipt: {receipt.receipt_number}</span>
            <span>Invoice: {receipt.invoice_number}</span>
            <span>Room Charge Subtotal: {receipt.currency} {money(receipt.room_charge_subtotal)}</span>
            <span>F&B / Other Charges: {receipt.currency} {money(receipt.fnb_other_charge_subtotal)}</span>
            <span>
              Service Charge: {receipt.currency} {money(receipt.service_charge_amount)}
              {receipt.service_charge_percent != null ? ` (${Number(receipt.service_charge_percent) * 100}%)` : ""}
            </span>
            <span>
              VAT / Tax: {receipt.currency} {money(receipt.vat_tax_amount)}
              {receipt.tax_percent != null ? ` (${Number(receipt.tax_percent) * 100}%)` : ""}
            </span>
            {!receipt.tax_service_posted ? (
              <span className="muted">{receipt.tax_service_warning || "Tax/service not posted."}</span>
            ) : null}
            <span>
              Charges {receipt.currency} {money(receipt.total_charges)} / Payments {receipt.currency} {money(receipt.total_payments)} / Balance {receipt.currency} {money(receipt.balance)}
            </span>
            <span>Tax / Service: {receipt.currency} {money(receipt.tax_service_charge)}</span>
            {receipt.payments?.some((payment) => payment.base_amount != null && payment.original_currency !== payment.base_currency) ? (
              <span>
                ETB Equivalent:{" "}
                {receipt.payments
                  .filter((payment) => payment.base_amount != null && payment.original_currency !== payment.base_currency)
                  .map((payment) =>
                    `${payment.original_currency} ${money(payment.original_amount)} = ${payment.base_currency} ${money(payment.base_amount)}`
                  )
                  .join("; ")}
              </span>
            ) : null}
            <span>Payment Method: {receipt.payment_method || "-"}</span>
            {receipt.line_items?.length ? (
              <div style={{ marginTop: "10px", overflowX: "auto" }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Description</th>
                      <th>Category</th>
                      <th>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {receipt.line_items.map((item: any) => (
                      <tr key={item.id}>
                        <td data-label="Date">{item.date || "-"}</td>
                        <td data-label="Description">{item.description || "-"}</td>
                        <td data-label="Category">{item.category || item.txn_type || "-"}</td>
                        <td data-label="Amount">{currencyAmount(item.currency, item.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Check-Out Settlement</h2>
        <div className="muted" style={{ marginBottom: "14px" }}>
          Settle remaining balance, close folio, complete guest Check-Out, issue receipt, and send room to Housekeeping.
        </div>

        <div className="toolbar-grid">
          <div className="field">
            <label>Balance Due</label>
            <input value={money(summary?.balance)} readOnly />
          </div>
          <div className="field">
            <label>Collect Now</label>
            <input
              type="number"
              value={checkoutPaymentAmount}
              onChange={(event) => setCheckoutPaymentAmount(event.target.value)}
              placeholder="0.00"
            />
          </div>
          {requiresExchangeRate ? (
            <div className="field">
              <label>{activeCurrency} to {baseCurrency} Rate</label>
              <input
                type="number"
                value={checkoutExchangeRate}
                onChange={(event) => setCheckoutExchangeRate(event.target.value)}
                placeholder="Exchange rate"
              />
            </div>
          ) : null}
          <div className="field">
            <label>Payment Method</label>
            <select
              value={checkoutPaymentMethod}
              onChange={(event) => setCheckoutPaymentMethod(event.target.value)}
            >
              <option value="cash">cash</option>
              <option value="card">card</option>
              <option value="pos">pos</option>
              <option value="bank_transfer">bank_transfer</option>
              <option value="telebirr">telebirr</option>
              <option value="mobile_money">mobile_money</option>
            </select>
          </div>
          <div className="field" style={{ alignSelf: "end" }}>
            <button
              className="primary-btn"
              disabled={!bookingId || loading}
              onClick={handleProcessCheckout}
            >
              Settle & Check-Out
            </button>
          </div>
        </div>
        {requiresExchangeRate ? (
          <div className="muted" style={{ marginTop: "10px" }}>
            ETB equivalent: {baseCurrency} {money(checkoutBaseEstimate)}
          </div>
        ) : null}

        {checkoutResult?.receipt ? (
          <div className="notice-box" style={{ marginTop: "14px" }}>
            <strong>Receipt Issued</strong>
            <span>Receipt: {checkoutResult.receipt.receipt_number}</span>
            <span>Invoice: {checkoutResult.receipt.invoice_number}</span>
            <span>
              Charges {checkoutResult.receipt.currency} {money(checkoutResult.receipt.total_charges)} /
              Payments {checkoutResult.receipt.currency} {money(checkoutResult.receipt.total_payments)} /
              Balance {checkoutResult.receipt.currency} {money(checkoutResult.receipt.balance)}
            </span>
          </div>
        ) : null}
      </div>

      <div className="kpi-grid">
        <KpiCard label="Gross Booking Value" value={money(controlReport?.finance_dashboard.gross_booking_value)} />
        <KpiCard label="Collected Payments" value={money(controlReport?.finance_dashboard.payments_collected)} />
        <KpiCard label="Pending Payments" value={money(controlReport?.finance_dashboard.pending_payments)} />
        <KpiCard label="Pending Guarantees" value={String(controlReport?.finance_dashboard.pending_guarantee_reservations ?? 0)} />
        <KpiCard label="Deposit Expected" value={String(controlReport?.finance_dashboard.deposit_expected ?? 0)} />
        <KpiCard label="Folios Prepared" value={String(controlReport?.finance_dashboard.folios_prepared ?? 0)} />
        <KpiCard label="Guest Ledger" value={money(controlReport?.finance_dashboard.guest_ledger_balance)} />
        <KpiCard label="Deposit Ledger" value={money(controlReport?.finance_dashboard.deposit_ledger_balance)} />
        <KpiCard label="Tax Collected" value={money(controlReport?.finance_dashboard.tax_collected)} />
        <KpiCard label="Open Folios" value={String(controlReport?.finance_dashboard.open_folios ?? 0)} />
        <KpiCard label="Cashier Variance" value={money(controlReport?.cashier_shift.variance)} />
      </div>

      {controlReport?.finance_exceptions?.length ? (
        <div className="notice-box">
          <strong>Finance Exceptions</strong>
          {controlReport.finance_exceptions.map((item: any) => (
            <span key={item.key}>{item.message}</span>
          ))}
        </div>
      ) : null}

      {activeTab === "daily_revenue" ? (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Daily Revenue Report</h2>
          <div className="muted" style={{ marginBottom: "14px" }}>
            Revenue, payments, refunds, taxes, and net revenue for the business date
          </div>
          <DataTable
            rows={Object.entries(controlReport?.daily_revenue || {}).map(([label, value]) => ({
              label: label.replace(/_/g, " "),
              value,
            }))}
            emptyMessage="No revenue report loaded."
            columns={[
              { key: "label", header: "Metric", render: (row) => row.label },
              { key: "value", header: "Amount", render: (row) => money(row.value) },
            ]}
          />
        </div>
      ) : null}

      {activeTab === "trial_balance" ? (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Trial Balance</h2>
          <div className="muted" style={{ marginBottom: "14px" }}>
            Guest ledger, deposit ledger, AR, revenue, payments, tax, and closing balance
          </div>
          <DataTable
            rows={Object.entries(controlReport?.trial_balance || {}).map(([label, value]) => ({
              label: label.replace(/_/g, " "),
              value,
            }))}
            emptyMessage="No trial balance loaded."
            columns={[
              { key: "label", header: "Ledger", render: (row) => row.label },
              { key: "value", header: "Balance", render: (row) => money(row.value) },
            ]}
          />
        </div>
      ) : null}

      {activeTab === "deposit_ledger" ? (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Deposit / Guarantee Ledger</h2>
          <div className="muted" style={{ marginBottom: "14px" }}>
            Pending guarantee, deposit-paid, and guaranteed future arrivals
          </div>
          <DataTable
            rows={depositAccounts}
            emptyMessage="No deposit or guarantee records found."
            columns={[
              { key: "booking", header: "Booking", render: (row: any) => `#${row.booking_id}` },
              { key: "requested", header: "Requested", render: (row: any) => currencyAmount(row.currency, row.requested_amount) },
              { key: "paid", header: "Paid", render: (row: any) => currencyAmount(row.currency, row.paid_amount) },
              { key: "remaining", header: "Remaining", render: (row: any) => currencyAmount(row.currency, row.remaining_amount) },
              { key: "allocated", header: "Allocated", render: (row: any) => currencyAmount(row.currency, row.allocated_amount) },
              { key: "refundable", header: "Terms", render: (row: any) => row.refundable ? "Refundable" : "Non-refundable" },
              { key: "method", header: "Method", render: (row: any) => row.payment_method || "-" },
              { key: "reference", header: "Reference", render: (row: any) => row.reference || "-" },
              { key: "status", header: "Status", render: (row: any) => <StatusBadge status={row.status} /> },
            ]}
          />
        </div>
      ) : null}

      {activeTab === "payment_ledger" ? (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Payment Ledger / Cashier</h2>
          <div className="muted" style={{ marginBottom: "14px" }}>
            Payments collected by method with cashier shift totals in ETB base currency
          </div>
          <div className="dashboard-metric-strip" style={{ marginBottom: "14px" }}>
            <div><span>Current Shift</span><strong>{cashierShift ? `#${cashierShift.id} · ${cashierShift.status}` : "Not Open"}</strong></div>
            <div><span>Assigned Cashier</span><strong>{cashierShift?.cashier_name || "-"}</strong></div>
            <div><span>Opening Float</span><strong>{baseCurrency} {money(cashierShift?.opening_float)}</strong></div>
            <div><span>Expected Total</span><strong>{baseCurrency} {money(cashierShift?.expected_total)}</strong></div>
            <div><span>Declared Total</span><strong>{baseCurrency} {money(cashierShift?.declared_total)}</strong></div>
            <div><span>Variance</span><strong>{baseCurrency} {money(cashierShift?.variance)}</strong></div>
          </div>
          <div className="dashboard-metric-strip" style={{ marginBottom: "14px" }}>
            <div><span>Expected Cash</span><strong>{baseCurrency} {money(cashierShift?.expected_by_method?.cash)}</strong></div>
            <div><span>Expected Card</span><strong>{baseCurrency} {money(cashierShift?.expected_by_method?.card)}</strong></div>
            <div><span>Expected Bank</span><strong>{baseCurrency} {money(cashierShift?.expected_by_method?.bank_transfer)}</strong></div>
            <div><span>Expected Mobile</span><strong>{baseCurrency} {money(cashierShift?.expected_by_method?.mobile_money)}</strong></div>
            <div><span>Expected Unassigned</span><strong>{baseCurrency} {money(cashierShift?.expected_by_method?.unassigned)}</strong></div>
          </div>
          <div className="toolbar-grid" style={{ marginBottom: "14px" }}>
            <div className="field">
              <label>Cashier</label>
              <input value={cashierName} onChange={(event) => setCashierName(event.target.value)} />
            </div>
            <div className="field">
              <label>Opening Float</label>
              <input type="number" value={openingFloat} onChange={(event) => setOpeningFloat(event.target.value)} />
            </div>
            <div className="field">
              <label>Actual Cash</label>
              <input type="number" value={actualCash} onChange={(event) => setActualCash(event.target.value)} placeholder={money(controlReport?.cashier_shift.cash)} />
            </div>
            <div className="field">
              <label>Actual Card</label>
              <input type="number" value={actualCard} onChange={(event) => setActualCard(event.target.value)} placeholder={money(controlReport?.cashier_shift.card)} />
            </div>
            <div className="field">
              <label>Actual Bank</label>
              <input type="number" value={actualBank} onChange={(event) => setActualBank(event.target.value)} placeholder={money(controlReport?.cashier_shift.bank_transfer)} />
            </div>
            <div className="field">
              <label>Actual Mobile</label>
              <input type="number" value={actualMobile} onChange={(event) => setActualMobile(event.target.value)} placeholder={money(controlReport?.cashier_shift.mobile_money)} />
            </div>
            <div className="field">
              <label>Variance Approval Reason</label>
              <input value={varianceReason} onChange={(event) => setVarianceReason(event.target.value)} placeholder="Required if variance exists" />
            </div>
          </div>
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginBottom: "14px" }}>
            <button className="small-btn" onClick={handleOpenCashierShift} disabled={Boolean(cashierShift)}>Open Shift</button>
            <button className="small-btn" onClick={handleDeclareCashierTotals} disabled={!cashierShift || cashierShift.status !== "open"}>Declare Totals</button>
            <button className="small-btn" onClick={handleRequestVarianceApproval} disabled={cashierShift?.status !== "approval_required"}>Request Approval</button>
            <button className="small-btn" onClick={handleApproveVariance} disabled={!cashierShift || !["approval_required", "approval_requested"].includes(cashierShift.status)}>Approve Variance</button>
            <button className="primary-btn" onClick={handleCloseCashierShift} disabled={!cashierShift || !["declared", "approved"].includes(cashierShift.status)}>Close Shift</button>
            <button className="small-btn" onClick={handlePrintReport}>Cashier Closure Report</button>
            <button className="small-btn" onClick={handleExportCsv}>Export CSV</button>
          </div>
          <DataTable
            rows={controlReport?.payment_ledger || []}
            emptyMessage="No payment ledger activity for this date."
            columns={[
              { key: "booking", header: "Booking", render: (row: any) => `#${row.booking_id}` },
              { key: "guest", header: "Guest", render: (row: any) => row.guest_name },
              { key: "method", header: "Method", render: (row: any) => row.payment_method },
              { key: "amount", header: "Paid", render: (row: any) => currencyAmount(row.original_currency || row.currency, row.original_amount ?? row.amount) },
              { key: "base", header: "ETB Equivalent", render: (row: any) => row.base_amount != null ? currencyAmount(row.base_currency || baseCurrency, row.base_amount) : "Rate Missing" },
              { key: "rate", header: "Rate", render: (row: any) => row.exchange_rate_to_base ?? "-" },
            ]}
          />
        </div>
      ) : null}

      {activeTab === "guest_ledger" ? (
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Guest Ledger</h2>
        <div className="muted" style={{ marginBottom: "14px" }}>
          Open folios and balance due control before checkout and night audit
        </div>
        <DataTable
          rows={controlReport?.guest_ledger || []}
          emptyMessage="No open guest ledger balances."
          columns={[
            { key: "folio", header: "Folio", render: (row: any) => `#${row.folio_id}` },
            { key: "booking", header: "Booking", render: (row: any) => `#${row.booking_id}` },
            { key: "guest", header: "Guest", render: (row: any) => row.guest_name },
            { key: "room", header: "Room", render: (row: any) => row.room_number || "-" },
            { key: "folio_status", header: "Handoff", render: () => <StatusBadge status="confirmed" label="Folio Prepared" /> },
            { key: "charges", header: "Charges", render: (row: any) => money(row.charges) },
            { key: "payments", header: "Payments", render: (row: any) => money(row.payments) },
            { key: "balance", header: "Balance", render: (row: any) => money(row.balance) },
          ]}
        />
      </div>
      ) : null}

      {activeTab === "tax_report" ? (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Tax Report</h2>
          <div className="muted" style={{ marginBottom: "14px" }}>
            VAT estimate, service charge, taxable revenue, and tax-exempt controls
          </div>
          <DataTable
            rows={Object.entries(controlReport?.tax_report || {}).map(([label, value]) => ({
              label: label.replace(/_/g, " "),
              value,
            }))}
            emptyMessage="No tax report loaded."
            columns={[
              { key: "label", header: "Tax Metric", render: (row) => row.label },
              { key: "value", header: "Amount", render: (row) => money(row.value) },
            ]}
          />
        </div>
      ) : null}

      {activeTab === "folio_audit" ? (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Folio Transaction Audit</h2>
          <div className="muted" style={{ marginBottom: "14px" }}>
            Detailed charge/payment/refund/adjustment activity for audit review
          </div>
          <DataTable
            rows={controlReport?.folio_transaction_audit || []}
            emptyMessage="No folio transactions for this date."
            columns={[
              { key: "id", header: "Txn", render: (row: any) => `#${row.id}` },
              { key: "booking", header: "Booking", render: (row: any) => `#${row.booking_id}` },
              { key: "guest", header: "Guest", render: (row: any) => row.guest_name },
              { key: "type", header: "Type", render: (row: any) => row.txn_type },
              { key: "category", header: "Category", render: (row: any) => row.category },
              { key: "amount", header: "Amount", render: (row: any) => money(row.amount) },
            ]}
          />
        </div>
      ) : null}

      {activeTab === "ar_city_ledger" ? (
        <div className="card" style={{display:"grid",gap:"18px"}}>
          <h2 style={{ marginTop: 0 }}>A/R City Ledger</h2>
          <div className="muted" style={{ marginBottom: "14px" }}>
            Company, direct bill, group, and event receivable controls
          </div>
          <div className="dashboard-metric-strip">
            <div><span>Company Accounts</span><strong>{arCompanies.length}</strong></div>
            <div><span>Open Invoices</span><strong>{arAging?.open_invoice_count || 0}</strong></div>
            <div><span>Total Receivable</span><strong>{baseCurrency} {money(arAging?.total)}</strong></div>
            <div><span>90+ Days</span><strong>{baseCurrency} {money(arAging?.buckets?.["90_plus"])}</strong></div>
          </div>
          <div>
            <h3>City Ledger Accounts / Create Company Account</h3>
            <div className="toolbar-grid">
              <div className="field"><label>Company Name</label><input value={arCompanyName} onChange={(e)=>setArCompanyName(e.target.value)} /></div>
              <div className="field"><label>Account Code</label><input value={arAccountCode} onChange={(e)=>setArAccountCode(e.target.value)} /></div>
              <div className="field"><label>Credit Limit</label><input type="number" value={arCreditLimit} onChange={(e)=>setArCreditLimit(e.target.value)} /></div>
              <button className="primary-btn" onClick={handleCreateArCompany}>Create Company Account</button>
            </div>
            <DataTable rows={arCompanies} columns={[
              {key:"code",header:"Code",render:(row:any)=>row.account_code},{key:"company",header:"Company",render:(row:any)=>row.company_name},
              {key:"limit",header:"Credit Limit",render:(row:any)=>money(row.credit_limit)},{key:"balance",header:"Current Balance",render:(row:any)=>money(row.current_balance)},
              {key:"terms",header:"Terms",render:(row:any)=>`${row.payment_terms} days`},{key:"status",header:"Status",render:(row:any)=><StatusBadge status={row.status}/>}]} />
          </div>
          <div>
            <h3>Transfer Folio to City Ledger / Receive AR Payment</h3>
            <div className="toolbar-grid">
              <div className="field"><label>Company Account</label><select value={arCompanyId} onChange={(e)=>setArCompanyId(Number(e.target.value))}><option value={0}>Select company</option>{arCompanies.map((item)=><option key={item.id} value={item.id}>{item.account_code} · {item.company_name}</option>)}</select></div>
              <button className="small-btn" onClick={handleArTransfer}>Transfer Selected Folio</button>
              <div className="field"><label>AR Payment Amount</label><input type="number" value={arPaymentAmount} onChange={(e)=>setArPaymentAmount(e.target.value)} /></div>
              <button className="primary-btn" onClick={handleArPayment}>Receive AR Payment</button>
              <button className="small-btn" disabled={!arCompanyId} onClick={()=>window.open(`/api/finance/ar/companies/${arCompanyId}/statement.csv?property_code=${encodeURIComponent(propertyCode)}`,"_blank")}>Company Statement Export</button>
            </div>
          </div>
          <div>
            <h3>AR Invoices</h3>
            <DataTable rows={arInvoices} emptyMessage="No AR invoices for this property." columns={[
              {key:"invoice",header:"Invoice",render:(row:any)=>row.invoice_number},{key:"company",header:"Company",render:(row:any)=>arCompanies.find((item)=>item.id===row.company_account_id)?.account_code||row.company_account_id},
              {key:"guest",header:"Guest / Folio",render:(row:any)=>row.guest_reference||`Folio #${row.folio_id}`},{key:"issue",header:"Issue",render:(row:any)=>row.issue_date},
              {key:"due",header:"Due",render:(row:any)=>row.due_date},{key:"total",header:"Total",render:(row:any)=>money(row.total)},
              {key:"balance",header:"Balance Due",render:(row:any)=>money(row.balance_due)},{key:"status",header:"Status",render:(row:any)=><StatusBadge status={row.status}/>}]} />
          </div>
          <div>
            <h3>Aging Report</h3>
            <div className="dashboard-metric-strip">
              <div><span>Current</span><strong>{money(arAging?.buckets?.current)}</strong></div><div><span>1–30</span><strong>{money(arAging?.buckets?.["1_30"])}</strong></div>
              <div><span>31–60</span><strong>{money(arAging?.buckets?.["31_60"])}</strong></div><div><span>61–90</span><strong>{money(arAging?.buckets?.["61_90"])}</strong></div><div><span>90+</span><strong>{money(arAging?.buckets?.["90_plus"])}</strong></div>
            </div>
          </div>
        </div>
      ) : null}

      {activeTab === "reports_export" ? (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Reports & Export</h2>
          <div className="muted" style={{ marginBottom: "14px" }}>
            Print for operations, CSV for accounting work, PDF for official manager package.
          </div>
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <button className="primary-btn" onClick={handlePrintReport}>Print Current Report</button>
            <button className="small-btn" onClick={handleExportCsv}>Export Current CSV</button>
            <button className="small-btn" onClick={() => setActionMessage("Official PDF export will be generated from the locked Night Audit package.")}>Export PDF</button>
            <button className="small-btn" onClick={() => setActionMessage("Manager report email queued.")}>Email Manager</button>
          </div>
        </div>
      ) : null}

      {activeTab === "night_audit" ? (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Night Audit Finance</h2>
          <div className="muted" style={{ marginBottom: "14px" }}>
            Finance close checklist before the business date can be locked.
          </div>
          <DataTable
            rows={[
              { label: "Guest ledger balanced", status: "review" },
              { label: "Deposit ledger reviewed", status: "review" },
              { label: "Payment ledger / cashier totals reviewed", status: "review" },
              { label: "Tax report reviewed", status: "review" },
              { label: "Trial balance generated", status: "review" },
            ]}
            columns={[
              { key: "label", header: "Check", render: (row) => row.label },
              { key: "status", header: "Status", render: (row) => <span className="pill pill-warning">{row.status}</span> },
            ]}
          />
        </div>
      ) : null}

      <div className="page-grid two-col">
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Post Charge</h2>
          <div className="muted" style={{ marginBottom: "14px" }}>
            Add a charge to the guest folio
          </div>

          <div className="toolbar-grid">
            <div className="field">
              <label>Amount</label>
              <input
                type="number"
                value={chargeAmount}
                onChange={(e) => setChargeAmount(e.target.value)}
              />
            </div>

            <div className="field">
              <label>Description</label>
              <input
                value={chargeDescription}
                onChange={(e) => setChargeDescription(e.target.value)}
              />
            </div>

            <div className="field">
              <label>Category</label>
              <input
                value={chargeCategory}
                onChange={(e) => setChargeCategory(e.target.value)}
              />
            </div>
          </div>

          <div style={{ marginTop: "14px" }}>
            {canPostCharge ? (
              <button className="primary-btn" onClick={handlePostCharge}>
                Submit Charge
              </button>
            ) : (
              <div className="notice-box">{permissionMessage("Charge posting")}</div>
            )}
          </div>
        </div>

        <div className="card">
          <h2 style={{ marginTop: 0 }}>Post Payment</h2>
          <div className="muted" style={{ marginBottom: "14px" }}>
            Record payment against the guest folio
          </div>

          <div className="toolbar-grid">
            <div className="field">
              <label>Amount</label>
              <input
                type="number"
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value)}
              />
            </div>

            <div className="field">
              <label>Payment Method</label>
              <select
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
              >
                <option value="cash">cash</option>
                <option value="card">card</option>
                <option value="bank_transfer">bank_transfer</option>
                <option value="telebirr">telebirr</option>
              </select>
            </div>

            <div className="field">
              <label>Reference</label>
              <input
                value={paymentReference}
                onChange={(e) => setPaymentReference(e.target.value)}
              />
            </div>
            {requiresExchangeRate ? (
              <div className="field">
                <label>{activeCurrency} to {baseCurrency} Rate</label>
                <input
                  type="number"
                  value={paymentExchangeRate}
                  onChange={(e) => setPaymentExchangeRate(e.target.value)}
                  placeholder="Exchange rate"
                />
              </div>
            ) : null}
          </div>
          {requiresExchangeRate ? (
            <div className="muted" style={{ marginTop: "10px" }}>
              ETB equivalent: {baseCurrency} {money(paymentBaseEstimate)}
            </div>
          ) : null}

          <div style={{ marginTop: "14px" }}>
            {canPostPayment ? (
              <button className="primary-btn" onClick={handlePostPayment}>
                Submit Payment
              </button>
            ) : (
              <div className="notice-box">{permissionMessage("Payment posting")}</div>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Transaction History</h2>
        <div className="muted" style={{ marginBottom: "14px" }}>
          Folio transactions for the selected booking
        </div>

        {loading ? (
          <div>Loading finance activity...</div>
        ) : transactions.length === 0 ? (
          <div className="muted">No transactions found.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Type</th>
                  <th>Category</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Method</th>
                  <th>Reference</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((txn: any, index: number) => (
                  <tr key={txn.id ?? index}>
                    <td data-label="ID">{txn.id ?? "-"}</td>
                    <td data-label="Type">{txn.txn_type ?? "-"}</td>
                    <td data-label="Category">{txn.category ?? "-"}</td>
                    <td data-label="Description">{txn.description ?? "-"}</td>
                    <td data-label="Amount">
                      {currencyAmount(txn.currency, txn.amount)}
                      {txn.base_amount != null && txn.original_currency !== txn.base_currency ? (
                        <div className="muted">
                          {currencyAmount(txn.base_currency, txn.base_amount)} @ {txn.exchange_rate_to_base}
                        </div>
                      ) : null}
                    </td>
                    <td data-label="Method">{txn.payment_method ?? "-"}</td>
                    <td data-label="Reference">{txn.reference ?? "-"}</td>
                    <td data-label="Action">
                      {canApproveAccounting && txn.id && ["charge", "payment"].includes(String(txn.txn_type)) ? (
                        <button className="small-btn" onClick={() => handleVoidTransaction(Number(txn.id))}>
                          Void
                        </button>
                      ) : (
                        <span className="muted">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
