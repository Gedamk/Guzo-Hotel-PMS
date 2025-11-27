// src/types/bookings.ts

export type RawBooking = {
  id: number;
  booking_code: string | null;
  guest_name: string;
  room_number: string | null;
  room_type: string | null;
  check_in: string; // "YYYY-MM-DD"
  check_out: string; // "YYYY-MM-DD"
  status: string | null;
  channel: string | null;
  total_amount_etb: number | null;
  created_at: string;
  updated_at: string;
  notes: string | null;
  property_code: string | null;
};
