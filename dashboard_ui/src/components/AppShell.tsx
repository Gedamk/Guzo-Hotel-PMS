import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import FrontDeskConsole from "./FrontDeskConsole";
import RoomsAvailability from "./RoomsAvailability";
import PortfolioDashboard from "./PortfolioDashboard";
import FrontDeskFooter from "./Footer/FrontDeskFooter";

type ViewKey = "frontdesk" | "rooms" | "portfolio" | "reports";

const AppShell: React.FC = () => {
  const todayBusinessDate = new Date().toISOString().slice(0, 10);

  const [activeView, setActiveView] = React.useState<ViewKey>("frontdesk");

  const renderView = () => {
    switch (activeView) {
      case "rooms":
        return <RoomsAvailability businessDate={todayBusinessDate} />;
      case "portfolio":
        return <PortfolioDashboard />;
      case "reports":
        return <PortfolioDashboard />;
      case "frontdesk":
      default:
        return <FrontDeskConsole />;
    }
  };

  return (
    <BrowserRouter>
      <div className="flex h-screen flex-col bg-slate-950 text-slate-50">
        {/* Top bar */}
        <header className="flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-4 py-2 lg:px-6">
          {/* Left: brand */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/10 ring-1 ring-emerald-500/40">
              <span className="text-sm font-semibold text-emerald-400">GZ</span>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.16em] text-slate-400">
                Guzo Guest Assist
              </p>
              <p className="text-sm font-semibold">Front Office · PMS Console</p>
            </div>
          </div>

          {/* Center: property + business date */}
          <div className="hidden items-center gap-3 text-xs text-slate-300 md:flex">
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400">Property</span>
              <select className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs">
                <option>All Properties</option>
                <option>Dream Big Hotel (DRE001)</option>
                <option>N&N Luxury (N&N002)</option>
              </select>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400">Business Date</span>
              <span className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1">
                {todayBusinessDate}
              </span>
            </div>
          </div>

          {/* Right: search + agent */}
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs text-slate-300 sm:flex">
              <span className="text-slate-500">🔍</span>
              <input
                type="text"
                placeholder="Search guest, room, booking code..."
                className="bg-transparent text-xs outline-none placeholder:text-slate-500"
              />
            </div>
            <div className="flex items-center gap-2 rounded-full border border-emerald-500/50 bg-emerald-500/10 px-3 py-1 text-xs">
              <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400" />
              <span className="font-medium">Front Desk Agent</span>
              <span className="text-slate-300">· Shift: Live · Online</span>
              <span className="ml-1 rounded-full bg-slate-900 px-1.5 text-[10px]">
                FD
              </span>
            </div>
          </div>
        </header>

        <div className="flex flex-1 overflow-hidden">
          {/* Left nav / sidebar */}
          <aside className="flex w-56 flex-col border-r border-slate-800 bg-slate-950/90 p-3 text-xs">
            <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              Navigation
            </p>

            <nav className="space-y-1">
              <button
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left ${
                  activeView === "frontdesk"
                    ? "bg-slate-800 text-emerald-300"
                    : "text-slate-200 hover:bg-slate-900"
                }`}
                onClick={() => setActiveView("frontdesk")}
              >
                <span>🛎</span>
                <span>Front Desk Console</span>
              </button>

              <button
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left ${
                  activeView === "rooms"
                    ? "bg-slate-800 text-sky-300"
                    : "text-slate-200 hover:bg-slate-900"
                }`}
                onClick={() => setActiveView("rooms")}
              >
                <span>🛏</span>
                <span>Rooms &amp; Availability</span>
              </button>

              <button
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left ${
                  activeView === "portfolio"
                    ? "bg-slate-800 text-amber-300"
                    : "text-slate-200 hover:bg-slate-900"
                }`}
                onClick={() => setActiveView("portfolio")}
              >
                <span>📊</span>
                <span>Portfolio / KPIs</span>
              </button>

              <button
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left ${
                  activeView === "reports"
                    ? "bg-slate-800 text-fuchsia-300"
                    : "text-slate-200 hover:bg-slate-900"
                }`}
                onClick={() => setActiveView("reports")}
              >
                <span>📑</span>
                <span>Reports</span>
              </button>
            </nav>
          </aside>

          {/* Main view */}
          <main className="flex-1 overflow-auto bg-slate-950 px-4 py-4 lg:px-6 lg:py-5">
            {renderView()}
          </main>
        </div>

        {/* Footer */}
        <FrontDeskFooter />
      </div>
    </BrowserRouter>
  );
};

export default AppShell;
