import { useState } from 'react'
import './GuzoAIPlatformPage.css'

const modules = [
  ['FD', 'Front Desk', 'Arrivals, departures, in-house guests, check-in, check-out, and room assignment.'],
  ['RS', 'Reservations', 'Booking requests, room availability, no-shows, guest details, and reservation support.'],
  ['HK', 'Housekeeping', 'Room status, task suggestions, cleaning priorities, maintenance flags, and staff coordination.'],
  ['FO', 'Folio & Cashier', 'Charges, payments, balances, cashier controls, and guest account visibility.'],
  ['NA', 'Night Audit', 'Warnings, open balances, pending arrivals, no-shows, and daily close readiness.'],
  ['RP', 'Reports', 'Daily manager summaries, occupancy, revenue, operational exceptions, and performance trends.'],
  ['FB', 'F&B Cost Control', 'Food and beverage cost awareness connected to hotel finance and management reporting.'],
  ['AD', 'Admin & Roles', 'Property-aware configuration, staff roles, secure access, and hotel owner controls.'],
]

const bridgeItems = [
  ['Guest to AI Agent to Guzo PMS', 'Answer guest questions, collect booking requests, check room availability, and keep front desk teams informed.'],
  ['Staff to AI Agent to PMS Data', 'Support reservations, housekeeping, front desk, folio, reports, and night audit workflows from one interface.'],
  ['Owner to Website to Demo Contact', 'Present the business value of Guzo PMS, route demo interest, and support hotel decision makers.'],
]

const phases = [
  ['1', 'Landing page first', 'Show Guzo PMS features, modules, hotel value, demo request, and PMS login.'],
  ['2', 'Chatbot second', 'Answer what Guzo PMS is, pricing questions, demo questions, and module explanations.'],
  ['3', 'AI agent third', 'Connect to backend APIs for availability, pending bookings, arrivals, room status, reports, and audit alerts.'],
]

const feed = [
  ['WA', 'Guest booking request', 'AI prepares dates, room type, guest count, and PMS note.', 'Booking', 'teal'],
  ['IG', 'Social media question', 'AI answers hotel and PMS questions, then routes demo interest.', 'Social', 'amber'],
  ['FD', 'Front desk support', 'AI summarizes arrivals, departures, room status, and no-shows.', 'Staff', 'coral'],
  ['NA', 'Night audit warning', 'AI flags pending balances and exceptions before daily close.', 'Audit', 'teal'],
]

const hotelNames = {
  DRE001: 'Dream Big Hotel',
  NN001: 'N&N Hotel',
}

const bookingEndpoint = '/public/booking-request'
const PUBLIC_BOOKING_ENABLED = true
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const lockedSubmissionMessage = 'Request preview prepared. This demo did not send anything to PMS; hotel staff must review availability and confirm the booking before a confirmation number is issued.'

const initialBookingDraft = {
  property_code: 'DRE001',
  channel: 'ai_platform_chatbot',
  check_in_date: '',
  check_out_date: '',
  adults: '2',
  children: '0',
  room_type: 'Deluxe',
  guest_name: '',
  guest_phone: '',
  guest_email: '',
  special_requests: '',
}

const chatbotSteps = [
  {
    key: 'property_code',
    bot: 'Welcome to Guzo. Which hotel should receive this booking request?',
    label: 'Hotel',
    type: 'select',
    options: [
      ['DRE001', 'Dream Big Hotel'],
      ['NN001', 'N&N Hotel'],
    ],
  },
  {
    key: 'check_in_date',
    bot: 'What is the check-in date?',
    label: 'Check-in Date',
    type: 'date',
  },
  {
    key: 'check_out_date',
    bot: 'What is the check-out date?',
    label: 'Check-out Date',
    type: 'date',
  },
  {
    key: 'adults',
    bot: 'How many adults are staying?',
    label: 'Adults',
    type: 'number',
    min: '1',
  },
  {
    key: 'children',
    bot: 'How many children are staying?',
    label: 'Children',
    type: 'number',
    min: '0',
  },
  {
    key: 'room_type',
    bot: 'What room type does the guest prefer?',
    label: 'Room Type',
    type: 'select',
    options: [
      ['Standard', 'Standard'],
      ['Deluxe', 'Deluxe'],
      ['Twin', 'Twin'],
      ['Family Room', 'Family Room'],
      ['Suite', 'Suite'],
    ],
  },
  {
    key: 'guest_name',
    bot: 'May I have the guest full name?',
    label: 'Guest Full Name',
    type: 'text',
    placeholder: 'Abebe Kebede',
  },
  {
    key: 'guest_phone',
    bot: 'What phone number should the hotel use for follow-up?',
    label: 'Phone Number',
    type: 'tel',
    placeholder: '+251900000000',
  },
  {
    key: 'guest_email',
    bot: 'What email address should receive the response?',
    label: 'Email',
    type: 'email',
    placeholder: 'guest@example.com',
  },
  {
    key: 'special_requests',
    bot: 'Any special request for the reservation team?',
    label: 'Special Request',
    type: 'textarea',
    placeholder: 'Late check-in, airport pickup, room preference',
    optional: true,
  },
]

function buildPublicBookingPayload(draft, channel = draft.channel) {
  return {
    property_code: draft.property_code,
    source: 'website_chatbot',
    channel,
    guest_name: draft.guest_name,
    guest_phone: draft.guest_phone,
    guest_email: draft.guest_email,
    check_in_date: draft.check_in_date,
    check_out_date: draft.check_out_date,
    adults: Number(draft.adults || 1),
    children: Number(draft.children || 0),
    room_type: draft.room_type,
    reservation_type: 'individual',
    booking_status: 'pending_request',
    guarantee_type: 'non_guaranteed',
    deposit_status: 'pending',
    special_requests: draft.special_requests,
    notes: `Created from Guzo website chatbot for ${hotelNames[draft.property_code] || 'Guzo PMS'}.`,
  }
}

function getFieldAnswer(step, value) {
  if (!value) {
    return 'Not provided'
  }

  if (step.options) {
    return step.options.find(([optionValue]) => optionValue === value)?.[1] || value
  }

  return value
}

function RequestPreview({ payload }) {
  if (!payload) {
    return null
  }

  return (
    <div className="ai-request-preview" aria-label="Prepared PMS request preview">
      <strong>Prepared PMS request</strong>
      <dl>
        <div><dt>Status</dt><dd>{payload.booking_status}</dd></div>
        <div><dt>Hotel</dt><dd>{hotelNames[payload.property_code] || payload.property_code}</dd></div>
        <div><dt>Guest</dt><dd>{payload.guest_name || 'Not provided'}</dd></div>
        <div><dt>Stay</dt><dd>{payload.check_in_date || 'TBD'} to {payload.check_out_date || 'TBD'}</dd></div>
        <div><dt>Guests</dt><dd>{payload.adults} adult(s), {payload.children} child(ren)</dd></div>
        <div><dt>Room</dt><dd>{payload.room_type || 'TBD'}</dd></div>
        <div><dt>Channel</dt><dd>{payload.channel}</dd></div>
      </dl>
    </div>
  )
}

export default function GuzoAIPlatformPage() {
  const [demoRequestStatus, setDemoRequestStatus] = useState({
    tone: 'idle',
    message: 'Complete the conversation to send a PMS-safe pending_request to Booking Hub for staff review.',
  })
  const [chatStepIndex, setChatStepIndex] = useState(0)
  const [bookingDraft, setBookingDraft] = useState(initialBookingDraft)
  const [previewPayload, setPreviewPayload] = useState(null)

  const currentChatStep = chatbotSteps[chatStepIndex]
  const isFinalChatStep = chatStepIndex === chatbotSteps.length - 1
  const completedChatSteps = chatbotSteps.slice(0, chatStepIndex)

  async function submitPublicBookingRequest(payload, successMessage) {
    setPreviewPayload(payload)

    if (!PUBLIC_BOOKING_ENABLED) {
      setDemoRequestStatus({
        tone: 'locked',
        message: lockedSubmissionMessage,
      })
      return false
    }

    setDemoRequestStatus({
      tone: 'loading',
      message: 'Sending this request to the Guzo PMS public booking endpoint...',
    })

    try {
      const response = await fetch(`${apiBaseUrl}${bookingEndpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`)
      }

      const data = await response.json()
      const requestId = data?.request?.id ? ` Request reference: ${data.request.id}.` : ''

      setDemoRequestStatus({
        tone: 'success',
        message: `${successMessage}${requestId}`,
      })

      return true
    } catch {
      setDemoRequestStatus({
        tone: 'error',
        message: 'We could not send your request right now. Please try again or contact the hotel team.',
      })

      return false
    }
  }

  function handleDraftChange(key, value) {
    setBookingDraft((draft) => ({
      ...draft,
      [key]: value,
    }))
  }

  async function handleChatbotSubmit(event) {
    event.preventDefault()

    if (!currentChatStep.optional && !bookingDraft[currentChatStep.key]) {
      setDemoRequestStatus({
        tone: 'error',
        message: `Please provide ${currentChatStep.label.toLowerCase()} before continuing.`,
      })
      return
    }

    if (!isFinalChatStep) {
      setChatStepIndex((stepIndex) => stepIndex + 1)
      return
    }

    const submitted = await submitPublicBookingRequest(
      buildPublicBookingPayload(bookingDraft),
      'Thank you. Your reservation request has been sent to Guzo PMS Booking Hub. Our team will review availability and confirm shortly.',
    )

    if (submitted) {
      setBookingDraft(initialBookingDraft)
      setChatStepIndex(0)
    }
  }

  async function handleDemoBookingSubmit(event) {
    event.preventDefault()
    const form = event.currentTarget
    const formData = new FormData(form)
    const draft = {
      property_code: formData.get('property_code'),
      channel: formData.get('channel'),
      guest_name: formData.get('guest_name'),
      guest_phone: formData.get('guest_phone'),
      guest_email: formData.get('guest_email'),
      check_in_date: formData.get('check_in_date'),
      check_out_date: formData.get('check_out_date'),
      adults: formData.get('adults'),
      children: formData.get('children'),
      room_type: formData.get('room_type'),
      special_requests: formData.get('special_requests'),
    }

    const submitted = await submitPublicBookingRequest(
      buildPublicBookingPayload(draft, draft.channel),
      'Thank you. Your reservation request has been sent to Guzo PMS Booking Hub. Our team will review availability and confirm shortly.',
    )

    if (submitted) {
      form.reset()
    }
  }

  return (
    <main className="ai-platform">
      <section className="ai-hero" id="top">
        <nav className="ai-nav" aria-label="Primary navigation">
          <a className="ai-brand" href="#top" aria-label="Guzo PMS home">
            <span className="ai-mark">G</span>
            <span>Guzo PMS</span>
          </a>
          <div className="ai-nav-links">
            <a href="#modules">Modules</a>
            <a href="#agent">AI Agent</a>
            <a href="#guest-platform">Guest Platform</a>
            <a href="#demo-booking">Booking Demo</a>
            <a href="#demo">Demo</a>
          </div>
          <div className="ai-nav-actions">
            <a className="ai-button ai-button-secondary" href="/login">Log in</a>
            <a className="ai-button ai-button-primary" href="#demo">Request demo</a>
          </div>
        </nav>

        <div className="ai-hero-grid">
          <div>
            <span className="ai-eyebrow">AI Agent + Landing Page + Secure PMS Dashboard</span>
            <h1>Guzo PMS</h1>
            <p className="ai-lead">
              A hotel operating platform where guests can preview reservation requests, while staff remain in control of real PMS booking approval.
            </p>
            <div className="ai-hero-actions">
              <a className="ai-button ai-button-primary" href="#demo-booking">Start Booking Demo</a>
              <a className="ai-button ai-button-primary" href="#agent">Chat with Guzo AI</a>
              <a className="ai-button ai-button-secondary" href="#modules">Explore PMS modules</a>
            </div>
            <div className="ai-metrics" aria-label="Guzo platform priorities">
              <div className="ai-metric"><strong>3-way</strong><span>Guest, staff, and owner connection</span></div>
              <div className="ai-metric"><strong>24/7</strong><span>AI hotel assistant readiness</span></div>
              <div className="ai-metric"><strong>PMS</strong><span>Reservations, rooms, folios, reports</span></div>
            </div>
          </div>

          <aside className="ai-agent-panel" id="agent" aria-label="Guzo AI Hotel Agent preview">
            <div className="ai-agent-head">
              <div className="ai-agent-title"><span className="ai-pulse" />Guzo AI Hotel Agent</div>
              <span className="ai-agent-state">Booking Hub request</span>
            </div>
            <div className="ai-agent-intro">
              Guests can send a reservation request to Booking Hub. Final confirmation still requires hotel staff approval.
            </div>
            <div className="ai-messages">
              {completedChatSteps.map((step) => (
                <div className="ai-chat-pair" key={step.key}>
                  <div className="ai-message ai-message-agent">{step.bot}</div>
                  <div className="ai-message ai-message-user">{getFieldAnswer(step, bookingDraft[step.key])}</div>
                </div>
              ))}
              <div className="ai-message ai-message-agent">{currentChatStep.bot}</div>
            </div>
            <form className="ai-chat-input" onSubmit={handleChatbotSubmit}>
              <label>
                {currentChatStep.label}
                {currentChatStep.type === 'select' ? (
                  <select
                    value={bookingDraft[currentChatStep.key]}
                    onChange={(event) => handleDraftChange(currentChatStep.key, event.target.value)}
                    required={!currentChatStep.optional}
                  >
                    {currentChatStep.options.map(([value, label]) => (
                      <option value={value} key={value}>{label}</option>
                    ))}
                  </select>
                ) : currentChatStep.type === 'textarea' ? (
                  <textarea
                    value={bookingDraft[currentChatStep.key]}
                    onChange={(event) => handleDraftChange(currentChatStep.key, event.target.value)}
                    placeholder={currentChatStep.placeholder}
                    rows="3"
                  />
                ) : (
                  <input
                    value={bookingDraft[currentChatStep.key]}
                    onChange={(event) => handleDraftChange(currentChatStep.key, event.target.value)}
                    type={currentChatStep.type}
                    min={currentChatStep.min}
                    placeholder={currentChatStep.placeholder}
                    required={!currentChatStep.optional}
                  />
                )}
              </label>
              <div className="ai-chat-actions">
                <button
                  className="ai-button ai-button-secondary-dark"
                  type="button"
                  disabled={chatStepIndex === 0 || demoRequestStatus.tone === 'loading'}
                  onClick={() => setChatStepIndex((stepIndex) => Math.max(0, stepIndex - 1))}
                >
                  Back
                </button>
                <button className="ai-button ai-button-primary" type="submit" disabled={demoRequestStatus.tone === 'loading'}>
                  {isFinalChatStep ? 'Send Request to Booking Hub' : 'Next'}
                </button>
              </div>
              <div className={`ai-form-status ai-form-status-${demoRequestStatus.tone}`} role="status">
                {demoRequestStatus.message}
              </div>
              <RequestPreview payload={previewPayload} />
            </form>
          </aside>
        </div>
      </section>

      <section className="ai-section" id="modules">
        <div className="ai-section-head">
          <h2>Global-standard PMS workflows for modern hotels.</h2>
          <p>Guzo starts with the operational work hotels run every day, then adds an AI agent that can explain, summarize, and eventually perform secure PMS actions.</p>
        </div>
        <div className="ai-modules">
          {modules.map(([code, title, copy]) => (
            <article className="ai-module" key={title}>
              <div className="ai-module-icon">{code}</div>
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="ai-bridge">
        <div className="ai-section">
          <div className="ai-section-head">
            <h2>The bridge between guests, hotel teams, and PMS data.</h2>
            <p>The landing page is the front door, the chat box is the conversation, and staff approval is the control point before any real booking enters PMS operations.</p>
          </div>
          <div className="ai-bridge-grid">
            {bridgeItems.map(([title, copy]) => (
              <article className="ai-bridge-card" key={title}>
                <b>{title}</b>
                <p>{copy}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="ai-section ai-platform-grid" id="guest-platform">
        <div>
          <h2>Built for social media and guest connection.</h2>
          <p className="ai-section-copy">
            Guzo can become the public guest platform for hotel questions, demo requests, booking intent, and staff follow-up across web and social channels.
          </p>
          <div className="ai-timeline">
            {phases.map(([number, title, copy]) => (
              <article className="ai-step" key={number}>
                <div className="ai-step-number">{number}</div>
                <div>
                  <h3>{title}</h3>
                  <p>{copy}</p>
                </div>
              </article>
            ))}
          </div>
        </div>

        <aside className="ai-social-board" aria-label="Guest and social platform preview">
          <div className="ai-social-top">
            <h3>Guest connection inbox</h3>
            <span>Demo-only</span>
          </div>
          <div className="ai-feed">
            {feed.map(([code, title, copy, tag, color]) => (
              <div className="ai-feed-item" key={title}>
                <div className={`ai-avatar ai-avatar-${color}`}>{code}</div>
                <div>
                  <strong>{title}</strong>
                  <span>{copy}</span>
                </div>
                <em>{tag}</em>
              </div>
            ))}
          </div>
        </aside>
      </section>

      <section className="ai-demo-booking" id="demo-booking">
        <div className="ai-section ai-demo-grid">
          <div>
            <span className="ai-section-kicker">LinkedIn and social demo bridge</span>
            <h2>Guzo AI Booking Assistant Demo.</h2>
            <p className="ai-section-copy">
              Public visitors can choose Dream Big Hotel or N&N Hotel and send a PMS-safe pending request to Booking Hub for staff review.
            </p>

            <div className="ai-demo-hotels" aria-label="Demo hotel actions">
              <article>
                <strong>Dream Big Hotel</strong>
                <span>DRE001</span>
                <a className="ai-button ai-button-primary" href="#demo-form">Start Booking Demo</a>
              </article>
              <article>
                <strong>N&amp;N Hotel</strong>
                <span>NN001</span>
                <a className="ai-button ai-button-primary" href="#demo-form">Start Booking Demo</a>
              </article>
            </div>

            <div className="ai-demo-actions">
              <a className="ai-button ai-button-secondary-dark" href="#agent">Chat with Guzo AI</a>
              <a className="ai-button ai-button-secondary-dark" href="#demo-form">Preview PMS Request</a>
              <a className="ai-button ai-button-secondary-dark" href="mailto:demo@guzopms.com?subject=Guzo%20Booking%20Assistant%20Demo">Contact Hotel Team</a>
              <a className="ai-button ai-button-secondary-dark" href="/">Open Demo PMS Dashboard</a>
              <a className="ai-button ai-button-secondary-dark" href="/login">Hotel Manager Login</a>
            </div>

            <div className="ai-security-note">
              Chatbot UI: <strong>open</strong>. Guest direct PMS booking: <strong>blocked</strong>. Backend public request: <strong>active</strong>. PMS direct bot booking: <strong>internal only</strong>.
            </div>
          </div>

          <form className="ai-demo-form" id="demo-form" onSubmit={handleDemoBookingSubmit}>
            <div className="ai-form-head">
              <h3>Booking Request</h3>
              <span>demo_preview</span>
            </div>

            <label>
              Hotel
              <select name="property_code" defaultValue="DRE001">
                <option value="DRE001">Dream Big Hotel</option>
                <option value="NN001">N&amp;N Hotel</option>
              </select>
            </label>

            <div className="ai-form-row">
              <label>
                Guest Name
                <input name="guest_name" placeholder="Sample guest name" required />
              </label>
              <label>
                Email
                <input name="guest_email" type="email" placeholder="guest@example.com" required />
              </label>
            </div>

            <div className="ai-form-row">
              <label>
                Phone
                <input name="guest_phone" type="tel" placeholder="+1 555 123 4567" required />
              </label>
              <label>
                Channel
                <select name="channel" defaultValue="ai_platform_chatbot">
                  <option value="ai_platform_chatbot">AI Platform Chatbot</option>
                  <option value="telegram_bot">Telegram Bot</option>
                  <option value="linkedin_demo">LinkedIn</option>
                  <option value="facebook_demo">Facebook</option>
                  <option value="instagram_demo">Instagram</option>
                  <option value="whatsapp_demo">WhatsApp</option>
                </select>
              </label>
            </div>

            <div className="ai-form-row">
              <label>
                Check-in Date
                <input name="check_in_date" type="date" required />
              </label>
              <label>
                Check-out Date
                <input name="check_out_date" type="date" required />
              </label>
            </div>

            <div className="ai-form-row">
              <label>
                Adults
                <input name="adults" type="number" min="1" defaultValue="1" required />
              </label>
              <label>
                Children
                <input name="children" type="number" min="0" defaultValue="0" />
              </label>
            </div>

            <div className="ai-form-row">
              <label>
                Room Type
                <select name="room_type" defaultValue="Standard">
                  <option>Standard</option>
                  <option>Deluxe</option>
                  <option>Twin</option>
                  <option>Family Room</option>
                  <option>Suite</option>
                </select>
              </label>
            </div>

            <label>
              Special Request
              <textarea name="special_requests" rows="4" placeholder="Late arrival, airport pickup, room preference" />
            </label>

            <div className={`ai-form-status ai-form-status-${demoRequestStatus.tone}`} role="status">
              {demoRequestStatus.message}
            </div>

            <RequestPreview payload={previewPayload} />

            <button className="ai-button ai-button-primary" type="submit" disabled={demoRequestStatus.tone === 'loading'}>
              {demoRequestStatus.tone === 'loading' ? 'Sending...' : 'Send Request to Booking Hub'}
            </button>
          </form>
        </div>
      </section>

      <section className="ai-cta" id="demo">
        <div className="ai-section">
          <div>
            <h2>Launch Guzo as a landing page now, then grow it into the hotel AI agent.</h2>
            <p>Start with demo capture, PMS module storytelling, guest questions, and staff login. Then connect secure backend actions when the APIs are ready.</p>
          </div>
          <a className="ai-button ai-button-primary" href="mailto:demo@guzopms.com?subject=Guzo%20PMS%20Demo%20Request">Request demo</a>
        </div>
      </section>
    </main>
  )
}
