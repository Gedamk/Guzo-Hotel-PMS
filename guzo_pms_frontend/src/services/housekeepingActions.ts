import { http } from "./http";

export type RoomActionPayload = {
  roomNumber: string;
  propertyCode: string;
  businessDate: string;
  note?: string;
  assignedTo?: string;
  maintenanceNote?: string;
  outOfOrderReason?: string;
  lostItemNote?: string;
};

function body(payload: RoomActionPayload) {
  return {
    room_number: payload.roomNumber,
    property_code: payload.propertyCode,
    business_date: payload.businessDate,
    note: payload.note,
    assigned_to: payload.assignedTo,
    maintenance_note: payload.maintenanceNote,
    out_of_order_reason: payload.outOfOrderReason,
    lost_item_note: payload.lostItemNote,
  };
}

export async function markRoomClean(payload: RoomActionPayload) {
  const { data } = await http.post("/rooms/housekeeping/mark-clean", body(payload));
  return data;
}

export async function markRoomDirty(payload: RoomActionPayload) {
  const { data } = await http.post("/rooms/housekeeping/mark-dirty", body(payload));
  return data;
}

export async function markRoomServiceInProgress(payload: RoomActionPayload) {
  const { data } = await http.post("/rooms/housekeeping/mark-in-service", body(payload));
  return data;
}

export async function markRoomOutOfOrder(payload: RoomActionPayload) {
  const { data } = await http.post("/rooms/housekeeping/mark-out-of-order", body(payload));
  return data;
}

export async function markRoomInspected(payload: RoomActionPayload) {
  const { data } = await http.post("/rooms/housekeeping/mark-inspected", body(payload));
  return data;
}

export async function markRoomOutOfService(payload: RoomActionPayload) {
  const { data } = await http.post("/rooms/housekeeping/mark-out-of-service", body(payload));
  return data;
}

export async function markRoomMaintenance(payload: RoomActionPayload) {
  const { data } = await http.post("/rooms/housekeeping/mark-maintenance", body(payload));
  return data;
}

export async function assignRoomAttendant(payload: RoomActionPayload) {
  const { data } = await http.post("/rooms/housekeeping/assign-attendant", body(payload));
  return data;
}
