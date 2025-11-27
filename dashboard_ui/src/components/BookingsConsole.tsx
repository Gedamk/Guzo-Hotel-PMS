// src/components/BookingsConsole.tsx
//
// Text-based console view for daily bookings,
// aligned with current RawBooking shape and /frontdesk/bookings API.

import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import type { RawBooking } from "../types/bookings";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "admin-secret-123";

// ---- date helpers ---------------------------------------------------------

const toLocalDate = (isoDate: string): Date => {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day);
};

const todayIsoLocal = (): string => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const isSameDayStr = (a: string, b: string): boolean => {
  if (!a || !b) return false;
  return a === b; // both "YYYY-MM-DD"
};

const isAfterStr = (a: string, b: string): boolean => {
  if (!a || !b) return false;
  const da = toLocalDate(a);
  const db = toLocalDate(b);
  return da.getTime() > db.getTime();
};

const isBeforeStr = (a: string, b: string): boolean => {
  if (!a || !b) return false;
  const da = toLocalDate(a);
  const db = toLocalDate(b);
  return da.getTime() < db.getTime();
};

const formatDate = (isoDate: string): string => {
  if (!isoDate) return "";
  return toLocalDate(isoDate).toLocaleDateString();
};

// ---- status + buckets -----------------------------------------------------

type NormalizedStatus =
  | "confirmed"
  | "in_house"
  | "checked_out"
  | "cancelled"
  | "no_show"
  | "other";

const normalizeStatus = (status: string | null): NormalizedStatus => {
  if (!status) return "other";
  const s = status.trim().toLowerCase();

  if (s === "confirmed") return "confirmed";
  if (s === "in_house" || s === "in-house") return "in_house";
  if (s === "checked_out" || s === "checked-out") return "checked_out";
  if (s === "cancelled" || s === "canceled") return "cancelled";
  if (s === "no_show" || s === "no-show") return "no_show";

  return "other";
};

type UiBucket = "arrivals" | "in_house" | "departures" | "upcoming" | "cancelled";

type UiBooking = RawBooking & {
  bucket: UiBucket;
  normalized_status: NormalizedStatus;
  hotel_name: string;
};

// Map property_code -> hotel name
const HOTEL_NAME_BY_PROPERTY: Record<string, string> = {
  DRE001: "Dream Big Hotel",
  "N&N002": "N&N Luxury Hotel",
};

const assignBucket = (b: RawBooking, businessDate: string): UiBucket => {
  const status = normalizeStatus(b.status ?? "");
  const ci = b.check_in;
  const co = b.check_out;

  if (!ci || !co) {
    return "upcoming";
  }

  if (status === "cancelled" || status === "no_show") {
    return "cancelled";
  }

  if (isSameDayStr(ci, businessDate)) {
    // Arrivals for the business date
    return "arrivals";
  }

  if (
    !isAfterStr(ci, businessDate) && // ci <= businessDate
    !isBeforeStr(co, businessDate) // co >= businessDate
  ) {
    // stay covers the business date
    return "in_house";
  }

  if (isSameDayStr(co, businessDate)) {
    return "departures";
  }

  if (isAfterStr(ci, businessDate)) {
    return "upcoming";
  }

  return "upcoming";
};

// ---- main component -------------------------------------------------------

const BookingsConsole: React.FC = () => {
  const [businessDate, setBusinessDate] = useState<string>(todayIsoLocal());
  const [bookings, setBookings] = useState<UiBooking[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState<string>("");

  useEffect(() => {
    const fetchBookings = async () => {
      try {
        setLoading(true);
        setError(null);

        const resp = await axios.get<RawBooking[]>(
          `${API_BASE}/frontdesk/bookings`,
          {
            params: {
              scope: "today",
              date: businessDate,
            },
            headers: {
              Authorization: `Bearer ${AUTH_TOKEN}`,
            },
          }
        );

        const ui = resp.data.map<UiBooking>((b) => {
          const propertyCode = b.property_code ?? "DRE001";
          const normalized_status = normalizeStatus(b.status ?? "");
          const bucket = assignBucket(b, businessDate);
          return {
            ...b,
            hotel_name:
              HOTEL_NAME_BY_PROPERTY[propertyCode] ?? propertyCode ?? "",
            normalized_status,
            bucket,
          };
        });

        setBookings(ui);
      } catch (err: any) {
        console.error("Error loading bookings for console", err);
        setError("Failed to load bookings for console.");
      } finally {
        setLoading(false);
      }
    };

    fetchBookings();
  }, [businessDate]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return bookings;

    return bookings.filter((b) => {
      return (
        (b.guest_name && b.guest_name.toLowerCase().includes(q)) ||
        (b.booking_code && b.booking_code.toLowerCase().includes(q)) ||
        (b.hotel_name && b.hotel_name.toLowerCase().includes(q)) ||
        (b.channel && b.channel.toLowerCase().includes(q))
      );
    });
  }, [bookings, search]);

  const arrivals = useMemo(
    () => filtered.filter((b) => b.bucket === "arrivals"),
    [filtered]
  );
  const inHouse = useMemo(
    () => filtered.filter((b) => b.bucket === "in_house"),
    [filtered]
  );
  const departures = useMemo(
    () => filtered.filter((b) => b.bucket === "departures"),
    [filtered]
  );
  const upcoming = useMemo(
    () => filtered.filter((b) => b.bucket === "upcoming"),
    [filtered]
  );
  const cancelled = useMemo(
    () => filtered.filter((b) => b.bucket === "cancelled"),
    [filtered]
  );

  return (
    <div className="fd-console">
      <div className="fd-console-header">
        <h2>Bookings Console</h2>
        <div className="fd-console-controls">
          <label style={{ marginRight: "0.75rem" }}>
            Business date:&nbsp;
            <input
              type="date"
              value={businessDate}
              onChange={(e) => setBusinessDate(e.target.value)}
            />
          </label>
          <input
            type="text"
            placeholder="Search guest / booking / hotel / channel"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ minWidth: "260px" }}
          />
        </div>
      </div>

      {loading && <div>Loading bookings…</div>}
      {error && <div style={{ color: "red" }}>{error}</div>}

      {!loading && !error && (
        <>
          <div className="fd-console-summary">
            <SummaryPill label="Arrivals" value={arrivals.length} />
            <SummaryPill label="In-House" value={inHouse.length} />
            <SummaryPill label="Departures" value={departures.length} />
            <SummaryPill label="Upcoming" value={upcoming.length} />
            <SummaryPill label="Cancelled / No-show" value={cancelled.length} />
          </div>

          <ConsoleSection title="Arrivals" items={arrivals} />
          <ConsoleSection title="In-House" items={inHouse} />
          <ConsoleSection title="Departures" items={departures} />
          <ConsoleSection title="Upcoming" items={upcoming} />
          <ConsoleSection title="Cancelled / No-show" items={cancelled} />
        </>
      )}
    </div>
  );
};

// ---- small presentational components --------------------------------------

type SummaryPillProps = {
  label: string;
  value: number;
};

const SummaryPill: React.FC<SummaryPillProps> = ({ label, value }) => (
  <div className="fd-console-pill">
    <span className="fd-console-pill-label">{label}</span>
    <span className="fd-console-pill-value">{value}</span>
  </div>
);

type ConsoleSectionProps = {
  title: string;
  items: UiBooking[];
};

const ConsoleSection: React.FC<ConsoleSectionProps> = ({ title, items }) => {
  return (
    <div className="fd-console-section">
      <h3 className="fd-console-section-title">
        {title} ({items.length})
      </h3>
      {items.length === 0 ? (
        <div className="fd-console-empty">No bookings.</div>
      ) : (
        <ul className="fd-console-list">
          {items.map((b) => (
            <li key={b.id} className="fd-console-li">
              <span className="fd-console-li-main">
                {b.guest_name} • {b.hotel_name} •{" "}
                {b.room_type ? b.room_type : "Room type?"} •{" "}
                {b.booking_code ? `Code: ${b.booking_code}` : `ID: ${b.id}`}
              </span>
              <span className="fd-console-li-sub">
                {b.property_code} • {formatDate(b.check_in)} →{" "}
                {formatDate(b.check_out)} • Status: {b.status || "—"} • Channel:{" "}
                {b.channel || "—"} • Total:{" "}
                {b.total_amount_etb != null ? `${b.total_amount_etb} ETB` : "—"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default BookingsConsole;
