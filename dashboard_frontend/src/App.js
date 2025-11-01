import React from "react";
import BookingTable from "./components/BookingTable";

function App() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-2xl font-bold mb-6">📊 Guzo Dashboard</h1>
      <BookingTable />
    </div>
  );
}

export default App;
