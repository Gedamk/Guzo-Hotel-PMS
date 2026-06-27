import { http } from "./http";
import type { FrontdeskBooking } from "../types/pms";

export type ReservationWorkflowAction =
  | "open_reservation"
  | "review_guarantee"
  | "send_deposit_link"
  | "record_deposit"
  | "request_card_guarantee"
  | "approve_pay_at_hotel"
  | "mark_guaranteed"
  | "waive_guarantee"
  | "add_trace"
  | "cancel_by_deadline"
  | "hold_at_frontdesk"
  | "send_to_frontdesk"
  | "add_alert"
  | "send_confirmation"
  | "add_arrival_note"
  | "assign_room_preference"
  | "mark_vip";

export type ReservationActionPayload = {
  bookingId: number;
  propertyCode: string;
  businessDate: string;
  action: ReservationWorkflowAction;
  note?: string;
  amount?: number;
};

export async function applyReservationAction(
  payload: ReservationActionPayload
): Promise<FrontdeskBooking> {
  const { data } = await http.post<FrontdeskBooking>("/frontdesk/reservation-action", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate,
    action: payload.action,
    note: payload.note || null,
    amount: payload.amount ?? null,
  });
  return data;
}

export type ReservationAvailabilityPayload = {
  property_code: string;
  check_in_date: string;
  check_out_date: string;
  room_type: string;
  rooms: number;
  adults: number;
  children: number;
  rate_code: string;
};

export type ReservationCreatePayload = ReservationAvailabilityPayload & {
  guest_name: string;
  guest_email?: string | null;
  guest_phone?: string | null;
  reservation_type: string;
  source: string;
  company_name?: string | null;
  travel_agent_name?: string | null;
  event_name?: string | null;
  guarantee_type: string;
  deposit_required: boolean;
  cancellation_policy?: string | null;
  special_requests?: string | null;
  vip_notes?: string | null;
  notes?: string | null;
};

export type ReservationAvailabilityQuote = {
  availability: {
    property_code: string;
    check_in_date: string;
    check_out_date: string;
    room_type: string;
    total_rooms: number;
    active_bookings: number;
    available_rooms: number;
    requested_rooms: number;
    is_available: boolean;
  };
  quote: Record<string, any>;
};

export type ReservationCreateResult = ReservationAvailabilityQuote & {
  ok: boolean;
  booking_id: number;
  confirmation_id: string;
  confirmation_status: string;
  duplicate_warnings: Array<Record<string, any>>;
  guest_notification_status: string;
};

export async function fetchReservationAvailabilityQuote(
  payload: ReservationAvailabilityPayload
): Promise<ReservationAvailabilityQuote> {
  const { data } = await http.post<ReservationAvailabilityQuote>(
    "/reservations/availability-quote",
    payload
  );
  return data;
}

export async function createReservation(
  payload: ReservationCreatePayload
): Promise<ReservationCreateResult> {
  const { data } = await http.post<ReservationCreateResult>("/reservations", payload);
  return data;
}

export type WaitlistStatus = "open" | "available" | "converted" | "cancelled";
export type ReservationWaitlistItem = {
  id: number;
  property_code: string;
  guest_name: string;
  guest_email?: string | null;
  guest_phone?: string | null;
  check_in_date: string;
  check_out_date: string;
  room_type: string;
  rooms: number;
  adults: number;
  children: number;
  rate_code: string;
  source: string;
  notes?: string | null;
  status: WaitlistStatus;
  available_rooms?: number | null;
  converted_booking_id?: number | null;
};

export type BlockStatus = "tentative" | "quoted" | "deposit_requested" | "confirmed" | "cancelled";
export type ReservationBlock = {
  id: number;
  property_code: string;
  block_name: string;
  company_name?: string | null;
  contact_name: string;
  contact_email?: string | null;
  contact_phone?: string | null;
  check_in_date: string;
  check_out_date: string;
  room_type: string;
  rooms: number;
  rate_code: string;
  status: BlockStatus;
  quoted_amount?: number | null;
  deposit_amount?: number | null;
  notes?: string | null;
};

export async function fetchWaitlist(propertyCode: string): Promise<ReservationWaitlistItem[]> {
  const { data } = await http.get<{ items: ReservationWaitlistItem[] }>("/reservations/waitlist", { params: { property_code: propertyCode } });
  return data.items;
}

export async function createWaitlistItem(payload: Omit<ReservationWaitlistItem, "id" | "status" | "available_rooms" | "converted_booking_id">): Promise<ReservationWaitlistItem> {
  const { data } = await http.post<ReservationWaitlistItem>("/reservations/waitlist", payload);
  return data;
}

export async function reviewWaitlistItem(id: number, propertyCode: string): Promise<ReservationWaitlistItem> {
  const { data } = await http.post<{ item: ReservationWaitlistItem }>(`/reservations/waitlist/${id}/review`, { property_code: propertyCode });
  return data.item;
}

export async function convertWaitlistItem(id: number, propertyCode: string): Promise<ReservationWaitlistItem> {
  const { data } = await http.post<{ item: ReservationWaitlistItem }>(`/reservations/waitlist/${id}/convert`, { property_code: propertyCode });
  return data.item;
}

export async function cancelWaitlistItem(id: number, propertyCode: string, reason: string): Promise<ReservationWaitlistItem> {
  const { data } = await http.post<ReservationWaitlistItem>(`/reservations/waitlist/${id}/cancel`, { property_code: propertyCode, reason });
  return data;
}

export async function fetchReservationBlocks(propertyCode: string): Promise<ReservationBlock[]> {
  const { data } = await http.get<{ items: ReservationBlock[] }>("/reservations/blocks", { params: { property_code: propertyCode } });
  return data.items;
}

export async function createReservationBlock(payload: Omit<ReservationBlock, "id" | "status" | "quoted_amount" | "deposit_amount">): Promise<ReservationBlock> {
  const { data } = await http.post<ReservationBlock>("/reservations/blocks", payload);
  return data;
}

export async function updateReservationBlock(id: number, propertyCode: string, updates: Partial<ReservationBlock>): Promise<ReservationBlock> {
  const { data } = await http.patch<ReservationBlock>(`/reservations/blocks/${id}`, { ...updates, property_code: propertyCode });
  return data;
}

export async function quoteReservationBlock(id: number, propertyCode: string): Promise<ReservationBlock> {
  const { data } = await http.post<{ item: ReservationBlock }>(`/reservations/blocks/${id}/quote`, { property_code: propertyCode });
  return data.item;
}

export async function requestReservationBlockDeposit(id: number, propertyCode: string): Promise<ReservationBlock> {
  const { data } = await http.post<ReservationBlock>(`/reservations/blocks/${id}/request-deposit`, { property_code: propertyCode });
  return data;
}

export async function cancelReservationBlock(id: number, propertyCode: string, reason: string): Promise<ReservationBlock> {
  const { data } = await http.post<ReservationBlock>(`/reservations/blocks/${id}/cancel`, { property_code: propertyCode, reason });
  return data;
}
