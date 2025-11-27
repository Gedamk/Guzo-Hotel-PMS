import React, { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "<REDACTED_DEMO_BEARER_TOKEN>";

function BookingsTable({ year, month }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const monthLabel = `${year}-${String(month).padStart(2, "0")}`;

  useEffect(() => {
    async function fetchBookings() {
      try {
        setLoading(true);
        setError(null);

        const headers = {
          Authorization: `Bearer ${AUTH_TOKEN}`,
        };

        // Reuse the same portfolio endpoint – it already returns per_hotel data
        const res = await fetch(
          `${API_BASE}/reports/portfolio?year=${year}&month=${month}`,
          { headers }
        );

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const json = await res.json();
        const perHotel = json?.report?.per_hotel || [];

        setRows(perHotel);
      } catch (err) {
        console.error(err);
        setError(err.message || "Failed to load bookings");
      } finally {
        setLoading(false);
      }
    }

    fetchBookings();
  }, [year, month]);

  const formatNumber = (value) =>
    Number(value || 0).toLocaleString("en-US", {
      maximumFractionDigits: 2,
    });

  const formatPercent = (value) =>
    ((Number(value || 0) * 100).toFixed(1) + "%");

  if (loading) {
    return (
      <div style={{ padding: "1rem" }}>
        Loading bookings for {monthLabel}…
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "1rem", color: "red" }}>
        Error loading bookings: {error}
      </div>
    );
  }

  if (!rows.length) {
    return (
      <div style={{ padding: "1rem" }}>
        No bookings data for {monthLabel}.
      </div>
    );
  }

  return (
    <div style={{ padding: "1rem" }}>
      <h2 style={{ fontSize: "1.4rem", marginBottom: "0.5rem" }}>
        Bookings by Hotel – {monthLabel}
      </h2>

      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            minWidth: "600px",
          }}
        >
          <thead>
            <tr style={{ backgroundColor: "#f3f3f3" }}>
              <Th>Code</Th>
              <Th>Hotel</Th>
              <Th>Bookings</Th>
              <Th>Nights</Th>
              <Th>Revenue (ETB)</Th>
              <Th>ADR</Th>
              <Th>RevPAR</Th>
              <Th>Occupancy</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((h) => (
              <tr key={h.property_code}>
                <Td>{h.property_code}</Td>
                <Td>{h.hotel_name}</Td>
                <Td>{h.bookings_count}</Td>
                <Td>{formatNumber(h.room_nights_sold)}</Td>
                <Td>{formatNumber(h.room_revenue_etb)}</Td>
                <Td>{formatNumber(h.adr)}</Td>
                <Td>{formatNumber(h.revpar)}</Td>
                <Td>{formatPercent(h.occupancy_pct)}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({ children }) {
  return (
    <th
      style={{
        textAlign: "left",
        padding: "0.5rem 0.75rem",
        fontSize: "0.85rem",
        fontWeight: 600,
        borderBottom: "1px solid #ddd",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </th>
  );
}

function Td({ children }) {
  return (
    <td
      style={{
        padding: "0.45rem 0.75rem",
        fontSize: "0.85rem",
        borderBottom: "1px solid #eee",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </td>
  );
}

export default BookingsTable;
