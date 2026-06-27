import { useState } from "react";
import PageHeader from "../../components/PageHeader";
import { usePmsContext } from "../../context/PmsContext";
import { getErrorMessage, http } from "../../services/http";
import { demoBookingWorkflow, demoFamilyBookings } from "./demoFamilyBookings";

type ChatEntry = {
  role: "guest" | "assistant";
  text: string;
};

export default function BookingAssistantPage() {
  const { propertyCode, propertyName, businessDate } = usePmsContext();
  const [guestName, setGuestName] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [chat, setChat] = useState<ChatEntry[]>([
    {
      role: "assistant",
      text: "Welcome. I can help record a booking inquiry, note guest preferences, and hand the conversation to reservations.",
    },
    {
      role: "guest",
      text: "Family booking request received from Guzo AI Guest Site for John Kelly, June 10-13, 2026, 3 guests, Deluxe Family Room.",
    },
    {
      role: "assistant",
      text: "Rooms and BAR rate checked. Booking confirmed as GUZO-JK-20260610-001 and confirmation message delivered.",
    },
    {
      role: "guest",
      text: "Family multi-room booking request received from Guzo AI Guest Site for Thomas Jefferson, June 10-13, 2026, 5 guests, 2 rooms.",
    },
    {
      role: "assistant",
      text: "Rooms 302 and 303 confirmed under BAR. Booking linked as GUZO-TJ-20260610-002 and confirmation message delivered.",
    },
  ]);

  async function handleSend(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanMessage = message.trim();
    if (!cleanMessage) return;

    setChat((prev) => [...prev, { role: "guest", text: cleanMessage }]);
    setMessage("");
    setError("");

    try {
      setSending(true);
      const { data } = await http.post("/chat/message", {
        message: cleanMessage,
        property_code: propertyCode,
        guest_name: guestName.trim() || null,
        channel: "booking-assistant",
      });
      setChat((prev) => [
        ...prev,
        {
          role: "assistant",
          text:
            data.reply ||
            "Inquiry received. Reservations can review this conversation.",
        },
      ]);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="page-grid booking-assistant-command">
      <PageHeader
        title="Booking Assistant"
        subtitle="Guided reservation intake."
        metadata={`${propertyCode} • ${propertyName} • ${businessDate}`}
        rightSlot={<div className="pill">Business Date: {businessDate}</div>}
      />

      {error ? <div className="error-box">{error}</div> : null}

      <section className="card">
        <div className="section-heading">
          <div>
            <h2>Guest Inquiry Inbox</h2>
            <div className="muted">Delivered AI-site messages ready for reservations review.</div>
          </div>
          <div className="pill pill-success">New Message Delivered</div>
        </div>
        <div className="booking-assistant-inbox">
          {demoFamilyBookings.map((booking) => (
            <div className="booking-assistant-message" key={booking.confirmationNo}>
              <div>
                <span className="pill pill-success">New Message Delivered</span>
                <h3>{booking.guestName}</h3>
                <p>{booking.intent}</p>
              </div>
              <div className="booking-assistant-message-grid">
                <span>Channel</span>
                <strong>{booking.channel}</strong>
                <span>Status</span>
                <strong>{booking.status}</strong>
                <span>Linked Booking</span>
                <strong>{booking.confirmationNo}</strong>
                <span>Assigned To</span>
                <strong>{booking.assignedTo}</strong>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="page-grid two-col">
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Guest Inquiry</h2>
          <form className="page-grid" onSubmit={handleSend}>
            <label>
              Guest Name
              <input
                value={guestName}
                onChange={(event) => setGuestName(event.target.value)}
                placeholder="Optional guest name"
              />
            </label>
            <label>
              Message
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Room request, dates, special needs, contact details"
                required
              />
            </label>
            <button className="primary-btn" type="submit" disabled={sending}>
              {sending ? "Sending..." : "Send to Booking Desk"}
            </button>
          </form>
        </div>

        <div className="card">
          <h2 style={{ marginTop: 0 }}>Conversation</h2>
          <div className="page-grid">
            {chat.map((entry, index) => (
              <div
                className={entry.role === "assistant" ? "card" : "error-box"}
                key={`${entry.role}-${index}`}
                style={{ margin: 0 }}
              >
                <strong>{entry.role === "assistant" ? "Assistant" : "Guest"}</strong>
                <div style={{ marginTop: "6px" }}>{entry.text}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Reservation SOP</h2>
        <div className="booking-workflow-list">
          {demoBookingWorkflow.map((step, index) => (
            <div key={step}>
              <span>{index + 1}</span>
              <strong>{step}</strong>
            </div>
          ))}
        </div>
        <div className="sop-list">
          <label className="sop-item">
            <input type="checkbox" /> Confirm stay dates, guest count, room type, and rate plan.
          </label>
          <label className="sop-item">
            <input type="checkbox" /> Capture contact, payment guarantee, and arrival time.
          </label>
          <label className="sop-item">
            <input type="checkbox" /> Record special requests for front desk handover.
          </label>
        </div>
      </div>
    </div>
  );
}
