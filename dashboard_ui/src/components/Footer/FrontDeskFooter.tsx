// src/components/FrontDeskFooter.tsx
import React from "react";

const FrontDeskFooter: React.FC = () => {
  return (
    <footer className="border-t border-slate-800 bg-slate-900/90 px-4 py-2 text-[11px] text-slate-400">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <span>
          Guzo Guest Assist • Front Desk PMS • v0.1.0 (Training / Demo Mode)
        </span>
        <span className="hidden sm:inline">
          Local time: System • Business date: Today
        </span>
      </div>
    </footer>
  );
};

export default FrontDeskFooter;
