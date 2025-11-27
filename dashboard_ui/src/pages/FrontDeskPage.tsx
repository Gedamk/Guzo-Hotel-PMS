// src/pages/FrontDeskPage.tsx

import React from "react";
import RoomsAvailability from "../components/RoomsAvailabilityPortfolio";
import FrontDeskBookings from "../components/FrontDeskBookings";

const todayISO = (): string => {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
};

const FrontDeskPage: React.FC = () => {
  const businessDate = todayISO();

  return (
    <div className="space-y-6">
      {/* Portfolio-style rooms availability bar */}
      <RoomsAvailability businessDate={businessDate} />

      {/* Classic arrivals / in-house / departures / future tables */}
      <FrontDeskBookings />
    </div>
  );
};

export default FrontDeskPage;
