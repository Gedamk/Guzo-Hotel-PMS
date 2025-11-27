import React, { useEffect, useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "admin-secret-123";

type PortfolioSummary = {
  bookings_count: number;
  room_nights_sold: number;
  room_revenue_etb: number;
  rooms_total: number;
  rooms_available: number;
  adr: number;
  revpar: number;
  occupancy_pct: number;
};

type PerHotelRow = {
  property_code: string;
  hotel_name: string;
  bookings_count: number;
  room_nights_sold: number;
  room_revenue_etb: number;
  rooms_total: number;
  rooms_available: number;
  adr: number;
  revpar: number;
  occupancy_pct: number;
};

type PortfolioReportResponse = {
  year: number;
  month: number;
  scope: string;
  report: {
    scope: string;
    year: number;
    month: number;
    period: {
      start_date: string;
      end_date: string;
    };
    summary: PortfolioSummary;
    per_hotel: PerHotelRow[];
  };
};

const PortfolioDashboard: React.FC = () => {
  const [data, setData] = useState<PortfolioReportResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // For now: hard-code to match your curl
  const year = 2025;
  const month = 11;

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await axios.get<PortfolioReportResponse>(
          `${API_BASE}/reports/portfolio`,
          {
            params: { year, month },
            headers: {
              Authorization: `Bearer ${AUTH_TOKEN}`,
            },
          }
        );

        setData(res.data);
      } catch (err: any) {
        console.error("Error loading portfolio report", err);
        setError(err?.message ?? "Failed to load portfolio report");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [year, month]);

  if (loading) {
    return <div className="p-4">Loading portfolio report…</div>;
  }

  if (error) {
    return (
      <div className="p-4 text-red-600">
        Error loading portfolio report: {error}
      </div>
    );
  }

  if (!data) {
    return <div className="p-4">No data.</div>;
  }

  const { report } = data;
  const { summary, per_hotel } = report;

  const pct = (value: number) => `${(value * 100).toFixed(1)}%`;
  const etb = (value: number) =>
    `${Number(value.toFixed(2)).toLocaleString("en-ET")} ETB`;

  return (
    <div className="p-4 space-y-6">
      {/* Header */}
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-bold">
          Portfolio Performance – {report.year}-
          {String(report.month).padStart(2, "0")}
        </h1>
        <span className="text-sm text-gray-500">
          Period: {report.period.start_date} → {report.period.end_date}
        </span>
      </div>

      {/* Summary tiles */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="border rounded-lg p-4 shadow-sm bg-white">
          <div className="text-sm text-gray-500">Bookings</div>
          <div className="text-2xl font-semibold">
            {summary.bookings_count}
          </div>
        </div>

        <div className="border rounded-lg p-4 shadow-sm bg-white">
          <div className="text-sm text-gray-500">Room Nights Sold</div>
          <div className="text-2xl font-semibold">
            {summary.room_nights_sold}
          </div>
        </div>

        <div className="border rounded-lg p-4 shadow-sm bg-white">
          <div className="text-sm text-gray-500">Room Revenue</div>
          <div className="text-xl font-semibold">
            {etb(summary.room_revenue_etb)}
          </div>
        </div>

        <div className="border rounded-lg p-4 shadow-sm bg-white">
          <div className="text-sm text-gray-500">Occupancy</div>
          <div className="text-2xl font-semibold">
            {pct(summary.occupancy_pct)}
          </div>
        </div>
      </div>

      {/* ADR / RevPAR / Inventory */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="border rounded-lg p-4 shadow-sm bg-white">
          <div className="text-sm text-gray-500">ADR</div>
          <div className="text-xl font-semibold">{etb(summary.adr)}</div>
        </div>

        <div className="border rounded-lg p-4 shadow-sm bg-white">
          <div className="text-sm text-gray-500">RevPAR</div>
          <div className="text-xl font-semibold">{etb(summary.revpar)}</div>
        </div>

        <div className="border rounded-lg p-4 shadow-sm bg-white">
          <div className="text-sm text-gray-500">Rooms (Total / Available)</div>
          <div className="text-xl font-semibold">
            {summary.rooms_total} rooms / {summary.rooms_available} room-nights
          </div>
        </div>
      </div>

      {/* Per-hotel table */}
      <div className="border rounded-lg p-4 shadow-sm bg-white overflow-x-auto">
        <h2 className="text-lg font-semibold mb-3">Per-Hotel Breakdown</h2>
        <table className="min-w-full text-sm">
          <thead className="border-b bg-gray-50">
            <tr>
              <th className="text-left py-2 px-2">Property</th>
              <th className="text-left py-2 px-2">Bookings</th>
              <th className="text-left py-2 px-2">Room Nights</th>
              <th className="text-left py-2 px-2">Revenue</th>
              <th className="text-left py-2 px-2">Occupancy</th>
              <th className="text-left py-2 px-2">ADR</th>
              <th className="text-left py-2 px-2">RevPAR</th>
            </tr>
          </thead>
          <tbody>
            {per_hotel.map((h) => (
              <tr key={h.property_code} className="border-b last:border-0">
                <td className="py-2 px-2">
                  <div className="font-medium">{h.hotel_name}</div>
                  <div className="text-xs text-gray-500">
                    {h.property_code}
                  </div>
                </td>
                <td className="py-2 px-2">{h.bookings_count}</td>
                <td className="py-2 px-2">{h.room_nights_sold}</td>
                <td className="py-2 px-2">{etb(h.room_revenue_etb)}</td>
                <td className="py-2 px-2">{pct(h.occupancy_pct)}</td>
                <td className="py-2 px-2">{etb(h.adr)}</td>
                <td className="py-2 px-2">{etb(h.revpar)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PortfolioDashboard;
