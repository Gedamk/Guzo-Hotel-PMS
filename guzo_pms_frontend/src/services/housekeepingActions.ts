import { http } from "./http";

export type RoomActionPayload = {
  roomNumber: string;
  propertyCode: string;
  businessDate: string;
};

export async function markRoomClean(payload: RoomActionPayload) {
  const { data } = await http.post("/rooms/housekeeping/mark-clean", {
    room_number: payload.roomNumber,
    property_code: payload.propertyCode,
    business_date: payload.businessDate,
  });
  return data;
}

export async function markRoomDirty(payload: RoomActionPayload) {
  const { data } = await http.post("/rooms/housekeeping/mark-dirty", {
    room_number: payload.roomNumber,
    property_code: payload.propertyCode,
    business_date: payload.businessDate,
  });
  return data;
}

export async function markRoomInService(payload: RoomActionPayload) {
  const { data } = await http.post("/rooms/housekeeping/mark-in-service", {
    room_number: payload.roomNumber,
    property_code: payload.propertyCode,
    business_date: payload.businessDate,
  });
  return data;
}

export async function markRoomOutOfOrder(payload: RoomActionPayload) {
  const { data } = await http.post("/rooms/housekeeping/mark-out-of-order", {
    room_number: payload.roomNumber,
    property_code: payload.propertyCode,
    business_date: payload.businessDate,
  });
  return data;
}
