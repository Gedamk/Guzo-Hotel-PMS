// src/components/FrontDeskHouseCount.tsx
//
// Ethiopian-style House Count widget for Front Desk.
// - Property selector (DRE001 / N&N002)
// - Business date selector
// - Fetches from:
//     • GET /rooms/availability?property_code=&target_date=
//     • GET /frontdesk/bookings?scope=today&date=
// - Shows: total rooms, in-house, OOO, available, arrivals, departures, occupancy%
// - Auto-refresh every 30 seconds.

import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "<REDACTED_DEMO_BEARER_TOKEN>";

type AvailabilitySummary = {
  property_code: string;
  date: string; // "YYYY-MM-DD"
  total_rooms: number;
  occupied_rooms: number;
  out_of_order_rooms: number;
  available_rooms: number;
  occupancy_pct: number;
};

type RawBooking = {
  id: number;
  guest_name: string | null;
  room_number: string | null;
  room_type: string | null;
  check_in: string; // "YYYY-MM-DD"
  check_out: string; // "YYYY-MM-DD"
  status: string;
  property_code: string;
};

type WidgetState = "idle" | "loading" | "ready" | "error";

const PROPERTY_OPTIONS: { code: string; label: string }[] = [
  { code: "DRE001", label: "Dream Big Hotel" },
  { code: "N&N002", label: "N&N Luxury Hotel" },
];

const todayIso = (): string => {
  const d = new Date();
  const y = d.getFullYear();
  const m = `${d.getMonth() + 1}`.padStart(2, "0");
  const day = `${d.getDate()}`.padStart(2, "0");
  return `${y}-${m}-${day}`;
};

const FrontDeskHouseCount: React.FC = () => {
  const [propertyCode, setPropertyCode] = useState<string>("DRE001");
  const [businessDate, setBusinessDate] = useState<string>(todayIso());

  const [availability, setAvailability] = useState<AvailabilitySummary | null>(
    null
  );
  const [arrivals, setArrivals] = useState<number>(0);
  const [departures, setDepartures] = useState<number>(0);

  const [state, setState] = useState<WidgetState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setState("loading");
    setErrorMsg(null);

    try {
      // 1) Availability: total rooms, in-house, ooo, available
      const availResp = await axios.get<AvailabilitySummary>(
        `${API_BASE}/rooms/availability`,
        {
          params: {
            property_code: propertyCode,
            target_date: businessDate,
          },
        }
      );

      setAvailability(availResp.data);

      // 2) Bookings for arrivals/departures summary
      const bookingsResp = await axios.get<RawBooking[]>(
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

      const list = bookingsResp.data || [];

      // Ethiopian-style front desk logic:
      // - Arrivals: check_in == businessDate, property, status confirmed
      // - Departures: check_out == businessDate, property, status in_house / checked_out / confirmed
      const propertyBookings = list.filter(
        (b) => b.property_code === propertyCode
      );

      const arrCount = propertyBookings.filter((b) => {
        const status = (b.status || "").toLowerCase();
        return (
          b.check_in === businessDate &&
          (status === "confirmed" ||
            status === "guaranteed" ||
            status === "tentative")
        );
      }).length;

      const depCount = propertyBookings.filter((b) => {
        const status = (b.status || "").toLowerCase();
        return (
          b.check_out === businessDate &&
          (status === "in_house" ||
            status === "checked_out" ||
            status === "confirmed")
        );
      }).length;

      setArrivals(arrCount);
      setDepartures(depCount);

      setState("ready");
    } catch (err: any) {
      console.error("HouseCount load error:", err);
      setErrorMsg(
        err?.response?.data?.detail
          ? String(err.response.data.detail)
          : "Failed to load house count."
      );
      setState("error");
    }
  }, [propertyCode, businessDate]);

  // load on first mount & whenever property/date changes
  useEffect(() => {
    loadData();
  }, [loadData]);

  // auto-refresh every 30 seconds
  useEffect(() => {
    const id = setInterval(() => {
      loadData();
    }, 30_000);

    return () => clearInterval(id);
  }, [loadData]);

  const handlePropertyChange = (
    e: React.ChangeEvent<HTMLSelectElement>
  ): void => {
    setPropertyCode(e.target.value);
  };

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    setBusinessDate(e.target.value);
  };

  const boxStyle: React.CSSProperties = {
    flex: 1,
    minWidth: 120,
    padding: 10,
    borderRadius: 8,
    border: "1px solid #e0e0e0",
    backgroundColor: "#fafafa",
    textAlign: "center",
    marginRight: 8,
    marginBottom: 8,
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 12,
    color: "#555",
    textTransform: "uppercase",
    marginBottom: 4,
  };

  const valueStyle: React.CSSProperties = {
    fontSize: 20,
    fontWeight: 700,
    color: "#222",
  };

  const subStyle: React.CSSProperties = {
    fontSize: 11,
    color: "#777",
    marginTop: 2,
  };

  const headerRowStyle: React.CSSProperties = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
    gap: 12,
  };

  const controlsStyle: React.CSSProperties = {
    display: "flex",
    gap: 8,
    alignItems: "center",
    flexWrap: "wrap",
  };

  const chipStyle: React.CSSProperties = {
    fontSize: 11,
    padding: "2px 8px",
    borderRadius: 12,
    backgroundColor: "#eef5ff",
    color: "#2451a6",
  };

  return (
    <div
      style={{
        borderRadius: 12,
        border: "1px solid #e0e0e0",
        padding: 16,
        marginBottom: 16,
        backgroundColor: "#ffffff",
        boxShadow: "0 2px 4px rgba(0,0,0,0.03)",
      }}
    >
      <div style={headerRowStyle}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 2 }}>
            House Count – Ethiopian Daily Snapshot
          </div>
          <div style={{ fontSize: 11, color: "#777" }}>
            Basic room division summary for{" "}
            <span style={{ fontWeight: 600 }}>{businessDate}</span>
          </div>
        </div>

        <div style={controlsStyle}>
          <label style={{ fontSize: 11, color: "#555" }}>
            Property&nbsp;
            <select
              value={propertyCode}
              onChange={handlePropertyChange}
              style={{ fontSize: 12, padding: "3px 6px" }}
            >
              {PROPERTY_OPTIONS.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>

          <label style={{ fontSize: 11, color: "#555" }}>
            Business Date&nbsp;
            <input
              type="date"
              value={businessDate}
              onChange={handleDateChange}
              style={{ fontSize: 12, padding: "3px 6px" }}
            />
          </label>

          <span style={chipStyle}>
            {state === "loading"
              ? "Refreshing…"
              : `Updated for ${propertyCode}`}
          </span>
        </div>
      </div>

      {state === "error" && (
        <div
          style={{
            marginTop: 8,
            marginBottom: 8,
            padding: 8,
            borderRadius: 6,
            backgroundColor: "#ffecec",
            color: "#b30000",
            fontSize: 12,
          }}
        >
          {errorMsg}
        </div>
      )}

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          marginTop: 8,
        }}
      >
        {/* Total Rooms */}
        <div style={{ ...boxStyle, backgroundColor: "#eef2ff" }}>
          <div style={labelStyle}>Total Rooms</div>
          <div style={valueStyle}>
            {availability ? availability.total_rooms : "--"}
          </div>
          <div style={subStyle}>Inventory keys in system</div>
        </div>

        {/* In House */}
        <div style={{ ...boxStyle, backgroundColor: "#e7f9ff" }}>
          <div style={labelStyle}>In House</div>
          <div style={valueStyle}>
            {availability ? availability.occupied_rooms : "--"}
          </div>
          <div style={subStyle}>Occupied tonight</div>
        </div>

        {/* Out of Order */}
        <div style={{ ...boxStyle, backgroundColor: "#ffecec" }}>
          <div style={labelStyle}>Out of Order</div>
          <div style={valueStyle}>
            {availability ? availability.out_of_order_rooms : "--"}
          </div>
          <div style={subStyle}>Rooms blocked (OOO)</div>
        </div>

        {/* Available */}
        <div style={{ ...boxStyle, backgroundColor: "#e9ffe9" }}>
          <div style={labelStyle}>Available</div>
          <div style={valueStyle}>
            {availability ? availability.available_rooms : "--"}
          </div>
          <div style={subStyle}>Sellable keys tonight</div>
        </div>

        {/* Arrivals Today */}
        <div style={{ ...boxStyle, backgroundColor: "#fff7e0" }}>
          <div style={labelStyle}>Arrivals Today</div>
          <div style={valueStyle}>{arrivals}</div>
          <div style={subStyle}>Expected check-ins</div>
        </div>

        {/* Departures Today */}
        <div style={{ ...boxStyle, backgroundColor: "#f5e9ff" }}>
          <div style={labelStyle}>Departures Today</div>
          <div style={valueStyle}>{departures}</div>
          <div style={subStyle}>Expected check-outs</div>
        </div>

        {/* Occupancy % */}
        <div style={{ ...boxStyle, backgroundColor: "#eaf4ff" }}>
          <div style={labelStyle}>Occupancy %</div>
          <div style={valueStyle}>
            {availability ? `${availability.occupancy_pct.toFixed(1)}%` : "--"}
          </div>
          <div style={subStyle}>Based on total rooms</div>
        </div>
      </div>
    </div>
  );
};

export default FrontDeskHouseCount;
