
from datetime import date, datetime

from numpy import block
from backend.engines.ai_agent import (
    run_ai_operations_agent,
    ask_ai_agent,
)

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.engines.analytics_engine import (
    get_operational_kpis,
    get_maintenance_analytics,
    get_defect_analytics,
    get_block_analytics,
    get_ai_analytics,
    get_admin_analytics,
)

from backend.engines.ai_planner import (
    generate_ai_best_plan,
    get_ai_plan_summary,
)


from backend.engines.ai_decision_engine import (
    calculate_ai_decision,
    calculate_all_ai_decisions,
)

from backend.engines.risk_engine import (
    calculate_asset_risk,
    calculate_all_asset_risks,
    calculate_smart_priority,
    calculate_all_smart_priorities,
)

from backend.database.connection import get_db
from backend.database.models import (
    Station,
    Section,
    Asset,
    MaintenanceTask,
    Defect,
    Train,
    TrainSchedule,
    GoodsForecast,
    Block,
    BlockTask,
    OperationalEvent,
)
from backend.engines.priority_engine import calculate_all_priorities
from backend.engines.block_planner import generate_maintenance_plan

from backend.engines.optimization_engine import (
    analyze_block_impact,
    analyze_all_blocks,
    recommend_reschedule,
    recommend_rescheduling_for_all_blocks,
    optimize_all_blocks,
    replan_after_event,
)
# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AI Automatic Railway Block Planner",
    description="Railway maintenance and automatic block planning system",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "message": "Railway Block Planner API is running"
    }


# ============================================================
# STATIONS
# ============================================================

@app.get("/stations")
def get_stations(
    db: Session = Depends(get_db),
):
    stations = (
        db.query(Station)
        .order_by(Station.station_id)
        .all()
    )

    return [
        {
            "station_id": station.station_id,
            "station_code": station.station_code,
            "station_name": station.station_name,
        }
        for station in stations
    ]


# ============================================================
# SECTIONS
# ============================================================

@app.get("/sections")
def get_sections(
    db: Session = Depends(get_db),
):
    sections = (
        db.query(Section)
        .order_by(Section.section_id)
        .all()
    )

    return [
        {
            "section_id": section.section_id,
            "section_code": section.section_code,
            "from_station_id": section.from_station_id,
            "to_station_id": section.to_station_id,
            "distance_km": (
                float(section.distance_km)
                if section.distance_km is not None
                else None
            ),
            "status": section.status,
        }
        for section in sections
    ]


# ============================================================
# ASSETS
# ============================================================

@app.get("/assets")
def get_assets(
    db: Session = Depends(get_db),
):
    assets = (
        db.query(Asset)
        .order_by(Asset.asset_id)
        .all()
    )

    return [
        {
            "asset_id": asset.asset_id,
            "asset_code": asset.asset_code,
            "asset_type": asset.asset_type,
            "section_id": asset.section_id,
            "department_id": asset.department_id,
            "criticality": asset.criticality,
            "status": asset.status,
        }
        for asset in assets
    ]


# ============================================================
# MAINTENANCE TASKS
# ============================================================

@app.get("/maintenance-tasks")
def get_maintenance_tasks(
    db: Session = Depends(get_db),
):
    tasks = (
        db.query(MaintenanceTask)
        .order_by(MaintenanceTask.task_id)
        .all()
    )

    return [
        {
            "task_id": task.task_id,
            "task_code": task.task_code,
            "source_system": task.source_system,
            "department_id": task.department_id,
            "asset_id": task.asset_id,
            "section_id": task.section_id,
            "task_type": task.task_type,
            "severity": task.severity,
            "duration_hours": (
                float(task.duration_hours)
                if task.duration_hours is not None
                else None
            ),
            "status": task.status,
            "due_date": task.due_date,
            "description": task.description,
            "created_at": task.created_at,
        }
        for task in tasks
    ]


# ============================================================
# DEFECTS
# ============================================================

@app.get("/defects")
def get_defects(
    db: Session = Depends(get_db),
):
    defects = (
        db.query(Defect)
        .order_by(Defect.defect_id)
        .all()
    )

    return [
        {
            "defect_id": defect.defect_id,
            "defect_code": defect.defect_code,
            "asset_id": defect.asset_id,
            "section_id": defect.section_id,
            "severity": defect.severity,
            "description": defect.description,
            "detected_date": defect.detected_date,
            "status": defect.status,
        }
        for defect in defects
    ]


# ============================================================
# TRAINS
# ============================================================

@app.get("/trains")
def get_trains(
    db: Session = Depends(get_db),
):
    trains = (
        db.query(Train)
        .order_by(Train.train_id)
        .all()
    )

    return [
        {
            "train_id": train.train_id,
            "train_no": train.train_no,
            "train_name": train.train_name,
            "train_type": train.train_type,
            "priority": train.priority,
        }
        for train in trains
    ]


# ============================================================
# TRAIN SCHEDULE
# ============================================================

@app.get("/train-schedule")
def get_train_schedule(
    db: Session = Depends(get_db),
):
    schedules = (
        db.query(TrainSchedule)
        .order_by(
            TrainSchedule.schedule_date,
            TrainSchedule.arrival_time,
        )
        .all()
    )

    return [
        {
            "schedule_id": schedule.schedule_id,
            "train_id": schedule.train_id,
            "section_id": schedule.section_id,
            "schedule_date": schedule.schedule_date,
            "arrival_time": schedule.arrival_time,
            "departure_time": schedule.departure_time,
        }
        for schedule in schedules
    ]


# ============================================================
# GOODS FORECAST
# ============================================================

@app.get("/goods-forecast")
def get_goods_forecast(
    db: Session = Depends(get_db),
):
    forecasts = (
        db.query(GoodsForecast)
        .order_by(
            GoodsForecast.forecast_date,
            GoodsForecast.section_id,
        )
        .all()
    )

    return [
        {
            "forecast_id": forecast.forecast_id,
            "section_id": forecast.section_id,
            "forecast_date": forecast.forecast_date,
            "expected_goods_trains": (
                forecast.expected_goods_trains
            ),
        }
        for forecast in forecasts
    ]


# ============================================================
# MAINTENANCE PRIORITY ENGINE
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
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.status.notin_(
                ["COMPLETED", "CANCELLED"]
            )
        )
        .all()
    )

    recommendations = generate_maintenance_plan(
        db=db,
        tasks=tasks,
        schedule_date=schedule_date,
    )

    return {
        "schedule_date": schedule_date,
        "total_tasks": len(tasks),
        "recommendations": recommendations,
    }


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
):
    """
    Create and save a maintenance block.
    """

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    if not task_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one task ID is required.",
        )

    # --------------------------------------------------------
    # Validate section
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Validate tasks
    # --------------------------------------------------------

    tasks = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.task_id.in_(task_ids)
        )
        .all()
    )

    if len(tasks) != len(set(task_ids)):
        raise HTTPException(
            status_code=404,
            detail="One or more task IDs were not found.",
        )

    for task in tasks:
        if task.section_id != section_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "All selected tasks must belong "
                    "to the same section."
                ),
            )

        if task.status in [
            "COMPLETED",
            "CANCELLED",
        ]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Task {task.task_code} cannot be "
                    f"scheduled because its status is "
                    f"{task.status}."
                ),
            )

    # --------------------------------------------------------
    # Parse times
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Prevent block overlap on same section/date
    # --------------------------------------------------------

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

        overlap = (
            new_start_minutes < existing_end
            and existing_start < new_end_minutes
        )

        if overlap:
            raise HTTPException(
                status_code=409,
                detail=(
                    "The requested block overlaps an "
                    "existing block on this section."
                ),
            )

    # --------------------------------------------------------
    # Generate block code
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Create block
    # --------------------------------------------------------

    block = Block(
        block_code=block_code,
        section_id=section_id,
        block_date=block_date,
        start_time=parsed_start_time,
        end_time=parsed_end_time,
        reason=(
            f"Automatic maintenance block for "
            f"{len(tasks)} task(s)"
        ),
        status="PLANNED",
    )

    db.add(block)
    db.flush()

    # --------------------------------------------------------
    # Create BlockTask records
    # --------------------------------------------------------

    for task in tasks:
        block_task = BlockTask(
            block_id=block.block_id,
            task_id=task.task_id,
        )

        db.add(block_task)

        task.status = "SCHEDULED"
        
       # --------------------------------------------------------
    # Calculate initial train impact
    # --------------------------------------------------------

    impact = analyze_block_impact(
        db=db,
        block=block,
    )

    recommendation = recommend_reschedule(
        db=db,
        block=block,
    )  
    
    # --------------------------------------------------------
# Save initial recommendation on block
# --------------------------------------------------------

    alternative_start = recommendation["alternative_start_time"]
    alternative_end = recommendation["alternative_end_time"]

    actual_timing_changed = (
    alternative_start is not None
    and alternative_end is not None
    and (
        alternative_start != block.start_time
        or alternative_end != block.end_time
    )
)

    block.replan_required = (
    recommendation["recommended_action"]
    in {
        "RESCHEDULE",
        "CONSIDER_RESCHEDULE",
    }
    and actual_timing_changed
)

    block.recommended_start_time = (
    alternative_start if actual_timing_changed else None
)

    block.recommended_end_time = (
    alternative_end if actual_timing_changed else None
)
          

    # --------------------------------------------------------
    # Commit
    # --------------------------------------------------------

    db.commit()
    db.refresh(block)
    
    
    
    return {
    "message": "Maintenance block created successfully",
    "block": {
        "block_id": block.block_id,
        "block_code": block.block_code,
        "section_id": block.section_id,
        "block_date": block.block_date,
        "start_time": block.start_time,
        "end_time": block.end_time,
        "reason": block.reason,
        "status": block.status,
        "task_ids": task_ids,

        # Initial train impact
        "conflict_count": impact["conflict_count"],
        "affected_train_ids": impact["affected_train_ids"],
        "total_conflict_minutes": impact["total_conflict_minutes"],
        "impact_level": impact["impact_level"],

        # Recommendation
        "recommended_action": recommendation["recommended_action"],
        "recommendation": recommendation["recommendation"],
        "alternative_start_time": recommendation["alternative_start_time"],
        "alternative_end_time": recommendation["alternative_end_time"],
             },
    }


# ============================================================
# GET ALL MAINTENANCE BLOCKS
# ============================================================

@app.get("/planner/blocks")
def get_maintenance_blocks(
    db: Session = Depends(get_db),
):
    """
    Return all saved maintenance blocks.
    """

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
            for block_task in block.block_tasks
        ]

        result.append(
            {
                "block_id": block.block_id,
                "block_code": block.block_code,
                "section_id": block.section_id,
                "block_date": block.block_date,
                "start_time": block.start_time,
                "end_time": block.end_time,
                "reason": block.reason,
                "status": block.status,
                "replan_required": block.replan_required,
                "recommended_start_time": block.recommended_start_time,
                "recommended_end_time": block.recommended_end_time,
                "task_ids": task_ids,
            }
        )

    return result


# ============================================================
# UPDATE MAINTENANCE BLOCK STATUS
# ============================================================

@app.patch("/planner/blocks/{block_id}/status")
def update_block_status(
    block_id: int,
    new_status: str,
    db: Session = Depends(get_db),
):
    """
    Update the status of a maintenance block.

    Allowed statuses:
        PLANNED
        APPROVED
        IN_PROGRESS
        COMPLETED
        CANCELLED
    """

    allowed_statuses = {
        "PLANNED",
        "APPROVED",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
    }

    new_status = new_status.upper().strip()

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid status '{new_status}'. "
                f"Allowed statuses: "
                f"{', '.join(sorted(allowed_statuses))}"
            ),
        )

    # --------------------------------------------------------
    # Find block
    # --------------------------------------------------------

    block = (
        db.query(Block)
        .filter(
            Block.block_id == block_id
        )
        .first()
    )

    if block is None:
        raise HTTPException(
            status_code=404,
            detail=f"Block {block_id} not found.",
        )

    current_status = block.status

    # --------------------------------------------------------
    # Validate status transition
    # --------------------------------------------------------

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
                    f"Invalid status transition: "
                    f"{current_status} → {new_status}"
                ),
            )

    # --------------------------------------------------------
    # Update block
    # --------------------------------------------------------

    block.status = new_status

    # --------------------------------------------------------
    # Update related task statuses
    # --------------------------------------------------------

    related_task_ids = [
        block_task.task_id
        for block_task in block.block_tasks
    ]

    tasks = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.task_id.in_(
                related_task_ids
            )
        )
        .all()
    )

    if new_status == "APPROVED":

        for task in tasks:
            if task.status == "SCHEDULED":
                task.status = "SCHEDULED"

    elif new_status == "IN_PROGRESS":

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

    # --------------------------------------------------------
    # Save changes
    # --------------------------------------------------------

    db.commit()
    db.refresh(block)

    return {
        "message": "Block status updated successfully",
        "block": {
            "block_id": block.block_id,
            "block_code": block.block_code,
            "section_id": block.section_id,
            "block_date": block.block_date,
            "start_time": block.start_time,
            "end_time": block.end_time,
            "status": block.status,
            "task_ids": related_task_ids,
        },
    }



# ============================================================
# ANALYZE SINGLE BLOCK TRAIN IMPACT
# ============================================================

@app.get("/planner/blocks/{block_id}/impact")
def get_block_impact(
    block_id: int,
    db: Session = Depends(get_db),
):
    """
    Analyze train conflicts for a single maintenance block.
    """

    block = (
        db.query(Block)
        .filter(
            Block.block_id == block_id
        )
        .first()
    )

    if block is None:
        raise HTTPException(
            status_code=404,
            detail=f"Block {block_id} not found.",
        )

    return analyze_block_impact(
        db=db,
        block=block,
    )


# ============================================================
# ANALYZE ALL MAINTENANCE BLOCKS
# ============================================================

@app.get("/planner/blocks/impact")
def get_all_block_impacts(
    db: Session = Depends(get_db),
):
    """
    Analyze train impact for all non-cancelled blocks.
    """

    results = analyze_all_blocks(
        db=db
    )

    return {
        "total_blocks": len(results),
        "blocks": results,
    }
    

# ============================================================
# SINGLE BLOCK RESCHEDULING RECOMMENDATION
# ============================================================

@app.get("/planner/blocks/{block_id}/recommendation")
def get_block_recommendation(
    block_id: int,
    db: Session = Depends(get_db),
):
    """
    Analyze one block and provide a rescheduling
    recommendation if required.
    """

    block = (
        db.query(Block)
        .filter(
            Block.block_id == block_id
        )
        .first()
    )

    if block is None:
        raise HTTPException(
            status_code=404,
            detail=f"Block {block_id} not found.",
        )

    return recommend_reschedule(
        db=db,
        block=block,
    )


# ============================================================
# ALL BLOCK RESCHEDULING RECOMMENDATIONS
# ============================================================

@app.get("/planner/blocks/recommendations")
def get_all_block_recommendations(
    db: Session = Depends(get_db),
):
    """
    Analyze all non-cancelled blocks and provide
    rescheduling recommendations.
    """

    results = recommend_rescheduling_for_all_blocks(
        db=db
    )

    return {
        "total_blocks": len(results),
        "recommendations": results,
    }
    

# ============================================================
# FINAL MAINTENANCE PLAN OPTIMIZATION
# ============================================================

@app.get("/planner/optimization")
def get_optimized_plans(
    db: Session = Depends(get_db),
):
    """
    Return optimized results for all non-cancelled
    maintenance blocks.
    """

    results = optimize_all_blocks(
        db=db
    )

    return {
        "total_blocks": len(results),
        "optimized_blocks": results,
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
):
    """
    Create a new operational event.

    Supported event types:
        DEFECT
        TRAIN_DELAY
        BLOCK_CHANGE
    """

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

    event_type = event_type.upper().strip()
    severity = severity.upper().strip()

    # --------------------------------------------------------
    # Normalize optional asset_id
    # --------------------------------------------------------

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
                asset_id = int(asset_id)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="asset_id must be a valid integer.",
                )

    # --------------------------------------------------------
    # Validate event type
    # --------------------------------------------------------

    if event_type not in allowed_event_types:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid event type '{event_type}'. "
                f"Allowed types: "
                f"{', '.join(sorted(allowed_event_types))}"
            ),
        )

    # --------------------------------------------------------
    # Validate severity
    # --------------------------------------------------------

    if severity not in allowed_severities:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid severity '{severity}'. "
                f"Allowed values: "
                f"{', '.join(sorted(allowed_severities))}"
            ),
        )

    # --------------------------------------------------------
    # Validate section
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Validate asset
    # --------------------------------------------------------

    if asset_id is not None:

        asset = (
            db.query(Asset)
            .filter(
                Asset.asset_id == asset_id
            )
            .first()
        )

        if asset is None:
            raise HTTPException(
                status_code=404,
                detail=f"Asset {asset_id} not found.",
            )

        if asset.section_id != section_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Asset does not belong to "
                    "the selected section."
                ),
            )

    # --------------------------------------------------------
    # Validate train
    # --------------------------------------------------------

    if train_id is not None:

        train = (
            db.query(Train)
            .filter(
                Train.train_id == train_id
            )
            .first()
        )

        if train is None:
            raise HTTPException(
                status_code=404,
                detail=f"Train {train_id} not found.",
            )

    # --------------------------------------------------------
    # Event-specific validation
    # --------------------------------------------------------

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

        if delay_minutes is None or delay_minutes <= 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "delay_minutes must be greater "
                    "than 0 for TRAIN_DELAY events."
                ),
            )

    # --------------------------------------------------------
    # Create event
    # --------------------------------------------------------

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
    db.refresh(event)

    return {
        "message": "Operational event created successfully",
        "event": {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "event_date": event.event_date,
            "section_id": event.section_id,
            "asset_id": event.asset_id,
            "train_id": event.train_id,
            "severity": event.severity,
            "delay_minutes": event.delay_minutes,
            "description": event.description,
            "status": event.status,
            "created_at": event.created_at,
        },
    }
# ============================================================
# GET OPERATIONAL EVENTS
# ============================================================

@app.get("/events")
def get_operational_events(
    db: Session = Depends(get_db),
):
    """
    Return all operational events.
    """

    events = (
        db.query(OperationalEvent)
        .order_by(
            OperationalEvent.created_at.desc()
        )
        .all()
    )

    return [
        {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "event_date": event.event_date,
            "section_id": event.section_id,
            "asset_id": event.asset_id,
            "train_id": event.train_id,
            "severity": event.severity,
            "delay_minutes": event.delay_minutes,
            "description": event.description,
            "status": event.status,
            "created_at": event.created_at,
        }
        for event in events
    ]    

# ============================================================
# TRIGGER DYNAMIC RE-PLANNING
# ============================================================

@app.post("/events/{event_id}/replan")
def trigger_event_replanning(
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Trigger dynamic maintenance re-planning for an
    operational event.
    """

    event = (
        db.query(OperationalEvent)
        .filter(
            OperationalEvent.event_id == event_id
        )
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail=f"Operational event {event_id} not found.",
        )

    if event.status != "OPEN":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Event {event_id} is already "
                f"{event.status}."
            ),
        )

    result = replan_after_event(
        db=db,
        event=event,
    )

    return {
        "message": "Dynamic re-planning completed successfully",
        "replanning_result": result,
    }
    
# ============================================================
# APPLY RECOMMENDED RE-PLANNING
# ============================================================

@app.post("/events/{event_id}/apply-replan")
def apply_recommended_replan(
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Apply the recommended maintenance block window
    generated by dynamic re-planning.
    """

    event = (
        db.query(OperationalEvent)
        .filter(
            OperationalEvent.event_id == event_id
        )
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail=f"Operational event {event_id} not found.",
        )

    # Recalculate latest recommendation
    result = replan_after_event(
        db=db,
        event=event,
    )

    applied_blocks = []

    for block_result in result["affected_blocks"]:

        if (
            block_result["recommended_action"]
            not in {
                "RESCHEDULE",
                "CONSIDER_RESCHEDULE",
            }
        ):
            continue

        block = (
            db.query(Block)
            .filter(
                Block.block_id
                == block_result["block_id"]
            )
            .first()
        )

        if block is None:
            continue

        alternative_start = (
            block_result["alternative_start_time"]
        )

        alternative_end = (
            block_result["alternative_end_time"]
        )

        if (
            alternative_start is None
            or alternative_end is None
        ):
            continue

        # Save recommendation fields
        block.replan_required = False
        block.recommended_start_time = (
            alternative_start
        )
        block.recommended_end_time = (
            alternative_end
        )

        # Apply new block timing
        block.start_time = alternative_start
        block.end_time = alternative_end

        applied_blocks.append(
            {
                "block_id": block.block_id,
                "block_code": block.block_code,
                "new_start_time": block.start_time,
                "new_end_time": block.end_time,
            }
        )
    # Apply recommended block changes
    # ...

    event.status = "RESOLVED"    

    db.commit()

    return {
        "message": "Recommended maintenance plan applied successfully",
        "event_id": event_id,
        "applied_blocks": applied_blocks,
    }    

# ============================================================
# AI ASSET RISK — SINGLE ASSET
# ============================================================

@app.get("/ai/risk/assets/{asset_id}")
def get_asset_risk(
    asset_id: int,
    db: Session = Depends(get_db),
):
    """
    Calculate maintenance risk for a single asset.
    """

    asset = (
        db.query(Asset)
        .filter(
            Asset.asset_id == asset_id
        )
        .first()
    )

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail=f"Asset {asset_id} not found.",
        )

    return calculate_asset_risk(
        db=db,
        asset=asset,
    )


# ============================================================
# AI ASSET RISK — ALL ASSETS
# ============================================================

@app.get("/ai/risk/assets")
def get_all_asset_risks(
    db: Session = Depends(get_db),
):
    """
    Calculate maintenance risk for all active assets.
    """

    results = calculate_all_asset_risks(
        db=db
    )

    return {
        "total_assets": len(results),
        "assets": results,
    }
    
# ============================================================
# AI SMART MAINTENANCE PRIORITY
# ============================================================

@app.get("/ai/smart-priority")
def get_smart_maintenance_priority(
    db: Session = Depends(get_db),
):
    """
    Calculate smart maintenance priority for all active tasks.

    Combines:
        - Existing maintenance priority
        - AI asset risk
    """

    results = calculate_all_smart_priorities(
        db=db
    )

    return {
        "total_tasks": len(results),
        "tasks": results,
    }    

# ============================================================
# AI MAINTENANCE DECISIONS
# ============================================================

@app.get("/ai/decisions")
def get_ai_maintenance_decisions(
    db: Session = Depends(get_db),
):
    """
    Generate AI-assisted maintenance decisions
    for all active maintenance tasks.
    """

    results = calculate_all_ai_decisions(
        db=db
    )

    return {
        "total_tasks": len(results),
        "decisions": results,
    }
    
    
# ============================================================
# AI BEST MAINTENANCE PLAN
# ============================================================

@app.get("/ai/best-plan")
def get_ai_best_plan(
    db: Session = Depends(get_db),
):
    """
    Generate the best maintenance plan using the
    combined AI decision engine.
    """

    result = generate_ai_best_plan(
        db=db
    )

    return result


# ============================================================
# AI BEST PLAN SUMMARY
# ============================================================

@app.get("/ai/best-plan/summary")
def get_ai_best_plan_summary(
    db: Session = Depends(get_db),
):
    """
    Return a compact summary of the AI-recommended plan.
    """

    return get_ai_plan_summary(
        db=db
    )    
    
# ============================================================
# ADMIN ANALYTICS
# ============================================================

@app.get("/admin/analytics")
def get_admin_analytics_dashboard(
    db: Session = Depends(get_db),
):
    """
    Return complete admin analytics and KPI data.
    """

    return get_admin_analytics(
        db=db
    ) 
    
# ============================================================
# AI OPERATIONS AGENT
# ============================================================

@app.get("/ai/agent")
def get_ai_operations_agent(
    db: Session = Depends(get_db),
):
    """
    Run the AI Operations Agent and return
    intelligent railway maintenance recommendations.
    """

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
    """
    Ask the AI Operations Agent a railway
    maintenance or operational question.
    """

    return ask_ai_agent(
        db=db,
        question=question,
    )        
    
