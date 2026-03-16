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
