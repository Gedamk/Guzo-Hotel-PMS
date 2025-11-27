// dashboard_ui/src/components/ReportsPanel.tsx

import React, { useState } from "react";

const API_BASE = process.env.REACT_APP_API_BASE || "http://127.0.0.1:8000";
const AUTH_TOKEN = process.env.REACT_APP_AUTH_TOKEN || "<REDACTED_DEMO_BEARER_TOKEN>";

const todayISO = (): string => {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
};

const ReportsPanel: React.FC = () => {
  const [businessDate, setBusinessDate] = useState<string>(todayISO());
  const [month, setMonth] = useState<string>(String(new Date().getMonth() + 1).padStart(2, "0"));
  const [year, setYear] = useState<string>(String(new Date().getFullYear()));
  const [week, setWeek] = useState<string>("01");

  const openWithAuth = (url: string) => {
    // Open in a new tab with token via query param (simple approach).
    const sep = url.includes("?") ? "&" : "?";
    const full = `${url}${sep}token=${AUTH_TOKEN}`;
    window.open(full, "_blank", "noopener,noreferrer");
  };

  const handleDailyPdf = () => {
    openWithAuth(`${API_BASE}/reports/daily/pdf?business_date=${businessDate}`);
  };

  const handleDailyExcel = () => {
    openWithAuth(`${API_BASE}/reports/daily/excel?business_date=${businessDate}`);
  };

  const handleWeeklyExcel = () => {
    openWithAuth(`${API_BASE}/reports/weekly/excel?year=${year}&week=${week}`);
  };

  const handleMonthlyExcel = () => {
    openWithAuth(`${API_BASE}/reports/monthly/excel?year=${year}&month=${month}`);
  };

  return (
    <section className="fd-card" style={{ marginBottom: "1rem" }}>
      <h3 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
        📊 Guzo – Room Division Reports
      </h3>

      {/* Daily section */}
      <div style={{ marginBottom: "1rem" }}>
        <div style={{ fontSize: "0.85rem", marginBottom: "0.25rem" }}>
          <strong>Daily Report</strong> (per business date)
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
          <label style={{ fontSize: "0.8rem" }}>
            Business Date:
            <input
              type="date"
              value={businessDate}
              onChange={(e) => setBusinessDate(e.target.value)}
              style={{ marginLeft: "0.4rem", padding: "0.15rem 0.3rem", fontSize: "0.8rem" }}
            />
          </label>

          <button type="button" className="fd-btn-export" onClick={handleDailyPdf}>
            Download Daily PDF
          </button>
          <button type="button" className="fd-btn-export" onClick={handleDailyExcel}>
            Download Daily Excel
          </button>
        </div>
      </div>

      <hr style={{ border: "none", borderTop: "1px solid #e5e7eb", margin: "0.75rem 0" }} />

      {/* Weekly section */}
      <div style={{ marginBottom: "1rem" }}>
        <div style={{ fontSize: "0.85rem", marginBottom: "0.25rem" }}>
          <strong>Weekly Report</strong> (ISO week)
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
          <label style={{ fontSize: "0.8rem" }}>
            Year:
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              style={{ marginLeft: "0.4rem", width: "5rem", padding: "0.15rem 0.3rem", fontSize: "0.8rem" }}
            />
          </label>
          <label style={{ fontSize: "0.8rem" }}>
            Week (01-53):
            <input
              type="text"
              value={week}
              onChange={(e) => setWeek(e.target.value)}
              style={{ marginLeft: "0.4rem", width: "3rem", padding: "0.15rem 0.3rem", fontSize: "0.8rem" }}
            />
          </label>

          <button type="button" className="fd-btn-export" onClick={handleWeeklyExcel}>
            Download Weekly Excel
          </button>
        </div>
      </div>

      <hr style={{ border: "none", borderTop: "1px solid #e5e7eb", margin: "0.75rem 0" }} />

      {/* Monthly section */}
      <div>
        <div style={{ fontSize: "0.85rem", marginBottom: "0.25rem" }}>
          <strong>Monthly Report</strong>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
          <label style={{ fontSize: "0.8rem" }}>
            Year:
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              style={{ marginLeft: "0.4rem", width: "5rem", padding: "0.15rem 0.3rem", fontSize: "0.8rem" }}
            />
          </label>
          <label style={{ fontSize: "0.8rem" }}>
            Month:
            <select
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              style={{ marginLeft: "0.4rem", padding: "0.15rem 0.3rem", fontSize: "0.8rem" }}
            >
              {Array.from({ length: 12 }).map((_, i) => {
                const val = String(i + 1).padStart(2, "0");
                return (
                  <option key={val} value={val}>
                    {val}
                  </option>
                );
              })}
            </select>
          </label>

          <button type="button" className="fd-btn-export" onClick={handleMonthlyExcel}>
            Download Monthly Excel
          </button>
        </div>
      </div>
    </section>
  );
};

export default ReportsPanel;
