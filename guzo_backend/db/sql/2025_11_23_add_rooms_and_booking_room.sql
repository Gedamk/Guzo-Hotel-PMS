-- 2025_11_23_add_rooms_and_booking_room.sql

-- Ensure rooms table exists
CREATE TABLE IF NOT EXISTS rooms (
    id              SERIAL PRIMARY KEY,
    property_code   VARCHAR(20),
    room_number     VARCHAR(20),
    room_type       VARCHAR(50),
    floor           VARCHAR(20),
    status          VARCHAR(20) NOT NULL DEFAULT 'vacant_clean',
    created_at      TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- If an older rooms table already existed without these columns,
-- add any missing columns safely.
ALTER TABLE rooms
    ADD COLUMN IF NOT EXISTS property_code VARCHAR(20),
    ADD COLUMN IF NOT EXISTS room_number VARCHAR(20),
    ADD COLUMN IF NOT EXISTS room_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS floor VARCHAR(20),
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'vacant_clean',
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_rooms_property_code
    ON rooms (property_code);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rooms_property_roomnumber
    ON rooms (property_code, room_number);

-- NOTE: we will add bookings.room_number manually as owner (postgres)
-- instead of here, to avoid "must be owner of table bookings" errors.
