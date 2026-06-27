import { useEffect, useMemo, useState } from "react";
import PageHeader from "../../components/PageHeader";
import DataTable from "../../components/DataTable";
import { LoadingState } from "../../components/ui/LoadingState";
import { usePmsContext } from "../../context/PmsContext";
import {
  fetchFrontdeskBookings,
  fetchGuestFeedback,
} from "../../services/pmsService";
import { getErrorMessage } from "../../services/http";
import type { FrontdeskBooking, GuestFeedback } from "../../types/pms";

const guestTabs = [
  "Profile Summary",
  "Reservations",
  "Stay History",
  "Preferences",
  "Billing",
  "Documents",
  "Messages",
  "Feedback",
  "Service Recovery",
  "Audit Trail",
] as const;

type GuestTab = (typeof guestTabs)[number];

function money(value: number | null | undefined) {
  return `ETB ${Number(value || 0).toLocaleString("en-US")}`;
}

function bookingStatus(row: FrontdeskBooking) {
  return String(row.booking_status || "").replace(/_/g, " ");
}

function statusClass(status: string) {
  const normalized = String(status || "").toLowerCase();
  if (["confirmed", "checked_in", "in_house", "closed", "reviewed"].includes(normalized)) {
    return "pill pill-success";
  }
  if (["new", "pending", "reserved", "service_recovery", "open"].includes(normalized)) {
    return "pill pill-warning";
  }
  if (["cancelled", "no_show", "blocked"].includes(normalized)) return "pill pill-danger";
  return "pill";
}

export default function GuestProfilesPage() {
  const { propertyCode, businessDate, refreshKey } = usePmsContext();
  const [bookings, setBookings] = useState<FrontdeskBooking[]>([]);
  const [feedback, setFeedback] = useState<GuestFeedback[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<GuestTab>("Profile Summary");
  const [search, setSearch] = useState("");
  const [selectedGuestName, setSelectedGuestName] = useState("");

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError("");
        const [bookingRows, feedbackRows] = await Promise.all([
          fetchFrontdeskBookings(propertyCode, businessDate),
          fetchGuestFeedback(propertyCode),
        ]);
        setBookings(bookingRows);
        setFeedback(feedbackRows);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [businessDate, propertyCode, refreshKey]);

  const guests = useMemo(() => {
    const map = new Map<string, {
      guestName: string;
      email?: string | null;
      phone?: string | null;
      reservations: FrontdeskBooking[];
      feedback: GuestFeedback[];
      totalSpend: number;
      lastStay?: string;
      upcomingStay?: string;
      balance: number;
      vip: boolean;
      preferences: string[];
    }>();

    bookings.forEach((row) => {
      const key = row.guest_name || "Guest";
      const current = map.get(key) || {
        guestName: key,
        email: row.guest_email,
        phone: null,
        reservations: [],
        feedback: [],
        totalSpend: 0,
        lastStay: row.check_out_date,
        upcomingStay: undefined,
        balance: 0,
        vip: false,
        preferences: [],
      };
      current.reservations.push(row);
      current.email = current.email || row.guest_email;
      current.totalSpend += Number(row.total_amount || row.rate_per_night_etb || 0);
      current.balance += Number(row.balance_due || 0);
      if (row.check_out_date <= businessDate) {
        current.lastStay = [current.lastStay, row.check_out_date].filter(Boolean).sort().reverse()[0];
      }
      if (row.check_in_date >= businessDate) {
        current.upcomingStay = [current.upcomingStay, row.check_in_date].filter(Boolean).sort()[0];
      }
      current.vip = current.vip || String(row.notes || row.special_requests || row.source || "").toLowerCase().includes("vip");
      const preferenceText = String(row.special_requests || row.notes || "").trim();
      if (preferenceText && !current.preferences.includes(preferenceText)) {
        current.preferences.push(preferenceText);
      }
      map.set(key, current);
    });

    feedback.forEach((row) => {
      const key = row.guest_name || "Guest";
      const current = map.get(key) || {
        guestName: key,
        reservations: [],
        feedback: [],
        totalSpend: 0,
        balance: 0,
        vip: false,
        preferences: [],
      };
      current.feedback.push(row);
      map.set(key, current);
    });

    const needle = search.trim().toLowerCase();
    return Array.from(map.values()).filter((guest) =>
      !needle ||
      guest.guestName.toLowerCase().includes(needle) ||
      String(guest.email || "").toLowerCase().includes(needle)
    );
  }, [bookings, businessDate, feedback, search]);

  useEffect(() => {
    if (!guests.length) {
      setSelectedGuestName("");
      return;
    }
    if (!selectedGuestName || !guests.some((guest) => guest.guestName === selectedGuestName)) {
      setSelectedGuestName(guests[0].guestName);
    }
  }, [guests, selectedGuestName]);

  const selectedGuest = guests.find((guest) => guest.guestName === selectedGuestName) || guests[0];
  const openRecovery = selectedGuest?.feedback.filter((row) =>
    ["new", "service_recovery"].includes(String(row.status || "").toLowerCase())
  ).length || 0;
  const activeReservations = selectedGuest?.reservations.filter((row) =>
    !["checked_out", "cancelled", "no_show", "no-show"].includes(String(row.booking_status || "").toLowerCase())
  ) || [];
  const stayHistory = selectedGuest?.reservations.filter((row) =>
    ["checked_out", "in_house", "checked_in"].includes(String(row.booking_status || "").toLowerCase()) ||
    row.check_out_date <= businessDate
  ) || [];
  const auditRows = [
    ...(selectedGuest?.reservations || []).slice(0, 6).map((row) => ({
      date: row.check_in_date,
      action: `Reservation ${row.confirmation_id || row.id}`,
      source: row.source || row.channel || "PMS",
      status: bookingStatus(row),
    })),
    ...(selectedGuest?.feedback || []).slice(0, 4).map((row) => ({
      date: row.created_at || businessDate,
      action: `Feedback ${row.rating ? `${row.rating}/5` : "received"}`,
      source: row.feedback_source || "Guest Feedback",
      status: row.status,
    })),
  ];

  return (
    <div className="page-grid guest-360-command">
      <PageHeader
        title="Guest Profiles"
        subtitle="Guest CRM, stay history, preferences, billing context, and service recovery."
        metadata={`${propertyCode} • ${businessDate}`}
        rightSlot={<span className="pill">{guests.length} guest profile(s)</span>}
      />

      {loading ? (
        <LoadingState label="Loading guest profiles..." />
      ) : (
        <>
          {error ? <div className="error-box">{error}</div> : null}

          <section className="guest-360-shell">
            <aside className="guest-360-list card">
              <div className="field">
                <label>Search Guest</label>
                <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Guest name or email" />
              </div>
              <div className="guest-360-profile-list">
                {guests.length ? guests.slice(0, 12).map((guest) => (
                  <button
                    key={guest.guestName}
                    type="button"
                    className={`guest-360-profile-row ${selectedGuest?.guestName === guest.guestName ? "active" : ""}`}
                    onClick={() => setSelectedGuestName(guest.guestName)}
                  >
                    <strong>{guest.guestName}</strong>
                    <span>{guest.reservations.length} stay record(s) | {money(guest.totalSpend)}</span>
                  </button>
                )) : (
                  <div className="empty-state">No guest profiles found for the selected business date.</div>
                )}
              </div>
            </aside>

            <main className="guest-360-main card">
              <div className="guest-360-header">
                <div>
                  <span>Guest Profile</span>
                  <h2>{selectedGuest?.guestName || "No Guest Selected"}</h2>
                  <p>{selectedGuest?.email || "Contact details can be completed from Front Desk registration."}</p>
                </div>
                <div className="guest-360-kpis">
                  <div><span>Stays</span><strong>{selectedGuest?.reservations.length || 0}</strong></div>
                  <div><span>Total Spend</span><strong>{money(selectedGuest?.totalSpend)}</strong></div>
                  <div><span>Open Recovery</span><strong>{openRecovery}</strong></div>
                  <div><span>VIP</span><strong>{selectedGuest?.vip ? "Yes" : "No"}</strong></div>
                </div>
              </div>

              <section className="guest-360-profile-card">
                <div>
                  <span>Contact Details</span>
                  <strong>{selectedGuest?.email || "Email not captured"}</strong>
                  <small>{selectedGuest?.phone || "Phone pending registration update"}</small>
                </div>
                <div>
                  <span>VIP / Loyalty</span>
                  <strong>{selectedGuest?.vip ? "VIP Guest" : "Standard Guest"}</strong>
                  <small>Loyalty tier placeholder</small>
                </div>
                <div>
                  <span>Preferences</span>
                  <strong>{selectedGuest?.preferences?.[0] || "No preference recorded"}</strong>
                  <small>{(selectedGuest?.preferences.length || 0) > 1 ? `${selectedGuest?.preferences.length} notes` : "From reservation notes"}</small>
                </div>
                <div>
                  <span>Last Stay</span>
                  <strong>{selectedGuest?.lastStay || "No past stay"}</strong>
                  <small>Derived from booking history</small>
                </div>
                <div>
                  <span>Upcoming Stay</span>
                  <strong>{selectedGuest?.upcomingStay || "No upcoming stay"}</strong>
                  <small>Future reservation view</small>
                </div>
                <div>
                  <span>Balance / Folio</span>
                  <strong>{money(selectedGuest?.balance)}</strong>
                  <small>Safe summary from loaded bookings</small>
                </div>
                <div>
                  <span>Feedback / Recovery</span>
                  <strong>{openRecovery ? `${openRecovery} open` : "Clear"}</strong>
                  <small>{selectedGuest?.feedback.length || 0} feedback record(s)</small>
                </div>
              </section>

              <div className="guest-360-tabs">
                {guestTabs.map((tab) => (
                  <button key={tab} className={`tab-btn ${activeTab === tab ? "active" : ""}`} type="button" onClick={() => setActiveTab(tab)}>
                    {tab}
                  </button>
                ))}
              </div>

              {activeTab === "Profile Summary" ? (
                <div className="guest-360-summary-grid">
                  <section>
                    <h3>Current Reservations</h3>
                    <DataTable
                      rows={activeReservations.slice(0, 5)}
                      emptyMessage="No active or upcoming reservations for this guest."
                      columns={[
                        { key: "id", header: "Booking", render: (row) => row.confirmation_id || row.id },
                        { key: "stay", header: "Stay", render: (row) => `${row.check_in_date} to ${row.check_out_date}` },
                        { key: "status", header: "Status", render: (row) => <span className={statusClass(row.booking_status)}>{bookingStatus(row)}</span> },
                      ]}
                    />
                  </section>
                  <section>
                    <h3>Service Recovery</h3>
                    <DataTable
                      rows={(selectedGuest?.feedback || []).filter((row) => ["new", "service_recovery"].includes(String(row.status || "").toLowerCase())).slice(0, 5)}
                      emptyMessage="No open service recovery cases."
                      columns={[
                        { key: "status", header: "Status", render: (row) => <span className={statusClass(row.status)}>{row.status}</span> },
                        { key: "comment", header: "Comment", render: (row) => row.comment || "-" },
                      ]}
                    />
                  </section>
                </div>
              ) : activeTab === "Reservations" ? (
                <DataTable
                  rows={activeReservations}
                  emptyMessage="No active or future reservations available for this guest yet."
                  columns={[
                    { key: "id", header: "Booking", render: (row) => row.confirmation_id || row.id },
                    { key: "stay", header: "Stay", render: (row) => `${row.check_in_date} to ${row.check_out_date}` },
                    { key: "room", header: "Room", render: (row) => row.room_number || row.room_type || "-" },
                    { key: "status", header: "Status", render: (row) => <span className={statusClass(row.booking_status)}>{bookingStatus(row)}</span> },
                    { key: "amount", header: "Amount", render: (row) => money(row.total_amount || row.rate_per_night_etb) },
                  ]}
                />
              ) : activeTab === "Stay History" ? (
                <DataTable
                  rows={stayHistory}
                  emptyMessage="No completed stay history is available for this guest yet."
                  columns={[
                    { key: "id", header: "Booking", render: (row) => row.confirmation_id || row.id },
                    { key: "stay", header: "Stay", render: (row) => `${row.check_in_date} to ${row.check_out_date}` },
                    { key: "room", header: "Room", render: (row) => row.room_number || row.room_type || "-" },
                    { key: "amount", header: "Spend", render: (row) => money(row.total_amount || row.rate_per_night_etb) },
                  ]}
                />
              ) : activeTab === "Preferences" ? (
                <div className="guest-360-coming-soon">
                  <strong>Guest Preferences</strong>
                  <span>{selectedGuest?.preferences.length ? selectedGuest.preferences.join(" | ") : "No preferences recorded yet. Use Front Desk registration notes to capture pillow, room, diet, and VIP preferences."}</span>
                </div>
              ) : activeTab === "Billing" ? (
                <DataTable
                  rows={selectedGuest?.reservations || []}
                  emptyMessage="No billing records are available from loaded bookings."
                  columns={[
                    { key: "booking", header: "Booking", render: (row) => row.confirmation_id || row.id },
                    { key: "charges", header: "Charges", render: (row) => money(row.total_amount || row.rate_per_night_etb) },
                    { key: "balance", header: "Balance", render: (row) => money(row.balance_due) },
                    { key: "payment", header: "Payment", render: (row) => row.payment_status || row.payment_method || "-" },
                  ]}
                />
              ) : activeTab === "Feedback" || activeTab === "Service Recovery" ? (
                <DataTable
                  rows={
                    activeTab === "Service Recovery"
                      ? (selectedGuest?.feedback || []).filter((row) => String(row.status || "").toLowerCase() === "service_recovery")
                      : selectedGuest?.feedback || []
                  }
                  emptyMessage="No guest feedback or recovery cases are linked yet."
                  columns={[
                    { key: "rating", header: "Rating", render: (row) => row.rating ? `${row.rating}/5` : "-" },
                    { key: "status", header: "Status", render: (row) => <span className={statusClass(row.status)}>{row.status}</span> },
                    { key: "source", header: "Source", render: (row) => row.feedback_source || "-" },
                    { key: "comment", header: "Comment", render: (row) => row.comment || "-" },
                  ]}
                />
              ) : activeTab === "Audit Trail" ? (
                <DataTable
                  rows={auditRows}
                  emptyMessage="No audit trail entries are available from the current guest data."
                  columns={[
                    { key: "date", header: "Date", render: (row) => row.date },
                    { key: "action", header: "Action", render: (row) => row.action },
                    { key: "source", header: "Source", render: (row) => row.source },
                    { key: "status", header: "Status", render: (row) => <span className={statusClass(row.status)}>{row.status}</span> },
                  ]}
                />
              ) : (
                <div className="guest-360-coming-soon">
                  <strong>{activeTab}</strong>
                  <span>
                    {activeTab === "Documents" || activeTab === "Messages"
                      ? "Coming soon. Dedicated document/message backend data is not available yet."
                      : "Coming soon in the Guest 360 CRM. Existing guest and reservation data remains available."}
                  </span>
                </div>
              )}
            </main>
          </section>
        </>
      )}
    </div>
  );
}
