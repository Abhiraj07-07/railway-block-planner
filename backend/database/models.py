from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Text,
    Numeric,
    Date,
    Time,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from backend.database.connection import Base


# ============================================================
# 1. DEPARTMENTS
# ============================================================

class Department(Base):
    __tablename__ = "departments"

    department_id = Column(Integer, primary_key=True, index=True)
    department_code = Column(String(20), unique=True, nullable=False)
    department_name = Column(String(100), nullable=False)

    assets = relationship(
        "Asset",
        back_populates="department"
    )

    maintenance_tasks = relationship(
        "MaintenanceTask",
        back_populates="department"
    )


# ============================================================
# 2. STATIONS
# ============================================================

class Station(Base):
    __tablename__ = "stations"

    station_id = Column(Integer, primary_key=True, index=True)
    station_code = Column(String(20), unique=True, nullable=False)
    station_name = Column(String(100), nullable=False)

    from_sections = relationship(
        "Section",
        foreign_keys="Section.from_station_id",
        back_populates="from_station"
    )

    to_sections = relationship(
        "Section",
        foreign_keys="Section.to_station_id",
        back_populates="to_station"
    )


# ============================================================
# 3. SECTIONS / CORRIDORS
# ============================================================

class Section(Base):
    __tablename__ = "sections"

    section_id = Column(Integer, primary_key=True, index=True)

    section_code = Column(
        String(30),
        unique=True,
        nullable=False
    )

    from_station_id = Column(
        Integer,
        ForeignKey("stations.station_id"),
        nullable=False
    )

    to_station_id = Column(
        Integer,
        ForeignKey("stations.station_id"),
        nullable=False
    )

    distance_km = Column(
        Numeric(8, 2)
    )

    status = Column(
        String(20),
        nullable=False,
        default="ACTIVE"
    )

    from_station = relationship(
        "Station",
        foreign_keys=[from_station_id],
        back_populates="from_sections"
    )

    to_station = relationship(
        "Station",
        foreign_keys=[to_station_id],
        back_populates="to_sections"
    )

    assets = relationship(
        "Asset",
        back_populates="section"
    )

    maintenance_tasks = relationship(
        "MaintenanceTask",
        back_populates="section"
    )

    defects = relationship(
        "Defect",
        back_populates="section"
    )

    train_schedules = relationship(
        "TrainSchedule",
        back_populates="section"
    )

    goods_forecasts = relationship(
        "GoodsForecast",
        back_populates="section"
    )

    blocks = relationship(
        "Block",
        back_populates="section"
    )


# ============================================================
# 4. ASSETS
# ============================================================

class Asset(Base):
    __tablename__ = "assets"

    asset_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    asset_code = Column(
        String(50),
        unique=True,
        nullable=False
    )

    asset_type = Column(
        String(30),
        nullable=False
    )

    section_id = Column(
        Integer,
        ForeignKey("sections.section_id"),
        nullable=False
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.department_id"),
        nullable=False
    )

    criticality = Column(
        String(20),
        nullable=False
    )

    installation_date = Column(
        Date
    )

    status = Column(
        String(20),
        nullable=False,
        default="ACTIVE"
    )

    section = relationship(
        "Section",
        back_populates="assets"
    )

    department = relationship(
        "Department",
        back_populates="assets"
    )

    maintenance_tasks = relationship(
        "MaintenanceTask",
        back_populates="asset"
    )

    defects = relationship(
        "Defect",
        back_populates="asset"
    )


# ============================================================
# 5. MAINTENANCE TASKS
# ============================================================

class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"

    task_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    task_code = Column(
        String(50),
        unique=True,
        nullable=False
    )

    source_system = Column(
        String(20),
        nullable=False
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.department_id"),
        nullable=False
    )

    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        nullable=False
    )

    section_id = Column(
        Integer,
        ForeignKey("sections.section_id"),
        nullable=False
    )

    task_type = Column(
        String(100),
        nullable=False
    )

    severity = Column(
        String(20),
        nullable=False
    )

    duration_hours = Column(
        Numeric(6, 2),
        nullable=False
    )

    status = Column(
        String(30),
        nullable=False,
        default="PENDING"
    )

    due_date = Column(
        Date
    )

    description = Column(
        Text
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default="CURRENT_TIMESTAMP"
    )

    department = relationship(
        "Department",
        back_populates="maintenance_tasks"
    )

    asset = relationship(
        "Asset",
        back_populates="maintenance_tasks"
    )

    section = relationship(
        "Section",
        back_populates="maintenance_tasks"
    )

    block_tasks = relationship(
        "BlockTask",
        back_populates="task"
    )


# ============================================================
# 6. DEFECTS
# ============================================================

class Defect(Base):
    __tablename__ = "defects"

    defect_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    defect_code = Column(
        String(50),
        unique=True,
        nullable=False
    )

    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        nullable=False
    )

    section_id = Column(
        Integer,
        ForeignKey("sections.section_id"),
        nullable=False
    )

    severity = Column(
        String(20),
        nullable=False
    )

    description = Column(
        Text,
        nullable=False
    )

    detected_date = Column(
        Date,
        nullable=False
    )

    status = Column(
        String(20),
        nullable=False,
        default="OPEN"
    )

    asset = relationship(
        "Asset",
        back_populates="defects"
    )

    section = relationship(
        "Section",
        back_populates="defects"
    )


# ============================================================
# 7. TRAINS
# ============================================================

class Train(Base):
    __tablename__ = "trains"

    train_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    train_no = Column(
        String(30),
        unique=True,
        nullable=False
    )

    train_name = Column(
        String(100)
    )

    train_type = Column(
        String(30),
        nullable=False
    )

    priority = Column(
        String(20),
        nullable=False,
        default="MEDIUM"
    )

    schedules = relationship(
        "TrainSchedule",
        back_populates="train"
    )


# ============================================================
# 8. TRAIN SCHEDULE
# ============================================================

class TrainSchedule(Base):
    __tablename__ = "train_schedule"

    schedule_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    train_id = Column(
        Integer,
        ForeignKey("trains.train_id"),
        nullable=False
    )

    section_id = Column(
        Integer,
        ForeignKey("sections.section_id"),
        nullable=False
    )

    schedule_date = Column(
        Date,
        nullable=False
    )

    arrival_time = Column(
        Time,
        nullable=False
    )

    departure_time = Column(
        Time,
        nullable=False
    )

    train = relationship(
        "Train",
        back_populates="schedules"
    )

    section = relationship(
        "Section",
        back_populates="train_schedules"
    )


# ============================================================
# 9. GOODS TRAIN FORECAST
# ============================================================

class GoodsForecast(Base):
    __tablename__ = "goods_forecast"

    forecast_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    section_id = Column(
        Integer,
        ForeignKey("sections.section_id"),
        nullable=False
    )

    forecast_date = Column(
        Date,
        nullable=False
    )

    expected_goods_trains = Column(
        Integer,
        nullable=False
    )

    section = relationship(
        "Section",
        back_populates="goods_forecasts"
    )


# ============================================================
# 10. BLOCKS
# ============================================================

class Block(Base):
    __tablename__ = "blocks"

    block_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    block_code = Column(
        String(50),
        unique=True,
        nullable=False
    )

    section_id = Column(
        Integer,
        ForeignKey("sections.section_id"),
        nullable=False
    )

    block_date = Column(
        Date,
        nullable=False
    )

    start_time = Column(
        Time,
        nullable=False
    )

    end_time = Column(
        Time,
        nullable=False
    )

    reason = Column(
        Text
    )

    status = Column(
        String(30),
        nullable=False,
        default="PLANNED"
    )
    
    replan_required = Column(
        Boolean,
        nullable=False,
        default=False
    )

    recommended_start_time = Column(
        Time,
        nullable=True
    )

    recommended_end_time = Column(
        Time,
        nullable=True
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default="CURRENT_TIMESTAMP"
    )

    section = relationship(
        "Section",
        back_populates="blocks"
    )

    block_tasks = relationship(
        "BlockTask",
        back_populates="block",
        cascade="all, delete-orphan"
    )


# ============================================================
# 11. BLOCK TASKS
# ============================================================

class BlockTask(Base):
    __tablename__ = "block_tasks"

    block_id = Column(
        Integer,
        ForeignKey("blocks.block_id"),
        primary_key=True
    )

    task_id = Column(
        Integer,
        ForeignKey("maintenance_tasks.task_id"),
        primary_key=True
    )

    block = relationship(
        "Block",
        back_populates="block_tasks"
    )

    task = relationship(
        "MaintenanceTask",
        back_populates="block_tasks"
    )
    
# ============================================================
# 12. OPERATIONAL EVENTS
# ============================================================

class OperationalEvent(Base):
    __tablename__ = "operational_events"

    event_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    event_type = Column(
        String(30),
        nullable=False
    )

    event_date = Column(
        Date,
        nullable=False
    )

    section_id = Column(
        Integer,
        ForeignKey("sections.section_id"),
        nullable=False
    )

    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        nullable=True
    )

    train_id = Column(
        Integer,
        ForeignKey("trains.train_id"),
        nullable=True
    )

    severity = Column(
        String(20),
        nullable=False,
        default="MEDIUM"
    )

    delay_minutes = Column(
        Integer,
        nullable=True
    )

    description = Column(
        Text
    )

    status = Column(
        String(20),
        nullable=False,
        default="OPEN"
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default="CURRENT_TIMESTAMP"
    )

    section = relationship(
        "Section"
    )

    asset = relationship(
        "Asset"
    )

    train = relationship(
        "Train"
    )    