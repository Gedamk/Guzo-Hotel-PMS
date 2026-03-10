// src/modules/finance/FinanceFolio.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import {
  apiGetFolioSummary,
  apiPostCharge,
  apiPostPayment,
  type FolioLine,
  type FolioSummary,
} from "../../services/financeFolioService";

type Toast = {
  id: string;
  kind: "success" | "error" | "info";
  message: string;
};

type FolioLineWithRunning = FolioLine & { running_balance: number };

export default function FinanceFolio({
  businessDateIso,
  propertyCode,
}: {
  businessDateIso: string;
  propertyCode: string;
}) {
  const [bookingIdText, setBookingIdText] = useState<string>("");

  const bookingId = useMemo(() => {
    const n = Number(bookingIdText);
    return Number.isFinite(n) && n > 0 ? Math.trunc(n) : null;
  }, [bookingIdText]);

  const [data, setData] = useState<FolioSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState("");

  const [toasts, setToasts] = useState<Toast[]>([]);
  const toastTimerRef = useRef<number | null>(null);

  function pushToast(kind: Toast["kind"], message: string) {
    const id = `${Date.now()}_${Math.random().toString(16).slice(2)}`;
    setToasts((prev) => [...prev, { id, kind, message }]);

    if (toastTimerRef.current) {
      window.clearTimeout(toastTimerRef.current);
    }

    toastTimerRef.current = window.setTimeout(() => {
      setToasts((prev) => prev.slice(1));
    }, 3500);
  }

  const [chargeCategory, setChargeCategory] = useState("room");
  const [chargeDesc, setChargeDesc] = useState("Room Charge");
  const [chargeAmountText, setChargeAmountText] = useState("1500");
  const [chargeCurrency, setChargeCurrency] = useState("ETB");

  const [payMethod, setPayMethod] = useState("cash");
  const [payDesc, setPayDesc] = useState("Cash Payment");
  const [payAmountText, setPayAmountText] = useState("500");
  const [payCurrency, setPayCurrency] = useState("ETB");

  async function load() {
    if (!businessDateIso) {
      setError("Missing business date.");
      return;
    }

    if (!propertyCode || propertyCode === "ALL") {
      setError("Select a single property (not ALL).");
      return;
    }

    if (!bookingId) {
      setError("Enter a valid booking_id.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const res = await apiGetFolioSummary({
        business_date: businessDateIso,
        property_code: propertyCode,
        booking_id: bookingId,
      });

      setData(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setData(null);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function postCharge() {
    if (!businessDateIso) {
      setError("Missing business date.");
      return;
    }

    if (!propertyCode || propertyCode === "ALL") {
      setError("Select a single property (not ALL).");
      return;
    }

    if (!bookingId) {
      setError("Enter a valid booking_id.");
      return;
    }

    const amt = Number(chargeAmountText);
    if (!Number.isFinite(amt) || amt <= 0) {
      setError("Charge amount must be a positive number.");
      return;
    }

    try {
      setPosting(true);
      setError("");

      await apiPostCharge({
        property_code: propertyCode,
        booking_id: bookingId,
        business_date: businessDateIso,
        category: chargeCategory,
        description: chargeDesc.trim() || "Charge",
        amount: amt,
        currency: chargeCurrency.trim().toUpperCase() || "ETB",
      });

      pushToast(
        "success",
        `Charge posted: ${amt} ${chargeCurrency.toUpperCase()} (${chargeCategory})`,
      );

      await load();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      pushToast("error", msg);
    } finally {
      setPosting(false);
    }
  }

  async function postPayment() {
    if (!businessDateIso) {
      setError("Missing business date.");
      return;
    }

    if (!propertyCode || propertyCode === "ALL") {
      setError("Select a single property (not ALL).");
      return;
    }

    if (!bookingId) {
      setError("Enter a valid booking_id.");
      return;
    }

    const amt = Number(payAmountText);
    if (!Number.isFinite(amt) || amt <= 0) {
      setError("Payment amount must be a positive number.");
      return;
    }

    try {
      setPosting(true);
      setError("");

      await apiPostPayment({
        property_code: propertyCode,
        booking_id: bookingId,
        business_date: businessDateIso,
        method: payMethod,
        description: payDesc.trim() || "Payment",
        amount: amt,
        currency: payCurrency.trim().toUpperCase() || "ETB",
      });

      pushToast(
        "success",
        `Payment posted: ${amt} ${payCurrency.toUpperCase()} (${payMethod})`,
      );

      await load();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      pushToast("error", msg);
    } finally {
      setPosting(false);
    }
  }

  useEffect(() => {
    setData(null);
    setError("");
  }, [businessDateIso, propertyCode]);

  const lines: FolioLine[] = useMemo(() => data?.lines ?? [], [data]);

  const linesWithRunning: FolioLineWithRunning[] = useMemo(() => {
    let running = 0;

    return lines.map((l) => {
      const amount = Number(l.amount ?? 0);

      if (l.kind === "charge") {
        running += amount;
      } else {
        running -= amount;
      }

      return {
        ...l,
        running_balance: running,
      };
    });
  }, [lines]);

  return (
    <div className="space-y-4">
      {toasts.length ? (
        <div className="fixed right-4 top-4 z-50 w-[380px] space-y-2">
          {toasts.map((t) => (
            <div
              key={t.id}
              className={[
                "rounded-2xl border p-3 text-sm shadow-lg",
                "bg-[color:var(--surface2)] border-[color:var(--border)] text-[color:var(--text)]",
                t.kind === "success"
                  ? "border-emerald-500/25"
                  : t.kind === "info"
                    ? "border-sky-500/25"
                    : "border-red-500/25",
              ].join(" ")}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="font-semibold">{t.message}</div>
                <span
                  className={[
                    "mt-0.5 inline-block rounded-full px-2 py-0.5 text-[11px] font-extrabold uppercase tracking-wider",
                    t.kind === "success"
                      ? "bg-emerald-500/10 text-emerald-200"
                      : t.kind === "info"
                        ? "bg-sky-500/10 text-sky-200"
                        : "bg-red-500/10 text-red-200",
                  ].join(" ")}
                >
                  {t.kind}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      <div className="rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4">
        <div className="text-[11px] font-extrabold uppercase tracking-wider text-[color:var(--faint)]">
          Finance
        </div>
        <div className="text-xl font-extrabold text-[color:var(--text)]">
          Folio
        </div>
        <div className="text-xs font-semibold text-[color:var(--muted)]">
          {businessDateIso} · {propertyCode}
        </div>

        <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-end">
          <div className="flex-1">
            <label className="block text-xs font-bold text-[color:var(--muted)]">
              Booking ID
            </label>
            <input
              value={bookingIdText}
              onChange={(e) => setBookingIdText(e.target.value)}
              placeholder="e.g. 94"
              className="mt-1 w-full rounded-xl border border-[color:var(--border)] bg-[color:rgba(15,23,42,0.35)] px-3 py-2 text-sm text-[color:var(--text)] placeholder:text-[color:var(--faint)]"
            />
            <div className="mt-1 text-[11px] text-[color:var(--faint)]">
              Required by backend:{" "}
              <span className="font-bold">business_date</span>, property_code,
              booking_id
            </div>
          </div>

          <button
            onClick={() => void load()}
            disabled={loading}
            className="rounded-xl border border-sky-500/25 bg-sky-500/10 px-4 py-2 text-sm font-extrabold text-sky-100 hover:bg-sky-500/15 disabled:opacity-50"
          >
            {loading ? "Loading..." : "Load folio"}
          </button>
        </div>

        {error ? (
          <div className="mt-3 rounded-xl border border-red-500/25 bg-red-500/10 p-3 text-sm text-red-100">
            {error}
          </div>
        ) : null}
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4">
          <div className="text-sm font-extrabold text-[color:var(--text)]">
            Post Charge
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className="block text-xs font-bold text-[color:var(--muted)]">
                Category
              </label>
              <select
                value={chargeCategory}
                onChange={(e) => setChargeCategory(e.target.value)}
                className="mt-1 w-full rounded-xl border border-[color:var(--border)] bg-[color:rgba(15,23,42,0.35)] px-3 py-2 text-sm text-[color:var(--text)]"
              >
                <option value="room">room</option>
                <option value="minibar">minibar</option>
                <option value="laundry">laundry</option>
                <option value="misc">misc</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-[color:var(--muted)]">
                Amount
              </label>
              <input
                value={chargeAmountText}
                onChange={(e) => setChargeAmountText(e.target.value)}
                className="mt-1 w-full rounded-xl border border-[color:var(--border)] bg-[color:rgba(15,23,42,0.35)] px-3 py-2 text-sm text-[color:var(--text)]"
                placeholder="1500"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-xs font-bold text-[color:var(--muted)]">
                Description
              </label>
              <input
                value={chargeDesc}
                onChange={(e) => setChargeDesc(e.target.value)}
                className="mt-1 w-full rounded-xl border border-[color:var(--border)] bg-[color:rgba(15,23,42,0.35)] px-3 py-2 text-sm text-[color:var(--text)]"
                placeholder="Room Charge"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[color:var(--muted)]">
                Currency
              </label>
              <input
                value={chargeCurrency}
                onChange={(e) => setChargeCurrency(e.target.value)}
                className="mt-1 w-full rounded-xl border border-[color:var(--border)] bg-[color:rgba(15,23,42,0.35)] px-3 py-2 text-sm text-[color:var(--text)]"
                placeholder="ETB"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={() => void postCharge()}
                disabled={posting}
                className="w-full rounded-xl border border-amber-500/25 bg-amber-500/10 px-4 py-2 text-sm font-extrabold text-amber-100 hover:bg-amber-500/15 disabled:opacity-50"
              >
                {posting ? "Working..." : "Post charge"}
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4">
          <div className="text-sm font-extrabold text-[color:var(--text)]">
            Post Payment
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className="block text-xs font-bold text-[color:var(--muted)]">
                Method
              </label>
              <select
                value={payMethod}
                onChange={(e) => setPayMethod(e.target.value)}
                className="mt-1 w-full rounded-xl border border-[color:var(--border)] bg-[color:rgba(15,23,42,0.35)] px-3 py-2 text-sm text-[color:var(--text)]"
              >
                <option value="cash">cash</option>
                <option value="telebirr">telebirr</option>
                <option value="cbebirr">cbebirr</option>
                <option value="pos">pos</option>
                <option value="bank_transfer">bank_transfer</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-[color:var(--muted)]">
                Amount
              </label>
              <input
                value={payAmountText}
                onChange={(e) => setPayAmountText(e.target.value)}
                className="mt-1 w-full rounded-xl border border-[color:var(--border)] bg-[color:rgba(15,23,42,0.35)] px-3 py-2 text-sm text-[color:var(--text)]"
                placeholder="500"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-xs font-bold text-[color:var(--muted)]">
                Description
              </label>
              <input
                value={payDesc}
                onChange={(e) => setPayDesc(e.target.value)}
                className="mt-1 w-full rounded-xl border border-[color:var(--border)] bg-[color:rgba(15,23,42,0.35)] px-3 py-2 text-sm text-[color:var(--text)]"
                placeholder="Cash Payment"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[color:var(--muted)]">
                Currency
              </label>
              <input
                value={payCurrency}
                onChange={(e) => setPayCurrency(e.target.value)}
                className="mt-1 w-full rounded-xl border border-[color:var(--border)] bg-[color:rgba(15,23,42,0.35)] px-3 py-2 text-sm text-[color:var(--text)]"
                placeholder="ETB"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={() => void postPayment()}
                disabled={posting}
                className="w-full rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2 text-sm font-extrabold text-emerald-100 hover:bg-emerald-500/15 disabled:opacity-50"
              >
                {posting ? "Working..." : "Post payment"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {data ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Kpi
            label="Balance"
            value={`${data.balance.toFixed(2)} ${data.currency}`}
          />
          <Kpi label="Lines" value={String(lines.length)} />
          <Kpi
            label="Status"
            value={
              data.balance > 0
                ? "Outstanding"
                : data.balance < 0
                  ? "Credit"
                  : "Settled"
            }
          />
        </div>
      ) : null}

      <div className="rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-extrabold text-[color:var(--text)]">
            Folio Lines
          </div>
          <button
            onClick={() => void load()}
            disabled={loading || posting}
            className="rounded-xl border border-[color:var(--border)] bg-[color:rgba(148,163,184,0.06)] px-3 py-1.5 text-sm font-semibold text-[color:var(--text)] hover:bg-[color:rgba(148,163,184,0.10)] disabled:opacity-50"
          >
            Refresh
          </button>
        </div>

        {!data && !loading ? (
          <div className="text-sm text-[color:var(--muted)]">
            Enter a booking id and click “Load folio”.
          </div>
        ) : null}

        {loading ? (
          <div className="text-sm text-[color:var(--muted)]">Loading…</div>
        ) : null}

        {data ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-[color:var(--muted)]">
                <tr className="border-b border-[color:var(--border)]">
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-left">Kind</th>
                  <th className="px-3 py-2 text-left">Category/Method</th>
                  <th className="px-3 py-2 text-left">Description</th>
                  <th className="px-3 py-2 text-right">Amount</th>
                  <th className="px-3 py-2 text-right">Running</th>
                </tr>
              </thead>
              <tbody className="text-[color:var(--text)]">
                {linesWithRunning.map((l) => (
                  <tr
                    key={`${l.kind}-${l.id}-${l.date}`}
                    className="border-b border-[color:rgba(148,163,184,0.08)]"
                  >
                    <td className="px-3 py-2 whitespace-nowrap">{l.date}</td>
                    <td className="px-3 py-2">
                      <span
                        className={[
                          "rounded-full border px-2 py-0.5 text-xs font-extrabold",
                          l.kind === "charge"
                            ? "border-amber-500/25 bg-amber-500/10 text-amber-100"
                            : "border-emerald-500/25 bg-emerald-500/10 text-emerald-100",
                        ].join(" ")}
                      >
                        {l.kind}
                      </span>
                    </td>
                    <td className="px-3 py-2">{l.category_or_method}</td>
                    <td className="px-3 py-2">{l.description}</td>
                    <td className="px-3 py-2 text-right">
                      {Number(l.amount ?? 0).toFixed(2)} {l.currency}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {Number(l.running_balance ?? 0).toFixed(2)} {l.currency}
                    </td>
                  </tr>
                ))}

                {linesWithRunning.length === 0 ? (
                  <tr>
                    <td
                      className="px-3 py-4 text-[color:var(--muted)]"
                      colSpan={6}
                    >
                      No folio lines returned.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4">
      <div className="text-[11px] font-extrabold uppercase tracking-wider text-[color:var(--faint)]">
        {label}
      </div>
      <div className="text-xl font-extrabold text-[color:var(--text)]">
        {value}
      </div>
    </div>
  );
}