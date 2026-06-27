import { http } from "./http";
import type {
  FrontDeskServiceRecord,
  FrontDeskServiceRecordPayload,
  FrontDeskServiceRecordStatus,
} from "../types/pms";

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

export type StayLifecyclePayload = {
  bookingId: number;
  propertyCode: string;
  businessDate: string;
  roomNumber?: string;
  checkOutDate?: string;
  note?: string;
};

export type WalkInBookingPayload = {
  propertyCode: string;
  guestName: string;
  adults?: number;
  children?: number;
  isVip?: boolean;
  documentType?: string;
  documentNumber?: string;
  email?: string;
  phone?: string;
  purposeOfVisit?: string;
  checkInDate: string;
  checkOutDate: string;
  roomNumber?: string;
  roomType?: string;
  currency?: string;
  ratePerNightEtb?: number;
  totalAmountEtb?: number;
  discountAmount?: number;
  extraBedCharge?: number;
  taxPercent?: number;
  taxAmount?: number;
  serviceChargePercent?: number;
  serviceChargeAmount?: number;
  vatPercent?: number;
  vatAmount?: number;
  downpaymentAmount?: number;
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

export async function moveGuestRoom(payload: StayLifecyclePayload) {
  const { data } = await http.post("/frontdesk/room-move", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate,
    room_number: payload.roomNumber,
    note: payload.note,
  });
  return data;
}

export async function extendStay(payload: StayLifecyclePayload) {
  const { data } = await http.post("/frontdesk/extend-stay", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate,
    check_out_date: payload.checkOutDate,
    note: payload.note,
  });
  return data;
}

export async function markEarlyDeparture(payload: StayLifecyclePayload) {
  const { data } = await http.post("/frontdesk/early-departure", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate,
    note: payload.note,
  });
  return data;
}

export async function addLateCheckoutNote(payload: StayLifecyclePayload) {
  const { data } = await http.post("/frontdesk/late-checkout-note", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate,
    note: payload.note,
  });
  return data;
}

export async function createWalkInBooking(payload: WalkInBookingPayload) {
  const { data } = await http.post("/frontdesk/walkin", {
    property_code: payload.propertyCode,
    guest_name: payload.guestName,
    adults: payload.adults ?? null,
    children: payload.children ?? null,
    is_vip: payload.isVip ?? false,
    document_type: payload.documentType || null,
    document_number: payload.documentNumber || null,
    email: payload.email || null,
    phone: payload.phone || null,
    purpose_of_visit: payload.purposeOfVisit || null,
    check_in_date: payload.checkInDate,
    check_out_date: payload.checkOutDate,
    room_number: payload.roomNumber || null,
    room_type: payload.roomType || null,
    currency: payload.currency || "ETB",
    rate_per_night_etb: payload.ratePerNightEtb ?? null,
    total_amount_etb: payload.totalAmountEtb ?? null,
    discount_amount: payload.discountAmount ?? null,
    extra_bed_charge: payload.extraBedCharge ?? null,
    tax_percent: payload.taxPercent ?? null,
    tax_amount: payload.taxAmount ?? null,
    service_charge_percent: payload.serviceChargePercent ?? null,
    service_charge_amount: payload.serviceChargeAmount ?? null,
    vat_percent: payload.vatPercent ?? null,
    vat_amount: payload.vatAmount ?? null,
    downpayment_amount: payload.downpaymentAmount ?? null,
    payment_method: payload.paymentMethod || null,
    amount_paid_now_etb: payload.amountPaidNowEtb ?? null,
    notes: payload.notes || null,
  });
  return data;
}

export async function placeReservationOnQ(payload: {
  bookingId: number;
  propertyCode: string;
  businessDate?: string;
  qPriority?: "normal" | "vip" | "urgent";
  qNotes?: string;
}) {
  const { data } = await http.post("/frontdesk/q/place", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate || null,
    q_priority: payload.qPriority || "normal",
    q_notes: payload.qNotes || null,
  });
  return data;
}

export async function removeReservationFromQ(payload: {
  bookingId: number;
  propertyCode: string;
  businessDate?: string;
  qNotes?: string;
}) {
  const { data } = await http.post("/frontdesk/q/remove", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate || null,
    q_notes: payload.qNotes || null,
  });
  return data;
}

export async function markRegistrationCardGenerated(payload: {
  bookingId: number;
  propertyCode: string;
  businessDate?: string;
  notes?: string;
}) {
  const { data } = await http.post("/frontdesk/registration-card/generated", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate || null,
    notes: payload.notes || null,
  });
  return data;
}

export async function markRegistrationCardSigned(payload: {
  bookingId: number;
  propertyCode: string;
  businessDate?: string;
  signed: boolean;
  notes?: string;
}) {
  const { data } = await http.post("/frontdesk/registration-card/signed", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate || null,
    signed: payload.signed,
    notes: payload.notes || null,
  });
  return data;
}

export async function recordManualAuthorization(payload: {
  bookingId: number;
  propertyCode: string;
  businessDate?: string;
  authorizationAmount: number;
  authorizationType?: "card" | "cash" | "offline";
  authorizationCode?: string;
  authorizationNotes?: string;
}) {
  const { data } = await http.post("/frontdesk/manual-authorization", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate || null,
    authorization_amount: payload.authorizationAmount,
    authorization_type: payload.authorizationType || "offline",
    authorization_code: payload.authorizationCode || null,
    authorization_notes: payload.authorizationNotes || null,
  });
  return data;
}

export async function recordUpsellDecision(payload: {
  bookingId: number;
  propertyCode: string;
  businessDate?: string;
  offered?: boolean;
  accepted: boolean;
  declined?: boolean;
  fromRoomType?: string;
  toRoomType?: string;
  amountPerNight?: number;
  totalAmount?: number;
  notes?: string;
}) {
  const { data } = await http.post("/frontdesk/upsell", {
    booking_id: payload.bookingId,
    property_code: payload.propertyCode,
    business_date: payload.businessDate || null,
    offered: payload.offered ?? true,
    accepted: payload.accepted,
    declined: payload.declined ?? !payload.accepted,
    from_room_type: payload.fromRoomType || null,
    to_room_type: payload.toRoomType || null,
    amount_per_night: payload.amountPerNight ?? null,
    total_amount: payload.totalAmount ?? null,
    notes: payload.notes || null,
  });
  return data;
}

export async function fetchFrontDeskServiceRecords(payload: {
  propertyCode: string;
  recordType?: string;
  status?: FrontDeskServiceRecordStatus;
  bookingId?: number;
}): Promise<FrontDeskServiceRecord[]> {
  const { data } = await http.get<FrontDeskServiceRecord[]>("/frontdesk/service-records", {
    params: {
      property_code: payload.propertyCode,
      record_type: payload.recordType,
      status: payload.status,
      booking_id: payload.bookingId,
    },
  });
  return data;
}

export async function createFrontDeskServiceRecord(
  payload: FrontDeskServiceRecordPayload
): Promise<FrontDeskServiceRecord> {
  const { data } = await http.post<FrontDeskServiceRecord>("/frontdesk/service-records", payload);
  return data;
}

export async function updateFrontDeskServiceRecord(payload: {
  id: number;
  propertyCode: string;
  status?: FrontDeskServiceRecordStatus;
  priority?: string;
  assignedTo?: string | null;
  notes?: string | null;
  roomNumber?: string | null;
  scheduledFor?: string | null;
}): Promise<FrontDeskServiceRecord> {
  const { data } = await http.patch<FrontDeskServiceRecord>(
    `/frontdesk/service-records/${payload.id}`,
    {
      status: payload.status,
      priority: payload.priority,
      assigned_to: payload.assignedTo,
      notes: payload.notes,
      room_number: payload.roomNumber,
      scheduled_for: payload.scheduledFor,
    },
    {
      params: {
        property_code: payload.propertyCode,
      },
    }
  );
  return data;
}
