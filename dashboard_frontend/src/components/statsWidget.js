import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";

const sampleData = [
  { date: "2025-09-25", bookings: 4 },
  { date: "2025-09-26", bookings: 6 },
  { date: "2025-09-27", bookings: 3 },
  { date: "2025-09-28", bookings: 5 },
];

export default function StatsWidget() {
  return (
    <div className="p-4 bg-white shadow rounded-lg mt-6">
      <h2 className="text-lg font-bold mb-4">📈 Booking Trends</h2>
      <LineChart width={500} height={300} data={sampleData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="bookings" stroke="#3b82f6" />
      </LineChart>
    </div>
  );
}
