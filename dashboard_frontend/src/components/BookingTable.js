import React, { useEffect, useState } from "react";
import axios from "axios";

export default function BookingTable() {
  const [bookings, setBookings] = useState([]);

  useEffect(() => {
    axios.get("http://127.0.0.1:8000/bookings") // API endpoint from backend
      .then(res => setBookings(res.data))
      .catch(err => console.error("Failed to fetch bookings:", err));
  }, []);

  return (
    <div className="p-4 bg-white shadow rounded-lg">
      <h2 className="text-lg font-bold mb-4">Recent Bookings</h2>
      <table className="w-full table-auto border-collapse">
        <thead>
          <tr className="bg-gray-100">
            <th className="p-2 text-left">Guest</th>
            <th className="p-2 text-left">Hotel</th>
            <th className="p-2 text-left">Check-in</th>
            <th className="p-2 text-left">Check-out</th>
            <th className="p-2 text-left">Status</th>
          </tr>
        </thead>
        <tbody>
          {bookings.map((b, i) => (
            <tr key={i} className="border-b">
              <td className="p-2">{b["Guest Name"]}</td>
              <td className="p-2">{b["Hotel Name"]}</td>
              <td className="p-2">{b["Check-in"]}</td>
              <td className="p-2">{b["Check-out"]}</td>
              <td className="p-2">{b["Status"]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
