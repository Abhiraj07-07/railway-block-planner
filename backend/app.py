import os
from datetime import date, datetime
from threading import Lock
from time import monotonic

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_admin
from backend.auth.routes import router as auth_router

from backend.database.connection import get_db
from backend.database.models import (
    Asset,
    Block,
    BlockTask,
    Defect,
    GoodsForecast,
    MaintenanceTask,
    OperationalEvent,
    Section,
    Station,
    Train,
    TrainSchedule,
)

from backend.engines.analytics_engine import get_admin_analytics

from backend.engines.ai_agent import (
    ask_ai_agent,
    run_ai_operations_agent,
)

from backend.engines.ai_decision_engine import (
    calculate_all_ai_decisions,
)

from backend.engines.ai_planner import (
    generate_ai_best_plan,
    get_ai_plan_summary,
)

from backend.engines.block_planner import (
    generate_maintenance_plan,
)

from backend.engines.horizon_planner import (
    generate_horizon_plan,
)

from backend.engines.optimization_engine import (
    analyze_all_blocks,
    analyze_block_impact,
    optimize_all_blocks,
    recommend_reschedule,
    recommend_rescheduling_for_all_blocks,
    replan_after_event,
)

from backend.engines.priority_engine import (
    calculate_all_priorities,
)

from backend.engines.risk_engine import (
    calculate_all_asset_risks,
    calculate_all_smart_priorities,
    calculate_asset_risk,
    invalidate_risk_cache,
)

from backend.integrations.integration_service import (
    integration_service,
)

from backend.ml.predict import (
    predict_all_asset_risks,
    predict_asset_risk,
)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AI Automatic Railway Block Planner",
    description=(
        "Railway maintenance and automatic block "
        "planning system"
    ),
    version="1.0.0",
)


# ============================================================
# AUTH ROUTER
# ============================================================

app.include_router(auth_router)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# RESPONSE CACHE HEADERS
# ============================================================

@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)

    if request.method == "GET" and response.status_code == 200:
        path = request.url.path

        # Relatively stable railway master data
        if path in {
            "/stations",
            "/sections",
            "/assets",
            "/trains",
            "/train-schedule",
            "/goods-forecast",
        }:
            response.headers["Cache-Control"] = (
                "private, max-age=20"
            )

        # Operational data: much shorter browser cache
        elif path in {
            "/maintenance-tasks",
            "/defects",
            "/planner/blocks",
            "/events",
        }:
            response.headers["Cache-Control"] = (
                "private, max-age=2"
            )

    return response


# ============================================================
# AI RESPONSE CACHE
#
# Expensive AI calculations are cached for short dashboard
# sessions to avoid recalculating the same results repeatedly.
# ============================================================

AI_CACHE_TTL_SECONDS = 30.0

_ai_cache = {
    "asset_risks": None,
    "smart_priorities": None,
    "decisions": None,
    "best_plan": None,
}

_ai_cache_time = {
    "asset_risks": 0.0,
    "smart_priorities": 0.0,
    "decisions": 0.0,
    "best_plan": 0.0,
}

_ai_cache_lock = Lock()


# ============================================================
# GENERAL DATABASE READ CACHE
# ============================================================

DATA_CACHE_TTLS = {
    "stations": 60.0,
    "sections": 60.0,
    "assets": 30.0,
    "maintenance_tasks": 5.0,
    "defects": 5.0,
    "trains": 60.0,
    "train_schedule": 30.0,
    "goods_forecast": 60.0,
    "blocks": 3.0,
    "events": 3.0,
}

_data_cache = {}
_data_cache_time = {}
_data_cache_lock = Lock()


def get_cached_data(key: str):
    """
    Return read-cache data if the configured TTL is still valid.
    """

    ttl = DATA_CACHE_TTLS.get(key, 0.0)

    if ttl <= 0:
        return None

    now = monotonic()

    with _data_cache_lock:
        value = _data_cache.get(key)
        created_at = _data_cache_time.get(
            key,
            0.0,
        )

        if (
            value is not None
            and (now - created_at) < ttl
        ):
            return value

    return None


def set_cached_data(
    key: str,
    value,
):
    """
    Store already-serialized endpoint data.
    """

    with _data_cache_lock:
        _data_cache[key] = value
        _data_cache_time[key] = monotonic()


def clear_data_cache(*keys):
    """
    Clear all read-cache entries or selected entries.
    """

    with _data_cache_lock:

        if not keys:
            _data_cache.clear()
            _data_cache_time.clear()
            return

        for key in keys:
            _data_cache.pop(key, None)
            _data_cache_time.pop(key, None)


def clear_ai_cache():
    """
    Clear AI caches and all database read caches because
    operational state may have changed.
    """

    global _ai_cache
    global _ai_cache_time

    with _ai_cache_lock:

        _ai_cache = {
            "asset_risks": None,
            "smart_priorities": None,
            "decisions": None,
            "best_plan": None,
        }

        _ai_cache_time = {
            "asset_risks": 0.0,
            "smart_priorities": 0.0,
            "decisions": 0.0,
            "best_plan": 0.0,
        }

    invalidate_risk_cache()

    # Important:
    # Block/task/event changes can affect all dashboard reads.
    clear_data_cache()
    clear_analytics_cache()


def get_cached_ai(key: str):
    """
    Return cached AI data if still valid.
    """

    now = monotonic()

    with _ai_cache_lock:

        value = _ai_cache.get(key)

        created_at = _ai_cache_time.get(
            key,
            0.0,
        )

        if (
            value is not None
            and (
                now - created_at
            ) < AI_CACHE_TTL_SECONDS
        ):
            return value

    return None


def set_cached_ai(
    key: str,
    value,
):
    """
    Store an AI result in the short-lived cache.
    """

    with _ai_cache_lock:
        _ai_cache[key] = value
        _ai_cache_time[key] = monotonic()


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "message": "Railway Block Planner API is running",
        "database_configured": bool(
            os.getenv("DATABASE_URL")
        ),
    }


# ============================================================
# STATIONS
# ============================================================

@app.get("/stations")
def get_stations(
    db: Session = Depends(get_db),
):
    cached = get_cached_data("stations")

    if cached is not None:
        return cached

    stations = (
        db.query(Station)
        .order_by(
            Station.station_id
        )
        .all()
    )

    result = [
        {
            "station_id":
                station.station_id,
            "station_code":
                station.station_code,
            "station_name":
                station.station_name,
        }
        for station in stations
    ]

    set_cached_data(
        "stations",
        result,
    )

    return result


# ============================================================
# SECTIONS
# ============================================================

@app.get("/sections")
def get_sections(
    db: Session = Depends(get_db),
):
    cached = get_cached_data("sections")

    if cached is not None:
        return cached

    sections = (
        db.query(Section)
        .order_by(
            Section.section_id
        )
        .all()
    )

    result = [
        {
            "section_id":
                section.section_id,
            "section_code":
                section.section_code,
            "from_station_id":
                section.from_station_id,
            "to_station_id":
                section.to_station_id,
            "distance_km": (
                float(
                    section.distance_km
                )
                if section.distance_km is not None
                else None
            ),
            "status":
                section.status,
        }
        for section in sections
    ]

    set_cached_data(
        "sections",
        result,
    )

    return result


# ============================================================
# ASSETS
# ============================================================

@app.get("/assets")
def get_assets(
    db: Session = Depends(get_db),
):
    cached = get_cached_data("assets")

    if cached is not None:
        return cached

    assets = (
        db.query(Asset)
        .order_by(
            Asset.asset_id
        )
        .all()
    )

    result = [
        {
            "asset_id":
                asset.asset_id,
            "asset_code":
                asset.asset_code,
            "asset_type":
                asset.asset_type,
            "section_id":
                asset.section_id,
            "department_id":
                asset.department_id,
            "criticality":
                asset.criticality,
            "status":
                asset.status,
        }
        for asset in assets
    ]

    set_cached_data(
        "assets",
        result,
    )

    return result


# ============================================================
# MAINTENANCE TASKS
# ============================================================

@app.get("/maintenance-tasks")
def get_maintenance_tasks(
    db: Session = Depends(get_db),
):
    cached = get_cached_data(
        "maintenance_tasks"
    )

    if cached is not None:
        return cached

    tasks = (
        db.query(
            MaintenanceTask
        )
        .order_by(
            MaintenanceTask.task_id
        )
        .all()
    )

    result = [
        {
            "task_id":
                task.task_id,
            "task_code":
                task.task_code,
            "source_system":
                task.source_system,
            "department_id":
                task.department_id,
            "asset_id":
                task.asset_id,
            "section_id":
                task.section_id,
            "task_type":
                task.task_type,
            "severity":
                task.severity,
            "duration_hours": (
                float(
                    task.duration_hours
                )
                if task.duration_hours is not None
                else None
            ),
            "status":
                task.status,
            "due_date":
                task.due_date,
            "description":
                task.description,
            "created_at":
                task.created_at,
        }
        for task in tasks
    ]

    set_cached_data(
        "maintenance_tasks",
        result,
    )

    return result

# ============================================================
# REOPEN COMPLETED MAINTENANCE TASK
# ============================================================

@app.patch("/maintenance-tasks/{task_id}/reopen")
def reopen_maintenance_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    task = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.task_id == task_id
        )
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Maintenance task {task_id} not found.",
        )

    if task.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only COMPLETED tasks can be reopened. "
                f"Current status is {task.status}."
            ),
        )

    # Reopen task for future maintenance planning.
    # Existing completed block/history is preserved.
    task.status = "PENDING"

    db.commit()

    clear_ai_cache()

    db.refresh(task)

    return {
        "message": (
            f"Maintenance task {task.task_code} "
            "reopened successfully."
        ),
        "task": {
            "task_id": task.task_id,
            "task_code": task.task_code,
            "section_id": task.section_id,
            "task_type": task.task_type,
            "severity": task.severity,
            "status": task.status,
        },
    }


# ============================================================
# DEFECTS
# ============================================================

@app.get("/defects")
def get_defects(
    db: Session = Depends(get_db),
):
    cached = get_cached_data("defects")

    if cached is not None:
        return cached

    defects = (
        db.query(Defect)
        .order_by(
            Defect.defect_id
        )
        .all()
    )

    result = [
        {
            "defect_id":
                defect.defect_id,
            "defect_code":
                defect.defect_code,
            "asset_id":
                defect.asset_id,
            "section_id":
                defect.section_id,
            "severity":
                defect.severity,
            "description":
                defect.description,
            "detected_date":
                defect.detected_date,
            "status":
                defect.status,
        }
        for defect in defects
    ]

    set_cached_data(
        "defects",
        result,
    )

    return result


# ============================================================
# TRAINS
# ============================================================

@app.get("/trains")
def get_trains(
    db: Session = Depends(get_db),
):
    cached = get_cached_data("trains")

    if cached is not None:
        return cached

    trains = (
        db.query(Train)
        .order_by(
            Train.train_id
        )
        .all()
    )

    result = [
        {
            "train_id":
                train.train_id,
            "train_no":
                train.train_no,
            "train_name":
                train.train_name,
            "train_type":
                train.train_type,
            "priority":
                train.priority,
        }
        for train in trains
    ]

    set_cached_data(
        "trains",
        result,
    )

    return result


# ============================================================
# TRAIN SCHEDULE
# ============================================================

@app.get("/train-schedule")
def get_train_schedule(
    db: Session = Depends(get_db),
):
    cached = get_cached_data(
        "train_schedule"
    )

    if cached is not None:
        return cached

    schedules = (
        db.query(
            TrainSchedule
        )
        .order_by(
            TrainSchedule.schedule_date,
            TrainSchedule.departure_time,
        )
        .all()
    )

    result = [
        {
            "schedule_id":
                schedule.schedule_id,
            "train_id":
                schedule.train_id,
            "section_id":
                schedule.section_id,
            "schedule_date":
                schedule.schedule_date,
            "arrival_time":
                schedule.arrival_time,
            "departure_time":
                schedule.departure_time,
        }
        for schedule in schedules
    ]

    set_cached_data(
        "train_schedule",
        result,
    )

    return result


# ============================================================
# GOODS FORECAST
# ============================================================

@app.get("/goods-forecast")
def get_goods_forecast(
    db: Session = Depends(get_db),
):
    cached = get_cached_data(
        "goods_forecast"
    )

    if cached is not None:
        return cached

    forecasts = (
        db.query(
            GoodsForecast
        )
        .order_by(
            GoodsForecast.forecast_date,
            GoodsForecast.section_id,
        )
        .all()
    )

    result = [
        {
            "forecast_id":
                forecast.forecast_id,
            "section_id":
                forecast.section_id,
            "forecast_date":
                forecast.forecast_date,
            "expected_goods_trains":
                forecast.expected_goods_trains,
        }
        for forecast in forecasts
    ]

    set_cached_data(
        "goods_forecast",
        result,
    )

    return result


# ============================================================
# PRIORITY ENGINE
# ============================================================

@app.get("/priority/tasks")
def get_priority_tasks(
    db: Session = Depends(get_db),
):
    priorities = calculate_all_priorities(db)

    return {
        "total_tasks": len(priorities),
        "tasks": priorities,
    }


# ============================================================
# BLOCK PLANNER RECOMMENDATIONS
# ============================================================

@app.get("/planner/recommendations")
def get_planner_recommendations(
    schedule_date: date,
    db: Session = Depends(get_db),
):
    tasks = (
        db.query(
            MaintenanceTask
        )
        .filter(
            MaintenanceTask.status.notin_(
                [
                    "COMPLETED",
                    "CANCELLED",
                ]
            )
        )
        .all()
    )

    recommendations = (
        generate_maintenance_plan(
            db=db,
            tasks=tasks,
            schedule_date=schedule_date,
        )
    )

    return {
        "schedule_date":
            schedule_date,
        "total_tasks":
            len(tasks),
        "recommendations":
            recommendations,
    }


# ============================================================
# WEEKLY / MONTHLY HORIZON PLANNING
# ============================================================

class HorizonPlanRequest(BaseModel):
    start_date: date
    end_date: date
    horizon: str = "WEEKLY"


@app.post("/planner/horizon-plan")
def create_horizon_plan(
    request: HorizonPlanRequest,
    db: Session = Depends(get_db),
):
    horizon = (
        request.horizon
        .upper()
        .strip()
    )

    if horizon not in {
        "WEEKLY",
        "MONTHLY",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid horizon. "
                "Allowed values: WEEKLY, MONTHLY."
            ),
        )

    if (
        request.end_date
        < request.start_date
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "end_date must be greater than "
                "or equal to start_date."
            ),
        )

    total_days = (
        request.end_date
        - request.start_date
    ).days + 1

    if (
        horizon == "WEEKLY"
        and total_days > 7
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Weekly planning can cover maximum 7 days."
            ),
        )

    if (
        horizon == "MONTHLY"
        and total_days > 30
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Monthly planning can cover maximum 30 days."
            ),
        )

    try:
        result = generate_horizon_plan(
            db=db,
            start_date=request.start_date,
            end_date=request.end_date,
            horizon=horizon,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return result


# ============================================================
# CREATE MAINTENANCE BLOCK
# ============================================================

@app.post("/planner/create-block")
def create_maintenance_block(
    section_id: int,
    block_date: date,
    start_time: str,
    end_time: str,
    task_ids: list[int],
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    if not task_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one task ID is required.",
        )

    unique_task_ids = list(dict.fromkeys(task_ids))

    section = (
        db.query(Section)
        .filter(
            Section.section_id == section_id
        )
        .first()
    )

    if section is None:
        raise HTTPException(
            status_code=404,
            detail=f"Section {section_id} not found.",
        )

    tasks = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.task_id.in_(unique_task_ids)
        )
        .all()
    )

    if len(tasks) != len(unique_task_ids):
        raise HTTPException(
            status_code=404,
            detail="One or more task IDs were not found.",
        )

    # ========================================================
    # TASK VALIDATION + DUPLICATE ACTIVE-BLOCK PROTECTION
    # ========================================================

    for task in tasks:

        # Task must belong to selected section
        if task.section_id != section_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "All selected tasks must "
                    "belong to the same section."
                ),
            )

        # Completed / cancelled tasks cannot be scheduled
        if task.status in {
            "COMPLETED",
            "CANCELLED",
        }:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Task {task.task_code} cannot be "
                    f"scheduled because its status is "
                    f"{task.status}."
                ),
            )

        # Same task cannot already belong to an active block
        existing_active_assignment = (
            db.query(BlockTask)
            .join(
                Block,
                Block.block_id == BlockTask.block_id,
            )
            .filter(
                BlockTask.task_id == task.task_id,
                Block.status.in_(
                    [
                        "PLANNED",
                        "APPROVED",
                        "IN_PROGRESS",
                    ]
                ),
            )
            .first()
        )

        if existing_active_assignment is not None:

            existing_block = (
                db.query(Block)
                .filter(
                    Block.block_id
                    == existing_active_assignment.block_id
                )
                .first()
            )

            existing_block_code = (
                existing_block.block_code
                if existing_block
                else (
                    f"Block "
                    f"{existing_active_assignment.block_id}"
                )
            )

            raise HTTPException(
                status_code=409,
                detail=(
                    f"Task {task.task_code} is already "
                    f"scheduled in active block "
                    f"{existing_block_code}. "
                    f"It cannot be assigned to another "
                    f"active maintenance block."
                ),
            )

    # ========================================================
    # TIME VALIDATION
    # ========================================================

    try:
        parsed_start_time = datetime.strptime(
            start_time,
            "%H:%M",
        ).time()

        parsed_end_time = datetime.strptime(
            end_time,
            "%H:%M",
        ).time()

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Time must be in HH:MM format.",
        )

    if parsed_start_time >= parsed_end_time:
        raise HTTPException(
            status_code=400,
            detail="Start time must be before end time.",
        )

    # ========================================================
    # EXISTING BLOCK OVERLAP CHECK
    # ========================================================

    existing_blocks = (
        db.query(Block)
        .filter(
            Block.section_id == section_id,
            Block.block_date == block_date,
            Block.status != "CANCELLED",
        )
        .all()
    )

    new_start_minutes = (
        parsed_start_time.hour * 60
        + parsed_start_time.minute
    )

    new_end_minutes = (
        parsed_end_time.hour * 60
        + parsed_end_time.minute
    )

    for existing_block in existing_blocks:

        existing_start = (
            existing_block.start_time.hour * 60
            + existing_block.start_time.minute
        )

        existing_end = (
            existing_block.end_time.hour * 60
            + existing_block.end_time.minute
        )

        if (
            new_start_minutes < existing_end
            and existing_start < new_end_minutes
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "The requested block overlaps "
                    "an existing block on this section."
                ),
            )

    # ========================================================
    # CREATE BLOCK
    # ========================================================

    existing_count = (
        db.query(Block)
        .filter(
            Block.block_date == block_date
        )
        .count()
    )

    block_code = (
        f"BLK-{block_date.strftime('%Y%m%d')}-"
        f"{existing_count + 1:03d}"
    )

    block = Block(
    block_code=block_code,
    section_id=section_id,
    block_date=block_date,
    start_time=parsed_start_time,
    end_time=parsed_end_time,
    reason=(
        "Automatic maintenance block for "
        f"{len(tasks)} task(s)"
    ),
    status="PLANNED",
    created_by=current_user.username,
)

    db.add(block)
    db.flush()

    # Link tasks to block
    for task in tasks:

        db.add(
            BlockTask(
                block_id=block.block_id,
                task_id=task.task_id,
            )
        )

        task.status = "SCHEDULED"

    # ========================================================
    # IMPACT + RECOMMENDATION
    # ========================================================

    impact = analyze_block_impact(
        db=db,
        block=block,
    )

    recommendation = recommend_reschedule(
        db=db,
        block=block,
    )

    alternative_start = recommendation.get(
        "alternative_start_time"
    )

    alternative_end = recommendation.get(
        "alternative_end_time"
    )

    actual_timing_changed = (
        alternative_start is not None
        and alternative_end is not None
        and (
            alternative_start != block.start_time
            or alternative_end != block.end_time
        )
    )

    block.replan_required = (
        recommendation.get(
            "recommended_action"
        )
        in {
            "RESCHEDULE",
            "CONSIDER_RESCHEDULE",
        }
        and actual_timing_changed
    )

    block.recommended_start_time = (
        alternative_start
        if actual_timing_changed
        else None
    )

    block.recommended_end_time = (
        alternative_end
        if actual_timing_changed
        else None
    )

    db.commit()

    clear_ai_cache()

    db.refresh(block)

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "message": (
            "Maintenance block created successfully"
        ),
        "block": {
            "block_id": block.block_id,
            "block_code": block.block_code,
            "section_id": block.section_id,
            "block_date": block.block_date,
            "start_time": block.start_time,
            "end_time": block.end_time,
            "reason": block.reason,
            "status": block.status,
            "created_by": block.created_by,
            "task_ids": unique_task_ids,
            "conflict_count": impact.get(
                "conflict_count",
                0,
            ),
            "affected_train_ids": impact.get(
                "affected_train_ids",
                [],
            ),
            "total_conflict_minutes": impact.get(
                "total_conflict_minutes",
                0,
            ),
            "impact_level": impact.get(
                "impact_level"
            ),
            "recommended_action": recommendation.get(
                "recommended_action"
            ),
            "recommendation": recommendation.get(
                "recommendation"
            ),
            "alternative_start_time": alternative_start,
            "alternative_end_time": alternative_end,
        },
    }
    
    
# ============================================================
# RESET DEMO / TEST DATA
# ============================================================

@app.post("/admin/reset-demo-data")
def reset_demo_data(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    Reset operational/demo data.

    Deletes:
    - Operational events
    - Block-task relationships
    - Maintenance blocks

    Resets:
    - Maintenance task statuses

    Preserves:
    - Stations
    - Sections
    - Assets
    - Trains
    - Train schedules
    - Goods forecasts
    - Defects
    """

    try:
        # --------------------------------------------------------
        # 1. Delete operational events
        # --------------------------------------------------------
        deleted_events = (
            db.query(OperationalEvent).delete(
                synchronize_session=False
            )
        )

        # --------------------------------------------------------
        # 2. Delete block-task relationships
        # --------------------------------------------------------
        deleted_block_tasks = (
            db.query(BlockTask).delete(
                synchronize_session=False
            )
        )

        # --------------------------------------------------------
        # 3. Delete maintenance blocks
        # --------------------------------------------------------
        deleted_blocks = (
            db.query(Block).delete(
                synchronize_session=False
            )
        )

        # --------------------------------------------------------
        # 4. Restore fresh demo task statuses
        # --------------------------------------------------------
        fresh_task_statuses = {
            "TMS001": "OVERDUE",
            "TMS002": "PENDING",
            "SMMS001": "PENDING",
            "SMMS002": "OVERDUE",
            "TDMS001": "PENDING",
            "TDMS002": "OVERDUE",
            "TMS003": "PENDING",
            "SMMS003": "PENDING",
            "TDMS003": "PENDING",
            "TMS004": "PENDING",
            "SMMS004": "PENDING",
            "TDMS004": "PENDING",
        }

        reset_task_count = 0

        for task_code, status in fresh_task_statuses.items():
            updated = (
                db.query(MaintenanceTask)
                .filter(
                    MaintenanceTask.task_code
                    == task_code
                )
                .update(
                    {
                        MaintenanceTask.status: status
                    },
                    synchronize_session=False,
                )
            )

            reset_task_count += updated

        # --------------------------------------------------------
        # 5. Commit reset
        # --------------------------------------------------------
        db.commit()

        # --------------------------------------------------------
        # 6. Clear caches
        # --------------------------------------------------------
        clear_ai_cache()
        clear_analytics_cache()

        return {
            "message": (
                "Demo data reset successfully."
            ),
            "reset": {
                "blocks_deleted": deleted_blocks,
                "block_tasks_deleted": deleted_block_tasks,
                "events_deleted": deleted_events,
                "maintenance_tasks_reset":
                    reset_task_count,
            },
            "master_data_preserved": True,
            "status": "SUCCESS",
        }

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to reset demo data: "
                f"{str(exc)}"
            ),
        )    


# ============================================================
# GET ALL MAINTENANCE BLOCKS
# ============================================================

@app.get("/planner/blocks")
def get_maintenance_blocks(
    db: Session = Depends(get_db),
):
    cached = get_cached_data("blocks")

    if cached is not None:
        return cached

    blocks = (
        db.query(Block)
        .order_by(
            Block.block_date,
            Block.start_time,
        )
        .all()
    )

    result = []

    for block in blocks:

        task_ids = [
            block_task.task_id
            for block_task
            in block.block_tasks
        ]

        result.append(
            {
                "block_id":
                    block.block_id,
                "block_code":
                    block.block_code,
                "section_id":
                    block.section_id,
                "block_date":
                    block.block_date,
                "start_time":
                    block.start_time,
                "end_time":
                    block.end_time,
                "reason":
                    block.reason,
                "status":
                    block.status,
                "created_by": block.created_by,    
                "replan_required":
                    block.replan_required,
                "recommended_start_time":
                    block.recommended_start_time,
                "recommended_end_time":
                    block.recommended_end_time,
                "task_ids":
                    task_ids,
            }
        )

    set_cached_data(
        "blocks",
        result,
    )

    return result


# ============================================================
# UPDATE BLOCK STATUS
# ============================================================

@app.patch(
    "/planner/blocks/{block_id}/status"
)
def update_block_status(
    block_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    allowed_statuses = {
        "PLANNED",
        "APPROVED",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
    }

    new_status = (
        new_status
        .upper()
        .strip()
    )

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid status '{new_status}'. "
                f"Allowed statuses: "
                f"{', '.join(sorted(allowed_statuses))}"
            ),
        )

    block = (
        db.query(Block)
        .filter(
            Block.block_id
            == block_id
        )
        .first()
    )

    if block is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Block {block_id} not found."
            ),
        )

    current_status = block.status

    allowed_transitions = {
        "PLANNED": {
            "APPROVED",
            "CANCELLED",
        },
        "APPROVED": {
            "IN_PROGRESS",
            "CANCELLED",
        },
        "IN_PROGRESS": {
            "COMPLETED",
            "CANCELLED",
        },
        "COMPLETED": set(),
        "CANCELLED": set(),
    }

    if new_status != current_status:

        if (
            new_status
            not in allowed_transitions.get(
                current_status,
                set(),
            )
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid status transition: "
                    f"{current_status} → {new_status}"
                ),
            )

    block.status = new_status

    related_task_ids = [
        block_task.task_id
        for block_task
        in block.block_tasks
    ]

    tasks = []

    if related_task_ids:

        tasks = (
            db.query(
                MaintenanceTask
            )
            .filter(
                MaintenanceTask.task_id.in_(
                    related_task_ids
                )
            )
            .all()
        )

    if new_status == "IN_PROGRESS":

        for task in tasks:

            if task.status == "SCHEDULED":
                task.status = "IN_PROGRESS"

    elif new_status == "COMPLETED":

        for task in tasks:
            task.status = "COMPLETED"

    elif new_status == "CANCELLED":

        for task in tasks:

            if task.status == "SCHEDULED":
                task.status = "PENDING"

    db.commit()

    clear_ai_cache()

    db.refresh(block)

    return {
        "message":
            "Block status updated successfully",

        "block": {
            "block_id":
                block.block_id,

            "block_code":
                block.block_code,

            "section_id":
                block.section_id,

            "block_date":
                block.block_date,

            "start_time":
                block.start_time,

            "end_time":
                block.end_time,

            "status":
                block.status,

            "task_ids":
                related_task_ids,
        },
    }


# ============================================================
# ALL BLOCK IMPACTS
# ============================================================

@app.get("/planner/blocks/impact")
def get_all_block_impacts(
    db: Session = Depends(get_db),
):
    results = analyze_all_blocks(
        db=db
    )

    return {
        "total_blocks":
            len(results),
        "blocks":
            results,
    }


# ============================================================
# ALL BLOCK RECOMMENDATIONS
# ============================================================

@app.get("/planner/blocks/recommendations")
def get_all_block_recommendations(
    db: Session = Depends(get_db),
):
    results = (
        recommend_rescheduling_for_all_blocks(
            db=db
        )
    )

    return {
        "total_blocks":
            len(results),
        "recommendations":
            results,
    }


# ============================================================
# SINGLE BLOCK IMPACT
# ============================================================

@app.get(
    "/planner/blocks/{block_id}/impact"
)
def get_block_impact(
    block_id: int,
    db: Session = Depends(get_db),
):
    block = (
        db.query(Block)
        .filter(
            Block.block_id
            == block_id
        )
        .first()
    )

    if block is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Block {block_id} not found."
            ),
        )

    return analyze_block_impact(
        db=db,
        block=block,
    )


# ============================================================
# SINGLE BLOCK RECOMMENDATION
# ============================================================

@app.get(
    "/planner/blocks/{block_id}/recommendation"
)
def get_block_recommendation(
    block_id: int,
    db: Session = Depends(get_db),
):
    block = (
        db.query(Block)
        .filter(
            Block.block_id
            == block_id
        )
        .first()
    )

    if block is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Block {block_id} not found."
            ),
        )

    return recommend_reschedule(
        db=db,
        block=block,
    )


# ============================================================
# FINAL BLOCK OPTIMIZATION
# ============================================================

@app.get("/planner/optimization")
def get_optimized_plans(
    db: Session = Depends(get_db),
):
    results = optimize_all_blocks(
        db=db
    )

    return {
        "total_blocks":
            len(results),
        "optimized_blocks":
            results,
    }


# ============================================================
# CREATE OPERATIONAL EVENT
# ============================================================

@app.post("/events")
def create_operational_event(
    event_type: str,
    event_date: date,
    section_id: int,
    severity: str = "MEDIUM",
    asset_id: str | None = None,
    train_id: int | None = None,
    delay_minutes: int | None = None,
    description: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    allowed_event_types = {
        "DEFECT",
        "TRAIN_DELAY",
        "BLOCK_CHANGE",
    }

    allowed_severities = {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }

    event_type = (
        event_type
        .upper()
        .strip()
    )

    severity = (
        severity
        .upper()
        .strip()
    )

    if asset_id is not None:

        asset_id = asset_id.strip()

        if asset_id.lower() in {
            "",
            "blank",
            "null",
            "none",
        }:
            asset_id = None

        else:

            try:
                asset_id = int(
                    asset_id
                )

            except ValueError:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "asset_id must be a valid integer."
                    ),
                )

    if event_type not in allowed_event_types:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid event type "
                f"'{event_type}'. "
                f"Allowed types: "
                f"{', '.join(sorted(allowed_event_types))}"
            ),
        )

    if severity not in allowed_severities:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid severity "
                f"'{severity}'. "
                f"Allowed values: "
                f"{', '.join(sorted(allowed_severities))}"
            ),
        )

    section = (
        db.query(Section)
        .filter(
            Section.section_id
            == section_id
        )
        .first()
    )

    if section is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Section {section_id} not found."
            ),
        )

    if asset_id is not None:

        asset = (
            db.query(Asset)
            .filter(
                Asset.asset_id
                == asset_id
            )
            .first()
        )

        if asset is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"Asset {asset_id} not found."
                ),
            )

        if asset.section_id != section_id:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Asset does not belong to "
                    "the selected section."
                ),
            )

    if train_id is not None:

        train = (
            db.query(Train)
            .filter(
                Train.train_id
                == train_id
            )
            .first()
        )

        if train is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"Train {train_id} not found."
                ),
            )

    if event_type == "DEFECT":

        if asset_id is None:

            raise HTTPException(
                status_code=400,
                detail=(
                    "asset_id is required for "
                    "DEFECT events."
                ),
            )

    elif event_type == "TRAIN_DELAY":

        if train_id is None:

            raise HTTPException(
                status_code=400,
                detail=(
                    "train_id is required for "
                    "TRAIN_DELAY events."
                ),
            )

        if (
            delay_minutes is None
            or delay_minutes <= 0
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "delay_minutes must be greater than 0 "
                    "for TRAIN_DELAY events."
                ),
            )

    event = OperationalEvent(
        event_type=event_type,
        event_date=event_date,
        section_id=section_id,
        asset_id=asset_id,
        train_id=train_id,
        severity=severity,
        delay_minutes=delay_minutes,
        description=description,
        status="OPEN",
    )

    db.add(event)

    db.commit()

    clear_ai_cache()

    db.refresh(event)

    return {
        "message":
            "Operational event created successfully",

        "event": {
            "event_id":
                event.event_id,

            "event_type":
                event.event_type,

            "event_date":
                event.event_date,

            "section_id":
                event.section_id,

            "asset_id":
                event.asset_id,

            "train_id":
                event.train_id,

            "severity":
                event.severity,

            "delay_minutes":
                event.delay_minutes,

            "description":
                event.description,

            "status":
                event.status,

            "created_at":
                event.created_at,
        },
    }


# ============================================================
# GET OPERATIONAL EVENTS
# ============================================================

@app.get("/events")
def get_operational_events(
    db: Session = Depends(get_db),
):
    cached = get_cached_data("events")

    if cached is not None:
        return cached

    events = (
        db.query(
            OperationalEvent
        )
        .order_by(
            OperationalEvent.created_at.desc()
        )
        .all()
    )

    result = [
        {
            "event_id":
                event.event_id,
            "event_type":
                event.event_type,
            "event_date":
                event.event_date,
            "section_id":
                event.section_id,
            "asset_id":
                event.asset_id,
            "train_id":
                event.train_id,
            "severity":
                event.severity,
            "delay_minutes":
                event.delay_minutes,
            "description":
                event.description,
            "status":
                event.status,
            "created_at":
                event.created_at,
        }
        for event in events
    ]

    set_cached_data(
        "events",
        result,
    )

    return result


# ============================================================
# RESOLVE OPERATIONAL EVENT
# ============================================================

@app.patch("/events/{event_id}/resolve")
def resolve_operational_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    event = (
        db.query(
            OperationalEvent
        )
        .filter(
            OperationalEvent.event_id
            == event_id
        )
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Operational event "
                f"{event_id} not found."
            ),
        )

    if event.status == "RESOLVED":

        return {
            "message":
                f"Event {event_id} is already RESOLVED.",
            "event_id":
                event_id,
            "status":
                event.status,
        }

    event.status = "RESOLVED"

    db.commit()

    clear_ai_cache()

    db.refresh(event)

    return {
        "message":
            "Operational event resolved successfully.",
        "event_id":
            event.event_id,
        "event_type":
            event.event_type,
        "status":
            event.status,
    }


# ============================================================
# TRIGGER DYNAMIC RE-PLANNING
# ============================================================

@app.post(
    "/events/{event_id}/replan"
)
def trigger_event_replanning(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    event = (
        db.query(
            OperationalEvent
        )
        .filter(
            OperationalEvent.event_id
            == event_id
        )
        .first()
    )

    if event is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Operational event "
                f"{event_id} not found."
            ),
        )

    if event.status != "OPEN":

        raise HTTPException(
            status_code=400,
            detail=(
                f"Event {event_id} is already "
                f"{event.status}."
            ),
        )

    try:

        result = replan_after_event(
            db=db,
            event=event,
        )

        clear_ai_cache()

    except ValueError as exc:

        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Dynamic re-planning failed: "
                f"{str(exc)}"
            ),
        )

    return {
        "message": (
            "Dynamic re-planning completed successfully"
        ),
        "replanning_result":
            result,
    }


# ============================================================
# APPLY BLOCK-LEVEL REPLAN
# ============================================================

@app.post(
    "/events/{event_id}/apply-replan"
)
def apply_recommended_replan(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    event = (
        db.query(
            OperationalEvent
        )
        .filter(
            OperationalEvent.event_id
            == event_id
        )
        .first()
    )

    if event is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Operational event "
                f"{event_id} not found."
            ),
        )

    if event.status != "OPEN":

        raise HTTPException(
            status_code=400,
            detail=(
                f"Event {event_id} is already "
                f"{event.status}."
            ),
        )

    try:

        result = replan_after_event(
            db=db,
            event=event,
        )

    except ValueError as exc:

        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to calculate re-plan: "
                f"{str(exc)}"
            ),
        )

    if not isinstance(
        result,
        dict,
    ):

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Re-planning engine returned "
                "an invalid response."
            ),
        )

    affected_blocks = (
        result.get(
            "affected_blocks",
            [],
        )
    )

    task_level_replan = (
        result.get(
            "replanned_tasks",
            [],
        )
    )

    applied_blocks = []
    manual_review_blocks = []

    # ========================================================
    # PROCESS AFFECTED BLOCKS
    # ========================================================

    for block_result in affected_blocks:

        if not isinstance(
            block_result,
            dict,
        ):
            continue

        block_id = block_result.get(
            "block_id"
        )

        if block_id is None:
            continue

        recommended_action = (
            block_result.get(
                "recommended_action"
            )
        )

        if (
            recommended_action
            == "MANUAL_REVIEW"
        ):

            manual_review_blocks.append(
                {
                    "block_id":
                        block_id,

                    "block_code":
                        block_result.get(
                            "block_code"
                        ),

                    "reason": (
                        block_result.get(
                            "recommendation"
                        )
                        or
                        "Manual review required."
                    ),

                    "conflict_count":
                        block_result.get(
                            "conflict_count",
                            0,
                        ),

                    "affected_train_ids":
                        block_result.get(
                            "affected_train_ids",
                            [],
                        ),
                }
            )

            continue

        if (
            recommended_action
            == "KEEP_BLOCK"
        ):
            continue

        if (
            recommended_action
            not in {
                "RESCHEDULE",
                "CONSIDER_RESCHEDULE",
            }
        ):
            continue

        alternative_start = (
            block_result.get(
                "alternative_start_time"
            )
        )

        alternative_end = (
            block_result.get(
                "alternative_end_time"
            )
        )

        if (
            alternative_start
            is None
            or alternative_end
            is None
        ):

            manual_review_blocks.append(
                {
                    "block_id":
                        block_id,

                    "block_code":
                        block_result.get(
                            "block_code"
                        ),

                    "reason": (
                        "No valid safe alternative "
                        "timing was returned."
                    ),
                }
            )

            continue

        block = (
            db.query(Block)
            .filter(
                Block.block_id
                == block_id
            )
            .first()
        )

        if block is None:

            manual_review_blocks.append(
                {
                    "block_id":
                        block_id,

                    "block_code":
                        block_result.get(
                            "block_code"
                        ),

                    "reason": (
                        "Referenced maintenance "
                        "block was not found."
                    ),
                }
            )

            continue

        new_start_minutes = (
            alternative_start.hour * 60
            + alternative_start.minute
        )

        new_end_minutes = (
            alternative_end.hour * 60
            + alternative_end.minute
        )

        if (
            new_start_minutes
            >= new_end_minutes
        ):

            manual_review_blocks.append(
                {
                    "block_id":
                        block_id,

                    "block_code":
                        block.block_code,

                    "reason": (
                        "Recommended block timing "
                        "is invalid."
                    ),
                }
            )

            continue

        other_blocks = (
            db.query(Block)
            .filter(
                Block.section_id
                == block.section_id,
                Block.block_date
                == block.block_date,
                Block.block_id
                != block.block_id,
                Block.status
                != "CANCELLED",
            )
            .all()
        )

        overlap_found = False

        for other_block in other_blocks:

            other_start = (
                other_block.start_time.hour
                * 60
                + other_block.start_time.minute
            )

            other_end = (
                other_block.end_time.hour
                * 60
                + other_block.end_time.minute
            )

            if (
                new_start_minutes
                < other_end
                and other_start
                < new_end_minutes
            ):

                overlap_found = True

                manual_review_blocks.append(
                    {
                        "block_id":
                            block_id,

                        "block_code":
                            block.block_code,

                        "reason": (
                            "Recommended timing overlaps "
                            "another active maintenance block."
                        ),

                        "conflicting_block_id":
                            other_block.block_id,

                        "conflicting_block_code":
                            other_block.block_code,
                    }
                )

                break

        if overlap_found:
            continue

        # ====================================================
        # FINAL TRAIN SAFETY CHECK
        # ====================================================

        original_start = block.start_time
        original_end = block.end_time

        block.start_time = (
            alternative_start
        )

        block.end_time = (
            alternative_end
        )

        try:

            safety_impact = (
                analyze_block_impact(
                    db=db,
                    block=block,
                )
            )

        finally:

            block.start_time = (
                original_start
            )

            block.end_time = (
                original_end
            )

        if (
            safety_impact.get(
                "conflict_count",
                0,
            )
            > 0
        ):

            manual_review_blocks.append(
                {
                    "block_id":
                        block_id,

                    "block_code":
                        block.block_code,

                    "reason": (
                        "Recommended timing still has "
                        "a train conflict after final "
                        "safety validation."
                    ),

                    "conflict_count":
                        safety_impact.get(
                            "conflict_count",
                            0,
                        ),

                    "affected_train_ids":
                        safety_impact.get(
                            "affected_train_ids",
                            [],
                        ),
                }
            )

            continue

        # ====================================================
        # APPLY
        # ====================================================

        old_start = block.start_time
        old_end = block.end_time

        block.start_time = (
            alternative_start
        )

        block.end_time = (
            alternative_end
        )

        block.replan_required = False

        block.recommended_start_time = (
            alternative_start
        )

        block.recommended_end_time = (
            alternative_end
        )

        applied_blocks.append(
            {
                "block_id":
                    block.block_id,

                "block_code":
                    block.block_code,

                "old_start_time":
                    old_start,

                "old_end_time":
                    old_end,

                "new_start_time":
                    block.start_time,

                "new_end_time":
                    block.end_time,
            }
        )

    # ========================================================
    # COMMIT ONLY WHEN SOMETHING WAS APPLIED
    # ========================================================

    if applied_blocks:

        event.status = "RESOLVED"

        db.commit()

        clear_ai_cache()

        return {
            "message": (
                "Recommended maintenance plan "
                "applied successfully."
            ),

            "event_id":
                event_id,

            "event_status":
                "RESOLVED",

            "applied_blocks":
                applied_blocks,

            "manual_review_blocks":
                manual_review_blocks,

            "task_level_replan":
                task_level_replan,

            "replanning_required":
                len(
                    manual_review_blocks
                ) > 0,

            "event_action":
                "REPLAN_APPLIED",
        }

    db.rollback()

    return {
        "message": (
            "No safe whole-block timing could "
            "be applied. The event remains OPEN "
            "for manual review."
        ),

        "event_id":
            event_id,

        "event_status":
            "OPEN",

        "applied_blocks": [],

        "manual_review_blocks":
            manual_review_blocks,

        "task_level_replan":
            task_level_replan,

        "replanning_required":
            True,

        "event_action":
            "MANUAL_REVIEW",
    }


# ============================================================
# APPLY TASK-LEVEL REPLANNING
# ============================================================

@app.post(
    "/events/{event_id}/apply-task-replan"
)
def apply_task_level_replan(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    # ========================================================
    # 1. GET EVENT
    # ========================================================

    event = (
        db.query(OperationalEvent)
        .filter(
            OperationalEvent.event_id
            == event_id
        )
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Operational event "
                f"{event_id} not found."
            ),
        )

    if event.status != "OPEN":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Event {event_id} is already "
                f"{event.status}."
            ),
        )

    # ========================================================
    # 2. GENERATE AI TASK-LEVEL REPLAN
    # ========================================================

    try:

        result = replan_after_event(
            db=db,
            event=event,
        )

    except ValueError as exc:

        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to calculate task-level "
                f"re-plan: {str(exc)}"
            ),
        )

    if not isinstance(
        result,
        dict,
    ):

        db.rollback()

        return {
            "message": (
                "AI task-level re-planning "
                "returned an invalid result."
            ),
            "event_id":
                event_id,
            "event_status":
                "OPEN",
            "created_blocks": [],
            "cancelled_blocks": [],
            "manual_review_tasks": [],
            "replanning_required":
                True,
            "event_action":
                "MANUAL_REVIEW",
        }

    task_level_replan = result.get(
        "replanned_tasks",
        [],
    )

    if not task_level_replan:

        db.rollback()

        return {
            "message": (
                "No AI task-level re-planning "
                "recommendation is available."
            ),
            "event_id":
                event_id,
            "event_status":
                "OPEN",
            "created_blocks": [],
            "cancelled_blocks": [],
            "manual_review_tasks": [],
            "replanning_required":
                True,
            "event_action":
                "MANUAL_REVIEW",
        }

    # ========================================================
    # 3. EXTRACT AI REPLANNED TASK IDS
    # ========================================================

    replanned_task_ids = set()

    for plan in task_level_replan:

        if not isinstance(
            plan,
            dict,
        ):
            continue

        task_id = plan.get(
            "task_id"
        )

        if task_id is not None:

            replanned_task_ids.add(
                int(task_id)
            )

    if not replanned_task_ids:

        db.rollback()

        return {
            "message": (
                "AI generated task-level plans, "
                "but no valid task IDs were found."
            ),
            "event_id":
                event_id,
            "event_status":
                "OPEN",
            "created_blocks": [],
            "cancelled_blocks": [],
            "manual_review_tasks": [],
            "task_level_replan":
                task_level_replan,
            "replanning_required":
                True,
            "event_action":
                "MANUAL_REVIEW",
        }

    # ========================================================
    # 4. LOAD TASKS
    # ========================================================

    tasks = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.task_id.in_(
                list(replanned_task_ids)
            )
        )
        .all()
    )

    task_by_id = {
        task.task_id:
            task
        for task in tasks
    }

    missing_task_ids = (
        replanned_task_ids
        - set(
            task_by_id.keys()
        )
    )

    if missing_task_ids:

        db.rollback()

        return {
            "message": (
                "One or more AI replanned "
                "maintenance tasks could not be found."
            ),

            "event_id":
                event_id,

            "event_status":
                "OPEN",

            "created_blocks": [],

            "cancelled_blocks": [],

            "manual_review_tasks": [
                {
                    "task_id":
                        task_id,

                    "reason":
                        "Maintenance task not found.",
                }
                for task_id
                in sorted(
                    missing_task_ids
                )
            ],

            "task_level_replan":
                task_level_replan,

            "replanning_required":
                True,

            "event_action":
                "MANUAL_REVIEW",
        }

    # ========================================================
    # 5. FIND CURRENT ACTIVE BLOCKS
    # ========================================================

    active_links = (
        db.query(BlockTask)
        .join(
            Block,
            Block.block_id
            == BlockTask.block_id,
        )
        .filter(
            BlockTask.task_id.in_(
                list(replanned_task_ids)
            ),
            Block.status
            != "CANCELLED",
        )
        .all()
    )

    affected_block_ids = {
        link.block_id
        for link in active_links
    }

    affected_blocks_db = []

    if affected_block_ids:

        affected_blocks_db = (
            db.query(Block)
            .filter(
                Block.block_id.in_(
                    list(
                        affected_block_ids
                    )
                )
            )
            .all()
        )

    # ========================================================
    # 6. CHECK BLOCK STATUS
    # ========================================================

    blocked_blocks = []

    for block in affected_blocks_db:

        if block.status in {
            "IN_PROGRESS",
            "COMPLETED",
        }:

            blocked_blocks.append(
                {
                    "block_id":
                        block.block_id,

                    "block_code":
                        block.block_code,

                    "status":
                        block.status,
                }
            )

    if blocked_blocks:

        db.rollback()

        return {
            "message": (
                "Task-level automatic re-planning "
                "cannot modify an IN_PROGRESS or "
                "COMPLETED block."
            ),

            "event_id":
                event_id,

            "event_status":
                "OPEN",

            "created_blocks": [],

            "cancelled_blocks": [],

            "manual_review_tasks": [],

            "blocked_blocks":
                blocked_blocks,

            "task_level_replan":
                task_level_replan,

            "replanning_required":
                True,

            "event_action":
                "MANUAL_REVIEW",
        }

    # ========================================================
    # 7. PARSE TIME
    # ========================================================

    def parse_time_value(value):

        if value is None:
            return None

        if (
            hasattr(value, "hour")
            and hasattr(value, "minute")
        ):
            return value

        if isinstance(
            value,
            str,
        ):

            for time_format in (
                "%H:%M",
                "%H:%M:%S",
            ):

                try:

                    return datetime.strptime(
                        value,
                        time_format,
                    ).time()

                except ValueError:
                    continue

        return None

    # ========================================================
    # 8. NORMALIZE AI PLANS
    # ========================================================

    normalized_plans = {}

    for plan in task_level_replan:

        if not isinstance(
            plan,
            dict,
        ):
            continue

        task_id = plan.get(
            "task_id"
        )

        if task_id is None:
            continue

        task_id = int(task_id)

        if task_id not in replanned_task_ids:
            continue

        start_time = parse_time_value(
            plan.get(
                "start_time"
            )
        )

        end_time = parse_time_value(
            plan.get(
                "end_time"
            )
        )

        if (
            start_time is None
            or end_time is None
        ):
            continue

        normalized_plans[task_id] = {
            "task_id":
                task_id,

            "task_code":
                plan.get(
                    "task_code"
                ),

            "section_id":
                plan.get(
                    "section_id"
                ),

            "start_time":
                start_time,

            "end_time":
                end_time,

            "duration_hours":
                plan.get(
                    "duration_hours"
                ),

            "priority":
                plan.get(
                    "priority"
                ),

            "priority_score":
                plan.get(
                    "priority_score"
                ),

            "ml_risk_percentage":
                plan.get(
                    "ml_risk_percentage"
                ),

            "ml_risk_level":
                plan.get(
                    "ml_risk_level"
                ),

            "combined_risk_score":
                plan.get(
                    "combined_risk_score"
                ),

            "planning_score":
                plan.get(
                    "planning_score"
                ),
        }

    # ========================================================
    # 9. CHECK MISSING AI WINDOWS
    # ========================================================

    manual_review_tasks = []

    for task_id in sorted(
        replanned_task_ids
    ):

        if task_id not in normalized_plans:

            task = task_by_id.get(
                task_id
            )

            manual_review_tasks.append(
                {
                    "task_id":
                        task_id,

                    "task_code": (
                        task.task_code
                        if task is not None
                        else None
                    ),

                    "reason": (
                        "No valid AI task-level "
                        "safe window was generated."
                    ),
                }
            )

    if manual_review_tasks:

        db.rollback()

        return {
            "message": (
                "Task-level re-planning is incomplete. "
                "Manual review is required."
            ),

            "event_id":
                event_id,

            "event_status":
                "OPEN",

            "created_blocks": [],

            "cancelled_blocks": [],

            "manual_review_tasks":
                manual_review_tasks,

            "task_level_replan":
                task_level_replan,

            "replanning_required":
                True,

            "event_action":
                "MANUAL_REVIEW",
        }

    # ========================================================
    # 10. SORT PLANS
    # ========================================================

    plan_items = list(
        normalized_plans.values()
    )

    plan_items.sort(
        key=lambda item: (
            item["start_time"],
            item["end_time"],
        )
    )

    # ========================================================
    # 11. VALIDATE TIME WINDOWS
    # ========================================================

    for plan in plan_items:

        start_minutes = (
            plan["start_time"].hour * 60
            + plan["start_time"].minute
        )

        end_minutes = (
            plan["end_time"].hour * 60
            + plan["end_time"].minute
        )

        if start_minutes >= end_minutes:

            db.rollback()

            return {
                "message": (
                    "Invalid AI task-level "
                    "timing detected."
                ),

                "event_id":
                    event_id,

                "event_status":
                    "OPEN",

                "created_blocks": [],

                "cancelled_blocks": [],

                "manual_review_tasks": [],

                "task_level_replan":
                    task_level_replan,

                "replanning_required":
                    True,

                "event_action":
                    "MANUAL_REVIEW",
            }

    # ========================================================
    # 12. VALIDATE OVERLAPPING AI WINDOWS
    # ========================================================

    for index in range(
        len(plan_items) - 1
    ):

        current_plan = plan_items[
            index
        ]

        next_plan = plan_items[
            index + 1
        ]

        current_end = (
            current_plan["end_time"].hour * 60
            + current_plan["end_time"].minute
        )

        next_start = (
            next_plan["start_time"].hour * 60
            + next_plan["start_time"].minute
        )

        if current_end > next_start:

            db.rollback()

            return {
                "message": (
                    "AI-generated task windows "
                    "overlap each other."
                ),

                "event_id":
                    event_id,

                "event_status":
                    "OPEN",

                "created_blocks": [],

                "cancelled_blocks": [],

                "manual_review_tasks": [],

                "task_level_replan":
                    task_level_replan,

                "replanning_required":
                    True,

                "event_action":
                    "MANUAL_REVIEW",
            }

    # ========================================================
    # 13. CHECK TASK DUPLICATES IN OTHER ACTIVE BLOCKS
    # ========================================================

    for task_id in replanned_task_ids:

        duplicate_query = (
            db.query(BlockTask)
            .join(
                Block,
                Block.block_id
                == BlockTask.block_id,
            )
            .filter(
                BlockTask.task_id
                == task_id,
                Block.status
                != "CANCELLED",
            )
        )

        if affected_block_ids:

            duplicate_query = duplicate_query.filter(
                ~Block.block_id.in_(
                    list(
                        affected_block_ids
                    )
                )
            )

        duplicate_links = (
            duplicate_query
            .all()
        )

        if duplicate_links:

            conflicting_blocks = [
                link.block_id
                for link in duplicate_links
            ]

            db.rollback()

            return {
                "message": (
                    "A task is already attached "
                    "to another active maintenance block."
                ),

                "event_id":
                    event_id,

                "event_status":
                    "OPEN",

                "created_blocks": [],

                "cancelled_blocks": [],

                "manual_review_tasks": [
                    {
                        "task_id":
                            task_id,

                        "task_code":
                            task_by_id[
                                task_id
                            ].task_code,

                        "reason": (
                            "Task already exists "
                            "in another active block."
                        ),

                        "conflicting_block_ids":
                            conflicting_blocks,
                    }
                ],

                "replanning_required":
                    True,

                "event_action":
                    "MANUAL_REVIEW",
            }

    # ========================================================
    # 14. CANCEL OLD BLOCKS
    # ========================================================

    cancelled_blocks = []

    for block in affected_blocks_db:

        old_status = block.status

        block.status = "CANCELLED"

        block.replan_required = False

        for block_task in block.block_tasks:

            task = task_by_id.get(
                block_task.task_id
            )

            if (
                task is not None
                and task.status == "SCHEDULED"
            ):

                task.status = "PENDING"

        cancelled_blocks.append(
            {
                "block_id":
                    block.block_id,

                "block_code":
                    block.block_code,

                "old_status":
                    old_status,

                "new_status":
                    "CANCELLED",
            }
        )

    db.flush()

    # ========================================================
    # 15. UNIQUE BLOCK CODE
    # ========================================================

    def generate_block_code(
        block_date_value
    ):

        existing_codes = {
            block.block_code
            for block in (
                db.query(Block)
                .filter(
                    Block.block_date
                    == block_date_value
                )
                .all()
            )
        }

        counter = 1

        while True:

            candidate = (
                f"BLK-"
                f"{block_date_value.strftime('%Y%m%d')}-"
                f"{counter:03d}"
            )

            if candidate not in existing_codes:

                return candidate

            counter += 1

    # ========================================================
    # 16. CREATE NEW TASK-LEVEL BLOCKS
    # ========================================================

    created_blocks = []

    for plan in plan_items:

        task_id = plan[
            "task_id"
        ]

        task = task_by_id[
            task_id
        ]

        if task.section_id != event.section_id:

            db.rollback()

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Task {task.task_code} "
                    f"does not belong to event "
                    f"section {event.section_id}."
                ),
            )

        block_date = event.event_date

        start_time = plan[
            "start_time"
        ]

        end_time = plan[
            "end_time"
        ]

        active_blocks = (
            db.query(Block)
            .filter(
                Block.section_id
                == task.section_id,

                Block.block_date
                == block_date,

                Block.status
                != "CANCELLED",
            )
            .all()
        )

        new_start_minutes = (
            start_time.hour * 60
            + start_time.minute
        )

        new_end_minutes = (
            end_time.hour * 60
            + end_time.minute
        )

        overlap_found = False

        for existing_block in active_blocks:

            existing_start = (
                existing_block.start_time.hour * 60
                + existing_block.start_time.minute
            )

            existing_end = (
                existing_block.end_time.hour * 60
                + existing_block.end_time.minute
            )

            if (
                new_start_minutes
                < existing_end
                and existing_start
                < new_end_minutes
            ):

                overlap_found = True

                break

        if overlap_found:

            db.rollback()

            return {
                "message": (
                    "AI task-level window conflicts "
                    "with another active maintenance block."
                ),

                "event_id":
                    event_id,

                "event_status":
                    "OPEN",

                "created_blocks": [],

                "cancelled_blocks": [],

                "manual_review_tasks": [
                    {
                        "task_id":
                            task_id,

                        "task_code":
                            task.task_code,

                        "start_time":
                            start_time,

                        "end_time":
                            end_time,

                        "reason": (
                            "Recommended task window "
                            "overlaps another active block."
                        ),
                    }
                ],

                "replanning_required":
                    True,

                "event_action":
                    "MANUAL_REVIEW",
            }

        block_code = generate_block_code(
            block_date
        )

        new_block = Block(
            block_code=block_code,

            section_id=task.section_id,

            block_date=block_date,

            start_time=start_time,

            end_time=end_time,

            reason=(
                "AI dynamic task-level "
                f"re-planning for event "
                f"{event_id} - "
                f"{task.task_code}"
            ),

            status="PLANNED",

            replan_required=False,

            recommended_start_time=None,

            recommended_end_time=None,
            
            created_by=current_user.username,
        )

        db.add(new_block)

        db.flush()

        db.add(
            BlockTask(
                block_id=
                    new_block.block_id,

                task_id=
                    task_id,
            )
        )

        task.status = "SCHEDULED"

        db.flush()

        impact = analyze_block_impact(
            db=db,
            block=new_block,
        )

        if (
            impact.get(
                "conflict_count",
                0,
            ) > 0
        ):

            db.rollback()

            return {
                "message": (
                    "AI task-level plan failed "
                    "final train safety validation."
                ),

                "event_id":
                    event_id,

                "event_status":
                    "OPEN",

                "created_blocks": [],

                "cancelled_blocks": [],

                "manual_review_tasks": [
                    {
                        "task_id":
                            task_id,

                        "task_code":
                            task.task_code,

                        "start_time":
                            start_time,

                        "end_time":
                            end_time,

                        "conflict_count":
                            impact.get(
                                "conflict_count",
                                0,
                            ),

                        "affected_train_ids":
                            impact.get(
                                "affected_train_ids",
                                [],
                            ),

                        "reason": (
                            "Recommended task window "
                            "still conflicts with "
                            "train operations."
                        ),
                    }
                ],

                "replanning_required":
                    True,

                "event_action":
                    "MANUAL_REVIEW",
            }

        created_blocks.append(
            {
                "block_id":
                    new_block.block_id,

                "block_code":
                    new_block.block_code,

                "task_id":
                    task.task_id,

                "task_code":
                    task.task_code,

                "section_id":
                    new_block.section_id,

                "block_date":
                    new_block.block_date,

                "start_time":
                    new_block.start_time,

                "end_time":
                    new_block.end_time,

                "duration_hours":
                    plan.get(
                        "duration_hours"
                    ),

                "priority":
                    plan.get(
                        "priority"
                    ),

                "priority_score":
                    plan.get(
                        "priority_score"
                    ),

                "ml_risk_percentage":
                    plan.get(
                        "ml_risk_percentage"
                    ),

                "ml_risk_level":
                    plan.get(
                        "ml_risk_level"
                    ),

                "combined_risk_score":
                    plan.get(
                        "combined_risk_score"
                    ),

                "planning_score":
                    plan.get(
                        "planning_score"
                    ),

                "conflict_count":
                    impact.get(
                        "conflict_count",
                        0,
                    ),

                "affected_train_ids":
                    impact.get(
                        "affected_train_ids",
                        [],
                    ),
            }
        )

    # ========================================================
    # 17. FINAL VALIDATION
    # ========================================================

    for created in created_blocks:

        block = (
            db.query(Block)
            .filter(
                Block.block_id
                == created[
                    "block_id"
                ]
            )
            .first()
        )

        if block is None:

            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Created task-level block "
                    "could not be reloaded."
                ),
            )

        final_impact = (
            analyze_block_impact(
                db=db,
                block=block,
            )
        )

        if (
            final_impact.get(
                "conflict_count",
                0,
            ) > 0
        ):

            db.rollback()

            return {
                "message": (
                    "Final safety validation failed. "
                    "No task-level changes were committed."
                ),

                "event_id":
                    event_id,

                "event_status":
                    "OPEN",

                "created_blocks": [],

                "cancelled_blocks": [],

                "manual_review_tasks": [
                    {
                        "task_id":
                            created.get(
                                "task_id"
                            ),

                        "task_code":
                            created.get(
                                "task_code"
                            ),

                        "conflict_count":
                            final_impact.get(
                                "conflict_count",
                                0,
                            ),

                        "affected_train_ids":
                            final_impact.get(
                                "affected_train_ids",
                                [],
                            ),

                        "reason": (
                            "Final train-safety "
                            "validation failed."
                        ),
                    }
                ],

                "replanning_required":
                    True,

                "event_action":
                    "MANUAL_REVIEW",
            }

    # ========================================================
    # 18. RESOLVE EVENT
    # ========================================================

    event.status = "RESOLVED"

    db.commit()

    clear_ai_cache()

    return {
        "message": (
            "AI task-level re-planning "
            "applied successfully."
        ),

        "event_id":
            event_id,

        "event_status":
            "RESOLVED",

        "cancelled_blocks":
            cancelled_blocks,

        "created_blocks":
            created_blocks,

        "manual_review_tasks":
            [],

        "task_level_replan":
            task_level_replan,

        "replanning_required":
            False,

        "event_action":
            "TASK_LEVEL_REPLAN_APPLIED",
    }


# ============================================================
# AI ASSET RISK — SINGLE
# ============================================================

@app.get(
    "/ai/risk/assets/{asset_id}"
)
def get_asset_risk(
    asset_id: int,
    db: Session = Depends(get_db),
):
    asset = (
        db.query(Asset)
        .filter(
            Asset.asset_id
            == asset_id
        )
        .first()
    )

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Asset {asset_id} not found."
            ),
        )

    return calculate_asset_risk(
        db=db,
        asset=asset,
    )


# ============================================================
# AI ASSET RISK — ALL
# ============================================================

@app.get("/ai/risk/assets")
def get_all_asset_risks(
    db: Session = Depends(get_db),
):
    cached = get_cached_ai(
        "asset_risks"
    )

    if cached is not None:

        return {
            "total_assets":
                len(cached),

            "assets":
                cached,

            "cached":
                True,
        }

    results = calculate_all_asset_risks(
        db=db
    )

    set_cached_ai(
        "asset_risks",
        results,
    )

    return {
        "total_assets":
            len(results),

        "assets":
            results,

        "cached":
            False,
    }


# ============================================================
# AI SMART MAINTENANCE PRIORITY
# ============================================================

@app.get("/ai/smart-priority")
def get_smart_maintenance_priority(
    db: Session = Depends(get_db),
):
    cached = get_cached_ai(
        "smart_priorities"
    )

    if cached is not None:

        return {
            "total_tasks":
                len(cached),

            "tasks":
                cached,

            "cached":
                True,
        }

    results = calculate_all_smart_priorities(
        db=db
    )

    set_cached_ai(
        "smart_priorities",
        results,
    )

    return {
        "total_tasks":
            len(results),

        "tasks":
            results,

        "cached":
            False,
    }


# ============================================================
# AI MAINTENANCE DECISIONS
# ============================================================

@app.get("/ai/decisions")
def get_ai_maintenance_decisions(
    db: Session = Depends(get_db),
):
    cached = get_cached_ai(
        "decisions"
    )

    if cached is not None:

        return {
            "total_tasks":
                len(cached),

            "decisions":
                cached,

            "cached":
                True,
        }

    results = calculate_all_ai_decisions(
        db=db
    )

    set_cached_ai(
        "decisions",
        results,
    )

    return {
        "total_tasks":
            len(results),

        "decisions":
            results,

        "cached":
            False,
    }


# ============================================================
# AI BEST MAINTENANCE PLAN
# ============================================================

@app.get("/ai/best-plan")
def get_ai_best_plan(
    db: Session = Depends(get_db),
):
    cached = get_cached_ai(
        "best_plan"
    )

    if cached is not None:

        return {
            **cached,
            "cached":
                True,
        }

    result = generate_ai_best_plan(
        db=db
    )

    if isinstance(
        result,
        dict,
    ):

        set_cached_ai(
            "best_plan",
            result,
        )

    return result


# ============================================================
# AI BEST PLAN SUMMARY
# ============================================================

@app.get("/ai/best-plan/summary")
def get_ai_best_plan_summary(
    db: Session = Depends(get_db),
):
    return get_ai_plan_summary(
        db=db
    )


# ============================================================
# ADMIN ANALYTICS
# ============================================================

ANALYTICS_CACHE_TTL_SECONDS = 10.0

_analytics_cache = None
_analytics_cache_time = 0.0
_analytics_cache_lock = Lock()


def clear_analytics_cache():
    global _analytics_cache
    global _analytics_cache_time

    with _analytics_cache_lock:
        _analytics_cache = None
        _analytics_cache_time = 0.0


def get_cached_analytics():
    now = monotonic()

    with _analytics_cache_lock:
        if (
            _analytics_cache is not None
            and (
                now - _analytics_cache_time
            ) < ANALYTICS_CACHE_TTL_SECONDS
        ):
            return _analytics_cache

    return None


def set_cached_analytics(value):
    global _analytics_cache
    global _analytics_cache_time

    with _analytics_cache_lock:
        _analytics_cache = value
        _analytics_cache_time = monotonic()


@app.get("/admin/analytics")
def get_admin_analytics_dashboard(
    db: Session = Depends(get_db),
):
    cached = get_cached_analytics()

    if cached is not None:
        return {
            **cached,
            "cached": True,
        }

    result = get_admin_analytics(
        db=db
    )

    set_cached_analytics(result)

    return {
        **result,
        "cached": False,
    }
# ============================================================
# AI OPERATIONS AGENT
# ============================================================

@app.get("/ai/agent")
def get_ai_operations_agent(
    db: Session = Depends(get_db),
):
    return run_ai_operations_agent(
        db=db
    )


# ============================================================
# ASK AI OPERATIONS AGENT
# ============================================================

@app.post("/ai/agent/ask")
def ask_ai_operations_agent(
    question: str,
    db: Session = Depends(get_db),
):
    return ask_ai_agent(
        db=db,
        question=question,
    )


# ============================================================
# INTEGRATION STATUS
# ============================================================

@app.get("/integration/status")
def get_integration_status(
    db: Session = Depends(get_db),
):
    return (
        integration_service
        .get_health_status(
            db=db
        )
    )


# ============================================================
# UNIFIED RAILWAY DATA
# ============================================================

@app.get("/integration/unified-data")
def get_unified_railway_data(
    db: Session = Depends(get_db),
):
    return (
        integration_service
        .get_unified_snapshot(
            db=db
        )
    )


# ============================================================
# ACTUAL ML ASSET RISK — SINGLE
# ============================================================

@app.get(
    "/ai/ml-risk/assets/{asset_id}"
)
def get_ml_asset_risk(
    asset_id: int,
    db: Session = Depends(get_db),
):
    asset = (
        db.query(Asset)
        .filter(
            Asset.asset_id
            == asset_id
        )
        .first()
    )

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Asset {asset_id} not found."
            ),
        )

    try:

        return predict_asset_risk(
            db=db,
            asset=asset,
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "ML prediction failed: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# ACTUAL ML ASSET RISK — ALL
# ============================================================

@app.get(
    "/ai/ml-risk/assets"
)
def get_all_ml_asset_risks(
    db: Session = Depends(get_db),
):
    try:

        results = predict_all_asset_risks(
            db=db
        )

        return {
            "total_assets":
                len(results),

            "model":
                "RandomForestClassifier",

            "training_source":
                "Synthetic prototype training data",

            "assets":
                results,
        }

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "ML prediction failed: "
                f"{str(exc)}"
            ),
        )