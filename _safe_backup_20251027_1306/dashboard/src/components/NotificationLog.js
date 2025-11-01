import React, { useEffect, useState } from "react";
import axios from "axios";

export default function NotificationLog() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    axios.get("http://127.0.0.1:8000/notifications") // Backend API
      .then(res => setLogs(res.data))
      .catch(err => console.error("Failed to fetch notifications:", err));
  }, []);

  return (
    <div className="p-4 bg-white shadow rounded-lg mt-6">
      <h2 className="text-lg font-bold mb-4">🔔 Notification Log</h2>
      <ul>
        {logs.map((log, i) => (
          <li key={i} className="border-b py-2">
            {log.Guest} | {log.Contact} | {log.Channel} | {log.Status}
          </li>
        ))}
      </ul>
    </div>
  );
}
