import { useState } from "react";
import PageHeader from "../../components/PageHeader";
import { usePmsContext } from "../../context/PmsContext";
import { getErrorMessage, http } from "../../services/http";

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
    <div className="page-grid">
      <PageHeader
        title="Booking Assistant"
        subtitle={`${propertyName} reservation intake for ${propertyCode}`}
        rightSlot={<div className="pill">Business Date: {businessDate}</div>}
      />

      {error ? <div className="error-box">{error}</div> : null}

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
