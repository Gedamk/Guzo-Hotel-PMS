export default function GuzoAIPlatformPage() {
  const modules = [
    ["FD", "Front Desk", "Arrivals, departures, in-house guests, check-in, check-out, and room assignment."],
    ["RS", "Reservations", "Booking requests, room availability, no-shows, guest details, and reservation support."],
    ["HK", "Housekeeping", "Room status, task suggestions, cleaning priorities, maintenance flags, and staff coordination."],
    ["FO", "Folio & Cashier", "Charges, payments, balances, cashier controls, and guest account visibility."],
    ["NA", "Night Audit", "Warnings, open balances, pending arrivals, no-shows, and daily close readiness."],
    ["RP", "Reports", "Daily manager summaries, occupancy, revenue, operational exceptions, and performance trends."],
    ["FB", "F&B Cost Control", "Food and beverage cost awareness connected to hotel finance and management reporting."],
    ["AD", "Admin & Roles", "Property-aware configuration, staff roles, secure access, and hotel owner controls."],
  ];

  const feed = [
    ["WA", "Guest booking request", "AI prepares dates, room type, guest count, and PMS note.", "Booking", "teal"],
    ["IG", "Social media question", "AI answers hotel and PMS questions, then routes demo interest.", "Social", "amber"],
    ["FD", "Front desk support", "AI summarizes arrivals, departures, room status, and no-shows.", "Staff", "coral"],
    ["NA", "Night audit warning", "AI flags pending balances and exceptions before daily close.", "Audit", "teal"],
  ];

  return (
    <main className="min-h-screen bg-[#eef3f5] text-[#101820]">
      <section
        id="top"
        className="relative flex min-h-[92vh] flex-col overflow-hidden bg-[#102027] text-white"
        style={{
          backgroundImage:
            'linear-gradient(90deg, rgba(8,18,24,.92) 0%, rgba(8,18,24,.76) 38%, rgba(8,18,24,.16) 78%), url("/assets/guzo-ai-hotel-ops.png"), linear-gradient(135deg, #102027 0%, #254047 45%, #b9c8c6 100%)',
          backgroundPosition: "center",
          backgroundSize: "cover",
        }}
      >
        <nav className="mx-auto flex w-[min(1180px,calc(100%-40px))] items-center justify-between gap-5 py-6">
          <a className="flex items-center gap-3 font-extrabold" href="#top" aria-label="Guzo PMS home">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#0f766e] shadow-lg">G</span>
            <span>Guzo PMS</span>
          </a>
          <div className="hidden items-center gap-6 text-sm text-white/80 md:flex">
            <a href="#modules">Modules</a>
            <a href="#agent">AI Agent</a>
            <a href="#guest-platform">Guest Platform</a>
            <a href="#demo">Demo</a>
          </div>
          <div className="flex items-center gap-2.5">
            <a className="hidden min-h-11 items-center rounded-lg border border-white/30 bg-white/10 px-4 text-sm font-bold sm:inline-flex" href="/login">
              Log in
            </a>
            <a className="inline-flex min-h-11 items-center rounded-lg bg-[#d5962c] px-4 text-sm font-extrabold text-[#15110a]" href="#demo">
              Request demo
            </a>
          </div>
        </nav>

        <div className="mx-auto grid w-[min(1180px,calc(100%-40px))] flex-1 grid-cols-1 items-center gap-10 py-14 lg:grid-cols-[1fr_minmax(340px,430px)]">
          <div>
            <span className="inline-flex rounded-full border border-white/15 bg-[#0f766e]/30 px-3 py-2 text-sm font-bold text-[#e7f4f1]">
              AI Agent + Landing Page + Secure PMS Dashboard
            </span>
            <h1 className="my-5 max-w-3xl text-[42px] font-black leading-none md:text-[72px]">Guzo PMS</h1>
            <p className="max-w-2xl text-lg leading-8 text-white/80">
              A hotel operating platform where guests, staff, owners, and social channels connect through one AI-powered property management workflow.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <a className="inline-flex min-h-11 items-center rounded-lg bg-[#d5962c] px-4 text-sm font-extrabold text-[#15110a]" href="#agent">
                Chat with Guzo AI
              </a>
              <a className="inline-flex min-h-11 items-center rounded-lg border border-white/30 bg-white/10 px-4 text-sm font-bold" href="#modules">
                Explore PMS modules
              </a>
            </div>
            <div className="mt-8 grid max-w-2xl grid-cols-1 gap-3 sm:grid-cols-3">
              {[
                ["3-way", "Guest, staff, and owner connection"],
                ["24/7", "AI hotel assistant readiness"],
                ["PMS", "Reservations, rooms, folios, reports"],
              ].map(([value, label]) => (
                <div className="rounded-lg border border-white/20 bg-white/10 p-4 backdrop-blur" key={value}>
                  <strong className="block text-2xl leading-none">{value}</strong>
                  <span className="mt-2 block text-sm leading-5 text-white/70">{label}</span>
                </div>
              ))}
            </div>
          </div>

          <aside id="agent" className="overflow-hidden rounded-lg border border-white/60 bg-white/95 text-[#101820] shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#d8dee7] px-5 py-4">
              <div className="flex items-center gap-3 font-extrabold">
                <span className="h-2.5 w-2.5 rounded-full bg-[#18a058] shadow-[0_0_0_6px_rgba(24,160,88,.14)]" />
                Guzo AI Hotel Agent
              </div>
              <span className="text-xs font-extrabold uppercase text-[#0f766e]">Connected</span>
            </div>
            <div className="grid gap-3 bg-[#f8fafb] p-5 text-sm leading-6">
              <div className="ml-auto max-w-[86%] rounded-lg bg-[#0b4f4a] px-4 py-3 text-white">Do we have standard rooms for July 18 to 20?</div>
              <div className="max-w-[86%] rounded-lg border border-[#d8dee7] bg-white px-4 py-3">
                I checked the PMS. Standard rooms are available. I can create a pending booking request and notify the front desk.
              </div>
              <div className="ml-auto max-w-[86%] rounded-lg bg-[#0b4f4a] px-4 py-3 text-white">Also summarize today for the manager.</div>
              <div className="max-w-[86%] rounded-lg border border-[#d8dee7] bg-white px-4 py-3">
                Arrivals, departures, in-house guests, housekeeping status, and night audit warnings are ready for review.
              </div>
            </div>
            <div className="grid grid-cols-1 gap-2.5 bg-[#f8fafb] px-5 pb-5 sm:grid-cols-2">
              {["Check availability", "Create request", "Show arrivals", "Summarize reports"].map((action) => (
                <span className="grid min-h-11 place-items-center rounded-lg border border-[#d8dee7] bg-white text-sm font-bold" key={action}>
                  {action}
                </span>
              ))}
            </div>
          </aside>
        </div>
      </section>

      <section id="modules" className="mx-auto w-[min(1180px,calc(100%-40px))] py-20">
        <div className="mb-8 flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <h2 className="max-w-3xl text-3xl font-black leading-tight md:text-5xl">Global-standard PMS workflows for modern hotels.</h2>
          <p className="max-w-md leading-7 text-[#5b6675]">
            Guzo starts with the operational work hotels run every day, then adds an AI agent that can explain, summarize, and eventually perform secure PMS actions.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
          {modules.map(([code, title, copy]) => (
            <article className="min-h-40 rounded-lg border border-[#d8dee7] bg-white p-5" key={title}>
              <div className="mb-4 grid h-10 w-10 place-items-center rounded-lg bg-[#e8f4f2] font-black text-[#0b4f4a]">{code}</div>
              <h3 className="mb-2 text-lg font-extrabold">{title}</h3>
              <p className="text-sm leading-6 text-[#5b6675]">{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-[#d8dee7] bg-white">
        <div className="mx-auto w-[min(1180px,calc(100%-40px))] py-20">
          <div className="mb-8 flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
            <h2 className="max-w-3xl text-3xl font-black leading-tight md:text-5xl">The bridge between guests, hotel teams, and PMS data.</h2>
            <p className="max-w-md leading-7 text-[#5b6675]">
              The landing page is the front door, the chat box is the conversation, and the AI agent is the smart worker connected to Guzo PMS.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-3">
            {[
              ["Guest ↔ AI Agent ↔ Guzo PMS", "Answer guest questions, collect booking requests, check room availability, and keep front desk teams informed."],
              ["Staff ↔ AI Agent ↔ PMS Data", "Support reservations, housekeeping, front desk, folio, reports, and night audit workflows from one interface."],
              ["Owner ↔ Website ↔ Demo Contact", "Present the business value of Guzo PMS, route demo interest, and support hotel decision makers."],
            ].map(([title, copy]) => (
              <article className="rounded-lg border border-[#d8dee7] bg-[#f7f9fb] p-6" key={title}>
                <b className="mb-2 block text-lg text-[#0b4f4a]">{title}</b>
                <p className="leading-7 text-[#5b6675]">{copy}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="guest-platform" className="mx-auto grid w-[min(1180px,calc(100%-40px))] grid-cols-1 gap-8 py-20 lg:grid-cols-[.9fr_1.1fr]">
        <div>
          <h2 className="text-3xl font-black leading-tight md:text-5xl">Built for social media and guest connection.</h2>
          <p className="mt-4 max-w-md leading-7 text-[#5b6675]">
            Guzo can become the public guest platform for hotel questions, demo requests, booking intent, and staff follow-up across web and social channels.
          </p>
          <div className="mt-7 grid gap-3.5">
            {[
              ["1", "Landing page first", "Show Guzo PMS features, modules, hotel value, demo request, and PMS login."],
              ["2", "Chatbot second", "Answer what Guzo PMS is, pricing questions, demo questions, and module explanations."],
              ["3", "AI agent third", "Connect to backend APIs for availability, pending bookings, arrivals, room status, reports, and audit alerts."],
            ].map(([number, title, copy]) => (
              <article className="grid grid-cols-[42px_1fr] gap-4 rounded-lg border border-[#d8dee7] bg-white p-5" key={number}>
                <div className="grid h-11 w-11 place-items-center rounded-lg bg-[#0f766e] font-extrabold text-white">{number}</div>
                <div>
                  <h3 className="mb-1 text-lg font-extrabold">{title}</h3>
                  <p className="leading-7 text-[#5b6675]">{copy}</p>
                </div>
              </article>
            ))}
          </div>
        </div>

        <aside className="rounded-lg bg-[#111b22] p-6 text-white shadow-2xl">
          <div className="mb-5 flex justify-between gap-4">
            <h3 className="text-2xl font-black">Guest connection inbox</h3>
            <span className="h-fit rounded-full bg-[#bff3cc] px-3 py-1.5 text-xs font-extrabold text-[#14351f]">Live-ready</span>
          </div>
          <div className="grid gap-2.5">
            {feed.map(([code, title, copy, tag, color]) => (
              <div className="grid grid-cols-[44px_1fr] items-center gap-3 rounded-lg border border-white/10 bg-white/10 p-3 sm:grid-cols-[44px_1fr_auto]" key={title}>
                <div
                  className={`grid h-11 w-11 place-items-center rounded-lg font-black ${
                    color === "amber" ? "bg-[#d5962c] text-[#21180a]" : color === "coral" ? "bg-[#c75b4f]" : "bg-[#0f766e]"
                  }`}
                >
                  {code}
                </div>
                <div>
                  <strong className="block">{title}</strong>
                  <span className="mt-1 block text-sm text-white/65">{copy}</span>
                </div>
                <span className="w-fit rounded-full border border-[#6c9eff]/30 bg-[#2d6cdf]/20 px-2.5 py-1.5 text-xs font-extrabold text-[#d9e9ff]">{tag}</span>
              </div>
            ))}
          </div>
        </aside>
      </section>

      <section id="demo" className="bg-[#0f1a20] text-white">
        <div className="mx-auto flex w-[min(1180px,calc(100%-40px))] flex-col justify-between gap-8 py-16 lg:flex-row lg:items-center">
          <div>
            <h2 className="max-w-3xl text-3xl font-black leading-tight md:text-5xl">Launch Guzo as a landing page now, then grow it into the hotel AI agent.</h2>
            <p className="mt-3 max-w-2xl leading-7 text-white/70">
              Start with demo capture, PMS module storytelling, guest questions, and staff login. Then connect secure backend actions when the APIs are ready.
            </p>
          </div>
          <a className="inline-flex min-h-11 w-fit items-center rounded-lg bg-[#d5962c] px-4 text-sm font-extrabold text-[#15110a]" href="mailto:demo@guzopms.com?subject=Guzo%20PMS%20Demo%20Request">
            Request demo
          </a>
        </div>
      </section>
    </main>
  );
}
