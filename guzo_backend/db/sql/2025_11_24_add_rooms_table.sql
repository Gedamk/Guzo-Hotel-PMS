-- 2025_11_24_add_rooms_table.sql
-- Rooms inventory per property

CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(20) NOT NULL,
    room_number VARCHAR(20) NOT NULL,
    room_type VARCHAR(50) NOT NULL,
    floor VARCHAR(20),
    status VARCHAR(20) DEFAULT 'available',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Avoid duplicate room numbers for same property
CREATE UNIQUE INDEX IF NOT EXISTS ux_rooms_property_room
ON rooms (property_code, room_number);
