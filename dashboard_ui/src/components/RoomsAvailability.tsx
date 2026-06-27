// src/components/RoomsAvailability.tsx
import React, { useEffect, useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "";

type RoomsAvailabilityProps = {
  businessDate: string; // coming from AppShell
};

// Be flexible with backend field names so it works with both versions
type AvailabilityResponse = {
  property_code: string;
  target_date: string;

  // Some backends use rooms_total, others total_rooms
  rooms_total?: number;
  total_rooms?: number;

  rooms_sold?: number;
  rooms_available?: number;
  occupancy_pct?: number;
};

const HOTEL_NAME_BY_PROPERTY: Record<string, string> = {
  DRE001: "Dream Big Hotel",
  "N&N002": "N&N Luxury Hotel",
};

// Hard-coded portfolio list for now (matches your PMS design)
const PORTFOLIO_PROPERTIES = ["DRE001", "N&N002"];

// Canonical room counts (your business rule)
const PROPERTY_TOTAL_ROOMS: Record<string, number> = {
  DRE001: 120,
  "N&N002": 80,
};

const RoomsAvailability: React.FC<RoomsAvailabilityProps> = ({
  businessDate,
}) => {
  const [rows, setRows] = useState<AvailabilityResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAvailability = async () => {
      setLoading(true);
      setError(null);

      try {
        const headers = {
          Authorization: `Bearer ${AUTH_TOKEN}`,
        };

        const results: AvailabilityResponse[] = [];

        for (const property_code of PORTFOLIO_PROPERTIES) {
          const res = await axios.get<AvailabilityResponse>(
            `${API_BASE}/rooms/availability`,
            {
              params: {
                property_code,
                target_date: businessDate,
              },
              headers,
            }
          );

          results.push(res.data);
        }

        setRows(results);
      } catch (err: any) {
        console.error("Error loading rooms availability", err);
        setError(err.message || "Unable to load rooms availability.");
      } finally {
        setLoading(false);
      }
    };

    if (businessDate) {
      fetchAvailability();
    }
  }, [businessDate]);

  return (
    <div
      style={{
        padding: "1.5rem",
        fontFamily:
          "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      }}
    >
      <h1
        style={{
          fontSize: "1.4rem",
          fontWeight: 700,
          marginBottom: "0.25rem",
        }}
      >
        🛏 Rooms Availability – {businessDate}
      </h1>

      <p style={{ marginBottom: "1rem", color: "#555", fontSize: "0.9rem" }}>
        Portfolio view of{" "}
        <strong>{PORTFOLIO_PROPERTIES.length} properties</strong> for the
        selected business date. This mirrors a modern multi-property PMS view.
      </p>

      {loading && <p>Loading availability…</p>}

      {error && !loading && (
        <p style={{ color: "red", marginBottom: "1rem" }}>
          Error loading availability: {error}
        </p>
      )}

      {!loading &&
        !error &&
        PORTFOLIO_PROPERTIES.map((code) => {
          const row = rows.find((r) => r.property_code === code);
          const hotelName = HOTEL_NAME_BY_PROPERTY[code] || code;

          // --- derive safe values even if backend fields differ or are missing ----
          const totalRooms =
            row?.rooms_total ??
            row?.total_rooms ??
            PROPERTY_TOTAL_ROOMS[code] ??
            0;

          const roomsSold = row?.rooms_sold ?? 0;
          const roomsAvailable =
            row?.rooms_available ?? Math.max(totalRooms - roomsSold, 0);

          const occupancyPct =
            row?.occupancy_pct ??
            (totalRooms > 0 ? (roomsSold / totalRooms) * 100 : 0);

          const pctClamped = Math.max(0, Math.min(100, occupancyPct));

          return (
            <div
              key={code}
              style={{
                borderRadius: "0.75rem",
                border: "1px solid #e2e2e2",
                padding: "1rem",
                marginBottom: "1rem",
                backgroundColor: "#fff",
                boxShadow: "0 1px 3px rgba(0, 0, 0, 0.04)",
              }}
            >
              <h2
                style={{
                  fontSize: "1.1rem",
                  fontWeight: 600,
                  marginBottom: "0.25rem",
                }}
              >
                {hotelName}
              </h2>

              <p
                style={{
                  fontSize: "0.85rem",
                  color: "#666",
                  marginBottom: "0.75rem",
                }}
              >
                Property code: <strong>{code}</strong> • Date:{" "}
                <strong>{businessDate}</strong>
              </p>

              {!row ? (
                <p style={{ fontSize: "0.85rem", color: "#777" }}>
                  No availability data returned from backend.
                </p>
              ) : (
                <>
                  {/* KPI row */}
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "1rem",
                      fontSize: "0.9rem",
                    }}
                  >
                    <div>
                      <div style={{ color: "#777", fontSize: "0.8rem" }}>
                        Total rooms
                      </div>
                      <div style={{ fontWeight: 600 }}>{totalRooms}</div>
                    </div>
                    <div>
                      <div style={{ color: "#777", fontSize: "0.8rem" }}>
                        Rooms sold
                      </div>
                      <div style={{ fontWeight: 600 }}>{roomsSold}</div>
                    </div>
                    <div>
                      <div style={{ color: "#777", fontSize: "0.8rem" }}>
                        Rooms available
                      </div>
                      <div style={{ fontWeight: 600 }}>{roomsAvailable}</div>
                    </div>
                    <div>
                      <div style={{ color: "#777", fontSize: "0.8rem" }}>
                        Occupancy
                      </div>
                      <div style={{ fontWeight: 600 }}>
                        {totalRooms > 0
                          ? `${pctClamped.toFixed(1)}%`
                          : "–"}
                      </div>
                    </div>
                  </div>

                  {/* simple occupancy bar like a PMS */}
                  <div
                    style={{
                      marginTop: "0.75rem",
                      height: "0.5rem",
                      borderRadius: "999px",
                      backgroundColor: "#e5e7eb",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${pctClamped}%`,
                        height: "100%",
                        background:
                          pctClamped < 70
                            ? "#10b981" // green
                            : pctClamped < 90
                            ? "#fbbf24" // amber
                            : "#ef4444", // red
                        transition: "width 0.3s ease",
                      }}
                    />
                  </div>
                </>
              )}
            </div>
          );
        })}
    </div>
  );
};

export default RoomsAvailability;
