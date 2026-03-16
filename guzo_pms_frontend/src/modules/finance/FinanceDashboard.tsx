import { useEffect, useState } from "react";
import PageHeader from "../../components/PageHeader";
import KpiCard from "../../components/KpiCard";
import { usePmsContext } from "../../context/PmsContext";
import { getErrorMessage } from "../../services/http";
import {
  fetchFolioSummary,
  fetchFolioTransactions,
  postCharge,
  postPayment,
  validateCheckout,
  type FolioSummary,
  type FolioTransaction,
} from "../../services/financeService";

function money(v: number | string | null | undefined) {
  const n = Number(v ?? 0);
  return Number.isFinite(n) ? n.toFixed(2) : "0.00";
}

export default function FinanceDashboard() {
  const { propertyCode, businessDate, refreshKey } = usePmsContext();

  const [bookingId, setBookingId] = useState<number>(1);
  const [summary, setSummary] = useState<FolioSummary | null>(null);
  const [transactions, setTransactions] = useState<FolioTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");

  const [chargeAmount, setChargeAmount] = useState("");
  const [chargeDescription, setChargeDescription] = useState("");
  const [chargeCategory, setChargeCategory] = useState("fnb");

  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [paymentReference, setPaymentReference] = useState("");

  async function loadData() {
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
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (bookingId > 0) {
      loadData();
    }
  }, [propertyCode, businessDate, refreshKey]);

  async function handlePostCharge() {
    try {
      setError("");
      setActionMessage("");

      await postCharge({
        property_code: propertyCode,
        booking_id: bookingId,
        amount: Number(chargeAmount),
        description: chargeDescription,
        category: chargeCategory,
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
        amount: Number(paymentAmount),
        payment_method: paymentMethod,
        reference: paymentReference,
      });

      setPaymentAmount("");
      setPaymentReference("");
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

      const result = await validateCheckout(propertyCode, bookingId);
      setActionMessage(
        result.can_checkout
          ? `Checkout allowed. Balance: ${money(result.balance)}`
          : `Checkout blocked. Balance: ${money(result.balance)}. ${result.message || ""}`
      );
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  return (
    <div className="page-grid">
      <PageHeader
        title="Finance"
        subtitle={`Folio and payment control for ${propertyCode} on ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">Booking ID: {bookingId}</div>
            <div className="pill">Property: {propertyCode}</div>
          </>
        }
      />

      {error ? <div className="error-box">{error}</div> : null}
      {actionMessage ? <div className="card">{actionMessage}</div> : null}

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Folio Lookup</h2>
        <div className="muted" style={{ marginBottom: "14px" }}>
          Load folio summary, transactions, and checkout validation
        </div>

        <div className="toolbar-grid">
          <div className="field">
            <label>Booking ID</label>
            <input
              type="number"
              value={bookingId}
              onChange={(e) => setBookingId(Number(e.target.value))}
            />
          </div>

          <div className="field" style={{ alignSelf: "end" }}>
            <button className="primary-btn" onClick={loadData}>
              Load Folio
            </button>
          </div>

          <div className="field" style={{ alignSelf: "end" }}>
            <button className="small-btn" onClick={handleValidateCheckout}>
              Validate Checkout
            </button>
          </div>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard label="Charges Total" value={money(summary?.charges_total)} />
        <KpiCard label="Payments Total" value={money(summary?.payments_total)} />
        <KpiCard label="Balance" value={money(summary?.balance)} />
      </div>

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
            <button className="primary-btn" onClick={handlePostCharge}>
              Submit Charge
            </button>
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
          </div>

          <div style={{ marginTop: "14px" }}>
            <button className="primary-btn" onClick={handlePostPayment}>
              Submit Payment
            </button>
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
                </tr>
              </thead>
              <tbody>
                {transactions.map((txn: any, index: number) => (
                  <tr key={txn.id ?? index}>
                    <td>{txn.id ?? "-"}</td>
                    <td>{txn.transaction_type ?? "-"}</td>
                    <td>{txn.category ?? "-"}</td>
                    <td>{txn.description ?? "-"}</td>
                    <td>{money(txn.amount)}</td>
                    <td>{txn.payment_method ?? "-"}</td>
                    <td>{txn.reference ?? "-"}</td>
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
