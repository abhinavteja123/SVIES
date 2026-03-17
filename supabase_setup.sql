-- ================================================================
-- SVIES — Supabase SQL Setup
-- Run this in the Supabase SQL Editor to create all tables
-- ================================================================

-- 1. Violations table (core — stores every detected violation)
CREATE TABLE IF NOT EXISTS violations (
    id          BIGSERIAL PRIMARY KEY,
    plate       TEXT        NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
    violation_types TEXT,
    risk_score  INTEGER     DEFAULT 0,
    zone_id     TEXT        DEFAULT '',
    alert_level TEXT        DEFAULT 'LOW',
    sha256_hash TEXT        UNIQUE,
    vehicle_type    TEXT    DEFAULT '',
    owner_name      TEXT    DEFAULT '',
    model_used      TEXT    DEFAULT '',
    captured_image  TEXT    DEFAULT '',
    annotated_image TEXT    DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_violations_plate     ON violations (plate);
CREATE INDEX IF NOT EXISTS idx_violations_timestamp ON violations (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_violations_level     ON violations (alert_level);

-- 2. Vehicle registration (VAHAN mirror)
CREATE TABLE IF NOT EXISTS vehicles (
    plate                   TEXT PRIMARY KEY,
    owner                   TEXT,
    phone                   TEXT,
    email                   TEXT,
    vehicle_type            TEXT,
    color                   TEXT,
    make                    TEXT,
    year                    INTEGER,
    state                   TEXT,
    registration_state_code TEXT,
    status                  TEXT DEFAULT 'ACTIVE'
);

-- 3. PUCC (Pollution Under Control Certificate) records
CREATE TABLE IF NOT EXISTS pucc (
    plate       TEXT PRIMARY KEY,
    valid_until DATE,
    status      TEXT DEFAULT 'VALID'
);

-- 4. Insurance records
CREATE TABLE IF NOT EXISTS insurance (
    plate       TEXT PRIMARY KEY,
    valid_until DATE,
    type        TEXT,
    status      TEXT DEFAULT 'VALID'
);

-- 5. Stolen vehicles registry
CREATE TABLE IF NOT EXISTS stolen_vehicles (
    plate       TEXT PRIMARY KEY,
    reported_on DATE DEFAULT CURRENT_DATE
);

-- 6. Feedback / active-learning corrections
CREATE TABLE IF NOT EXISTS feedback (
    id                  BIGSERIAL PRIMARY KEY,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT now(),
    original_plate      TEXT,
    correct_plate       TEXT,
    correct_vehicle_type TEXT,
    notes               TEXT,
    image_file          TEXT
);

CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback (timestamp DESC);

-- ================================================================
-- Enable Row Level Security (optional — for production)
-- ================================================================
-- ALTER TABLE violations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE pucc ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE insurance ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE stolen_vehicles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

-- ================================================================
-- Seed VAHAN mock data (16 vehicles from mock_db/vahan.json)
-- ================================================================
INSERT INTO vehicles (plate, owner, phone, email, vehicle_type, color, make, year, state, registration_state_code, status) VALUES
    ('AP09AB1234', 'Rajesh Kumar', '+919876543210', 'rajesh.kumar@gmail.com', 'CAR', 'WHITE', 'Maruti Suzuki Swift', 2020, 'Andhra Pradesh', 'AP', 'ACTIVE'),
    ('TS08CD5678', 'Priya Sharma', '+919876543211', 'priya.sharma@gmail.com', 'MOTORCYCLE', 'BLACK', 'Honda Activa', 2021, 'Telangana', 'TS', 'ACTIVE'),
    ('KA01EE9999', 'Suresh Reddy', '+919876543212', 'suresh.reddy@gmail.com', 'SUV', 'GREY', 'Hyundai Creta', 2022, 'Karnataka', 'KA', 'ACTIVE'),
    ('TN22FF4444', 'Lakshmi Devi', '+919876543213', 'lakshmi.devi@gmail.com', 'CAR', 'RED', 'Kia Seltos', 2023, 'Tamil Nadu', 'TN', 'ACTIVE'),
    ('MH12GH7777', 'Amit Patel', '+919876543214', 'amit.patel@gmail.com', 'TRUCK', 'BLUE', 'Tata Ace', 2019, 'Maharashtra', 'MH', 'ACTIVE'),
    ('DL01AB0001', 'Vikram Singh', '+919876543215', 'vikram.singh@gmail.com', 'CAR', 'SILVER', 'Honda City', 2021, 'Delhi', 'DL', 'ACTIVE'),
    ('AP28HH3333', 'Srinivasarao M', '+919876543216', 'srinivas@gmail.com', 'AUTO', 'YELLOW', 'Bajaj RE', 2018, 'Andhra Pradesh', 'AP', 'ACTIVE'),
    ('TS09KK8888', 'Mohammed Irfan', '+919876543217', 'irfan@gmail.com', 'MOTORCYCLE', 'RED', 'Royal Enfield Classic', 2022, 'Telangana', 'TS', 'ACTIVE'),
    ('TS09EF1234', 'Anitha Rao', '+919876543218', 'anitha.rao@gmail.com', 'SCOOTER', 'WHITE', 'Honda Dio', 2021, 'Telangana', 'TS', 'ACTIVE'),
    ('TS06AB5678', 'Ravi Teja', '+919876543219', 'ravi.teja@gmail.com', 'CAR', 'BLACK', 'Toyota Fortuner', 2023, 'Telangana', 'TS', 'ACTIVE'),
    ('AP28CD1234', 'Padma Kumari', '+919876543220', 'padma@gmail.com', 'CAR', 'WHITE', 'Hyundai i20', 2020, 'Andhra Pradesh', 'AP', 'ACTIVE'),
    ('KA01MN4567', 'Deepak Hegde', '+919876543221', 'deepak@gmail.com', 'SUV', 'GREY', 'Mahindra XUV700', 2023, 'Karnataka', 'KA', 'ACTIVE'),
    ('TN07GH8901', 'Kavitha S', '+919876543222', 'kavitha@gmail.com', 'MOTORCYCLE', 'BLUE', 'TVS Apache', 2022, 'Tamil Nadu', 'TN', 'ACTIVE'),
    ('DL04RS2345', 'Rohit Mehra', '+919876543223', 'rohit.mehra@gmail.com', 'CAR', 'RED', 'Tata Nexon EV', 2024, 'Delhi', 'DL', 'ACTIVE'),
    ('MH02AB3333', 'Sneha Joshi', '+919876543224', 'sneha@gmail.com', 'CAR', 'SILVER', 'Maruti Baleno', 2021, 'Maharashtra', 'MH', 'ACTIVE'),
    ('RJ14UV6789', 'Arun Shekhawat', '+919876543225', 'arun@gmail.com', 'TRUCK', 'WHITE', 'Ashok Leyland', 2018, 'Rajasthan', 'RJ', 'ACTIVE')
ON CONFLICT (plate) DO NOTHING;

-- ================================================================
-- Seed PUCC mock data
-- ================================================================
INSERT INTO pucc (plate, valid_until, status) VALUES
    ('AP09AB1234', '2026-12-15', 'VALID'),
    ('TS08CD5678', '2025-06-30', 'EXPIRED'),
    ('KA01EE9999', '2026-08-20', 'VALID'),
    ('TN22FF4444', '2027-01-10', 'VALID'),
    ('MH12GH7777', '2025-03-01', 'EXPIRED'),
    ('DL01AB0001', '2026-11-25', 'VALID'),
    ('AP28HH3333', '2025-09-15', 'EXPIRED'),
    ('TS09KK8888', '2026-07-01', 'VALID'),
    ('TS09EF1234', '2026-10-10', 'VALID'),
    ('TS06AB5678', '2027-02-28', 'VALID'),
    ('AP28CD1234', '2025-12-01', 'EXPIRED'),
    ('KA01MN4567', '2026-09-15', 'VALID'),
    ('TN07GH8901', '2026-04-30', 'VALID'),
    ('DL04RS2345', '2027-03-01', 'VALID'),
    ('MH02AB3333', '2026-06-15', 'VALID'),
    ('RJ14UV6789', '2025-01-31', 'EXPIRED')
ON CONFLICT (plate) DO NOTHING;

-- ================================================================
-- Seed Insurance mock data
-- ================================================================
INSERT INTO insurance (plate, valid_until, type, status) VALUES
    ('AP09AB1234', '2026-09-01', 'COMPREHENSIVE', 'VALID'),
    ('TS08CD5678', '2025-04-15', 'THIRD_PARTY', 'EXPIRED'),
    ('KA01EE9999', '2027-01-20', 'COMPREHENSIVE', 'VALID'),
    ('TN22FF4444', '2026-12-31', 'COMPREHENSIVE', 'VALID'),
    ('MH12GH7777', '2025-02-28', 'THIRD_PARTY', 'EXPIRED'),
    ('DL01AB0001', '2026-10-15', 'COMPREHENSIVE', 'VALID'),
    ('AP28HH3333', '2025-08-01', 'THIRD_PARTY', 'EXPIRED'),
    ('TS09KK8888', '2026-06-30', 'COMPREHENSIVE', 'VALID'),
    ('TS09EF1234', '2026-11-15', 'THIRD_PARTY', 'VALID'),
    ('TS06AB5678', '2027-03-15', 'COMPREHENSIVE', 'VALID'),
    ('AP28CD1234', '2026-03-01', 'THIRD_PARTY', 'VALID'),
    ('KA01MN4567', '2027-02-01', 'COMPREHENSIVE', 'VALID'),
    ('TN07GH8901', '2026-05-30', 'THIRD_PARTY', 'VALID'),
    ('DL04RS2345', '2027-04-01', 'COMPREHENSIVE', 'VALID'),
    ('MH02AB3333', '2026-07-31', 'COMPREHENSIVE', 'VALID'),
    ('RJ14UV6789', '2025-06-15', 'THIRD_PARTY', 'EXPIRED')
ON CONFLICT (plate) DO NOTHING;

-- ================================================================
-- Seed Stolen Vehicles
-- ================================================================
INSERT INTO stolen_vehicles (plate, reported_on) VALUES
    ('AP28CD1234', '2025-11-01'),
    ('TS07GH5555', '2025-10-15'),
    ('MH02AB3333', '2025-12-20'),
    ('AN01WF2525', '2025-09-10'),
    ('OD09JT2581', '2025-08-05'),
    ('TS07AZ1048', '2025-07-22'),
    ('BR03CB2741', '2025-06-30'),
    ('MP09CN2822', '2025-11-15'),
    ('RJ04BS2679', '2025-10-01'),
    ('TN74DQ8360', '2025-09-20'),
    ('24BH7585LH', '2025-08-15'),
    ('MH48GE5485', '2025-07-10')
ON CONFLICT (plate) DO NOTHING;

-- ================================================================
-- Done! All tables created and seeded.
-- ================================================================
ALTER TABLE violations ADD COLUMN IF NOT EXISTS vehicle_type    TEXT DEFAULT '';
ALTER TABLE violations ADD COLUMN IF NOT EXISTS owner_name      TEXT DEFAULT '';
ALTER TABLE violations ADD COLUMN IF NOT EXISTS model_used      TEXT DEFAULT '';
ALTER TABLE violations ADD COLUMN IF NOT EXISTS captured_image  TEXT DEFAULT '';
ALTER TABLE violations ADD COLUMN IF NOT EXISTS annotated_image TEXT DEFAULT '';
-- adding the new columns --
