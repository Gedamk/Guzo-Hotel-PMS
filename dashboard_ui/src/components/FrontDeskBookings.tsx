import React, {
  useEffect,
  useMemo,
  useState,
  useCallback,
} from "react";
import axios from "axios";
import FrontDeskHouseCount from "./FrontDeskHouseCount";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "admin-secret-123";

// --- date helpers ----------------------------------------------------------

const toLocalDate = (isoDate: string): Date => {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day);
};

const isSameDay = (a: string, b: string): boolean => {
  if (!a || !b) return false;
  return a === b;
};

// Approximate number of rooms per property
const ROOMS_TOTAL_BY_PROPERTY: Record<string, number> = {
  DRE001: 60,
  "N&N002": 45,
};

// Map property_code -> hotel name
const HOTEL_NAME_BY_PROPERTY: Record<string, string> = {
  DRE001: "Dream Big Hotel",
  "N&N002": "N&N Luxury Hotel",
};

type BookingStatus =
  | "confirmed"
  | "in_house"
  | "checked_out"
  | "cancelled"
  | "no_show"
  | string;

type BackendBooking = {
  id: number;
  booking_code: string | null;
  guest_name: string;
  room_number: string | null;
  room_type: string | null;
  check_in: string;
  check_out: string;
  status: string;
  channel: string | null;
  total_amount_etb: number | null;
  created_at: string;
  updated_at: string;
  notes: string | null;
  property_code: string | null;
};

type Booking = {
  id: number;
  guest_name: string;
  property_code: string;
  hotel_name: string;
  check_in: string;
  check_out: string;
  status: BookingStatus;
  channel: string;
  total_amount_etb: number;
  room_number?: string | null;
  guest_note?: string | null;
};

type BookingStatusUpdate = {
  new_status: BookingStatus;
};

// Ethiopian room status item from /rooms/status-list
type RoomStatusItem = {
  property_code: string;
  room_number: string;
  room_type: string | null;
  floor: number | string | null;
  status: string; // 'available', 'vacant_dirty', 'ooo', ...
  current_booking_id: number | null;
  current_guest_name: string | null;
  check_in: string | null;
  check_out: string | null;
};

// format status label
const formatStatusLabel = (status: BookingStatus): string => {
  if (!status) return "pending";
  return String(status).replace(/_/g, " ");
};

type Scope = "today" | "inhouse" | "arrivals" | "departures" | "all";

const scopeOptions: { value: Scope; label: string }[] = [
  { value: "today", label: "Today (touches business date)" },
  { value: "inhouse", label: "In-House" },
  { value: "arrivals", label: "Arrivals" },
  { value: "departures", label: "Departures" },
  { value: "all", label: "All (±30 days)" },
];

// --- API helpers: explicit room assign / clear -----------------------------

const assignRoomExplicit = async (
  bookingId: number,
  roomNumber: string
): Promise<void> => {
  await axios.post(
    `${API_BASE}/bookings/${bookingId}/assign-room`,
    {
      room_number: roomNumber,
      force: false,
    },
    {
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
};

const clearRoomExplicit = async (bookingId: number): Promise<void> => {
  await axios.post(`${API_BASE}/bookings/${bookingId}/clear-room`);
};

// --- Component -------------------------------------------------------------

const FrontDeskConsole: React.FC = () => {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [roomsByProperty, setRoomsByProperty] = useState<
    Record<string, RoomStatusItem[]>
  >({});

  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedProperty, setSelectedProperty] = useState<string>("ALL");
  const [scope, setScope] = useState<Scope>("today");

  // Business date (hotel business day)
  const realToday = new Date();
  const todayStr = realToday.toISOString().slice(0, 10); // YYYY-MM-DD
  const [businessDate, setBusinessDate] = useState<string>(todayStr);

  const businessDateObj = useMemo(
    () => toLocalDate(businessDate),
    [businessDate]
  );

  const fetchBookings = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const headers = {
        Authorization: `Bearer ${AUTH_TOKEN}`,
      };

      // Matches FastAPI: /frontdesk/bookings?scope=...&date=YYYY-MM-DD
      const res = await axios.get<BackendBooking[]>(
        `${API_BASE}/frontdesk/bookings`,
        {
          headers,
          params: {
            scope,
            date: businessDate,
          },
        }
      );

      const mapped: Booking[] = (res.data || []).map((b) => {
        const propertyCode = b.property_code || "UNKNOWN";
        const hotelName =
          HOTEL_NAME_BY_PROPERTY[propertyCode] || propertyCode || "N/A";

        return {
          id: b.id,
          guest_name: b.guest_name,
          property_code: propertyCode,
          hotel_name: hotelName,
          check_in: b.check_in,
          check_out: b.check_out,
          status: (b.status as BookingStatus) || "confirmed",
          channel: b.channel || "",
          total_amount_etb: b.total_amount_etb ?? 0,
          room_number: b.room_number,
          guest_note: b.notes,
        };
      });

      setBookings(mapped);

      // Load rooms/status for each property in these bookings
      const propertyCodes = Array.from(
        new Set(mapped.map((b) => b.property_code))
      );

      const roomsMap: Record<string, RoomStatusItem[]> = {};

      await Promise.all(
        propertyCodes.map(async (prop) => {
          try {
            const resp = await axios.get<RoomStatusItem[]>(
              `${API_BASE}/rooms/status-list`,
              {
                params: {
                  property_code: prop,
                  business_date: businessDate,
                },
              }
            );
            roomsMap[prop] = resp.data || [];
          } catch (e) {
            console.warn("Failed to load rooms for property", prop, e);
            roomsMap[prop] = [];
          }
        })
      );

      setRoomsByProperty(roomsMap);
    } catch (err: any) {
      console.error(err);
      setError(
        err?.response?.data?.detail ||
          err.message ||
          "Failed to load bookings"
      );
    } finally {
      setLoading(false);
    }
  }, [scope, businessDate]);

  useEffect(() => {
    fetchBookings();
  }, [fetchBookings]);

  // Optional auto-refresh
  useEffect(() => {
    const id = setInterval(() => {
      fetchBookings();
    }, 45_000);
    return () => clearInterval(id);
  }, [fetchBookings]);

  // -------------------------------------------------------------------------
  // Room helpers (from rooms/status-list)
  // -------------------------------------------------------------------------

  const getAssignedRoomNumber = useCallback(
    (b: Booking): string | null => {
      const list = roomsByProperty[b.property_code] || [];

      // priority 1: status-list mapping
      const matched = list.find((r) => r.current_booking_id === b.id);
      if (matched) return matched.room_number;

      // priority 2: booking.room_number
      if (b.room_number) return b.room_number;

      return null;
    },
    [roomsByProperty]
  );

  const getRoomOptions = useCallback(
    (property_code: string): RoomStatusItem[] => {
      const list = roomsByProperty[property_code] || [];
      // exclude OOO rooms from options
      return list.filter(
        (r) => (r.status || "").toLowerCase() !== "ooo"
      );
    },
    [roomsByProperty]
  );

  // -------------------------------------------------------------------------
  // Derived data (filters, KPIs)
  // -------------------------------------------------------------------------

  const propertyOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const b of bookings) {
      if (!map.has(b.property_code)) {
        map.set(b.property_code, b.hotel_name);
      }
    }
    return Array.from(map.entries()).map(([code, name]) => ({ code, name }));
  }, [bookings]);

  const filteredBookings = useMemo(() => {
    if (selectedProperty === "ALL") return bookings;
    return bookings.filter((b) => b.property_code === selectedProperty);
  }, [bookings, selectedProperty]);

  const calcNights = (ci: string, co: string) => {
    const a = toLocalDate(ci);
    const b = toLocalDate(co);
    const diffMs = b.getTime() - a.getTime();
    return Math.max(diffMs / (1000 * 60 * 60 * 24), 0);
  };

  const isInHouse = (b: Booking) => b.status === "in_house";

  const arrivalsToday = filteredBookings.filter(
    (b) => b.status === "confirmed" && isSameDay(b.check_in, businessDate)
  );

  const departuresToday = filteredBookings.filter(
    (b) => b.status === "in_house" && isSameDay(b.check_out, businessDate)
  );

  const inHouse = filteredBookings.filter(isInHouse);

  const cancelled = filteredBookings.filter(
    (b) => b.status === "cancelled" || b.status === "no_show"
  );

  const upcoming = filteredBookings.filter(
    (b) => b.status === "confirmed" && b.check_in > businessDate
  );

  const roomsOccupiedToday = inHouse.length;
  let roomsTotalForScope = 0;

  if (selectedProperty === "ALL") {
    const seenProps = new Set<string>();
    for (const b of filteredBookings) {
      if (!seenProps.has(b.property_code)) {
        seenProps.add(b.property_code);
        roomsTotalForScope +=
          ROOMS_TOTAL_BY_PROPERTY[b.property_code] ?? 0;
      }
    }
  } else {
    roomsTotalForScope =
      ROOMS_TOTAL_BY_PROPERTY[selectedProperty] ??
      roomsOccupiedToday ??
      0;
  }

  const occupancyPct =
    roomsTotalForScope > 0
      ? (roomsOccupiedToday / roomsTotalForScope) * 100
      : 0;

  const handleStatusChange = async (
    bookingId: number,
    newStatus: BookingStatus
  ) => {
    try {
      setBusyId(bookingId);

      const payload: BookingStatusUpdate = { new_status: newStatus };

      const res = await axios.patch(
        `${API_BASE}/frontdesk/bookings/${bookingId}/status`,
        payload,
        {
          headers: {
            Authorization: `Bearer ${AUTH_TOKEN}`,
            "Content-Type": "application/json",
          },
        }
      );

      const updated = res.data as Booking;
      setBookings((prev) =>
        prev.map((b) => (b.id === bookingId ? updated : b))
      );
      await fetchBookings();
    } catch (err) {
      console.error(err);
      alert("Failed to update booking status");
    } finally {
      setBusyId(null);
    }
  };

  const handleRoomChange = async (
    bookingId: number,
    roomNumber: string
  ) => {
    if (!roomNumber) return;
    try {
      setBusyId(bookingId);
      await assignRoomExplicit(bookingId, roomNumber);
      await fetchBookings();
    } catch (err) {
      console.error(err);
      alert("Failed to assign room");
    } finally {
      setBusyId(null);
    }
  };

  const handleClearRoom = async (bookingId: number) => {
    try {
      setBusyId(bookingId);
      await clearRoomExplicit(bookingId);
      await fetchBookings();
    } catch (err) {
      console.error(err);
      alert("Failed to clear room");
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return <div style={{ padding: "1rem" }}>Loading front desk view…</div>;
  }

  if (error) {
    return (
      <div style={{ padding: "1rem", color: "red" }}>
        Error loading bookings: {error}
      </div>
    );
  }

  const selectedHotelLabel =
    selectedProperty === "ALL"
      ? "All Properties"
      : propertyOptions.find((p) => p.code === selectedProperty)?.name ||
        selectedProperty;

  const currentScopeLabel =
    scopeOptions.find((s) => s.value === scope)?.label || "Today";

  const businessDateLabel = businessDateObj.toLocaleDateString(
    undefined,
    {
      year: "numeric",
      month: "short",
      day: "numeric",
    }
  );

  return (
    <div
      style={{
        padding: "1.5rem",
        fontFamily:
          "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      }}
    >
      <h1
        style={{
          fontSize: "1.8rem",
          fontWeight: 700,
          marginBottom: "0.25rem",
        }}
      >
        🛎 Front Desk – Room Division Console
      </h1>

      <p style={{ marginBottom: "0.5rem", color: "#555" }}>
        Business Date: <strong>{businessDateLabel}</strong>
      </p>

      {/* Filters row: scope + business date + property */}
      <div
        style={{
          marginBottom: "1rem",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: "0.75rem",
        }}
      >
        <span style={{ fontSize: "0.9rem", color: "#555" }}>
          View scope:
        </span>

        <select
          value={scope}
          onChange={(e) => setScope(e.target.value as Scope)}
          style={{
            padding: "0.35rem 0.75rem",
            borderRadius: "999px",
            border: "1px solid #ccc",
            fontSize: "0.9rem",
          }}
        >
          {scopeOptions.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>

        <span
          style={{
            fontSize: "0.9rem",
            color: "#555",
            marginLeft: "1rem",
          }}
        >
          Business date:
        </span>

        <input
          type="date"
          value={businessDate}
          onChange={(e) => setBusinessDate(e.target.value)}
          style={{
            padding: "0.35rem 0.75rem",
            borderRadius: "999px",
            border: "1px solid #ccc",
            fontSize: "0.9rem",
          }}
        />

        <span
          style={{
            fontSize: "0.9rem",
            color: "#555",
            marginLeft: "1rem",
          }}
        >
          Property:
        </span>

        <select
          value={selectedProperty}
          onChange={(e) => setSelectedProperty(e.target.value)}
          style={{
            padding: "0.35rem 0.75rem",
            borderRadius: "999px",
            border: "1px solid #ccc",
            fontSize: "0.9rem",
          }}
        >
          <option value="ALL">All Properties</option>
          {propertyOptions.map((p) => (
            <option key={p.code} value={p.code}>
              {p.name} ({p.code})
            </option>
          ))}
        </select>

        <span style={{ fontSize: "0.85rem", color: "#777" }}>
          Viewing: <strong>{selectedHotelLabel}</strong> –{" "}
          <span>{currentScopeLabel}</span>
        </span>
      </div>

      {/* Ethiopian style house count widget */}
      <div style={{ marginBottom: "1.5rem" }}>
        <FrontDeskHouseCount />
      </div>

      {/* KPI cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <KpiCard label="Arrivals (Business Date)" value={arrivalsToday.length.toString()} />
        <KpiCard label="In-House Rooms" value={inHouse.length.toString()} />
        <KpiCard
          label="Departures (Business Date)"
          value={departuresToday.length.toString()}
        />
        <KpiCard
          label="Cancelled / No-Show"
          value={cancelled.length.toString()}
        />
        <KpiCard
          label="Occupancy (Rooms)"
          value={occupancyPct.toFixed(1) + "%"}
        />
      </div>

      {/* Sections */}
      <Section
        title="🟢 Arrivals (Business Date)"
        bookings={arrivalsToday}
        calcNights={calcNights}
        onStatusChange={handleStatusChange}
        getAssignedRoomNumber={getAssignedRoomNumber}
        getRoomOptions={getRoomOptions}
        onRoomChange={handleRoomChange}
        onClearRoom={handleClearRoom}
        busyId={busyId}
        mode="arrivals"
      />

      <Section
        title="🟡 In-House"
        bookings={inHouse}
        calcNights={calcNights}
        onStatusChange={handleStatusChange}
        getAssignedRoomNumber={getAssignedRoomNumber}
        getRoomOptions={getRoomOptions}
        onRoomChange={handleRoomChange}
        onClearRoom={handleClearRoom}
        busyId={busyId}
        mode="in_house"
      />

      <Section
        title="🔵 Departures (Business Date)"
        bookings={departuresToday}
        calcNights={calcNights}
        onStatusChange={handleStatusChange}
        getAssignedRoomNumber={getAssignedRoomNumber}
        getRoomOptions={getRoomOptions}
        onRoomChange={handleRoomChange}
        onClearRoom={handleClearRoom}
        busyId={busyId}
        mode="departures"
      />

      <Section
        title="📆 Upcoming Bookings"
        bookings={upcoming}
        calcNights={calcNights}
        onStatusChange={handleStatusChange}
        getAssignedRoomNumber={getAssignedRoomNumber}
        getRoomOptions={getRoomOptions}
        onRoomChange={handleRoomChange}
        onClearRoom={handleClearRoom}
        busyId={busyId}
        mode="upcoming"
      />

      <Section
        title="❌ Cancelled / No-Show"
        bookings={cancelled}
        calcNights={calcNights}
        onStatusChange={handleStatusChange}
        getAssignedRoomNumber={getAssignedRoomNumber}
        getRoomOptions={getRoomOptions}
        onRoomChange={handleRoomChange}
        onClearRoom={handleClearRoom}
        busyId={busyId}
        mode="readonly"
      />
    </div>
  );
};

// --- KPI Card -------------------------------------------------------

const KpiCard: React.FC<{ label: string; value: string }> = ({
  label,
  value,
}) => (
  <div
    style={{
      borderRadius: "0.75rem",
      border: "1px solid #e2e2e2",
      padding: "0.9rem",
      backgroundColor: "#fff",
      boxShadow: "0 1px 3px rgba(0, 0, 0, 0.04)",
    }}
  >
    <div
      style={{
        fontSize: "0.85rem",
        color: "#777",
        marginBottom: "0.25rem",
      }}
    >
      {label}
    </div>

    <div style={{ fontSize: "1.3rem", fontWeight: 600 }}>{value}</div>
  </div>
);

// --- Section -------------------------------------------------------

type SectionMode =
  | "arrivals"
  | "in_house"
  | "departures"
  | "upcoming"
  | "readonly";

type SectionProps = {
  title: string;
  bookings: Booking[];
  calcNights: (ci: string, co: string) => number;
  onStatusChange: (id: number, newStatus: BookingStatus) => void;
  getAssignedRoomNumber: (b: Booking) => string | null;
  getRoomOptions: (property_code: string) => RoomStatusItem[];
  onRoomChange: (id: number, roomNumber: string) => void;
  onClearRoom: (id: number) => void;
  busyId: number | null;
  mode: SectionMode;
};

const Section: React.FC<SectionProps> = ({
  title,
  bookings,
  calcNights,
  onStatusChange,
  getAssignedRoomNumber,
  getRoomOptions,
  onRoomChange,
  onClearRoom,
  busyId,
  mode,
}) => {
  const formatDate = (iso: string) => {
    const d = toLocalDate(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  };

  const formatCurrency = (v: number) =>
    v.toLocaleString("en-US", { maximumFractionDigits: 0 });

  const renderActions = (b: Booking) => {
    const disabled = busyId === b.id;

    if (mode === "arrivals") {
      return (
        <button
          style={buttonStyle}
          disabled={disabled}
          onClick={() => onStatusChange(b.id, "in_house")}
        >
          {disabled ? "..." : "Check In"}
        </button>
      );
    }

    if (mode === "in_house" || mode === "departures") {
      return (
        <button
          style={buttonStyle}
          disabled={disabled}
          onClick={() => onStatusChange(b.id, "checked_out")}
        >
          {disabled ? "..." : "Check Out"}
        </button>
      );
    }

    return null;
  };

  return (
    <div style={{ marginBottom: "1.5rem" }}>
      <h2
        style={{
          fontSize: "1.2rem",
          marginBottom: "0.5rem",
        }}
      >
        {title}{" "}
        <span style={{ fontSize: "0.9rem", color: "#777" }}>
          ({bookings.length})
        </span>
      </h2>

      {bookings.length === 0 ? (
        <p style={{ color: "#777" }}>No bookings in this category.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              minWidth: "950px",
              borderCollapse: "collapse",
              borderRadius: "0.5rem",
              overflow: "hidden",
            }}
          >
            <thead>
              <tr style={{ backgroundColor: "#f5f5f5" }}>
                <Th>Guest</Th>
                <Th>Hotel</Th>
                <Th>Property</Th>
                <Th>Room</Th>
                <Th>Check-In</Th>
                <Th>Check-Out</Th>
                <Th>Nights</Th>
                <Th>Status</Th>
                <Th>Channel</Th>
                <Th>Total (ETB)</Th>
                <Th>Note</Th>
                <Th>Action</Th>
              </tr>
            </thead>

            <tbody>
              {bookings.map((b) => {
                const assignedRoom = getAssignedRoomNumber(b);
                const roomOptions = getRoomOptions(b.property_code);
                const disabled = busyId === b.id;

                return (
                  <tr key={b.id}>
                    <Td>{b.guest_name}</Td>
                    <Td>{b.hotel_name}</Td>
                    <Td>{b.property_code}</Td>

                    {/* Room: Ethiopian-style dropdown + clear */}
                    <Td>
                      <div
                        style={{
                          display: "flex",
                          gap: "0.25rem",
                          alignItems: "center",
                        }}
                      >
                        <select
                          value={assignedRoom || ""}
                          onChange={(e) =>
                            onRoomChange(b.id, e.target.value || "")
                          }
                          disabled={disabled || mode === "readonly"}
                          style={{
                            fontSize: "0.8rem",
                            padding: "0.15rem 0.35rem",
                          }}
                        >
                          <option value="">-- no room --</option>
                          {roomOptions.map((r) => (
                            <option
                              key={r.room_number}
                              value={r.room_number}
                            >
                              {r.room_number} (
                              {r.room_type || "Room"})
                            </option>
                          ))}
                        </select>
                        {assignedRoom && mode !== "readonly" && (
                          <button
                            type="button"
                            onClick={() => onClearRoom(b.id)}
                            disabled={disabled}
                            style={{
                              ...buttonStyle,
                              backgroundColor: "#e5e7eb",
                              color: "#111827",
                              padding: "0.25rem 0.6rem",
                            }}
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    </Td>

                    <Td>{formatDate(b.check_in)}</Td>
                    <Td>{formatDate(b.check_out)}</Td>
                    <Td>{calcNights(b.check_in, b.check_out)}</Td>

                    <td style={{ textTransform: "capitalize" }}>
                      {formatStatusLabel(b.status)}
                    </td>

                    <td style={{ textTransform: "capitalize" }}>
                      {b.channel || "-"}
                    </td>

                    <Td>{formatCurrency(b.total_amount_etb)}</Td>

                    <td style={{ maxWidth: "160px" }}>
                      <span
                        style={{
                          fontSize: "0.8rem",
                          display: "inline-block",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {b.guest_note || b.guest_name}
                      </span>
                    </td>

                    <Td>{renderActions(b)}</Td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// --- Styled Cells ----------------------------------------------------

const buttonStyle: React.CSSProperties = {
  borderRadius: "999px",
  border: "none",
  padding: "0.35rem 0.9rem",
  fontSize: "0.8rem",
  fontWeight: 600,
  cursor: "pointer",
  backgroundColor: "#2563eb",
  color: "#fff",
};

const Th: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <th
    style={{
      textAlign: "left",
      padding: "0.5rem 0.75rem",
      fontSize: "0.85rem",
      fontWeight: 600,
      borderBottom: "1px solid #ddd",
      whiteSpace: "nowrap",
    }}
  >
    {children}
  </th>
);


const Td: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <td
    style={{
      padding: "0.45rem 0.75rem",
      fontSize: "0.85rem",
      borderBottom: "1px solid #eee",
      whiteSpace: "nowrap",
    }}
  >
    {children}
  </td>
);

export default FrontDeskConsole;
