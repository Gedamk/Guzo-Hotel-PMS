import React from "react";
import "./App.css";

import BookingTable from "./components/BookingTable";
import MonthlyPortfolioDashboard from "./components/MonthlyPortfolioDashboard";

function App() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Top title */}
      <h1 className="text-2xl font-bold mb-6">📊 Guzo Dashboard</h1>

      <div className="space-y-6">
        {/* Portfolio Dashboard */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <MonthlyPortfolioDashboard year={2025} month={11} />
        </div>

        {/* Booking Table */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h2 className="text-lg font-semibold mb-4">📅 Live Bookings</h2>
          <BookingTable />
        </div>
      </div>
    </div>
  );
}

export default App;
