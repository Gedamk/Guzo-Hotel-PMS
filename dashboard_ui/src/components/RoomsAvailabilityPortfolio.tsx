// src/components/RoomsAvailabilityPortfolio.tsx

import React, { useEffect, useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "";

type RoomAvailabilityRow = {
  room_type: string;
  rooms_total: number;
  rooms_booked: number;
  rooms_available: number;
};

type PropertyAvailability = {
  property_code: string;
  date: string;
  availability: RoomAvailabilityRow[];
};

type RoomsAvailabilityPortfolioProps = {
  // Optional: if not provided, we use today's date
  businessDate?: string;
};

const PROPERTIES = [
  { code: "DRE001", name: "Dream Big Hotel" },
  { code: "N&N002", name: "N&N Luxury Hotel" },
];

const todayISO = (): string => {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
};

const RoomsAvailabilityPortfolio: React.FC<RoomsAvailabilityPortfolioProps> = ({
  businessDate,
}) => {
  const effectiveDate = businessDate ?? todayISO();

  const [data, setData] = useState<Record<string, PropertyAvailability | null>>(
    {}
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAvailability = async () => {
      setLoading(true);
      setError(null);

      try {
        const results: Record<string, PropertyAvailability | null> = {};

        await Promise.all(
          PROPERTIES.map(async (p) => {
            try {
              const res = await axios.get(`${API_BASE}/rooms/availability`, {
                headers: {
                  Authorization: `Bearer ${AUTH_TOKEN}`,
                },
                params: {
                  property_code: p.code,
                  target_date: effectiveDate,
                },
              });
              results[p.code] = res.data as PropertyAvailability;
            } catch (err) {
              console.error(
                "[RoomsAvailabilityPortfolio] error for",
                p.code,
                err
              );
              results[p.code] = null;
            }
          })
        );

        setData(results);
      } catch (err: any) {
        console.error("[RoomsAvailabilityPortfolio] fetch error:", err);
        setError("Error loading rooms availability.");
      } finally {
        setLoading(false);
      }
    };

    fetchAvailability();
  }, [effectiveDate]);

  return (
    <section className="fd-section">
      <h2 className="fd-section-title">
        Rooms Availability – {effectiveDate}
      </h2>

      {error && <div className="fd-error">{error}</div>}
      {loading && (
        <div className="fd-loading">Loading room availability…</div>
      )}

      <div className="fd-rooms-grid">
        {PROPERTIES.map((p) => {
          const entry = data[p.code];

          if (!entry || !entry.availability) {
            return (
              <div key={p.code} className="fd-rooms-card">
                <h3 className="fd-rooms-title">{p.name}</h3>
                <p className="fd-rooms-subtitle">
                  Property code: {p.code} • Date: {effectiveDate}
                </p>
                <p className="fd-empty">No availability data.</p>
              </div>
            );
          }

          const totalRooms = entry.availability.reduce(
            (sum, r) => sum + (r.rooms_total || 0),
            0
          );
          const booked = entry.availability.reduce(
            (sum, r) => sum + (r.rooms_booked || 0),
            0
          );
          const available = entry.availability.reduce(
            (sum, r) => sum + (r.rooms_available || 0),
            0
          );
          const occupancyPct =
            totalRooms > 0 ? (booked / totalRooms) * 100 : 0;

          return (
            <div key={p.code} className="fd-rooms-card">
              <h3 className="fd-rooms-title">{p.name}</h3>
              <p className="fd-rooms-subtitle">
                Property code: {p.code} • Date: {entry.date}
              </p>

              <div className="fd-rooms-kpis">
                <div className="fd-rooms-kpi">
                  <span className="fd-rooms-kpi-label">Occupancy</span>
                  <span className="fd-rooms-kpi-value">
                    {occupancyPct.toFixed(0)}%
                  </span>
                </div>
                <div className="fd-rooms-kpi">
                  <span className="fd-rooms-kpi-label">Total Rooms</span>
                  <span className="fd-rooms-kpi-value">{totalRooms}</span>
                </div>
                <div className="fd-rooms-kpi">
                  <span className="fd-rooms-kpi-label">Booked</span>
                  <span className="fd-rooms-kpi-value">{booked}</span>
                </div>
                <div className="fd-rooms-kpi">
                  <span className="fd-rooms-kpi-label">Available</span>
                  <span className="fd-rooms-kpi-value">{available}</span>
                </div>
              </div>

              <table className="fd-table fd-rooms-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Total</th>
                    <th>Booked</th>
                    <th>Available</th>
                  </tr>
                </thead>
                <tbody>
                  {entry.availability.map((r) => (
                    <tr key={r.room_type}>
                      <td>{r.room_type}</td>
                      <td>{r.rooms_total}</td>
                      <td>{r.rooms_booked}</td>
                      <td>{r.rooms_available}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default RoomsAvailabilityPortfolio;
