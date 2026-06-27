# Guzo Booking Assistant and Booking Hub SOP

## Purpose
The Booking Assistant and Booking Hub should operate as Guzo's reservation sales workspace, not only as a chatbot or simple booking form. The module must help reservations, front desk, and management teams quote, create, confirm, modify, and hand off reservations using five-star hotel operating standards.

## Global PMS Standard
Benchmark PMS workflows such as OPERA Cloud's Reservation Sales Screen treat booking as a hub process with caller capture, guest/profile lookup, availability search, room type and rate selection, booking rules, confirmation, and follow-up operations. Guzo should follow the same service shape while keeping its own modules simple and property-aware.

Core capabilities:

- Capture caller details: first name, last name, phone, email, source, company, travel agent, and reservation notes.
- Search or create guest profiles before confirming a reservation.
- Search availability by property, arrival, departure, nights, room count, adults, children, room type, rate code, package, promotion, preferences, and accessibility need.
- Display sell messages, policies, deposit rules, cancellation rules, and rate breakdown before confirmation.
- Support single-room, multi-room, group, waitlist, and linked-reservation workflows.
- Record turnaways or lost business when an inquiry cannot be confirmed.
- Produce confirmation details that can be sent to the guest and used by the front desk.
- Hand confirmed bookings into arrivals, room assignment, housekeeping, folio, night audit, reports, and admin controls.

## Guzo Module Responsibilities

### Booking Assistant
The Booking Assistant is the guided sales workflow for staff-assisted or guest-assisted booking.

Functions:

- Start inquiry with caller or guest context.
- Identify booking type: FIT, family, group, corporate, OTA, direct, complimentary, house use, or walk-in.
- Ask for stay dates, guest count, room preferences, accessibility needs, package needs, and special requests.
- Check availability and show only operationally valid options.
- Explain rate, tax, fee, deposit, guarantee, cancellation, and no-show policy.
- Capture required guest data and payment guarantee status.
- Create the reservation with clear notes and source tracking.
- Escalate exceptions such as overbooking risk, VIP handling, rate override, blocked room, out-of-order room, or same-day arrival.

### Booking Hub
The Booking Hub is the staff command center for active booking work.

Functions:

- Show booking pipeline: new inquiries, tentative, confirmed, waitlisted, cancelled, no-show risk, and turnaways.
- Show today's operational impact: arrivals, departures, in-house linked reservations, rooms needed, deposits due, and unassigned rooms.
- Allow search by guest, confirmation number, phone, email, company, OTA reference, source, arrival date, departure date, status, and room type.
- Provide quick actions for confirm, modify, cancel, reinstate, assign room, add note, collect deposit, send confirmation, and mark turnaway.
- Surface exceptions: missing profile data, missing guarantee, deposit due, overcapacity, room not assigned, room type unavailable, policy conflict, VIP/special request, and housekeeping dependency.

## Five-Star Hotel SOP Workflow

### 1. Inquiry Intake
- Greet guest and record caller/guest identity.
- Confirm source: direct, phone, walk-in, website, OTA, corporate, travel agent, group, or internal.
- Record stay intent, dates, occupancy, room needs, preferences, budget/rate plan, membership, company, and special requests.
- Search for an existing guest profile before creating a duplicate profile.

### 2. Availability and Quote
- Search exact dates first.
- If unavailable or restricted, offer alternate room types, alternate dates, waitlist, or approved turnaway logging.
- Quote room type, rate code, inclusions, taxes/fees, total stay value, deposit requirement, cancellation policy, and guarantee requirement.
- Do not confirm a booking until inventory, rate, policy, and guest requirements are valid.

### 3. Reservation Creation
- Create or attach guest profile.
- Attach company, travel agent, source, group/block, membership, and promotion when applicable.
- Store room type, rate code, stay dates, adults, children, preferences, notes, source, payment guarantee, and deposit status.
- For multiple rooms, create linked reservations or splitable room records so arrivals and room assignment can be managed correctly.

### 4. Confirmation
- Generate a confirmation number.
- Confirm room type, dates, rate, total, cancellation policy, deposit/guarantee status, and special requests.
- Send or record confirmation delivery.
- Record staff user, timestamp, source, and any manual override reason.

### 5. Pre-Arrival Handoff
- Feed confirmed reservations into arrivals.
- Flag VIP, accessibility, special request, airport transfer, early arrival, late arrival, deposit due, and missing guarantee.
- Enable room assignment only against clean/inspected or operationally approved rooms.
- Notify housekeeping and front desk of room dependency risks.

### 6. In-Stay and Folio Handoff
- On check-in, move reservation to in-house status.
- Open folio with rate, tax, package, deposit, and payment method context.
- Preserve booking notes that affect service delivery.

### 7. Departure, No-Show, and Audit
- Same-day unarrived confirmed reservations should appear as no-show risk before night audit.
- Night audit should process no-shows according to guarantee and cancellation policy.
- Turnaways, cancellations, no-shows, source, rate code, room type demand, and conversion should be reportable.

## Data Fields Required

Minimum booking fields:

- `property_id`
- `confirmation_number`
- `guest_profile_id`
- `guest_name`
- `guest_phone`
- `guest_email`
- `arrival_date`
- `departure_date`
- `nights`
- `adults`
- `children`
- `rooms`
- `room_type`
- `assigned_room_id`
- `rate_code`
- `rate_amount`
- `currency`
- `tax_amount`
- `total_amount`
- `source`
- `company_id`
- `travel_agent_id`
- `group_block_id`
- `status`
- `deposit_required`
- `deposit_paid`
- `guarantee_type`
- `cancellation_policy`
- `special_requests`
- `internal_notes`
- `created_by`
- `updated_by`

Recommended operational fields:

- `vip_status`
- `accessibility_required`
- `eta`
- `late_arrival`
- `early_check_in_requested`
- `ota_reference`
- `promotion_code`
- `package_code`
- `turnaway_reason`
- `override_reason`
- `confirmation_sent_at`
- `waitlist_priority`

## Status Model

Use clear reservation statuses that map to hotel operations:

- `inquiry`
- `tentative`
- `confirmed`
- `waitlisted`
- `cancelled`
- `no_show`
- `arrived`
- `in_house`
- `checked_out`
- `turnaway`

Status rules:

- `confirmed` requires valid guest identity, arrival/departure, room type, rate, source, and guarantee/deposit decision.
- `arrived` requires check-in action and room assignment decision.
- `in_house` requires active stay and open folio context.
- `checked_out` requires departure action and folio settlement.
- `no_show` should normally be applied during night audit after review.
- `turnaway` should preserve demand data for revenue reporting.

## Guzo Workflow Integration

Booking Assistant and Booking Hub must connect to these PMS priorities:

- Dashboard: booking conversion, arrivals, no-show risk, deposits due, and room demand.
- Reservations: reservation create/edit/cancel/reinstate/search.
- Front Desk: arrivals, room assignment, check-in, check-out, guest notes.
- Housekeeping: clean/dirty/inspected/out-of-order room dependency.
- Folio: deposit, payment guarantee, charges, tax, package posting, settlement.
- Reports: production, source mix, turnaways, no-shows, occupancy forecast, ADR, revenue.
- Night Audit: no-show review, deposit handling, room/rate posting validation.
- Admin: property setup, room types, rate codes, policies, sources, roles, overrides.

## Operational Controls

Booking actions should respect role-based access:

- Front desk agent: create standard bookings, add notes, assign available rooms, send confirmation.
- Reservations agent: manage inquiry, quote, confirm, modify, cancel, waitlist, turnaway.
- Supervisor/manager: approve rate override, overbooking, blocked room use, policy override, cancellation exception.
- Night auditor: review arrivals, process no-shows, validate deposits and postings.
- Admin: configure policies, rate codes, room types, sources, and permissions.

## Implementation Acceptance Checklist

A Booking Assistant or Booking Hub change is complete when:

- Staff can capture caller and guest profile context.
- Staff can search availability and select room/rate options.
- The system shows booking policies before confirmation.
- The system creates a reservation with source, status, notes, guarantee, and operational handoff fields.
- Confirmed reservations appear in arrivals and room assignment workflows.
- Deposit/guarantee context is visible to folio and night audit.
- Exceptions are visible in the hub.
- Turnaways and no-shows are reportable.
- Existing public API behavior is preserved unless intentionally changed.
