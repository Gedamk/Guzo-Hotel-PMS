// src/pages/FrontDeskDashboard.tsx

import React from "react";
import RoomsAvailability from "../components/RoomsAvailabilityPortfolio";
import BookingsConsole from "../components/BookingsConsole";
import FrontDeskBookings from "../components/FrontDeskBookings";
import ReportsPanel from "../components/ReportsPanel";

// Same helper as other files – business date in YYYY-MM-DD
const todayISO = (): string => {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
};

const FrontDeskDashboard: React.FC = () => {
  const businessDate = todayISO();

  return (
    <div className="frontdesk-root space-y-6">
      {/* Page header */}
      <header className="fd-header">
        <div>
          <h1 className="fd-title">Guzo – Front Desk Console</h1>
          <p className="fd-subtitle">
            Portfolio view of room division activity and today&apos;s operations.
          </p>
        </div>
        <div className="fd-header-date">
          <span className="fd-header-label">Business Date</span>
          <span className="fd-header-value">{businessDate}</span>
        </div>
      </header>
  // inside component return, ABOVE RoomsAvailability:
return (
  <div className="space-y-6">
    {/* New reports panel */}
    <ReportsPanel />

    {/* Existing Rooms availability / occupancy strip */}
    <section>
      <RoomsAvailability businessDate={businessDate} />
    </section>

    {/* ... rest of your layout ... */}
  </div>
);
      {/* Rooms availability / occupancy strip */}
      <section className="fd-section">
        <div className="fd-section-header">
          <h2 className="fd-section-title">Rooms Availability</h2>
          <span className="fd-section-chip">Live</span>
        </div>

        <RoomsAvailability businessDate={businessDate} />

        {/* Daily reports toolbar */}
        <div className="fd-reports-toolbar">
          <div>
            <span className="fd-reports-label">
              Daily Room Division Reports
            </span>
            <p className="fd-reports-caption">
              Download a snapshot for {businessDate} to share with management,
              finance, or owners.
            </p>
          </div>
          <div className="fd-reports-actions">
            <a
              className="fd-btn-export"
              href={`http://127.0.0.1:8000/reports/daily/pdf?business_date=${businessDate}`}
              target="_blank"
              rel="noreferrer"
            >
              Download PDF
            </a>

            <a
              className="fd-btn-export fd-btn-export--secondary"
              href={`http://127.0.0.1:8000/reports/daily/excel?business_date=${businessDate}`}
              target="_blank"
              rel="noreferrer"
            >
              Download Excel
            </a>
          </div>
        </div>
      </section>

      {/* Two-column layout: Operations buckets + Detailed list */}
      <section className="fd-page-grid">
  <article className="fd-page-main">
    <BookingsConsole />
  </article>
  <aside className="fd-page-side">
    <FrontDeskBookings />
  </aside>
</section>

    </div>
  );
};

export default FrontDeskDashboard;


