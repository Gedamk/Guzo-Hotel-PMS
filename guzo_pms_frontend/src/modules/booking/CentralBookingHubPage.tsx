import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../../components/PageHeader";
import { HandoffBadge } from "../../components/ui/HandoffBadge";
import { StatusBadge, type BadgeVariant } from "../../components/ui/StatusBadge";
import { usePmsContext } from "../../context/PmsContext";
import {
  convertPublicBookingRequest,
  fetchFrontdeskBookings,
  fetchPublicBookingRequests,
  updatePublicBookingRequestStatus,
} from "../../services/pmsService";
import { getErrorMessage, http } from "../../services/http";
import type { FrontdeskBooking, PublicBookingRequest } from "../../types/pms";
import { demoBookingWorkflow, demoFamilyBookings } from "./demoFamilyBookings";
import { permissionMessage, roleCan } from "../../auth/permissions";

type AvailabilityResult = {
  available_rooms: number;
  total_rooms: number;
  overlapping_bookings: number;
  out_of_order_rooms?: number;
  is_available: boolean;
  min_available_rooms?: number;
  room_type?: string | null;
  daily_breakdown?: Array<Record<string, any>>;
};

type RateQuoteResult = {
  currency: string;
  room_type: string;
  rate_code: string;
  rate_label: string;
  nights: number;
  rooms: number;
  adults: number;
  children: number;
  nightly_rate_etb: number;
  room_subtotal_etb: number;
  weekend_surcharge_etb: number;
  extra_guest_charge_etb: number;
  service_charge_etb: number;
  tax_etb: number;
  net_revenue_etb: number;
  gross_revenue_etb: number;
  total_etb: number;
  deposit_percent: number;
  deposit_required_etb: number;
  guarantee_required: boolean;
  cancellation_policy: string;
  applied_rules: string[];
  quote_notes: string[];
};

type BookingForm = {
  guestName: string;
  guestEmail: string;
  guestPhone: string;
  checkIn: string;
  checkOut: string;
  rooms: string;
  adults: string;
  children: string;
  roomType: string;
  rate: string;
  rateCode: "BAR" | "CORP" | "GRP10";
  channel: "Website Chatbot" | "Telegram Bot";
  paymentStatus: "pending" | "guaranteed" | "deposit_paid" | "paid";
  purposeOfVisit: string;
  notes: string;
};

const defaultForm: BookingForm = {
  guestName: "",
  guestEmail: "",
  guestPhone: "",
  checkIn: "",
  checkOut: "",
  rooms: "1",
  adults: "1",
  children: "0",
  roomType: "Standard Room",
  rate: "5200",
  rateCode: "BAR",
  channel: "Website Chatbot",
  paymentStatus: "pending",
  purposeOfVisit: "Leisure",
  notes: "",
};

const publicRequestRate = 5200;

function nights(checkIn: string, checkOut: string) {
  if (!checkIn || !checkOut) return 0;
  const diff = new Date(checkOut).getTime() - new Date(checkIn).getTime();
  return Math.max(Math.round(diff / 86400000), 0);
}

function money(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "ETB",
    maximumFractionDigits: 0,
  }).format(value);
}

function sourceOf(row: FrontdeskBooking) {
  return row.source || row.channel || "Direct";
}

function publicRequestNights(request: PublicBookingRequest) {
  return nights(request.check_in_date, request.check_out_date);
}

function publicRequestValue(request: PublicBookingRequest) {
  return publicRequestNights(request) * publicRequestRate;
}

function isConvertedRequest(request: PublicBookingRequest) {
  return Boolean(request.converted_booking_id) || request.booking_status === "converted";
}

function publicRequestSource(request: PublicBookingRequest) {
  const source = request.channel || request.source || "public_request";
  const labels: Record<string, string> = {
    ai_platform_chatbot: "Website Chatbot",
    website_chatbot: "Website Chatbot",
    website_chat: "Website Chat",
    telegram_bot: "Telegram Bot",
  };
  return labels[source] || source;
}

function requestSopAction(request: PublicBookingRequest) {
  if (isConvertedRequest(request)) return "Confirmed PMS booking: hand off to Front Desk";
  if (request.booking_status === "rejected") return "Turnaway/lost business: keep demand for reports";
  if (request.booking_status === "deposit_requested" || request.booking_status === "deposit_required") {
    return "Collect guarantee/deposit before confirmation";
  }
  if (request.booking_status === "reviewed" || request.booking_status === "tentative") {
    return "Quote room/rate/policy, then convert or reject";
  }
  return "Review chatbot request and validate availability";
}

function requestWorkflowSteps(request: PublicBookingRequest) {
  const converted = isConvertedRequest(request);
  const needsDeposit =
    request.deposit_status !== "paid" &&
    request.guarantee_type !== "guaranteed" &&
    !converted;
  return [
    {
      label: "Chatbot request",
      detail: `${publicRequestSource(request)} captured guest, dates, room need, guests, and notes.`,
      state: "done",
    },
    {
      label: "Booking Hub review",
      detail: "Reservations verifies profile, availability, rate, policy, and special requests.",
      state: request.booking_status === "pending_request" ? "active" : "done",
    },
    {
      label: "Guarantee / deposit",
      detail: needsDeposit
        ? "Request deposit or payment guarantee before final confirmation."
        : "Guarantee/deposit decision is ready for conversion.",
      state: needsDeposit ? "active" : "done",
    },
    {
      label: "Convert to reservation",
      detail: converted
        ? `Confirmed PMS booking #${request.converted_booking_id} created.`
        : "Staff converts only after room/rate/policy are valid.",
      state: converted ? "done" : "pending",
    },
    {
      label: "Front desk handoff",
      detail: "Arrivals, room assignment, VIP/special requests, and guest notes become visible.",
      state: converted ? "active" : "pending",
    },
    {
      label: "Folio / night audit",
      detail: "Deposit, payment status, no-show risk, revenue, and source flow into audit and reports.",
      state: converted ? "pending" : "pending",
    },
  ];
}

function bookingNextStep(booking: FrontdeskBooking) {
  const status = booking.booking_status.toLowerCase();
  const paymentStatus = (booking.payment_status || "").toLowerCase();

  if (status.includes("pending_guarantee") || paymentStatus === "pending") {
    return "Booking Hub: collect guarantee/deposit";
  }
  if (!booking.room_number) return "Front Desk: assign room";
  if (status === "confirmed") return "Housekeeping: verify room readiness";
  if (status === "in_house" || status === "arrived") return "Folio: post charges and monitor stay";
  if (status === "checked_out") return "Reports: include production and source";
  if (status === "no_show") return "Night Audit: process no-show policy";
  return "Reservations: review status";
}

function bookingHandoffBadges(booking: FrontdeskBooking) {
  const paymentStatus = String(booking.payment_status || "pending").toLowerCase();
  const badges = [
    booking.room_number
      ? { label: "Room Assigned", variant: "success" }
      : { label: "Front Desk: Room TBD", variant: "warning" },
    paymentStatus === "deposit_paid" || paymentStatus === "guaranteed" || paymentStatus === "paid"
      ? { label: "Guarantee Ready", variant: "success" }
      : { label: "Finance: Deposit Expected", variant: "warning" },
  ];
  return badges;
}

function requestHandoffBadges(request: PublicBookingRequest) {
  const notificationStatus = String(request.guest_notification_status || "").toLowerCase();
  if (!isConvertedRequest(request)) {
    return [
      { label: "Booking Hub Review", variant: "warning" },
      request.deposit_payment_link
        ? { label: "Secure Deposit Link Sent", variant: "success" }
        : { label: "Deposit Link Pending", variant: "neutral" },
    ];
  }
  return [
    { label: "PMS Booking Created", variant: "success" },
    request.confirmation_id
      ? { label: `Conf ${request.confirmation_id}`, variant: "success" }
      : { label: "Confirmation Pending", variant: "warning" },
    notificationStatus === "queued"
      ? { label: "Guest Notification Queued", variant: "success" }
      : { label: "Guest Contact Review", variant: "warning" },
    request.deposit_status === "paid"
      ? { label: "Deposit Paid", variant: "success" }
      : { label: "Folio Prepared / Deposit Expected", variant: "warning" },
  ];
}

export default function CentralBookingHubPage() {
  const { propertyCode, propertyName, businessDate, refreshKey } = usePmsContext();
  const [form, setForm] = useState<BookingForm>({
    ...defaultForm,
    checkIn: businessDate,
    checkOut: businessDate,
  });
  const [availability, setAvailability] = useState<AvailabilityResult | null>(null);
  const [quote, setQuote] = useState<RateQuoteResult | null>(null);
  const [bookings, setBookings] = useState<FrontdeskBooking[]>([]);
  const [publicRequests, setPublicRequests] = useState<PublicBookingRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [requestActionId, setRequestActionId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const canReviewRequests = roleCan("booking.review_public_request");
  const canRejectRequests = roleCan("booking.reject_public_request");
  const canRequestDeposit = roleCan("booking.request_deposit");
  const canConvertRequests = roleCan("booking.convert_public_request");
  const canUseBookingActions =
    canReviewRequests || canRejectRequests || canRequestDeposit || canConvertRequests;

  const stayNights = nights(form.checkIn, form.checkOut);
  const roomCount = Math.max(Number(form.rooms || 1), 1);
  const adultCount = Math.max(Number(form.adults || 1), 1);
  const childCount = Math.max(Number(form.children || 0), 0);
  const rate = Math.max(Number(form.rate || 0), 0);
  const totalAmount = quote?.total_etb ?? stayNights * roomCount * rate;
  const openPublicRequests = publicRequests.filter((request) => !isConvertedRequest(request));
  const estimatedPublicRequestValue = openPublicRequests.reduce(
    (sum, request) => sum + publicRequestValue(request),
    0
  );

  const channelSummary = useMemo(() => {
    const rows = bookings.reduce<Record<string, number>>((acc, row) => {
      const source = sourceOf(row);
      acc[source] = (acc[source] || 0) + 1;
      return acc;
    }, {});
    return Object.entries(rows).map(([source, count]) => ({ source, count }));
  }, [bookings]);

  const rateControls = [
    { code: "BAR", label: "Best Available Rate", rate: 5200, use: "Default public rate" },
    { code: "CORP", label: "Corporate Preferred", rate: 4680, use: "Approved accounts" },
    { code: "GRP10", label: "Group 10+ Rooms", rate: 4800, use: "Manager approval" },
  ];

  const sopActions = [
    "Capture guest/caller profile",
    "Validate availability and room type",
    "Quote rate, tax, deposit, and cancellation policy",
    "Request guarantee or deposit when required",
    "Convert to confirmed PMS booking",
    "Hand off to Front Desk, Housekeeping, Folio, Night Audit, and Reports",
  ];

  async function loadBookings() {
    const rows = await fetchFrontdeskBookings(propertyCode, businessDate);
    setBookings(rows);
  }

  async function loadPublicRequests() {
    const rows = await fetchPublicBookingRequests(propertyCode);
    setPublicRequests(rows);
  }

  useEffect(() => {
    Promise.all([loadBookings(), loadPublicRequests()]).catch((err) => setError(getErrorMessage(err)));
  }, [propertyCode, businessDate, refreshKey]);

  async function updateRequestStatus(request: PublicBookingRequest, status: string) {
    setError("");
    setMessage("");
    setRequestActionId(request.id);

    const statusMessages: Record<string, string> = {
      reviewed: "Public request marked reviewed.",
      rejected: "Public request rejected.",
      deposit_requested: "Deposit requested for public booking request.",
      tentative: "Public request moved to tentative.",
    };

    try {
      const updated = await updatePublicBookingRequestStatus(
        request.id,
        status,
        propertyCode,
        status === "deposit_requested" ? "Deposit requested from Booking Hub" : undefined
      );
      setMessage(
        status === "deposit_requested"
          ? `Deposit requested. Link: ${updated.deposit_payment_link || "pending"}; notification: ${updated.guest_notification_status || "pending"}; deposit: ${updated.deposit_status}.`
          : statusMessages[status] || "Public request updated."
      );
      await loadPublicRequests();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setRequestActionId(null);
    }
  }

  async function fetchRateQuote(params: {
    checkIn: string;
    checkOut: string;
    rooms: number;
    adults: number;
    children: number;
    roomType?: string | null;
    rateCode?: string;
  }) {
    const { data } = await http.get<RateQuoteResult>("/rate-quote/quote", {
      params: {
        property_code: propertyCode,
        check_in: params.checkIn,
        check_out: params.checkOut,
        rooms: params.rooms,
        adults: params.adults,
        children: params.children,
        room_type: params.roomType || undefined,
        rate_code: params.rateCode || "BAR",
      },
    });
    return data;
  }

  async function convertRequestToBooking(request: PublicBookingRequest) {
    setError("");
    setMessage("");
    let requestQuote: RateQuoteResult | null = null;

    try {
      setRequestActionId(request.id);
      const { data: requestAvailability } = await http.get<AvailabilityResult>("/availability/search", {
        params: {
          property_code: propertyCode,
          check_in: request.check_in_date,
          check_out: request.check_out_date,
          rooms: 1,
          room_type: request.room_type || undefined,
        },
      });
      if (!requestAvailability.is_available) {
        setError(
          `${request.room_type || "Requested room type"} is not available for the full stay. ` +
          `Minimum availability: ${requestAvailability.available_rooms}. Offer alternate room/date, waitlist, or manager-approved overbooking.`
        );
        return;
      }
      requestQuote = await fetchRateQuote({
        checkIn: request.check_in_date,
        checkOut: request.check_out_date,
        rooms: 1,
        adults: request.adults,
        children: request.children,
        roomType: request.room_type,
        rateCode: "BAR",
      });
    } catch (err) {
      setError(getErrorMessage(err));
      return;
    } finally {
      setRequestActionId(null);
    }

    if (!requestQuote) {
      setError("Rate quote could not be calculated.");
      return;
    }

    setRequestActionId(request.id);
    try {
      const result = await convertPublicBookingRequest(request.id, {
        total_amount_etb: requestQuote.total_etb,
        rate_per_night_etb: requestQuote.nightly_rate_etb,
        room_type: request.room_type,
        payment_status: request.deposit_status === "paid" ? "deposit_paid" : "pending",
        notes:
          `Converted by Booking Hub staff review. ` +
          `Quote ${requestQuote.rate_code}: total ${money(requestQuote.total_etb)}, ` +
          `deposit ${money(requestQuote.deposit_required_etb)}.`,
      }, propertyCode);
      setMessage(result.message);
      await Promise.all([loadPublicRequests(), loadBookings()]);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setRequestActionId(null);
    }
  }

  async function checkAvailability(event?: React.FormEvent) {
    event?.preventDefault();
    setError("");
    setMessage("");

    if (!form.checkIn || !form.checkOut || stayNights <= 0) {
      setError("Check-Out date must be after Check-In date.");
      return;
    }

    try {
      setLoading(true);
      const { data } = await http.get<AvailabilityResult>("/availability/search", {
        params: {
          property_code: propertyCode,
          check_in: form.checkIn,
          check_out: form.checkOut,
          rooms: roomCount,
          room_type: form.roomType,
        },
      });
      setAvailability(data);
      const rateQuote = await fetchRateQuote({
        checkIn: form.checkIn,
        checkOut: form.checkOut,
        rooms: roomCount,
        adults: adultCount,
        children: childCount,
        roomType: form.roomType,
        rateCode: form.rateCode,
      });
      setQuote(rateQuote);
      setForm((prev) => ({ ...prev, rate: String(Math.round(rateQuote.nightly_rate_etb)) }));
      setMessage(
        data.is_available
          ? `Availability confirmed. PMS quote total: ${money(rateQuote.total_etb)}.`
          : "Requested rooms are not available."
      );
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function createBooking(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!form.guestName.trim()) {
      setError("Guest or group name is required.");
      return;
    }

    if (stayNights <= 0) {
      setError("Check-Out date must be after Check-In date.");
      return;
    }

    try {
      setSaving(true);
      const { data: intakeAvailability } = await http.get<AvailabilityResult>("/availability/search", {
        params: {
          property_code: propertyCode,
          check_in: form.checkIn,
          check_out: form.checkOut,
          rooms: roomCount,
          room_type: form.roomType,
        },
      });
      if (!intakeAvailability.is_available) {
        setError(
          `${form.roomType} is not available for the full stay. ` +
          `Minimum availability: ${intakeAvailability.available_rooms}. Use an alternate room type/date or manager-approved overbooking.`
        );
        return;
      }
      const rateQuote = await fetchRateQuote({
        checkIn: form.checkIn,
        checkOut: form.checkOut,
        rooms: roomCount,
        adults: adultCount,
        children: childCount,
        roomType: form.roomType,
        rateCode: form.rateCode,
      });
      await http.post("/bot/bookings", {
        property_code: propertyCode,
        check_in: form.checkIn,
        check_out: form.checkOut,
        guest_name: form.guestName.trim(),
        channel: form.channel,
        total_amount_etb: rateQuote.total_etb,
        currency: "ETB",
        room_type: form.roomType,
        guest_email: form.guestEmail.trim() || undefined,
        guest_phone: form.guestPhone.trim() || undefined,
        adults: adultCount,
        children: childCount,
        purpose_of_visit: form.purposeOfVisit,
        payment_status: form.paymentStatus,
        notes: [
          `Booking Hub SOP intake`,
          `Rooms requested: ${roomCount}`,
          `Rate code: ${rateQuote.rate_code} ${rateQuote.rate_label}`,
          `Rate quoted: ${money(rateQuote.nightly_rate_etb)} per room/night`,
          `Service charge: ${money(rateQuote.service_charge_etb)}`,
          `Tax: ${money(rateQuote.tax_etb)}`,
          `Deposit required: ${money(rateQuote.deposit_required_etb)}`,
          form.notes.trim(),
        ]
          .filter(Boolean)
          .join(" | "),
      });
      setMessage(`${form.channel} booking created for ${form.guestName.trim()}.`);
      setForm({
        ...defaultForm,
        checkIn: form.checkIn,
        checkOut: form.checkOut,
        channel: form.channel,
      });
      setAvailability(null);
      setQuote(null);
      await loadBookings();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-grid">
      <PageHeader
        title="Central Booking Hub"
        subtitle="Reservation desk for direct, website chatbot, and Telegram booking intake."
        metadata={`${propertyCode} • ${propertyName} • ${businessDate}`}
        rightSlot={<div className="pill">Business Date: {businessDate}</div>}
      />

      {error ? <div className="error-box">{error}</div> : null}
      {message ? <div className="notice-box">{message}</div> : null}
      {!canUseBookingActions ? (
        <div className="notice-box">
          {permissionMessage("Booking Hub request actions")}
        </div>
      ) : null}

      <section className="ops-strip">
        <div className="card">
          <div className="ops-label">Open Public Requests</div>
          <div className="ops-value">{openPublicRequests.length}</div>
        </div>
        <div className="card">
          <div className="ops-label">Available Rooms</div>
          <div className="ops-value">{availability ? availability.available_rooms : "-"}</div>
        </div>
        <div className="card">
          <div className="ops-label">Estimated Request Value</div>
          <div className="ops-value">{money(estimatedPublicRequestValue)}</div>
        </div>
        <div className="card">
          <div className="ops-label">Nights / Rooms</div>
          <div className="ops-value">{stayNights} / {roomCount}</div>
        </div>
      </section>

      <section className="card">
        <div className="section-heading">
          <div>
            <h2>Booking Hub Rate Controls</h2>
            <p className="muted">
              Revenue optimization is kept inside Reservations for now: rate codes, corporate/group controls, and channel mapping.
            </p>
          </div>
          <Link className="small-btn" to="/reservations">Open Reservations Rates</Link>
        </div>
        <div className="room-status-strip">
          {rateControls.map((ratePlan) => (
            <div className="room-status-chip" key={ratePlan.code}>
              <div>
                <strong>{ratePlan.code}</strong>
                <div className="muted">{ratePlan.label}</div>
              </div>
              <div>
                <strong>{money(ratePlan.rate)}</strong>
                <div className="muted">{ratePlan.use}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <div className="section-heading">
          <div>
            <h2>Public Requests</h2>
            <p className="muted">Actual website chatbot and public channel requests stay here until staff review, request deposit, reject, or convert them to PMS bookings.</p>
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", justifyContent: "flex-end" }}>
            <div className="pill">Staff approval required</div>
            {canRequestDeposit ? (
              <button className="small-btn" type="button" disabled title="Use the row action on an eligible request.">
                Request Deposit
              </button>
            ) : null}
            {canConvertRequests ? (
              <button className="primary-btn" type="button" disabled title="Use the row action on an eligible request.">
                Convert to Booking
              </button>
            ) : null}
          </div>
        </div>
        <div className="booking-sop-actions">
          {sopActions.map((action, index) => (
            <div className="booking-sop-step" key={action}>
              <span>{index + 1}</span>
              <strong>{action}</strong>
            </div>
          ))}
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Guest Name</th>
                <th>Phone</th>
                <th>Stay</th>
                <th>Room Type</th>
                <th>Guests</th>
                <th>Source</th>
                <th>Status</th>
                <th>SOP Action</th>
                <th>Handoff</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {publicRequests.length ? (
                publicRequests.map((request) => (
                  <tr key={request.id}>
                    <td data-label="Guest Name">
                      <strong>{request.guest_name}</strong>
                      <div className="muted">{request.guest_email || "No email"}</div>
                    </td>
                    <td data-label="Phone">{request.guest_phone || "-"}</td>
                    <td data-label="Stay">
                      {request.check_in_date} to {request.check_out_date}
                      <div className="muted">{publicRequestNights(request)} night(s)</div>
                    </td>
                    <td data-label="Room Type">{request.room_type || "TBD"}</td>
                    <td data-label="Guests">{request.adults} adult(s), {request.children} child(ren)</td>
                    <td data-label="Source">{publicRequestSource(request)}</td>
                    <td data-label="Status">
                      <StatusBadge status={request.booking_status} />
                      {request.converted_booking_id ? (
                        <div className="muted">Booking #{request.converted_booking_id}</div>
                      ) : null}
                      {request.confirmation_id ? (
                        <div className="muted">{request.confirmation_id}</div>
                      ) : null}
                      {request.deposit_status ? (
                        <div className="muted">Deposit: {request.deposit_status}</div>
                      ) : null}
                      {request.guest_notification_status ? (
                        <div className="muted">Notify: {request.guest_notification_status}</div>
                      ) : null}
                      {request.deposit_payment_link ? (
                        <a className="muted" href={request.deposit_payment_link} target="_blank" rel="noreferrer">
                          Open deposit link
                        </a>
                      ) : null}
                    </td>
                    <td data-label="SOP Action">{requestSopAction(request)}</td>
                    <td data-label="Handoff">
                      <div className="fd-ops-badge-stack">
                        {requestHandoffBadges(request).map((badge) => (
                          <HandoffBadge
                            key={badge.label}
                            label={badge.label}
                            variant={badge.variant as BadgeVariant}
                          />
                        ))}
                      </div>
                    </td>
                    <td data-label="Created At">{new Date(request.created_at).toLocaleString()}</td>
                    <td data-label="Actions">
                      <div className="table-actions">
                        {isConvertedRequest(request) ? (
                          <Link className="small-btn" to="/frontdesk">
                            View Booking #{request.converted_booking_id}
                          </Link>
                        ) : (
                          <>
                            {canReviewRequests ? (
                              <button
                                className="small-btn"
                                type="button"
                                disabled={requestActionId === request.id}
                                onClick={() => updateRequestStatus(request, "reviewed")}
                              >
                                Mark Reviewed
                              </button>
                            ) : null}
                            {canRequestDeposit ? (
                              <button
                                className="small-btn"
                                type="button"
                                disabled={requestActionId === request.id}
                                onClick={() => updateRequestStatus(request, "deposit_requested")}
                              >
                                {request.deposit_payment_link ? "Deposit Requested" : "Request Deposit"}
                              </button>
                            ) : null}
                            {canRejectRequests ? (
                              <button
                                className="small-btn"
                                type="button"
                                disabled={requestActionId === request.id}
                                onClick={() => updateRequestStatus(request, "rejected")}
                              >
                                Reject
                              </button>
                            ) : null}
                            {canConvertRequests ? (
                              <button
                                className="primary-btn"
                                type="button"
                                disabled={requestActionId === request.id || request.booking_status === "rejected"}
                                onClick={() => convertRequestToBooking(request)}
                              >
                                Convert to Booking
                              </button>
                            ) : null}
                            {!canUseBookingActions ? <span className="pill pill-muted">Read Only</span> : null}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="pms-empty-row" colSpan={11}>No public booking requests found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <div className="section-heading">
          <div>
            <h2>Where Each Chatbot Booking Goes</h2>
            <p className="muted">Step-by-step hotel SOP path from guest request to PMS operations handoff.</p>
          </div>
          <Link className="small-btn" to="/frontdesk">Open Front Desk</Link>
        </div>
        {publicRequests.length ? (
          <div className="booking-flow-grid">
            {publicRequests.slice(0, 4).map((request) => (
              <div className="booking-flow-card" key={request.id}>
                <div className="booking-flow-title">
                  <div>
                    <strong>{request.guest_name}</strong>
                    <span>{request.check_in_date} to {request.check_out_date}</span>
                  </div>
                  <StatusBadge status={request.booking_status} />
                </div>
                <div className="booking-workflow-list">
                  {requestWorkflowSteps(request).map((step, index) => (
                    <div className={`booking-workflow-row ${step.state}`} key={`${request.id}-${step.label}`}>
                      <span>{index + 1}</span>
                      <div>
                        <strong>{step.label}</strong>
                        <p>{step.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="notice-box">No chatbot requests are waiting in Booking Hub.</div>
        )}
      </section>

      <section className="card">
        <div className="section-heading">
          <div>
            <h2>Confirmed AI Guest Site Demo Bookings</h2>
            <p className="muted">Future family bookings created through the PMS-standard AI intake cycle.</p>
          </div>
          <div className="pill pill-success">Guaranteed</div>
        </div>
        <div className="booking-demo-grid">
          {demoFamilyBookings.map((booking) => (
            <div className="booking-demo-card" key={booking.confirmationNo}>
              <div>
                <span className="pill pill-success">{booking.status}</span>
                <h3>{booking.guestName}</h3>
                <p>{booking.confirmationNo}</p>
              </div>
              <div className="booking-demo-meta">
                <span>Stay</span>
                <strong>{booking.checkIn} to {booking.checkOut}</strong>
                <span>Rate Plan</span>
                <strong>{booking.ratePlan}</strong>
                <span>Market Segment</span>
                <strong>{booking.marketSegment}</strong>
                <span>Total Revenue</span>
                <strong>USD {booking.totalUsd}</strong>
              </div>
              <div className="booking-demo-room-list">
                {booking.rooms.map((room) => (
                  <div key={`${booking.confirmationNo}-${room.roomNumber}`}>
                    <strong>Room {room.roomNumber}</strong>
                    <span>{room.roomType} | {room.guests} guest(s) | USD {room.rateUsd}/night</span>
                  </div>
                ))}
              </div>
              <div className="booking-workflow-list">
                {demoBookingWorkflow.map((step, index) => (
                  <div className="booking-workflow-row done" key={`${booking.confirmationNo}-${step}`}>
                    <span>{index + 1}</span>
                    <div>
                      <strong>{step}</strong>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="page-grid two-col">
        <div className="card">
          <div className="section-heading">
            <div>
              <h2>Reservation Intake</h2>
              <p className="muted">Create guaranteed bookings from website chatbot or Telegram channels.</p>
            </div>
          </div>

          <form className="page-grid" onSubmit={createBooking}>
            <div className="form-grid">
              <label className="field">
                <span>Channel</span>
                <select
                  value={form.channel}
                  onChange={(event) =>
                    setForm((prev) => ({
                      ...prev,
                      channel: event.target.value as BookingForm["channel"],
                    }))
                  }
                >
                  <option value="Website Chatbot">Website Chatbot</option>
                  <option value="Telegram Bot">Telegram Bot</option>
                </select>
              </label>

              <label className="field span-2">
                <span>Guest / Group Name</span>
                <input
                  value={form.guestName}
                  onChange={(event) => setForm((prev) => ({ ...prev, guestName: event.target.value }))}
                  placeholder="Guest name or group profile"
                  required
                />
              </label>

              <label className="field">
                <span>Guest Phone</span>
                <input
                  value={form.guestPhone}
                  onChange={(event) => setForm((prev) => ({ ...prev, guestPhone: event.target.value }))}
                  placeholder="+251..."
                />
              </label>

              <label className="field span-2">
                <span>Guest Email</span>
                <input
                  type="email"
                  value={form.guestEmail}
                  onChange={(event) => setForm((prev) => ({ ...prev, guestEmail: event.target.value }))}
                  placeholder="guest@example.com"
                />
              </label>

              <label className="field">
                <span>Check-in</span>
                <input
                  type="date"
                  value={form.checkIn}
                  onChange={(event) => setForm((prev) => ({ ...prev, checkIn: event.target.value }))}
                  required
                />
              </label>

              <label className="field">
                <span>Check-out</span>
                <input
                  type="date"
                  value={form.checkOut}
                  onChange={(event) => setForm((prev) => ({ ...prev, checkOut: event.target.value }))}
                  required
                />
              </label>

              <label className="field">
                <span>Rooms</span>
                <input
                  type="number"
                  min="1"
                  value={form.rooms}
                  onChange={(event) => setForm((prev) => ({ ...prev, rooms: event.target.value }))}
                />
              </label>

              <label className="field">
                <span>Adults</span>
                <input
                  type="number"
                  min="1"
                  value={form.adults}
                  onChange={(event) => setForm((prev) => ({ ...prev, adults: event.target.value }))}
                />
              </label>

              <label className="field">
                <span>Children</span>
                <input
                  type="number"
                  min="0"
                  value={form.children}
                  onChange={(event) => setForm((prev) => ({ ...prev, children: event.target.value }))}
                />
              </label>

              <label className="field">
                <span>Room Type</span>
                <select
                  value={form.roomType}
                  onChange={(event) => setForm((prev) => ({ ...prev, roomType: event.target.value }))}
                >
                  <option>Standard Room</option>
                  <option>Deluxe King</option>
                  <option>Twin Room</option>
                  <option>Suite</option>
                </select>
              </label>

              <label className="field">
                <span>Rate / Room / Night</span>
                <input
                  type="number"
                  min="0"
                  value={form.rate}
                  onChange={(event) => setForm((prev) => ({ ...prev, rate: event.target.value }))}
                />
              </label>

              <label className="field">
                <span>Rate Code</span>
                <select
                  value={form.rateCode}
                  onChange={(event) =>
                    setForm((prev) => ({
                      ...prev,
                      rateCode: event.target.value as BookingForm["rateCode"],
                    }))
                  }
                >
                  <option value="BAR">BAR - Best Available</option>
                  <option value="CORP">CORP - Corporate</option>
                  <option value="GRP10">GRP10 - Group</option>
                </select>
              </label>

              <label className="field">
                <span>Guarantee Status</span>
                <select
                  value={form.paymentStatus}
                  onChange={(event) =>
                    setForm((prev) => ({
                      ...prev,
                      paymentStatus: event.target.value as BookingForm["paymentStatus"],
                    }))
                  }
                >
                  <option value="pending">Pending Guarantee</option>
                  <option value="guaranteed">Guarantee on File</option>
                  <option value="deposit_paid">Deposit Paid</option>
                  <option value="paid">Paid</option>
                </select>
              </label>

              <label className="field">
                <span>Purpose</span>
                <select
                  value={form.purposeOfVisit}
                  onChange={(event) => setForm((prev) => ({ ...prev, purposeOfVisit: event.target.value }))}
                >
                  <option>Leisure</option>
                  <option>Business</option>
                  <option>Family</option>
                  <option>Group</option>
                  <option>Event</option>
                </select>
              </label>

              <label className="field span-3">
                <span>Reservation Notes</span>
                <textarea
                  value={form.notes}
                  onChange={(event) => setForm((prev) => ({ ...prev, notes: event.target.value }))}
                  placeholder="Arrival time, guest count, guarantee details, special requests"
                />
              </label>
            </div>

            <div className="rate-quote-panel">
              <div>
                <span className="muted">Rate Plan</span>
                <strong>{quote ? `${quote.rate_code} - ${quote.rate_label}` : form.rateCode}</strong>
              </div>
              <div>
                <span className="muted">Room Total</span>
                <strong>{money(quote?.room_subtotal_etb ?? stayNights * roomCount * rate)}</strong>
              </div>
              <div>
                <span className="muted">Service / Tax</span>
                <strong>{quote ? `${money(quote.service_charge_etb)} / ${money(quote.tax_etb)}` : "-"}</strong>
              </div>
              <div>
                <span className="muted">Grand Total</span>
                <strong>{money(totalAmount)}</strong>
              </div>
              <div>
                <span className="muted">Deposit Required</span>
                <strong>{quote ? money(quote.deposit_required_etb) : "-"}</strong>
              </div>
              <div>
                <span className="muted">Policy</span>
                <strong>{quote ? quote.cancellation_policy : "Check availability to calculate PMS quote"}</strong>
              </div>
              <div>
                <span className="muted">Rules Applied</span>
                <strong>{quote?.applied_rules?.length ? quote.applied_rules.join(", ") : "-"}</strong>
              </div>
            </div>

            <div className="form-actions">
              <button className="small-btn" type="button" onClick={() => checkAvailability()} disabled={loading}>
                {loading ? "Checking..." : "Check Availability"}
              </button>
              <button className="primary-btn" type="submit" disabled={saving}>
                {saving ? "Creating..." : "Create Booking"}
              </button>
            </div>
          </form>
        </div>

        <div className="card">
          <div className="section-heading">
            <div>
              <h2>Channel Control</h2>
              <p className="muted">PMS-standard handover from booking source to reservations and front desk.</p>
            </div>
          </div>

          <div className="source-matrix">
            {channelSummary.length ? (
              channelSummary.map((item) => (
                <div className="source-row" key={item.source}>
                  <strong>{item.source}</strong>
                  <span>{item.count} booking(s)</span>
                </div>
              ))
            ) : (
              <div className="notice-box">No channel bookings found for this business date.</div>
            )}
          </div>

          <div className="frontdesk-readiness">
            <div>
              <span className="muted">Guarantee</span>
              <strong>Required</strong>
            </div>
            <div>
              <span className="muted">Room Assignment</span>
              <strong>Front Desk</strong>
            </div>
            <div>
              <span className="muted">Guest Profile</span>
              <strong>Captured</strong>
            </div>
          </div>

          <div className="form-actions" style={{ marginTop: 16 }}>
            <Link className="small-btn" to="/booking/guest">Open Guest Booking</Link>
            <Link className="small-btn" to="/booking-assistant">Open Assistant</Link>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="section-heading">
          <div>
            <h2>Reservation Pipeline</h2>
            <p className="muted">Bookings touching the selected business date.</p>
          </div>
        </div>

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Guest</th>
                <th>Source</th>
                <th>Stay</th>
                <th>Room</th>
                <th>Status</th>
                <th>Next SOP Step</th>
                <th>Handoff</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {bookings.length ? (
                bookings.map((booking) => (
                  <tr key={booking.id}>
                    <td data-label="Guest">{booking.guest_name}</td>
                    <td data-label="Source">{sourceOf(booking)}</td>
                    <td data-label="Stay">{booking.check_in_date} to {booking.check_out_date}</td>
                    <td data-label="Room">{booking.room_number || booking.room_type || "TBD"}</td>
                    <td data-label="Status">{booking.booking_status}</td>
                    <td data-label="Next SOP Step">{bookingNextStep(booking)}</td>
                    <td data-label="Handoff">
                      <div className="fd-ops-badge-stack">
                        {bookingHandoffBadges(booking).map((badge) => (
                          <HandoffBadge
                            key={badge.label}
                            label={badge.label}
                            variant={badge.variant as BadgeVariant}
                          />
                        ))}
                      </div>
                    </td>
                    <td data-label="Total">{booking.total_amount ? money(Number(booking.total_amount)) : "-"}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="pms-empty-row" colSpan={8}>No reservations found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
