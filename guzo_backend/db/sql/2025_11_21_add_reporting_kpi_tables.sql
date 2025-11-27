-- Global-standard Room Division KPI tables

CREATE TABLE IF NOT EXISTS hotel_daily_kpi (
    id SERIAL PRIMARY KEY,
    business_date DATE NOT NULL,
    hotel_id INTEGER NOT NULL REFERENCES hotels(id),
    rooms_total INTEGER NOT NULL,
    rooms_sold INTEGER NOT NULL,
    rooms_available INTEGER NOT NULL,
    room_revenue NUMERIC(12,2) NOT NULL,
    adr NUMERIC(10,2) NOT NULL,
    revpar NUMERIC(10,2) NOT NULL,
    occupancy_pct NUMERIC(5,2) NOT NULL,
    no_shows INTEGER DEFAULT 0,
    cancellations INTEGER DEFAULT 0,
    oo_rooms INTEGER DEFAULT 0,
    oos_rooms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (business_date, hotel_id)
);

CREATE TABLE IF NOT EXISTS hotel_segment_kpi (
    id SERIAL PRIMARY KEY,
    business_date DATE NOT NULL,
    hotel_id INTEGER NOT NULL REFERENCES hotels(id),
    market_segment VARCHAR(30) NOT NULL,
    rooms_sold INTEGER NOT NULL,
    room_revenue NUMERIC(12,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (business_date, hotel_id, market_segment)
);

CREATE TABLE IF NOT EXISTS hotel_channel_kpi (
    id SERIAL PRIMARY KEY,
    business_date DATE NOT NULL,
    hotel_id INTEGER NOT NULL REFERENCES hotels(id),
    channel VARCHAR(30) NOT NULL,
    bookings_count INTEGER NOT NULL,
    room_revenue NUMERIC(12,2) NOT NULL,
    cancellations INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (business_date, hotel_id, channel)
);
