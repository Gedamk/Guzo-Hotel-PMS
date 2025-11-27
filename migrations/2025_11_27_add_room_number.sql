-- Add a dedicated column for assigned room numbers.
-- Front office will use this for room assignment / room moves.

ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS room_number VARCHAR(10);
