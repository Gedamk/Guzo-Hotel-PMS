// src/App.tsx
import React from "react";
import FrontDeskConsole from "./components/FrontDeskConsole";
import HousekeepingBoard from "./components/HousekeepingBoard";

function App() {
  return (
    <div className="min-h-screen bg-slate-100">
      {/* App shell */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div>
            <h1 className="text-base font-semibold text-slate-900">
              Guzo Guest Assist – Portfolio Console
            </h1>
            <p className="text-xs text-slate-500">
              Front Desk &amp; Housekeeping live overview for all properties.
            </p>
          </div>
          <div className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-medium text-slate-600">
            Demo Environment
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6">
        {/* Front Desk – arrivals / in-house / departures */}
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="mb-2 text-sm font-semibold text-slate-900">
            Front Desk – Room Division Console
          </h2>
          <p className="mb-4 text-xs text-slate-500">
            Manage arrivals, in-house guests, departures, and assign rooms.
          </p>
          <FrontDeskConsole />
        </section>

        {/* Housekeeping Board – room status per floor/property */}
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="mb-2 text-sm font-semibold text-slate-900">
            Housekeeping Board
          </h2>
          <p className="mb-4 text-xs text-slate-500">
            Live room status by property, floor, and housekeeping status.
          </p>
          <HousekeepingBoard />
        </section>
      </main>
    </div>
  );
}

export default App;
