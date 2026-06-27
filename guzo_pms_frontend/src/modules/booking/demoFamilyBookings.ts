export type DemoFamilyBooking = {
  guestName: string;
  confirmationNo: string;
  intent: string;
  channel: string;
  status: string;
  guarantee: string;
  assignedTo: string;
  propertyCode: string;
  propertyName: string;
  businessDate: string;
  checkIn: string;
  checkOut: string;
  nights: number;
  guests: number;
  roomsNeeded: number;
  ratePlan: string;
  marketSegment: string;
  totalUsd: number;
  rooms: Array<{
    roomNumber: string;
    roomType: string;
    guests: number;
    rateUsd: number;
    totalUsd: number;
  }>;
  confirmationMessage: string;
};

export const demoFamilyBookings: DemoFamilyBooking[] = [
  {
    guestName: "John Kelly",
    confirmationNo: "GUZO-JK-20260610-001",
    intent: "Family Booking",
    channel: "Guzo AI Guest Site",
    status: "Confirmed",
    guarantee: "Guaranteed",
    assignedTo: "Booking Desk",
    propertyCode: "DRE001",
    propertyName: "Dream Big Hotel",
    businessDate: "2026-05-29",
    checkIn: "2026-06-10",
    checkOut: "2026-06-13",
    nights: 3,
    guests: 3,
    roomsNeeded: 1,
    ratePlan: "BAR - Best Available Rate",
    marketSegment: "Family / Direct AI Guest Site",
    totalUsd: 360,
    rooms: [
      {
        roomNumber: "301",
        roomType: "Deluxe Family Room",
        guests: 3,
        rateUsd: 120,
        totalUsd: 360,
      },
    ],
    confirmationMessage:
      "Dear John Kelly,\n\nYour family booking is confirmed at Dream Big Hotel.\n\nConfirmation Number: GUZO-JK-20260610-001\nCheck-in: June 10, 2026\nCheck-out: June 13, 2026\nGuests: 3\nRoom: Deluxe Family Room - Room 301\nRate: USD 120 per night\nTotal: USD 360\n\nThank you for booking with Guzo PMS Guest Assistant.",
  },
  {
    guestName: "Thomas Jefferson",
    confirmationNo: "GUZO-TJ-20260610-002",
    intent: "Family Multi-Room Booking",
    channel: "Guzo AI Guest Site",
    status: "Confirmed",
    guarantee: "Guaranteed",
    assignedTo: "Booking Desk",
    propertyCode: "DRE001",
    propertyName: "Dream Big Hotel",
    businessDate: "2026-05-29",
    checkIn: "2026-06-10",
    checkOut: "2026-06-13",
    nights: 3,
    guests: 5,
    roomsNeeded: 2,
    ratePlan: "BAR - Best Available Rate",
    marketSegment: "Family / Direct AI Guest Site",
    totalUsd: 645,
    rooms: [
      {
        roomNumber: "302",
        roomType: "Deluxe Twin Room",
        guests: 3,
        rateUsd: 120,
        totalUsd: 360,
      },
      {
        roomNumber: "303",
        roomType: "Standard Double Room",
        guests: 2,
        rateUsd: 95,
        totalUsd: 285,
      },
    ],
    confirmationMessage:
      "Dear Thomas Jefferson,\n\nYour family booking is confirmed at Dream Big Hotel.\n\nConfirmation Number: GUZO-TJ-20260610-002\nCheck-in: June 10, 2026\nCheck-out: June 13, 2026\nGuests: 5\nRooms: 2\n\nRoom 302: Deluxe Twin Room, USD 120 per night\nRoom 303: Standard Double Room, USD 95 per night\n\nTotal Stay Amount: USD 645\n\nThank you for booking with Guzo PMS Guest Assistant.",
  },
];

export const demoBookingWorkflow = [
  "Guest AI Site / Private Browser",
  "Guest enters booking request",
  "AI Agent captures inquiry",
  "Booking Assistant receives message",
  "AI checks room/rate",
  "Booking Hub creates reservation",
  "Confirmation sent to guest",
  "PMS inbox shows delivered message",
];
