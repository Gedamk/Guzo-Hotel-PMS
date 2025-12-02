// src/components/PortfolioConsole.tsx

import React, { useState } from "react";
import FrontDeskBookings from "./FrontDeskBookings";
import HousekeepingBoard from "./HousekeepingBoard";

const PortfolioConsole: React.FC = () => {
  // Default to "today" but you can override in UI
  const [businessDate, setBusinessDate] = useState<string>("2025-12-02");

  return (
    <div className="portfolio-console">
      <header style={{ marginBottom: "1rem" }}>
        <h1>Guzo Guest Assist – Portfolio Console</h1>
        <p>Front Desk &amp; Housekeeping live overview for all properties.</p>

        <div style={{ marginTop: "0.75rem" }}>
          <label style={{ marginRight: "0.5rem" }}>
            Business Date:
            <input
              type="date"
              value={businessDate}
              onChange={(e) => setBusinessDate(e.target.value)}
              style={{ marginLeft: "0.5rem" }}
            />
          </label>
        </div>
      </header>

      <section style={{ marginBottom: "2rem" }}>
        <h2>Front Desk – Room Division Console</h2>
        <p>Manage arrivals, in-house guests, departures, and assign rooms.</p>
        <FrontDeskBookings businessDate={businessDate} />
      </section>

      <section>
        <h2>Housekeeping Board</h2>
        <p>Live room status by property, floor, and housekeeping status.</p>
        <HousekeepingBoard businessDate={businessDate} />
      </section>
    </div>
  );
};

export default PortfolioConsole;
