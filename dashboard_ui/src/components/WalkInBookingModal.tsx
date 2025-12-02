// dashboard_ui/src/components/WalkInBookingModal.tsx

import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "<REDACTED_DEMO_BEARER_TOKEN>";

interface WalkInBookingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void; // callback to refresh bookings
  defaultPropertyCode?: string;
  businessDate: string; // "YYYY-MM-DD"
}

type PaymentMethod =
  | "cash"
  | "card"
  | "mobile_money"
  | "bank_transfer"
  | "ota_collect"
  | "other";

interface WalkInFormState {
  property_code: string;
  room_type: string;
  check_in: string; // ISO date
  check_out: string; // ISO date
  guest_name: string;
  rate_per_night_etb: string;
  nights: string;
  total_amount_etb: string;
  payment_method: PaymentMethod;
  amount_paid_now_etb: string;
  notes: string;
}

const DEFAULT_FORM: WalkInFormState = {
  property_code: "",
  room_type: "Single",
  check_in: "",
  check_out: "",
  guest_name: "",
  rate_per_night_etb: "",
  nights: "1",
  total_amount_etb: "",
  payment_method: "mobile_money",
  amount_paid_now_etb: "",
  notes: "",
};

const HOTEL_NAME_BY_PROPERTY: Record<string, string> = {
  DRE001: "Dream Big Hotel",
  "N&N002": "N&N Luxury Hotel",
};

function formatDateForInput(iso: string): string {
  // assume iso YYYY-MM-DD
  return iso;
}

export const WalkInBookingModal: React.FC<WalkInBookingModalProps> = ({
  isOpen,
  onClose,
  onCreated,
  defaultPropertyCode = "DRE001",
  businessDate,
}) => {
  const [form, setForm] = useState<WalkInFormState>({
    ...DEFAULT_FORM,
    property_code: defaultPropertyCode,
    check_in: formatDateForInput(businessDate),
    check_out: formatDateForInput(businessDate),
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Reset form when opening
  useEffect(() => {
    if (isOpen) {
      setError(null);
      setSuccessMessage(null);
      setForm({
        ...DEFAULT_FORM,
        property_code: defaultPropertyCode,
        check_in: formatDateForInput(businessDate),
        check_out: formatDateForInput(businessDate),
        nights: "1",
      });
    }
  }, [isOpen, defaultPropertyCode, businessDate]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setForm((prev) => {
      const updated = { ...prev, [name]: value };

      // Auto-calc total if rate or nights changes
      if (name === "rate_per_night_etb" || name === "nights") {
        const rate = parseFloat(updated.rate_per_night_etb || "0");
        const nights = parseInt(updated.nights || "0", 10);
        if (!isNaN(rate) && !isNaN(nights) && nights > 0) {
          updated.total_amount_etb = String(Math.round(rate * nights));
        }
      }

      return updated;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (!form.guest_name.trim()) {
      setError("Guest name is required.");
      return;
    }

    if (!form.property_code) {
      setError("Property is required.");
      return;
    }

    const rate = parseFloat(form.rate_per_night_etb || "0");
    const nightsNum = parseInt(form.nights || "0", 10);
    const total = parseFloat(form.total_amount_etb || "0");
    const paidNow = parseFloat(form.amount_paid_now_etb || "0");

    if (isNaN(rate) || rate <= 0) {
      setError("Please enter a valid rate per night.");
      return;
    }
    if (isNaN(nightsNum) || nightsNum <= 0) {
      setError("Nights must be at least 1.");
      return;
    }
    if (isNaN(total) || total <= 0) {
      setError("Total amount must be a positive number.");
      return;
    }
    if (paidNow < 0 || paidNow > total) {
      setError("Paid amount must be between 0 and total.");
      return;
    }

    const payload = {
      property_code: form.property_code,
      room_type: form.room_type,
      check_in: form.check_in,
      check_out: form.check_out,
      guest_name: form.guest_name.trim(),
      rate_per_night_etb: rate,
      nights: nightsNum,
      total_amount_etb: total,
      payment_method: form.payment_method,
      amount_paid_now_etb: paidNow,
      notes: form.notes.trim() || null,
    };

    try {
      setSubmitting(true);
      await axios.post(`${API_BASE}/frontdesk/walkin`, payload, {
        headers: {
          Authorization: `Bearer ${AUTH_TOKEN}`,
        },
      });

      setSuccessMessage("Walk-in booking created and checked-in successfully.");
      onCreated();
      // You can auto-close after a short delay if you prefer
      // setTimeout(onClose, 800);
    } catch (err: any) {
      console.error("Error creating walk-in booking", err);
      const detail =
        err?.response?.data?.detail ||
        "Failed to create walk-in booking. Please verify details or try again.";
      setError(String(detail));
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const propertyLabel =
    HOTEL_NAME_BY_PROPERTY[form.property_code] || form.property_code || "Unknown";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-xl font-semibold">
              New Walk-In Booking (Front Desk)
            </h2>
            <p className="text-sm text-gray-600">
              Use this when a guest arrives without a reservation and books at the desk.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-800 text-lg"
            type="button"
          >
            ✕
          </button>
        </div>

        <div className="text-sm mb-3">
          <span className="font-medium">Business Date: </span>
          {businessDate} •{" "}
          <span className="font-medium">Property: </span>
          {propertyLabel}
        </div>

        {error && (
          <div className="mb-3 rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            ⚠ {error}
          </div>
        )}

        {successMessage && (
          <div className="mb-3 rounded-md bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-700">
            ✅ {successMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-sm">
          {/* Row 1: Property & Room Type */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block font-medium mb-1">Property</label>
              <select
                name="property_code"
                value={form.property_code}
                onChange={handleChange}
                className="w-full border rounded px-2 py-1"
              >
                <option value="DRE001">Dream Big Hotel (DRE001)</option>
                <option value="N&N002">N&N Luxury Hotel (N&N002)</option>
              </select>
            </div>
            <div>
              <label className="block font-medium mb-1">Room Type</label>
              <select
                name="room_type"
                value={form.room_type}
                onChange={handleChange}
                className="w-full border rounded px-2 py-1"
              >
                <option value="Single">Single</option>
                <option value="Double">Double</option>
                <option value="Twin">Twin</option>
                <option value="Suite">Suite</option>
                <option value="Family">Family</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          {/* Row 2: Dates & Guest */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block font-medium mb-1">Check-In</label>
              <input
                type="date"
                name="check_in"
                value={form.check_in}
                onChange={handleChange}
                className="w-full border rounded px-2 py-1"
              />
            </div>
            <div>
              <label className="block font-medium mb-1">Check-Out</label>
              <input
                type="date"
                name="check_out"
                value={form.check_out}
                onChange={handleChange}
                className="w-full border rounded px-2 py-1"
              />
            </div>
            <div>
              <label className="block font-medium mb-1">Guest Name</label>
              <input
                type="text"
                name="guest_name"
                value={form.guest_name}
                onChange={handleChange}
                placeholder="e.g. Bekele"
                className="w-full border rounded px-2 py-1"
              />
            </div>
          </div>

          {/* Row 3: Rate / Nights / Total */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block font-medium mb-1">Rate / Night (ETB)</label>
              <input
                type="number"
                name="rate_per_night_etb"
                value={form.rate_per_night_etb}
                onChange={handleChange}
                className="w-full border rounded px-2 py-1"
                min={0}
              />
            </div>
            <div>
              <label className="block font-medium mb-1">Nights</label>
              <input
                type="number"
                name="nights"
                value={form.nights}
                onChange={handleChange}
                className="w-full border rounded px-2 py-1"
                min={1}
              />
            </div>
            <div>
              <label className="block font-medium mb-1">Total (ETB)</label>
              <input
                type="number"
                name="total_amount_etb"
                value={form.total_amount_etb}
                onChange={handleChange}
                className="w-full border rounded px-2 py-1"
                min={0}
              />
            </div>
          </div>

          {/* Row 4: Payment */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block font-medium mb-1">Payment Method</label>
              <select
                name="payment_method"
                value={form.payment_method}
                onChange={handleChange}
                className="w-full border rounded px-2 py-1"
              >
                <option value="cash">Cash</option>
                <option value="card">Credit / Debit Card</option>
                <option value="mobile_money">Mobile Money / Transfer</option>
                <option value="bank_transfer">Bank Transfer</option>
                <option value="ota_collect">OTA Collect (Booking.com, etc.)</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="block font-medium mb-1">Amount Paid Now (ETB)</label>
              <input
                type="number"
                name="amount_paid_now_etb"
                value={form.amount_paid_now_etb}
                onChange={handleChange}
                className="w-full border rounded px-2 py-1"
                min={0}
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block font-medium mb-1">
              Notes / Special Requests
            </label>
            <textarea
              name="notes"
              value={form.notes}
              onChange={handleChange}
              placeholder="E.g. high floor, late check-out, quiet room..."
              className="w-full border rounded px-2 py-1 min-h-[70px]"
            />
          </div>

          {/* Actions */}
          <div className="flex justify-between items-center pt-4 border-t mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded border border-gray-300 text-gray-700 hover:bg-gray-100"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-60"
              disabled={submitting}
            >
              {submitting ? "Saving..." : "Save & Check-In"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
