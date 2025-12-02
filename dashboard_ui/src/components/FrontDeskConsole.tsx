// src/components/FrontDeskConsole.tsx
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "<REDACTED_DEMO_BEARER_TOKEN>";

// Map property_code -> hotel name (for display)
const HOTEL_NAME_BY_PROPERTY: Record<string, string> = {
  DRE001: "Dream Big Hotel",
  "N&N002": "N&N Luxury Hotel",
};

// Approximate number of rooms per property
const ROOMS_TOTAL_BY_PROPERTY: Record<string, number> = {
  DRE001: 60, // Dream Big Hotel
  "N&N002": 45, // N&N Luxury Hotel
};

// Keep types flexible to avoid TS errors if backend sends "Confirmed"/"confirmed"
type BookingStatus = string;
type Channel = string;
type Bucket =
  | "arrivals"
  | "in_house"
  | "departures"
  | "upcoming"
  | "cancelled"
  | string;

interface FrontDeskBooking {
  id: number;
  guest_name: string;
  hotel_name: string;
  property_code: string;
  room_number: string | null;
  room_type?: string | null;
  check_in_date: string; // "2025-12-01"
  check_out_date: string; // "2025-12-06"
  nights?: number | null;
  status: BookingStatus; // booking_status from backend
  channel: Channel;
  total_amount?: number | null;
  currency?: string | null;
  note?: string | null;
  bucket: Bucket; // computed on frontend
}

interface HouseCount {
  property_code: string;
  date: string;
  total_rooms: number;
  occupied_rooms: number;
  out_of_order_rooms: number;
  available_rooms: number;
  occupancy_pct: number;
  arrivals_today: number;
  departures_today: number;
  cancelled_today: number;
}

// We allow two shapes:
// 1) { bookings: [...], house_count?: {...} }
// 2) plain array: [...]
type FrontDeskApiData = ApiFrontDeskResponse | FrontDeskBooking[];

interface ApiFrontDeskResponse {
  house_count?: HouseCount;
  bookings: FrontDeskBooking[];
}

const formatMoney = (amount?: number | null, currency?: string | null) => {
  const safeAmount =
    typeof amount === "number" && !Number.isNaN(amount) ? amount : 0;
  const safeCurrency = currency && currency.trim() ? currency : "ETB"; // default to ETB
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: safeCurrency,
      maximumFractionDigits: 0,
    }).format(safeAmount);
  } catch {
    // Fallback if currency code is invalid
    return `${safeAmount.toLocaleString("en-US")} ${safeCurrency}`;
  }
};

// --- helpers -----------------------------------------------------------

// Robust nights calculator (handles "YYYY-MM-DD" or generic date strings)
const calculateNights = (checkIn: string, checkOut: string): number | null => {
  if (!checkIn || !checkOut) return null;

  const isoRegex = /^\d{4}-\d{2}-\d{2}$/;

  let ci: Date;
  let co: Date;

  if (isoRegex.test(checkIn) && isoRegex.test(checkOut)) {
    const [ciY, ciM, ciD] = checkIn.split("-").map(Number);
    const [coY, coM, coD] = checkOut.split("-").map(Number);
    ci = new Date(ciY, ciM - 1, ciD);
    co = new Date(coY, coM - 1, coD);
  } else {
    ci = new Date(checkIn);
    co = new Date(checkOut);
  }

  if (isNaN(ci.getTime()) || isNaN(co.getTime())) return null;

  const msPerDay = 1000 * 60 * 60 * 24;
  const diff = co.getTime() - ci.getTime();
  const nights = diff / msPerDay;

  if (nights <= 0) return 1; // minimum 1 night if dates are weird
  return Math.round(nights);
};

const parseYmd = (s: string): Date | null => {
  const isoRegex = /^\d{4}-\d{2}-\d{2}$/;
  if (!isoRegex.test(s)) return null;
  const [y, m, d] = s.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  return isNaN(dt.getTime()) ? null : dt;
};

const isSameDay = (a: Date, b: Date): boolean => {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
};

// Classify bucket based on status first, then dates + businessDate
const classifyBucket = (
  rawStatus: string | null | undefined,
  checkIn: string,
  checkOut: string,
  businessDate: string
): Bucket => {
  const status = (rawStatus || "").toLowerCase();

  // 1) Hard overrides based on status
  if (
    status === "cancelled" ||
    status === "canceled" ||
    status === "no_show" ||
    status === "no-show"
  ) {
    return "cancelled";
  }

  if (status === "in_house" || status === "in house") {
    return "in_house";
  }

  if (status === "checked_out" || status === "checked out") {
    // Once it's checked-out, show under Departures
    return "departures";
  }

  // 2) Fallback to date logic
  const ci = parseYmd(checkIn);
  const co = parseYmd(checkOut);
  const bd = parseYmd(businessDate);

  if (!ci || !co || !bd) {
    // If dates are weird, treat as upcoming
    return "upcoming";
  }

  if (isSameDay(ci, bd)) return "arrivals";
  if (isSameDay(co, bd)) return "departures";
  if (ci < bd && co > bd) return "in_house";
  if (ci > bd) return "upcoming";

  return "upcoming";
};

// Normalize status label per booking + bucket (for display only)
const getDisplayStatus = (
  booking: FrontDeskBooking,
  bucket: Bucket
): string => {
  const raw = (booking.status || "").toLowerCase();

  if (bucket === "arrivals") {
    return "Confirmed";
  }

  if (bucket === "in_house") {
    return "In House";
  }

  if (bucket === "departures") {
    if (raw === "checked_out" || raw === "checked out") {
      return "Checked Out";
    }
    return "Departure";
  }

  if (raw === "cancelled" || raw === "canceled") return "Cancelled";
  if (raw === "no_show" || raw === "no-show") return "No-Show";

  // fallback: capitalize raw
  if (!raw) return "—";
  return raw.charAt(0).toUpperCase() + raw.slice(1);
};

// Status pill colors based on raw status
const getStatusPillClass = (status: BookingStatus): string => {
  const raw = (status || "").toLowerCase();
  if (raw === "in_house" || raw === "in house") {
    return "bg-sky-50 text-sky-700 ring-sky-200";
  }
  if (raw === "checked_out" || raw === "checked out") {
    return "bg-slate-50 text-slate-700 ring-slate-200";
  }
  if (raw === "cancelled" || raw === "canceled") {
    return "bg-rose-50 text-rose-700 ring-rose-200";
  }
  if (raw === "no_show" || raw === "no-show") {
    return "bg-amber-50 text-amber-700 ring-amber-200";
  }
  // default: confirmed
  return "bg-emerald-50 text-emerald-700 ring-emerald-200";
};

const channelPill =
  "inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 ring-1 ring-indigo-200";

// --- main component ----------------------------------------------------

const FrontDeskConsole: React.FC = () => {
  const [businessDate, setBusinessDate] = useState(() => {
    const d = new Date();
    return d.toISOString().slice(0, 10); // "YYYY-MM-DD"
  });
  const [viewScope, setViewScope] = useState<"touches" | "today">("touches");
  const [selectedProperty, setSelectedProperty] = useState("ALL");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<FrontDeskApiData | null>(null);

  const propertyOptions = [
    { code: "ALL", name: "All Properties" },
    { code: "DRE001", name: "Dream Big Hotel" },
    { code: "N&N002", name: "N&N Luxury Hotel" },
  ];

  // Load bookings from backend and normalize into FrontDeskBooking[]
  const loadBookings = async () => {
    try {
      setLoading(true);
      setError(null);

      const res = await axios.get(`${API_BASE}/frontdesk/bookings`, {
        params: {
          scope: viewScope, // "touches" or "today"
          date: businessDate, // "2025-12-01"
        },
        headers: {
          Authorization: `Bearer ${AUTH_TOKEN}`,
        },
      });

      const raw = res.data;

      const rows: any[] = Array.isArray(raw)
        ? raw
        : Array.isArray(raw?.bookings)
        ? raw.bookings
        : [];

      const mapped: FrontDeskBooking[] = rows.map((r) => {
        const property_code: string = r.property_code || "DRE001";
        const hotel_name =
          HOTEL_NAME_BY_PROPERTY[property_code] || property_code;

        const status: string = r.booking_status || r.status || "";
        const bucket: Bucket = classifyBucket(
          status,
          r.check_in_date,
          r.check_out_date,
          businessDate
        );

        return {
          id: r.id,
          guest_name: r.guest_name,
          hotel_name,
          property_code,
          room_number: r.room_number ?? null,
          room_type: r.room_type ?? null,
          check_in_date: r.check_in_date,
          check_out_date: r.check_out_date,
          nights: calculateNights(r.check_in_date, r.check_out_date),
          status,
          channel: r.channel || "",
          total_amount: r.total_amount ?? null,
          currency: r.currency ?? "ETB",
          note: r.note ?? null,
          bucket,
        };
      });

      console.log("Frontdesk bookings response (normalized):", mapped);
      setData(mapped);
    } catch (err: any) {
      console.error(
        "Error loading bookings:",
        err?.response?.data || err.message || err
      );
      setError(
        "Error loading bookings. " +
          (err?.response?.data?.detail ||
            err.message ||
            "Please check backend connection.")
      );
    } finally {
      setLoading(false);
    }
  };

  // --- Action handlers: Assign Room / Check In / Check Out --------------

  const handleAssignRoom = async (booking: FrontDeskBooking) => {
    const current = booking.room_number || "";
    const room = window.prompt(
      `Assign room for ${booking.guest_name} (${booking.property_code}):`,
      current
    );
    if (!room) return;

    try {
      setLoading(true);
      setError(null);

      await axios.post(
        `${API_BASE}/frontdesk/assign-room`,
        { booking_id: booking.id, room_number: room },
        {
          headers: {
            Authorization: `Bearer ${AUTH_TOKEN}`,
            "Content-Type": "application/json",
          },
        }
      );

      await loadBookings();
    } catch (err: any) {
      console.error(
        "Error assigning room:",
        err?.response?.data || err.message || err
      );
      setError(
        "Unable to assign room. " +
          (err?.response?.data?.detail || err.message || "")
      );
    } finally {
      setLoading(false);
    }
  };

  const handleCheckIn = async (booking: FrontDeskBooking) => {
    try {
      setLoading(true);
      setError(null);

      await axios.post(
        `${API_BASE}/frontdesk/check-in`,
        { booking_id: booking.id },
        {
          headers: {
            Authorization: `Bearer ${AUTH_TOKEN}`,
            "Content-Type": "application/json",
          },
        }
      );

      await loadBookings();
    } catch (err: any) {
      console.error(
        "Error performing check-in:",
        err?.response?.data || err.message || err
      );
      setError(
        "Unable to perform check-in. " +
          (err?.response?.data?.detail || err.message || "")
      );
    } finally {
      setLoading(false);
    }
  };

  const handleCheckOut = async (booking: FrontDeskBooking) => {
    try {
      setLoading(true);
      setError(null);

      await axios.post(
        `${API_BASE}/frontdesk/check-out`,
        { booking_id: booking.id },
        {
          headers: {
            Authorization: `Bearer ${AUTH_TOKEN}`,
            "Content-Type": "application/json",
          },
        }
      );

      await loadBookings();
    } catch (err: any) {
      console.error(
        "Error performing check-out:",
        err?.response?.data || err.message || err
      );
      setError(
        "Unable to perform check-out. " +
          (err?.response?.data?.detail || err.message || "")
      );
    } finally {
      setLoading(false);
    }
  };

  // Reload when businessDate / property / scope changes
  useEffect(() => {
    loadBookings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [businessDate, selectedProperty, viewScope]);

  // Normalize data to: bookingsByBucket + optional houseCount
  const { bookingsByBucket, houseCount } = useMemo(() => {
    const emptyBuckets: Record<Bucket, FrontDeskBooking[]> = {
      arrivals: [],
      in_house: [],
      departures: [],
      upcoming: [],
      cancelled: [],
    };

    if (!data) {
      return {
        bookingsByBucket: emptyBuckets,
        houseCount: undefined as HouseCount | undefined,
      };
    }

    let bookings: FrontDeskBooking[] = [];
    let hc: HouseCount | undefined = undefined;

    if (Array.isArray(data)) {
      bookings = data;
    } else if (Array.isArray((data as ApiFrontDeskResponse).bookings)) {
      bookings = (data as ApiFrontDeskResponse).bookings;
    } else {
      console.warn("Unexpected frontdesk response shape:", data);
      return {
        bookingsByBucket: emptyBuckets,
        houseCount: undefined as HouseCount | undefined,
      };
    }

    // Filter by selected property if not ALL
    if (selectedProperty !== "ALL") {
      bookings = bookings.filter((b) => b.property_code === selectedProperty);
    }

    // Bucket bookings
    const result: Record<Bucket, FrontDeskBooking[]> = {
      arrivals: [],
      in_house: [],
      departures: [],
      upcoming: [],
      cancelled: [],
    };

    for (const b of bookings) {
      const key = (b.bucket || "").toLowerCase() as Bucket;
      if (key in result) {
        result[key].push(b);
      } else {
        result.upcoming.push(b); // fallback
      }
    }

    // --- Compute house count / occupancy for current view --------------------

    const propertiesInScope = new Set<string>(
      bookings.map((b) => b.property_code)
    );

    let totalRooms = 0;
    propertiesInScope.forEach((code) => {
      const rooms = ROOMS_TOTAL_BY_PROPERTY[code];
      if (typeof rooms === "number" && rooms > 0) {
        totalRooms += rooms;
      }
    });

    if (totalRooms > 0) {
      const occupiedRooms = result.in_house.length + result.arrivals.length;
      const occupancyPct =
        totalRooms > 0 ? (occupiedRooms / totalRooms) * 100 : 0;

      hc = {
        property_code:
          selectedProperty === "ALL" ? "PORTFOLIO" : selectedProperty,
        date: businessDate,
        total_rooms: totalRooms,
        occupied_rooms: occupiedRooms,
        out_of_order_rooms: 0,
        available_rooms: Math.max(0, totalRooms - occupiedRooms),
        occupancy_pct: occupancyPct,
        arrivals_today: result.arrivals.length,
        departures_today: result.departures.length,
        cancelled_today: result.cancelled.length,
      };
    }

    return { bookingsByBucket: result, houseCount: hc };
  }, [data, selectedProperty, businessDate]);

  const hc = houseCount;

  return (
    <div className="min-h-screen bg-slate-100 py-8">
      <div className="mx-auto max-w-6xl px-4">
        <div className="flex overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-200/80 ring-1 ring-slate-200/70">
          {/* Left sidebar */}
          <div className="flex w-16 flex-col items-center justify-between border-r border-slate-100 bg-slate-50/80 py-6">
            <button className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-indigo-600 text-white shadow-md">
              🛎️
            </button>
            <button className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm">
              ⚙️
            </button>
          </div>

          {/* Main content */}
          <div className="flex-1 px-5 pb-6 pt-5 sm:px-8 sm:pb-8 sm:pt-6">
            {/* Header */}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-indigo-50 text-indigo-600 ring-1 ring-indigo-100">
                    GZ
                  </span>
                  <div>
                    <h1 className="text-lg font-semibold tracking-tight text-slate-900">
                      Front Desk – Room Division Console
                    </h1>
                    <p className="mt-1 text-xs text-slate-500">
                      Today: {businessDate} · Portfolio view of arrivals,
                      in-house, and departures.
                    </p>
                  </div>
                </div>
              </div>

              {/* Filters: business date, scope, property */}
              <div className="flex flex-col gap-2 text-xs text-slate-600 sm:flex-row">
                <InfoCard label="Business Date">
                  <input
                    type="date"
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    value={businessDate}
                    onChange={(e) => setBusinessDate(e.target.value)}
                  />
                </InfoCard>

                <InfoCard label="View scope">
                  <select
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    value={viewScope}
                    onChange={(e) =>
                      setViewScope(
                        e.target.value === "touches" ? "touches" : "today"
                      )
                    }
                  >
                    <option value="touches">Today (touches today)</option>
                    <option value="today">Today (business date only)</option>
                  </select>
                </InfoCard>

                <InfoCard label="Property">
                  <select
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    value={selectedProperty}
                    onChange={(e) => setSelectedProperty(e.target.value)}
                  >
                    {propertyOptions.map((p) => (
                      <option key={p.code} value={p.code}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </InfoCard>
              </div>
            </div>

            <div className="mt-4 h-px bg-slate-100" />

            {/* Loading + Error */}
            {loading && (
              <p className="mt-2 text-xs text-slate-400">Loading data...</p>
            )}

            {error && (
              <div className="mt-3 rounded-2xl border border-rose-100 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                {error}
              </div>
            )}

            {/* House Count + KPI row */}
            <section className="mt-4">
              <h2 className="text-sm font-semibold text-slate-900">
                House Count & Occupancy – Portfolio
              </h2>
              <p className="text-xs text-slate-500">
                In-House / Total Rooms:&nbsp;
                <span className="font-medium">
                  {hc ? `${hc.occupied_rooms} / ${hc.total_rooms}` : "—"}
                </span>
                &nbsp;· Occupancy:&nbsp;
                <span className="font-medium">
                  {hc ? `${hc.occupancy_pct.toFixed(1)}%` : "—"}
                </span>
              </p>

              {/* Summary pills */}
              <div className="mt-3 flex flex-wrap gap-2">
                <StatPill
                  label="Arrivals Today"
                  value={bookingsByBucket.arrivals.length}
                  tone="emerald"
                />
                <StatPill
                  label="In-House Rooms"
                  value={bookingsByBucket.in_house.length}
                  tone="sky"
                />
                <StatPill
                  label="Departures Today"
                  value={bookingsByBucket.departures.length}
                  tone="violet"
                />
                <StatPill
                  label="Cancelled / No-Show"
                  value={bookingsByBucket.cancelled.length}
                  tone="rose"
                />
                <StatPill
                  label="Occupancy (Rooms) – Portfolio"
                  value={hc?.occupancy_pct ?? 0}
                  suffix="%"
                  tone="indigo"
                />
              </div>
            </section>

            {/* Arrivals */}
            <BucketSection
              title="Arrivals Today"
              colorDot="bg-emerald-500"
              bucketKey="arrivals"
              bookings={bookingsByBucket.arrivals}
              onAssignRoom={handleAssignRoom}
              onCheckIn={handleCheckIn}
              onCheckOut={handleCheckOut}
            />

            {/* In-House */}
            <BucketSection
              title="In-House"
              colorDot="bg-amber-400"
              bucketKey="in_house"
              bookings={bookingsByBucket.in_house}
              onAssignRoom={handleAssignRoom}
              onCheckIn={handleCheckIn}
              onCheckOut={handleCheckOut}
            />

            {/* Departures */}
            <BucketSection
              title="Departures Today"
              colorDot="bg-sky-500"
              bucketKey="departures"
              bookings={bookingsByBucket.departures}
              onAssignRoom={handleAssignRoom}
              onCheckIn={handleCheckIn}
              onCheckOut={handleCheckOut}
            />

            {/* Upcoming */}
            <BucketSection
              title="Upcoming Bookings"
              colorDot="bg-slate-400"
              bucketKey="upcoming"
              bookings={bookingsByBucket.upcoming}
              onAssignRoom={handleAssignRoom}
              onCheckIn={handleCheckIn}
              onCheckOut={handleCheckOut}
            />

            {/* Cancelled / No-Show */}
            <BucketSection
              title="Cancelled / No-Show"
              colorDot="bg-rose-500"
              bucketKey="cancelled"
              bookings={bookingsByBucket.cancelled}
              onAssignRoom={handleAssignRoom}
              onCheckIn={handleCheckIn}
              onCheckOut={handleCheckOut}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default FrontDeskConsole;

// --- small UI helpers --------------------------------------------------

const InfoCard: React.FC<{ label: string; children: React.ReactNode }> = ({
  label,
  children,
}) => (
  <div className="flex items-center gap-2 rounded-2xl border border-slate-100 bg-slate-50 px-3 py-2 shadow-sm">
    <div className="flex flex-col">
      <span className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
        {label}
      </span>
      {children}
    </div>
  </div>
);

interface StatPillProps {
  label: string;
  value: number;
  suffix?: string;
  tone: "emerald" | "sky" | "violet" | "rose" | "indigo";
}

const StatPill: React.FC<StatPillProps> = ({ label, value, suffix, tone }) => {
  const toneMap: Record<StatPillProps["tone"], string> = {
    emerald: "bg-emerald-50 text-emerald-800 ring-emerald-100",
    sky: "bg-sky-50 text-sky-800 ring-sky-100",
    violet: "bg-violet-50 text-violet-800 ring-violet-100",
    rose: "bg-rose-50 text-rose-800 ring-rose-100",
    indigo: "bg-indigo-50 text-indigo-800 ring-indigo-100",
  };

  return (
    <div
      className={`${toneMap[tone]} inline-flex items-center justify-between gap-4 rounded-2xl px-3 py-1.5 text-[11px] font-medium ring-1`}
    >
      <span>{label}</span>
      <span className="text-sm font-semibold">
        {value}
        {suffix ?? ""}
      </span>
    </div>
  );
};

interface BucketSectionProps {
  title: string;
  colorDot: string;
  bucketKey: Bucket;
  bookings: FrontDeskBooking[];
  onAssignRoom: (b: FrontDeskBooking) => void;
  onCheckIn: (b: FrontDeskBooking) => void;
  onCheckOut: (b: FrontDeskBooking) => void;
}

const BucketSection: React.FC<BucketSectionProps> = ({
  title,
  colorDot,
  bucketKey,
  bookings,
  onAssignRoom,
  onCheckIn,
  onCheckOut,
}) => {
  return (
    <section className="mt-6">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${colorDot}`} />
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          <span className="text-xs text-slate-400">({bookings.length})</span>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-100 bg-slate-50/70">
        {bookings.length === 0 ? (
          <div className="px-4 py-4 text-xs text-slate-500">
            No bookings in this category.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100 text-xs">
              <thead className="bg-white">
                <tr>
                  <Th>Guest</Th>
                  <Th>Hotel</Th>
                  <Th>Property</Th>
                  <Th>Room</Th>
                  <Th>Check-In</Th>
                  <Th>Check-Out</Th>
                  <Th className="text-center">Nights</Th>
                  <Th>Status</Th>
                  <Th>Channel</Th>
                  <Th className="text-right">Total</Th>
                  <Th className="text-right">Action</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white/80">
                {bookings.map((b) => {
                  const nights =
                    b.nights != null
                      ? b.nights
                      : calculateNights(b.check_in_date, b.check_out_date);
                  const displayStatus = getDisplayStatus(b, bucketKey);
                  const pillClass = getStatusPillClass(b.status);

                  const canAssignRoom =
                    !b.room_number &&
                    (bucketKey === "arrivals" || bucketKey === "in_house");
                  const canCheckIn = bucketKey === "arrivals";
                  const isAlreadyCheckedOut =
                    (b.status || "").toLowerCase() === "checked_out" ||
                    displayStatus === "Checked Out";
                  const canCheckOut =
                    bucketKey === "in_house" ||
                    (bucketKey === "departures" && !isAlreadyCheckedOut);

                  return (
                    <tr key={b.id} className="hover:bg-slate-50/80">
                      <Td className="font-medium text-slate-900">
                        {b.guest_name}
                      </Td>
                      <Td>{b.hotel_name}</Td>
                      <Td className="text-[11px] text-slate-500">
                        {b.property_code}
                      </Td>
                      <Td>
                        {b.room_number ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-700 ring-1 ring-slate-200">
                            {b.room_number}
                            {b.room_type && (
                              <span className="text-slate-400">
                                {b.room_type}
                              </span>
                            )}
                          </span>
                        ) : (
                          <span className="text-[11px] text-slate-400">
                            TBD
                          </span>
                        )}
                      </Td>
                      <Td>{b.check_in_date}</Td>
                      <Td>{b.check_out_date}</Td>
                      <Td className="text-center">
                        {nights != null ? nights : "—"}
                      </Td>
                      <Td>
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ${pillClass}`}
                        >
                          {displayStatus}
                        </span>
                      </Td>
                      <Td>
                        <span className={channelPill}>{b.channel || "—"}</span>
                      </Td>
                      <Td className="whitespace-nowrap text-right">
                        {formatMoney(b.total_amount, b.currency)}
                      </Td>
                      <Td className="whitespace-nowrap text-right">
                        {canAssignRoom || canCheckIn || canCheckOut ? (
                          <div className="flex justify-end gap-1">
                            {canAssignRoom && (
                              <button
                                onClick={() => onAssignRoom(b)}
                                className="inline-flex items-center rounded-full bg-white px-2 py-1 text-[11px] font-semibold text-indigo-600 ring-1 ring-indigo-200 hover:bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1"
                              >
                                Assign Room
                              </button>
                            )}
                            {canCheckIn && (
                              <button
                                onClick={() => onCheckIn(b)}
                                className="inline-flex items-center rounded-full bg-indigo-600 px-3 py-1.5 text-[11px] font-semibold text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1"
                              >
                                Check In
                              </button>
                            )}
                            {canCheckOut && (
                              <button
                                onClick={() => onCheckOut(b)}
                                className="inline-flex items-center rounded-full bg-indigo-600 px-3 py-1.5 text-[11px] font-semibold text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1"
                              >
                                Check Out
                              </button>
                            )}
                          </div>
                        ) : (
                          <span className="text-[11px] text-slate-400">
                            No action
                          </span>
                        )}
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
};

const Th: React.FC<React.ThHTMLAttributes<HTMLTableCellElement>> = ({
  children,
  className = "",
  ...rest
}) => (
  <th
    className={`whitespace-nowrap px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400 ${className}`}
    {...rest}
  >
    {children}
  </th>
);

const Td: React.FC<React.TdHTMLAttributes<HTMLTableCellElement>> = ({
  children,
  className = "",
  ...rest
}) => (
  <td
    className={`whitespace-nowrap px-3 py-2 align-middle text-[12px] text-slate-700 ${className}`}
    {...rest}
  >
    {children}
  </td>
);
