import './App.css'

const modules = [
  {
    title: 'Executive Dashboard',
    text: 'Live KPI cards for occupancy, rooms sold, revenue, ADR, RevPAR, arrivals, departures, and operational attention.',
  },
  {
    title: 'Front Desk',
    text: 'Arrivals, departures, in-house guests, room assignment, walk-in registration, check-in, check-out, and no-show handling.',
  },
  {
    title: 'Reservations',
    text: 'Track guest bookings from direct, website, Telegram, chatbot, OTA, and walk-in channels with clear booking status.',
  },
  {
    title: 'Housekeeping',
    text: 'Room readiness, clean/dirty status, occupied/vacant tracking, out-of-order visibility, and daily room control.',
  },
  {
    title: 'Finance & Folio',
    text: 'Guest folios, charges, payments, balances, payment methods, checkout validation, and receipt preview workflow.',
  },
  {
    title: 'Night Audit',
    text: 'Business-date control, end-of-day checks, audit status, and operational closing support for hotel teams.',
  },
  {
    title: 'Booking Assistant',
    text: 'Website, chatbot, Telegram, and front desk booking channels organized into one guest acquisition hub.',
  },
  {
    title: 'Reports',
    text: 'Daily operations summaries, channel mix, occupancy readiness, and management reporting views.',
  },
]

const workflow = [
  'Guest inquiry',
  'Availability check',
  'Reservation or walk-in',
  'Room assignment',
  'Check-in',
  'Folio and payment',
  'Housekeeping update',
  'Night audit and reports',
]

const channels = [
  {
    name: 'Website Booking',
    status: 'Guest-facing',
    detail: 'Guests can start booking from a public website and connect to hotel availability workflows.',
  },
  {
    name: 'Chatbot Booking',
    status: 'Prototype live',
    detail: 'Embedded chat can collect booking intent and check property-level availability through backend sessions.',
  },
  {
    name: 'Telegram Booking',
    status: 'Backend connected',
    detail: 'Telegram bot integration supports guest conversations while tokens stay backend-only.',
  },
  {
    name: 'Front Desk Walk-In',
    status: 'Operational',
    detail: 'Hotel agents can register walk-in guests with room, dates, amount, and payment method.',
  },
]

export default function GuzoLandingPage() {
  return (
    <main className="site-shell">
      <header className="hero-section">
        <nav className="top-nav">
          <div className="brand-block">
            <span className="brand-mark">G</span>
            <div>
              <strong>Guzo Guest Assist PMS</strong>
              <small>Hotel operations • Guest booking • Front desk control</small>
            </div>
          </div>

          <div className="nav-actions">
            <a href="#modules">Modules</a>
            <a href="#booking">Booking Channels</a>
            <a href="#workflow">Workflow</a>
          </div>
        </nav>

        <section className="hero-grid">
          <div className="hero-copy">
            <span className="eyebrow">Global hotel operations platform</span>
            <h1>Run hotel operations with clarity from booking to night audit.</h1>
            <p>
              Guzo Guest Assist PMS is a modern hotel operations and guest acquisition
              platform for front desk, reservations, housekeeping, finance, night audit,
              and digital booking channels.
            </p>

            <div className="hero-buttons">
              <a className="primary-button" href="http://127.0.0.1:5173/">
                View PMS Demo
              </a>
              <a className="secondary-button" href="#booking">
                Explore Booking Assistant
              </a>
            </div>

            <div className="hero-highlights">
              <span>Front desk workflow</span>
              <span>Live dashboard data</span>
              <span>Telegram booking</span>
              <span>Finance & folio control</span>
            </div>
          </div>

          <div className="hero-card">
            <div className="mini-dashboard-header">
              <div>
                <small>Dream Big Hotel</small>
                <strong>Today’s operation</strong>
              </div>
              <span className="status-pill">Live PMS</span>
            </div>

            <div className="metric-grid">
              <div>
                <small>Occupancy</small>
                <strong>Property-aware</strong>
              </div>
              <div>
                <small>Rooms</small>
                <strong>Status board</strong>
              </div>
              <div>
                <small>Bookings</small>
                <strong>Multi-channel</strong>
              </div>
              <div>
                <small>Audit</small>
                <strong>Business date</strong>
              </div>
            </div>

            <div className="operation-list">
              <p><span /> Arrivals, departures, and in-house guests</p>
              <p><span /> Walk-in registration and payment capture</p>
              <p><span /> Housekeeping readiness and room control</p>
              <p><span /> Telegram, chatbot, website, and direct sources</p>
            </div>
          </div>
        </section>
      </header>

      <section className="content-section problem-section">
        <div>
          <span className="section-label">The hotel problem</span>
          <h2>Too many tools. Not enough operational clarity.</h2>
        </div>
        <div className="problem-grid">
          <article>Bookings arrive from phone, website, Telegram, WhatsApp, walk-ins, and OTAs.</article>
          <article>Front desk teams switch between paper, spreadsheets, messages, and disconnected systems.</article>
          <article>Room readiness, payments, folios, reports, and night audit can become hard to control.</article>
        </div>
      </section>

      <section className="content-section solution-section">
        <div className="solution-card">
          <span className="section-label">The Guzo solution</span>
          <h2>One workflow for guest booking and hotel operations.</h2>
          <p>
            Guzo connects reservations, front desk, housekeeping, finance, reports,
            and digital guest channels into one property-aware PMS workflow. It is
            designed for hotel teams that need practical control, clean dashboards,
            and modern guest acquisition.
          </p>
        </div>
      </section>

      <section id="modules" className="content-section">
        <div className="section-heading">
          <span className="section-label">Core PMS modules</span>
          <h2>Built around real hotel daily operations.</h2>
        </div>

        <div className="module-grid">
          {modules.map((module) => (
            <article className="module-card" key={module.title}>
              <h3>{module.title}</h3>
              <p>{module.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="booking" className="content-section booking-section">
        <div className="section-heading">
          <span className="section-label">Guest acquisition</span>
          <h2>Website, chatbot, Telegram, and desk bookings in one PMS view.</h2>
          <p>
            Every reservation should have a clear source: direct, website, Telegram,
            chatbot, OTA, or walk-in. Guzo helps hotel teams understand where guests
            come from and how bookings move into operations.
          </p>
        </div>

        <div className="channel-grid">
          {channels.map((channel) => (
            <article className="channel-card" key={channel.name}>
              <div className="channel-card-header">
                <h3>{channel.name}</h3>
                <span>{channel.status}</span>
              </div>
              <p>{channel.detail}</p>
            </article>
          ))}
        </div>

        <div className="security-note">
          <strong>Security note:</strong> Telegram bot tokens, API keys, database passwords,
          and private credentials stay backend-only. The frontend should show safe
          integration status, never secret values.
        </div>
      </section>

      <section id="workflow" className="content-section workflow-section">
        <div className="section-heading">
          <span className="section-label">Hotel workflow</span>
          <h2>From guest inquiry to daily closing.</h2>
        </div>

        <div className="workflow-line">
          {workflow.map((step, index) => (
            <div className="workflow-step" key={step}>
              <span>{index + 1}</span>
              <p>{step}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="content-section hospitality-section">
        <div>
          <span className="section-label">Hospitality positioning</span>
          <h2>Designed for hotels, guest houses, boutique properties, and growing hospitality businesses.</h2>
        </div>
        <p>
          Guzo is built with hospitality operations in mind, including properties in Ethiopia
          and teams that want global hotel-standard workflows: business date control,
          front desk discipline, housekeeping coordination, payment visibility, and
          guest booking channels.
        </p>
      </section>

      <section className="content-section tech-section">
        <div className="section-heading">
          <span className="section-label">Technology foundation</span>
          <h2>Modern, practical, and property-aware.</h2>
        </div>

        <div className="tech-grid">
          <article><strong>React + Vite</strong><p>Fast frontend experience for PMS screens and website pages.</p></article>
          <article><strong>FastAPI backend</strong><p>Hotel operations APIs for rooms, bookings, folios, reports, and integrations.</p></article>
          <article><strong>PostgreSQL</strong><p>Structured hotel data for reservations, rooms, finance, and audit workflows.</p></article>
          <article><strong>Telegram + chatbot</strong><p>Digital guest booking channels connected safely through backend services.</p></article>
        </div>
      </section>

      <section className="final-cta">
        <span className="section-label">Ready for hotel operations</span>
        <h2>Run hotel operations with clarity.</h2>
        <p>
          Bring bookings, room readiness, front desk actions, payments, and reporting
          into one connected workflow.
        </p>
        <div className="hero-buttons">
          <a className="primary-button" href="http://127.0.0.1:5173/">
            Open PMS Dashboard
          </a>
          <a className="secondary-button" href="mailto:info@guzo.example">
            Contact / Request Demo
          </a>
        </div>
      </section>

      <footer className="site-footer">
        <strong>Guzo Guest Assist PMS</strong>
        <span>Hotel operations • Guest booking • Front desk control • Digital hospitality</span>
      </footer>
    </main>
  )
}
