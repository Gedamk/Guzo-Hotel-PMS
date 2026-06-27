import { useMemo, useState } from "react";
import PageHeader from "../../components/PageHeader";
import { usePmsContext } from "../../context/PmsContext";
import { getErrorMessage, http } from "../../services/http";

type AvailabilityResult = {
  available_rooms: number;
  total_rooms: number;
  is_available: boolean;
};

const rateByRoomType: Record<string, number> = {
  "Standard Room": 5200,
  "Standard Double Room": 95,
  "Deluxe Family Room": 120,
  "Deluxe Twin Room": 120,
  "Deluxe King": 6800,
  "Twin Room": 5900,
  Suite: 12500,
};

function nights(checkIn: string, checkOut: string) {
  if (!checkIn || !checkOut) return 0;
  return Math.max(
    Math.round((new Date(checkOut).getTime() - new Date(checkIn).getTime()) / 86400000),
    0
  );
}

function quoteMoney(roomType: string, value: number) {
  const currency = ["Standard Double Room", "Deluxe Family Room", "Deluxe Twin Room"].includes(roomType) ? "USD" : "ETB";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

export default function HotelBookingPage() {
  const { propertyCode, propertyName, businessDate } = usePmsContext();
  const [guestName, setGuestName] = useState("");
  const [checkIn, setCheckIn] = useState(businessDate);
  const [checkOut, setCheckOut] = useState(businessDate);
  const [roomType, setRoomType] = useState("Standard Room");
  const [rooms, setRooms] = useState("1");
  const [email, setEmail] = useState("");
  const [arrivalTime, setArrivalTime] = useState("");
  const [availability, setAvailability] = useState<AvailabilityResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const roomCount = Math.max(Number(rooms || 1), 1);
  const stayNights = nights(checkIn, checkOut);
  const totalAmount = useMemo(
    () => stayNights * roomCount * rateByRoomType[roomType],
    [stayNights, roomCount, roomType]
  );

  async function checkAvailability() {
    setError("");
    setMessage("");
    if (stayNights <= 0) {
      setError("Check-Out date must be after Check-In date.");
      return;
    }

    try {
      setChecking(true);
      const { data } = await http.get<AvailabilityResult>("/availability/search", {
        params: {
          property_code: propertyCode,
          check_in: checkIn,
          check_out: checkOut,
          rooms: roomCount,
        },
      });
      setAvailability(data);
      setMessage(data.is_available ? "Rooms are available for this stay." : "Requested rooms are not available.");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setChecking(false);
    }
  }

  async function submitBooking(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!guestName.trim()) {
      setError("Guest name is required.");
      return;
    }

    if (stayNights <= 0) {
      setError("Check-Out date must be after Check-In date.");
      return;
    }

    try {
      setSaving(true);
      await http.post("/bot/bookings", {
        property_code: propertyCode,
        check_in: checkIn,
        check_out: checkOut,
        guest_name: guestName.trim(),
        channel: "Website Chatbot",
        total_amount_etb: totalAmount,
        currency: "ETB",
      });
      setMessage(`Booking confirmed for ${guestName.trim()}. Reservations can complete guarantee and profile review.`);
      setGuestName("");
      setEmail("");
      setArrivalTime("");
      setAvailability(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-grid">
      <PageHeader
        title="Hotel Booking"
        subtitle="Direct guest reservation flow."
        metadata={`${propertyCode} • ${propertyName} • ${businessDate}`}
        rightSlot={<div className="pill">Website Chatbot</div>}
      />

      {error ? <div className="error-box">{error}</div> : null}
      {message ? <div className="notice-box">{message}</div> : null}

      <section className="booking-hero card">
        <div>
          <p className="eyebrow">Direct Reservation</p>
          <h2>Guest Booking Workspace</h2>
          <p className="muted">
            Capture guest details, verify availability, quote the stay, and create a confirmed PMS booking.
          </p>
        </div>
        <div className="source-pill">
          <strong>{quoteMoney(roomType, totalAmount)}</strong>
          <span>{stayNights} night(s), {roomCount} room(s)</span>
        </div>
      </section>

      <section className="page-grid two-col">
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Booking Details</h2>
          <form className="page-grid" onSubmit={submitBooking}>
            <div className="form-grid">
              <label className="field span-2">
                <span>Guest Name</span>
                <input value={guestName} onChange={(event) => setGuestName(event.target.value)} required />
              </label>

              <label className="field">
                <span>Email / Contact</span>
                <input value={email} onChange={(event) => setEmail(event.target.value)} />
              </label>

              <label className="field">
                <span>Check-In</span>
                <input type="date" value={checkIn} onChange={(event) => setCheckIn(event.target.value)} required />
              </label>

              <label className="field">
                <span>Check-Out</span>
                <input type="date" value={checkOut} onChange={(event) => setCheckOut(event.target.value)} required />
              </label>

              <label className="field">
                <span>Rooms</span>
                <input type="number" min="1" value={rooms} onChange={(event) => setRooms(event.target.value)} />
              </label>

              <label className="field">
                <span>Room Type</span>
                <select value={roomType} onChange={(event) => setRoomType(event.target.value)}>
                  {Object.keys(rateByRoomType).map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Arrival Time</span>
                <input value={arrivalTime} onChange={(event) => setArrivalTime(event.target.value)} placeholder="Optional" />
              </label>
            </div>

            <div className="form-actions">
              <button className="small-btn" type="button" onClick={checkAvailability} disabled={checking}>
                {checking ? "Checking..." : "Check Availability"}
              </button>
              <button className="primary-btn" type="submit" disabled={saving}>
                {saving ? "Creating..." : "Confirm Booking"}
              </button>
            </div>
          </form>
        </div>

        <div className="card">
          <h2 style={{ marginTop: 0 }}>Reservation Summary</h2>
          <div className="source-matrix">
            <div className="source-row">
              <strong>Property</strong>
              <span>{propertyCode}</span>
            </div>
            <div className="source-row">
              <strong>Room Type</strong>
              <span>{roomType}</span>
            </div>
            <div className="source-row">
              <strong>Rate</strong>
              <span>{quoteMoney(roomType, rateByRoomType[roomType])}</span>
            </div>
            <div className="source-row">
              <strong>Total Stay</strong>
              <span>{quoteMoney(roomType, totalAmount)}</span>
            </div>
            <div className="source-row">
              <strong>Availability</strong>
              <span>{availability ? `${availability.available_rooms}/${availability.total_rooms} rooms` : "Not checked"}</span>
            </div>
          </div>

          <div className="notice-box">
            PMS handover: Reservations confirms guarantee, Front Desk assigns room, Housekeeping prepares status, and the folio opens at Check-In.
          </div>
        </div>
      </section>
    </div>
  );
}
