-- Add a real room_number column so front desk can assign rooms
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS room_number VARCHAR(10);
