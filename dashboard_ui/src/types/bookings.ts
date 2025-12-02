// src/types/bookings.ts

// All possible booking statuses coming from the backend
export type BookingStatus =
  | "confirmed"
  | "in_house"
  | "checked_out"
  | "cancelled"
  | "no_show";

// Raw shape of a booking as returned by the backend
export interface RawBooking {
  id: number;
  booking_code: string;
  guest_name: string;

  // We treat property_code as always a string here so we can safely use it
  // as an index into HOTEL_NAME_BY_PROPERTY without TS errors.
  property_code: string;

  // Optional / nullable fields
  room_number: string | null;
  check_in: string; // "YYYY-MM-DD"
  check_out: string; // "YYYY-MM-DD"
  status: BookingStatus;
  channel: string | null;

  // Financial and stay details – some APIs may or may not send them,
  // so keep them optional.
  total_price?: number | null;
  nights?: number | null;

  // Extra fields used in BookingsConsole / other UIs
  room_type?: string | null;
  total_amount_etb?: number | null;

  // Notes – some parts of the code use `notes`, some use `note`.
  // We support both to keep TypeScript happy.
  notes?: string | null;
  note?: string | null;

  // Some views may attach hotel_name on the frontend side
  // (e.g., via enrichment). Leave it optional.
  hotel_name?: string | null;
}

// If you need a UI-specific booking with extra fields,
// you can extend RawBooking in your components like:
// type UiBooking = RawBooking & { bucket: UiBucket; };
