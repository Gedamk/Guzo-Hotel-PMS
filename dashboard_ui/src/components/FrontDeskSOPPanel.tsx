// src/components/FrontDeskSOPPanel.tsx
import React from "react";

const FrontDeskSOPPanel: React.FC = () => {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-xs text-slate-200 shadow-lg shadow-black/40 sm:p-5 lg:p-6">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            Front Office SOP
          </p>
          <h2 className="text-sm font-semibold text-slate-50 sm:text-base">
            24/7 Front Desk Operations with PMS
          </h2>
        </div>
        <span className="hidden rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-[11px] text-slate-300 sm:inline">
          Training &amp; best practice
        </span>
      </div>

      <div className="mt-4 space-y-2">
        <h3 className="text-xs font-semibold text-slate-100">
          1. Core 24/7 front desk workflow (every shift)
        </h3>
        <ul className="list-disc space-y-1 pl-4">
          <li>
            <span className="font-semibold">Start of shift:</span> read the
            handover log, log into PMS, verify{" "}
            <span className="font-semibold">business date</span> and house
            count.
          </li>
          <li>
            <span className="font-semibold">Arrivals:</span> review today&apos;s
            arrivals, room types, rates, payment methods, and special requests.
            Pre-assign rooms where needed.
          </li>
          <li>
            <span className="font-semibold">Check-ins:</span> verify ID, nights,
            rate, and payment, assign room, encode keys, and set status to{" "}
            <span className="font-semibold">In-house</span>.
          </li>
          <li>
            <span className="font-semibold">In-house management:</span> handle
            room moves, messages, packages, and incidents in the PMS.
          </li>
          <li>
            <span className="font-semibold">Departures:</span> prepare folios,
            post final charges, settle the bill, and mark rooms as checked-out
            and vacant/dirty.
          </li>
          <li>
            <span className="font-semibold">No-shows &amp; cancellations:</span>{" "}
            mark no-shows at cut-off time, post fees, and free up inventory.
          </li>
          <li>
            <span className="font-semibold">Future bookings:</span> check
            upcoming arrivals, groups, and busy dates for forecasting.
          </li>
          <li>
            <span className="font-semibold">End of shift:</span> close cashier,
            review reports, write handover notes, and log out.
          </li>
        </ul>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            Morning Shift
          </p>
          <p className="text-xs font-semibold text-slate-50">
            Example: 07:00 – 15:00
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-[11px]">
            <li>Confirm night audit and business date.</li>
            <li>Prepare and manage departures and payments.</li>
            <li>
              Coordinate early check-ins and room readiness with Housekeeping.
            </li>
            <li>Handle walk-ins, extensions, and day-use.</li>
            <li>Run late-morning house count and occupancy check.</li>
          </ul>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            Evening Shift
          </p>
          <p className="text-xs font-semibold text-slate-50">
            Example: 15:00 – 23:00
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-[11px]">
            <li>Review handover: VIPs, groups, complaints, pending items.</li>
            <li>Handle main wave of check-ins and upsell opportunities.</li>
            <li>
              Follow up on in-house guest requests and room moves in the PMS.
            </li>
            <li>Monitor overbookings, walk-ins, and potential walk-outs.</li>
            <li>Clean up data before night audit.</li>
          </ul>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            Night Shift
          </p>
          <p className="text-xs font-semibold text-slate-50">
            Example: 23:00 – 07:00
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-[11px]">
            <li>Verify all arrivals and departures are posted correctly.</li>
            <li>Mark no-shows and apply fees according to policy.</li>
            <li>Post remaining manual charges from outlets if any.</li>
            <li>Run night audit, close the business date, and send reports.</li>
            <li>Pre-assign rooms for next-day VIPs and groups.</li>
          </ul>
        </div>
      </div>

      <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3 text-[11px] text-slate-300 sm:px-4">
        <p className="font-semibold text-slate-100">
          How this links to your Guzo Front Desk Console
        </p>
        <p className="mt-1">
          Use <span className="font-semibold">Arrivals</span> for check-ins,{" "}
          <span className="font-semibold">In-house</span> for active guests,{" "}
          <span className="font-semibold">Departures</span> for folio control,
          and <span className="font-semibold">Future bookings</span> for
          forecasting. The console becomes your daily control panel for 24/7
          front desk operations.
        </p>
      </div>
    </section>
  );
};

export default FrontDeskSOPPanel;

