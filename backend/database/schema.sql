-- ============================================================
-- RAILWAY AUTOMATIC BLOCK PLANNER
-- PHASE 1 DATABASE SCHEMA
-- ============================================================

-- 1. DEPARTMENTS
CREATE TABLE IF NOT EXISTS departments (
    department_id SERIAL PRIMARY KEY,
    department_code VARCHAR(20) UNIQUE NOT NULL,
    department_name VARCHAR(100) NOT NULL
);

-- 2. STATIONS
CREATE TABLE IF NOT EXISTS stations (
    station_id SERIAL PRIMARY KEY,
    station_code VARCHAR(20) UNIQUE NOT NULL,
    station_name VARCHAR(100) NOT NULL
);

-- 3. RAILWAY SECTIONS / CORRIDORS
CREATE TABLE IF NOT EXISTS sections (
    section_id SERIAL PRIMARY KEY,
    section_code VARCHAR(30) UNIQUE NOT NULL,
    from_station_id INTEGER NOT NULL REFERENCES stations(station_id),
    to_station_id INTEGER NOT NULL REFERENCES stations(station_id),
    distance_km NUMERIC(8,2),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

-- 4. ASSETS
CREATE TABLE IF NOT EXISTS assets (
    asset_id SERIAL PRIMARY KEY,
    asset_code VARCHAR(50) UNIQUE NOT NULL,
    asset_type VARCHAR(30) NOT NULL
        CHECK (asset_type IN ('TRACK', 'SIGNAL', 'OHE', 'BRIDGE', 'OTHER')),
    section_id INTEGER NOT NULL REFERENCES sections(section_id),
    department_id INTEGER NOT NULL REFERENCES departments(department_id),
    criticality VARCHAR(20) NOT NULL
        CHECK (criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    installation_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'UNDER_MAINTENANCE', 'FAILED', 'INACTIVE'))
);

-- 5. MAINTENANCE TASKS
CREATE TABLE IF NOT EXISTS maintenance_tasks (
    task_id SERIAL PRIMARY KEY,
    task_code VARCHAR(50) UNIQUE NOT NULL,

    source_system VARCHAR(20) NOT NULL
        CHECK (source_system IN ('TMS', 'SMMS', 'TDMS')),

    department_id INTEGER NOT NULL REFERENCES departments(department_id),
    asset_id INTEGER NOT NULL REFERENCES assets(asset_id),
    section_id INTEGER NOT NULL REFERENCES sections(section_id),

    task_type VARCHAR(100) NOT NULL,

    severity VARCHAR(20) NOT NULL
        CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),

    duration_hours NUMERIC(6,2) NOT NULL
        CHECK (duration_hours > 0),

    status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN (
            'PENDING',
            'OVERDUE',
            'IN_PROGRESS',
            'COMPLETED',
            'CANCELLED'
        )),

    due_date DATE,
    description TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. DEFECTS
CREATE TABLE IF NOT EXISTS defects (
    defect_id SERIAL PRIMARY KEY,
    defect_code VARCHAR(50) UNIQUE NOT NULL,

    asset_id INTEGER NOT NULL REFERENCES assets(asset_id),
    section_id INTEGER NOT NULL REFERENCES sections(section_id),

    severity VARCHAR(20) NOT NULL
        CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),

    description TEXT NOT NULL,

    detected_date DATE NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'UNDER_REVIEW', 'RESOLVED', 'CLOSED'))
);

-- 7. TRAINS
CREATE TABLE IF NOT EXISTS trains (
    train_id SERIAL PRIMARY KEY,
    train_no VARCHAR(30) UNIQUE NOT NULL,
    train_name VARCHAR(100),
    train_type VARCHAR(30) NOT NULL
        CHECK (train_type IN ('EXPRESS', 'PASSENGER', 'GOODS', 'SPECIAL')),
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM'
        CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

-- 8. TRAIN SCHEDULE
CREATE TABLE IF NOT EXISTS train_schedule (
    schedule_id SERIAL PRIMARY KEY,

    train_id INTEGER NOT NULL REFERENCES trains(train_id),
    section_id INTEGER NOT NULL REFERENCES sections(section_id),

    schedule_date DATE NOT NULL,
    arrival_time TIME NOT NULL,
    departure_time TIME NOT NULL,

    CHECK (departure_time >= arrival_time)
);

-- 9. GOODS TRAIN FORECAST
CREATE TABLE IF NOT EXISTS goods_forecast (
    forecast_id SERIAL PRIMARY KEY,

    section_id INTEGER NOT NULL REFERENCES sections(section_id),
    forecast_date DATE NOT NULL,

    expected_goods_trains INTEGER NOT NULL
        CHECK (expected_goods_trains >= 0)
);

-- 10. BLOCKS
CREATE TABLE IF NOT EXISTS blocks (
    block_id SERIAL PRIMARY KEY,

    block_code VARCHAR(50) UNIQUE NOT NULL,

    section_id INTEGER NOT NULL REFERENCES sections(section_id),

    block_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,

    reason TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'PLANNED'
        CHECK (status IN (
            'PLANNED',
            'APPROVED',
            'ACTIVE',
            'COMPLETED',
            'CANCELLED'
        )),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (end_time > start_time)
);

-- 11. MAINTENANCE TASKS INCLUDED IN A BLOCK
-- One block can contain multiple tasks from multiple departments.
CREATE TABLE IF NOT EXISTS block_tasks (
    block_id INTEGER NOT NULL REFERENCES blocks(block_id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL REFERENCES maintenance_tasks(task_id) ON DELETE CASCADE,

    PRIMARY KEY (block_id, task_id)
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_assets_section
    ON assets(section_id);

CREATE INDEX IF NOT EXISTS idx_maintenance_section
    ON maintenance_tasks(section_id);

CREATE INDEX IF NOT EXISTS idx_maintenance_status
    ON maintenance_tasks(status);

CREATE INDEX IF NOT EXISTS idx_maintenance_due_date
    ON maintenance_tasks(due_date);

CREATE INDEX IF NOT EXISTS idx_defects_section
    ON defects(section_id);

CREATE INDEX IF NOT EXISTS idx_defects_status
    ON defects(status);

CREATE INDEX IF NOT EXISTS idx_train_schedule_section_date
    ON train_schedule(section_id, schedule_date);

CREATE INDEX IF NOT EXISTS idx_goods_forecast_section_date
    ON goods_forecast(section_id, forecast_date);

CREATE INDEX IF NOT EXISTS idx_blocks_section_date
    ON blocks(section_id, block_date);

-- ============================================================
-- END OF SCHEMA
-- ============================================================