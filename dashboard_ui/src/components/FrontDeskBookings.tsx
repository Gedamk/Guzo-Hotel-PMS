// src/components/FrontDeskBookings.tsx

import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import type { RawBooking } from "../types/bookings";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "admin-secret-123";

const HOTEL_NAME_BY_PROPERTY: Record<string, string> = {
  DRE001: "Dream Big Hotel",
  "N&N002": "N&N Luxury Hotel",
};

type UiBucket = "arrivals" | "in_house" | "departures" | "future";

/**
 * Extend RawBooking with the fields we know the backend returns.
 * This avoids TypeScript errors when we access these properties.
 */
type GuzoBooking = RawBooking & {
  id: number | string;
  guest_name: string;
  property_code: string;
  check_in_date: string;
  check_out_date: string;
  booking_status: string;
  room_number?: string | null;
  channel?: string | null;
  total_amount?: string | number | null;
  nights?: number;
};

type UiBooking = GuzoBooking & {
  hotel_name: string;
  bucket: UiBucket;
};

interface FrontDeskBookingsProps {
  /**
   * Business date in YYYY-MM-DD.
   * If not provided, defaults to today's date.
   */
  businessDate?: string;
}

// --- date helpers ----------------------------------------------------------

const toDate = (s: string): Date => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
};

const isSameDay = (a: Date, b: Date): boolean =>
  a.getFullYear() === b.getFullYear() &&
  a.getMonth() === b.getMonth() &&
  a.getDate() === b.getDate();

// --- helper: bucket bookings -----------------------------------------------

const bucketBooking = (b: GuzoBooking, businessDate: Date): UiBucket => {
  const ci = toDate(b.check_in_date);
  const co = toDate(b.check_out_date);

  if (isSameDay(ci, businessDate)) {
    return "arrivals";
  }

  // in-house if businessDate is within stay (ci <= date < co)
  if (ci <= businessDate && businessDate < co) {
    return "in_house";
  }

  if (isSameDay(co, businessDate)) {
    return "departures";
  }

  // otherwise it's a future booking (beyond businessDate)
  if (businessDate < ci) {
    return "future";
  }

  // Fallback
  return "future";
};

// --- component -------------------------------------------------------------

const FrontDeskBookings: React.FC<FrontDeskBookingsProps> = ({
  businessDate,
}) => {
  const [bookings, setBookings] = useState<UiBooking[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Default business date = today if not passed by parent
  const todayIso = new Date().toISOString().slice(0, 10);
  const effectiveBusinessDate = businessDate || todayIso;

  // For portfolio summary (house count & occupancy)
  const TOTAL_ROOMS_PORTFOLIO = 60; // adjust if you include more properties

  useEffect(() => {
    const loadBookings = async () => {
      setLoading(true);
      setError(null);
      try {
        const resp = await axios.get<GuzoBooking[]>(
          `${API_BASE}/frontdesk/bookings`,
          {
            params: {
              scope: "touches",
              date: effectiveBusinessDate,
            },
            headers: {
              Authorization: `Bearer ${AUTH_TOKEN}`,
            },
          }
        );

        const bizDateObj = toDate(effectiveBusinessDate);

        const uiBookings: UiBooking[] = resp.data.map((b) => {
          const hotel_name =
            HOTEL_NAME_BY_PROPERTY[b.property_code] || b.property_code;
          const bucket = bucketBooking(b, bizDateObj);
          return { ...b, hotel_name, bucket };
        });

        setBookings(uiBookings);
      } catch (e: any) {
        console.error("Error loading bookings:", e);
        setError("Error loading bookings");
      } finally {
        setLoading(false);
      }
    };

    if (effectiveBusinessDate) {
      loadBookings();
    }
  }, [effectiveBusinessDate]);

  // Buckets
  const arrivals = useMemo(
    () => bookings.filter((b) => b.bucket === "arrivals"),
    [bookings]
  );
  const inHouse = useMemo(
    () => bookings.filter((b) => b.bucket === "in_house"),
    [bookings]
  );
  const departures = useMemo(
    () => bookings.filter((b) => b.bucket === "departures"),
    [bookings]
  );
  const future = useMemo(
    () => bookings.filter((b) => b.bucket === "future"),
    [bookings]
  );

  const inHouseRoomsCount = inHouse.length; // assuming 1 room per booking in demo
  const occupancyPct =
    TOTAL_ROOMS_PORTFOLIO > 0
      ? (inHouseRoomsCount / TOTAL_ROOMS_PORTFOLIO) * 100
      : 0;

  return (
    <div className="frontdesk-console">
      <div style={{ marginBottom: "0.75rem" }}>
        <strong>Today:</strong> {effectiveBusinessDate} · Portfolio view of
        arrivals, in-house, and departures.
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <div>
          <strong>House Count &amp; Occupancy – Portfolio</strong>
        </div>
        <div>
          In-House / Total Rooms: {inHouseRoomsCount} / {TOTAL_ROOMS_PORTFOLIO}{" "}
          · Occupancy: {occupancyPct.toFixed(1)}%
        </div>
      </div>

      {loading && <p>Loading bookings...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {!loading && !error && (
        <>
          {/* Summary cards */}
          <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
            <div>
              <strong>Arrivals Today</strong>
              <div>{arrivals.length}</div>
            </div>
            <div>
              <strong>In-House Rooms</strong>
              <div>{inHouse.length}</div>
            </div>
            <div>
              <strong>Departures Today</strong>
              <div>{departures.length}</div>
            </div>
            <div>
              <strong>Cancelled / No-Show</strong>
              <div>0</div>
            </div>
          </div>

          {/* Departures Today table */}
          <div style={{ marginBottom: "1rem" }}>
            <h3>Departures Today ({departures.length})</h3>
            {departures.length === 0 ? (
              <p>No bookings in this category.</p>
            ) : (
              <table
                style={{ width: "100%", borderCollapse: "collapse" }}
                cellPadding={4}
              >
                <thead>
                  <tr>
                    <th>Guest</th>
                    <th>Hotel</th>
                    <th>Property</th>
                    <th>Room</th>
                    <th>Check-In</th>
                    <th>Check-Out</th>
                    <th>Nights</th>
                    <th>Status</th>
                    <th>Channel</th>
                    <th>Total</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {departures.map((b) => (
                    <tr key={b.id}>
                      <td>{b.guest_name}</td>
                      <td>{b.hotel_name}</td>
                      <td>{b.property_code}</td>
                      <td>{b.room_number || "TBD"}</td>
                      <td>{b.check_in_date}</td>
                      <td>{b.check_out_date}</td>
                      <td>{b.nights ?? ""}</td>
                      <td>{b.booking_status}</td>
                      <td>{b.channel || "—"}</td>
                      <td>{b.total_amount ?? "ETB 0"}</td>
                      <td>No action</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* You can later render arrivals, inHouse, upcoming similar to above */}
        </>
      )}
    </div>
  );
};

export default FrontDeskBookings;
