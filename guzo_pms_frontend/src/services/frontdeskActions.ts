import { http } from "./http";

export type CheckInPayload = {
  bookingId: number;
  propertyCode: string;
  businessDate: string;
};

export type CheckOutPayload = {
  bookingId: number;
  propertyCode: string;
  businessDate: string;
};

export type AssignRoomPayload = {
  bookingId: number;
  propertyCode: string;
  roomNumber: string;
};

export type WalkInBookingPayload = {
  propertyCode: string;
  guestName: string;
  checkInDate: string;
  checkOutDate: string;
  roomNumber?: string;
  roomType?: string;
  ratePerNightEtb?: number;
  totalAmountEtb?: number;
  paymentMethod?: string;
  amountPaidNowEtb?: number;
  notes?: string;
};

export async function checkInGuest(payload: CheckInPayload) {
  const { data } = await http.post("/frontdesk/check-in", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate,
  });
  return data;
}

export async function checkOutGuest(payload: CheckOutPayload) {
  const { data } = await http.post("/frontdesk/check-out", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate,
  });
  return data;
}

export async function assignRoom(payload: AssignRoomPayload) {
  const { data } = await http.post("/frontdesk/assign-room", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    room_number: payload.roomNumber,
  });
  return data;
}

export async function createWalkInBooking(payload: WalkInBookingPayload) {
  const { data } = await http.post("/frontdesk/walkin", {
    property_code: payload.propertyCode,
    guest_name: payload.guestName,
    check_in_date: payload.checkInDate,
    check_out_date: payload.checkOutDate,
    room_number: payload.roomNumber || null,
    room_type: payload.roomType || null,
    rate_per_night_etb: payload.ratePerNightEtb ?? null,
    total_amount_etb: payload.totalAmountEtb ?? null,
    payment_method: payload.paymentMethod || null,
    amount_paid_now_etb: payload.amountPaidNowEtb ?? null,
    notes: payload.notes || null,
  });
  return data;
}
