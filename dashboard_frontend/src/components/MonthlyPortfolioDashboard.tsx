import React, { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "";

const DRE_CODE = "DRE001";
const NN_CODE = "N&N002";

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

type HotelReportResponse = {
  year: number;
  month: number;
  property_code: string;
  hotel_name: string;
  period: {
    start_date: string;
    end_date: string;
  };
  summary: PerHotelRow;
};

type Props = {
  year: number;
  month: number;
};

export const MonthlyPortfolioDashboard: React.FC<Props> = ({ year, month }) => {
  const [portfolio, setPortfolio] = useState<PortfolioReportResponse | null>(null);
  const [dre, setDre] = useState<HotelReportResponse | null>(null);
  const [nn, setNn] = useState<HotelReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const monthLabel = `${year}-${String(month).padStart(2, "0")}`;

  useEffect(() => {
    async function fetchAll() {
      try {
        setLoading(true);
        setError(null);

        const headers = {
          Authorization: `Bearer ${AUTH_TOKEN}`,
        };

        // Portfolio
        const portfolioRes = await fetch(
          `${API_BASE}/reports/portfolio?year=${year}&month=${month}`,
          { headers }
        );
        if (!portfolioRes.ok) {
          throw new Error(`Portfolio error: ${portfolioRes.status}`);
        }
        const portfolioJson =
          (await portfolioRes.json()) as PortfolioReportResponse;

        // Dream Big (DRE001)
        const dreRes = await fetch(
          `${API_BASE}/reports/hotel?property_code=${encodeURIComponent(
            DRE_CODE
          )}&year=${year}&month=${month}`,
          { headers }
        );
        const dreJson = dreRes.ok
          ? ((await dreRes.json()) as HotelReportResponse)
          : null;

        // N&N (N&N002) — need encodeURIComponent for "&"
        const nnRes = await fetch(
          `${API_BASE}/reports/hotel?property_code=${encodeURIComponent(
            NN_CODE
          )}&year=${year}&month=${month}`,
          { headers }
        );
        const nnJson = nnRes.ok
          ? ((await nnRes.json()) as HotelReportResponse)
          : null;

        setPortfolio(portfolioJson);
        setDre(dreJson);
        setNn(nnJson);
      } catch (err: any) {
        console.error(err);
        setError(err.message || "Failed to load reports");
      } finally {
        setLoading(false);
      }
    }

    fetchAll();
  }, [year, month]);

  if (loading) {
    return (
      <div style={{ padding: "1rem" }}>
        Loading monthly reports for {monthLabel}…
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "1rem", color: "red" }}>
        Error loading reports: {error}
      </div>
    );
  }

  if (!portfolio) {
    return <div style={{ padding: "1rem" }}>No portfolio data.</div>;
  }

  const summary = portfolio.report.summary;
  const perHotel = portfolio.report.per_hotel || [];

  const formatNumber = (value: number) =>
    value.toLocaleString("en-US", { maximumFractionDigits: 2 });

  const formatPercent = (value: number) => (value * 100).toFixed(1) + "%";

  return (
    <div style={{ padding: "1.5rem", fontFamily: "system-ui, sans-serif" }}>
      <h1 style={{ fontSize: "1.8rem", marginBottom: "0.5rem" }}>
        Guzo Guest Assist – Monthly Portfolio Report
      </h1>
      <p style={{ marginBottom: "1rem", color: "#555" }}>
        Period: {portfolio.report.period.start_date} →{" "}
        {portfolio.report.period.end_date}
      </p>

      {/* KPI Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <KpiCard label="Bookings" value={summary.bookings_count.toString()} />
        <KpiCard
          label="Room Nights"
          value={formatNumber(summary.room_nights_sold)}
        />
        <KpiCard
          label="Room Revenue (ETB)"
          value={formatNumber(summary.room_revenue_etb)}
        />
        <KpiCard label="ADR (ETB)" value={formatNumber(summary.adr)} />
        <KpiCard label="RevPAR (ETB)" value={formatNumber(summary.revpar)} />
        <KpiCard
          label="Occupancy"
          value={formatPercent(summary.occupancy_pct)}
        />
      </div>

      {/* Per-hotel table */}
      <h2 style={{ fontSize: "1.4rem", marginBottom: "0.5rem" }}>
        Performance by Hotel – {monthLabel}
      </h2>
      {perHotel.length === 0 ? (
        <p style={{ color: "#777" }}>No hotel data for this month.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              marginBottom: "1.5rem",
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
              {perHotel.map((h) => (
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
      )}

      {/* Individual hotel sections */}
      <h2 style={{ fontSize: "1.4rem", marginBottom: "0.5rem" }}>
        Individual Hotels
      </h2>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "1rem",
        }}
      >
        {dre && (
          <HotelSummaryCard
            title="Dream Big Hotel (DRE001)"
            data={dre.summary}
          />
        )}
        {nn && (
          <HotelSummaryCard
            title="N&N Luxury Hotel (N&N002)"
            data={nn.summary}
          />
        )}
      </div>
    </div>
  );
};

type KpiCardProps = { label: string; value: string };

const KpiCard: React.FC<KpiCardProps> = ({ label, value }) => (
  <div
    style={{
      borderRadius: "0.75rem",
      border: "1px solid #e2e2e2",
      padding: "0.9rem",
      backgroundColor: "#fff",
      boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
    }}
  >
    <div
      style={{
        fontSize: "0.85rem",
        color: "#777",
        marginBottom: "0.25rem",
      }}
    >
      {label}
    </div>
    <div style={{ fontSize: "1.3rem", fontWeight: 600 }}>{value}</div>
  </div>
);

type HotelSummaryCardProps = {
  title: string;
  data: PerHotelRow;
};

const HotelSummaryCard: React.FC<HotelSummaryCardProps> = ({ title, data }) => {
  const formatNumber = (value: number) =>
    value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  const formatPercent = (value: number) => (value * 100).toFixed(1) + "%";

  return (
    <div
      style={{
        borderRadius: "0.75rem",
        border: "1px solid #e2e2e2",
        padding: "1rem",
        backgroundColor: "#fff",
        boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
      }}
    >
      <h3 style={{ fontSize: "1.05rem", marginBottom: "0.5rem" }}>{title}</h3>
      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          fontSize: "0.9rem",
        }}
      >
        <li>Bookings: {data.bookings_count}</li>
        <li>Room nights: {formatNumber(data.room_nights_sold)}</li>
        <li>Revenue (ETB): {formatNumber(data.room_revenue_etb)}</li>
        <li>ADR: {formatNumber(data.adr)}</li>
        <li>RevPAR: {formatNumber(data.revpar)}</li>
        <li>Occupancy: {formatPercent(data.occupancy_pct)}</li>
      </ul>
    </div>
  );
};

const Th: React.FC<{ children: React.ReactNode }> = ({ children }) => (
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

const Td: React.FC<{ children: React.ReactNode }> = ({ children }) => (
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
