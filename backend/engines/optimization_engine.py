from datetime import time

from sqlalchemy.orm import Session

from backend.database.models import (
    Asset,
    Block,
    TrainSchedule,
    MaintenanceTask,
    OperationalEvent,
)

from backend.engines.priority_engine import (
    calculate_task_priority,
)

from backend.engines.risk_engine import (
    calculate_asset_risk,
)

from backend.engines.block_planner import (
    find_available_window,
)


# ============================================================
# SETTINGS
# ============================================================

TRAIN_BUFFER_MINUTES = 15

WORKING_START = time(8, 0)
WORKING_END = time(20, 0)


# ============================================================
# ML / EVENT SETTINGS
# ============================================================

TASK_PRIORITY_WEIGHT = 0.60
ASSET_RISK_WEIGHT = 0.40

EVENT_SEVERITY_BOOST = {
    "LOW": 0.0,
    "MEDIUM": 5.0,
    "HIGH": 10.0,
    "CRITICAL": 15.0,
}


# ============================================================
# TIME HELPERS
# ============================================================

def time_to_minutes(value: time) -> int:
    """
    Convert time into minutes from midnight.
    """

    return (
        value.hour * 60
        + value.minute
    )


def minutes_to_time(value: int) -> time:
    """
    Convert minutes from midnight into time safely.
    """

    value = max(
        0,
        min(
            value,
            23 * 60 + 59,
        ),
    )

    return time(
        value // 60,
        value % 60,
    )


# ============================================================
# INTERVAL OVERLAP
# ============================================================

def intervals_overlap(
    start_a: int,
    end_a: int,
    start_b: int,
    end_b: int,
) -> bool:
    """
    Return True when two intervals overlap.
    """

    return (
        start_a < end_b
        and start_b < end_a
    )


# ============================================================
# GET TRAINS FOR BLOCK
# ============================================================

def get_block_train_schedules(
    db: Session,
    block: Block,
) -> list[TrainSchedule]:
    """
    Get train schedules for the same section/date.
    """

    return (
        db.query(TrainSchedule)
        .filter(
            TrainSchedule.section_id
            == block.section_id,

            TrainSchedule.schedule_date
            == block.block_date,
        )
        .order_by(
            TrainSchedule.arrival_time
        )
        .all()
    )


# ============================================================
# GET ACTIVE TRAIN DELAYS
# ============================================================

def get_active_train_delays(
    db: Session,
    section_id: int,
    schedule_date,
) -> dict[int, int]:
    """
    Return the latest ACTIVE delay for each train.

    Multiple OPEN delay events for the same train
    are not accumulated.

    Latest event wins.
    """

    events = (
        db.query(OperationalEvent)
        .filter(
            OperationalEvent.event_type
            == "TRAIN_DELAY",

            OperationalEvent.event_date
            == schedule_date,

            OperationalEvent.section_id
            == section_id,

            OperationalEvent.status
            == "OPEN",
        )
        .order_by(
            OperationalEvent.created_at.desc(),
            OperationalEvent.event_id.desc(),
        )
        .all()
    )

    delay_by_train: dict[int, int] = {}

    for event in events:

        if event.train_id is None:
            continue

        if (
            event.train_id
            not in delay_by_train
        ):

            delay_by_train[event.train_id] = (
                event.delay_minutes
                or 0
            )

    return delay_by_train


# ============================================================
# GET EFFECTIVE TRAIN MOVEMENTS
# ============================================================

def get_effective_train_movements(
    db: Session,
    section_id: int,
    schedule_date,
) -> list[dict]:
    """
    Return effective train timings after applying
    latest OPEN TRAIN_DELAY event for each train.
    """

    schedules = (
        db.query(TrainSchedule)
        .filter(
            TrainSchedule.section_id
            == section_id,

            TrainSchedule.schedule_date
            == schedule_date,
        )
        .order_by(
            TrainSchedule.arrival_time
        )
        .all()
    )

    delay_by_train = get_active_train_delays(
        db=db,
        section_id=section_id,
        schedule_date=schedule_date,
    )

    movements = []

    for schedule in schedules:

        delay = delay_by_train.get(
            schedule.train_id,
            0,
        )

        original_arrival = time_to_minutes(
            schedule.arrival_time
        )

        original_departure = time_to_minutes(
            schedule.departure_time
        )

        effective_arrival = (
            original_arrival
            + delay
        )

        effective_departure = (
            original_departure
            + delay
        )

        movements.append(
            {
                "schedule_id": (
                    schedule.schedule_id
                ),

                "train_id": (
                    schedule.train_id
                ),

                "section_id": (
                    schedule.section_id
                ),

                "original_arrival_time": (
                    schedule.arrival_time
                ),

                "original_departure_time": (
                    schedule.departure_time
                ),

                "arrival_time": minutes_to_time(
                    effective_arrival
                ),

                "departure_time": minutes_to_time(
                    effective_departure
                ),

                "delay_minutes": (
                    delay
                ),
            }
        )

    return movements


# ============================================================
# DETECT TRAIN CONFLICTS
# ============================================================

def detect_block_conflicts(
    db: Session,
    block: Block,
) -> list[dict]:
    """
    Detect train movements conflicting with a maintenance block.

    A 15-minute safety buffer is applied around train movements.

    Active TRAIN_DELAY events are automatically considered.
    """

    block_start = time_to_minutes(
        block.start_time
    )

    block_end = time_to_minutes(
        block.end_time
    )

    schedules = get_effective_train_movements(
        db=db,
        section_id=block.section_id,
        schedule_date=block.block_date,
    )

    conflicts = []

    for schedule in schedules:

        train_start = (
            time_to_minutes(
                schedule["arrival_time"]
            )
            - TRAIN_BUFFER_MINUTES
        )

        train_end = (
            time_to_minutes(
                schedule["departure_time"]
            )
            + TRAIN_BUFFER_MINUTES
        )

        train_start = max(
            train_start,
            0,
        )

        train_end = min(
            train_end,
            24 * 60,
        )

        if not intervals_overlap(
            block_start,
            block_end,
            train_start,
            train_end,
        ):
            continue

        overlap_start = max(
            block_start,
            train_start,
        )

        overlap_end = min(
            block_end,
            train_end,
        )

        if overlap_end <= overlap_start:
            continue

        conflicts.append(
            {
                "schedule_id": (
                    schedule["schedule_id"]
                ),

                "train_id": (
                    schedule["train_id"]
                ),

                "section_id": (
                    schedule["section_id"]
                ),

                "arrival_time": (
                    schedule["arrival_time"]
                ),

                "departure_time": (
                    schedule["departure_time"]
                ),

                "delay_minutes": (
                    schedule["delay_minutes"]
                ),

                "conflict_start": (
                    minutes_to_time(
                        overlap_start
                    )
                ),

                "conflict_end": (
                    minutes_to_time(
                        overlap_end
                    )
                ),

                "conflict_duration_minutes": (
                    overlap_end
                    - overlap_start
                ),
            }
        )

    return conflicts


# ============================================================
# CONFLICT IMPACT LEVEL
# ============================================================

def calculate_impact_level(
    conflict_count: int,
    total_conflict_minutes: int,
) -> str:
    """
    Convert conflict information into impact level.
    """

    if conflict_count == 0:
        return "NONE"

    if (
        conflict_count >= 3
        or total_conflict_minutes >= 60
    ):
        return "HIGH"

    if (
        conflict_count >= 2
        or total_conflict_minutes >= 30
    ):
        return "MEDIUM"

    return "LOW"


# ============================================================
# ANALYZE BLOCK IMPACT
# ============================================================

def analyze_block_impact(
    db: Session,
    block: Block,
) -> dict:
    """
    Analyze complete train impact for one block.
    """

    conflicts = detect_block_conflicts(
        db=db,
        block=block,
    )

    total_conflict_minutes = sum(
        conflict[
            "conflict_duration_minutes"
        ]
        for conflict in conflicts
    )

    impact_level = calculate_impact_level(
        conflict_count=len(conflicts),
        total_conflict_minutes=(
            total_conflict_minutes
        ),
    )

    affected_train_ids = [
        conflict["train_id"]
        for conflict in conflicts
    ]

    return {
        "block_id": block.block_id,

        "block_code": block.block_code,

        "section_id": block.section_id,

        "block_date": block.block_date,

        "start_time": block.start_time,

        "end_time": block.end_time,

        "conflict_count": (
            len(conflicts)
        ),

        "affected_train_ids": (
            affected_train_ids
        ),

        "total_conflict_minutes": (
            total_conflict_minutes
        ),

        "impact_level": (
            impact_level
        ),

        "conflicts": conflicts,
    }


# ============================================================
# ANALYZE ALL PLANNED BLOCKS
# ============================================================

def analyze_all_blocks(
    db: Session,
) -> list[dict]:
    """
    Analyze all non-cancelled blocks.
    """

    blocks = (
        db.query(Block)
        .filter(
            Block.status != "CANCELLED"
        )
        .order_by(
            Block.block_date,
            Block.start_time,
        )
        .all()
    )

    return [
        analyze_block_impact(
            db=db,
            block=block,
        )
        for block in blocks
    ]


# ============================================================
# GET EFFECTIVE TRAIN INTERVALS
# ============================================================

def get_effective_train_intervals(
    db: Session,
    section_id: int,
    schedule_date,
) -> list[tuple[int, int]]:
    """
    Return occupied train intervals after applying
    active train-delay events.
    """

    schedules = get_effective_train_movements(
        db=db,
        section_id=section_id,
        schedule_date=schedule_date,
    )

    intervals = []

    for schedule in schedules:

        arrival = (
            time_to_minutes(
                schedule["arrival_time"]
            )
            - TRAIN_BUFFER_MINUTES
        )

        departure = (
            time_to_minutes(
                schedule["departure_time"]
            )
            + TRAIN_BUFFER_MINUTES
        )

        intervals.append(
            (
                max(arrival, 0),
                min(
                    departure,
                    24 * 60,
                ),
            )
        )

    return intervals


# ============================================================
# FIND SAFEST ALTERNATIVE WINDOW
# ============================================================

def find_conflict_free_window(
    db: Session,
    section_id: int,
    schedule_date,
    duration_hours: float,
    working_start: time = WORKING_START,
    working_end: time = WORKING_END,
    reserved_intervals: list[
        tuple[int, int]
    ] | None = None,
) -> tuple[time, time] | None:
    """
    Find the earliest maintenance window that avoids:

        1. Train movements
        2. Existing reserved maintenance windows
    """

    duration_minutes = max(
        int(
            round(
                duration_hours * 60
            )
        ),
        1,
    )

    candidate_start = time_to_minutes(
        working_start
    )

    end_limit = time_to_minutes(
        working_end
    )

    occupied_intervals = (
        get_effective_train_intervals(
            db=db,
            section_id=section_id,
            schedule_date=schedule_date,
        )
    )

    if reserved_intervals:
        occupied_intervals.extend(
            reserved_intervals
        )

    occupied_intervals.sort(
        key=lambda interval: interval[0]
    )

    while (
        candidate_start
        + duration_minutes
        <= end_limit
    ):

        candidate_end = (
            candidate_start
            + duration_minutes
        )

        conflict_found = False

        for (
            occupied_start,
            occupied_end,
        ) in occupied_intervals:

            if (
                candidate_end
                <= occupied_start
            ):
                break

            if intervals_overlap(
                candidate_start,
                candidate_end,
                occupied_start,
                occupied_end,
            ):

                candidate_start = (
                    occupied_end
                )

                conflict_found = True

                break

        if not conflict_found:

            return (
                minutes_to_time(
                    candidate_start
                ),
                minutes_to_time(
                    candidate_end
                ),
            )

    return None


# ============================================================
# RESCHEDULING RECOMMENDATION
# ============================================================

def recommend_reschedule(
    db: Session,
    block: Block,
) -> dict:
    """
    Analyze current block and recommend an alternative
    window when train conflicts exist.
    """

    impact = analyze_block_impact(
        db=db,
        block=block,
    )

    # ========================================================
    # NO CONFLICT
    # ========================================================

    if impact["conflict_count"] == 0:

        return {
            **impact,

            "recommended_action": (
                "KEEP_BLOCK"
            ),

            "recommendation": (
                "The current maintenance block is safe. "
                "No train conflict was detected."
            ),

            "alternative_start_time": (
                block.start_time
            ),

            "alternative_end_time": (
                block.end_time
            ),
        }

    # ========================================================
    # CURRENT BLOCK DURATION
    # ========================================================

    current_start = time_to_minutes(
        block.start_time
    )

    current_end = time_to_minutes(
        block.end_time
    )

    duration_minutes = (
        current_end
        - current_start
    )

    if duration_minutes <= 0:

        return {
            **impact,

            "recommended_action": (
                "MANUAL_REVIEW"
            ),

            "recommendation": (
                "The maintenance block has an invalid "
                "duration and requires manual review."
            ),

            "alternative_start_time": None,

            "alternative_end_time": None,
        }

    duration_hours = (
        duration_minutes / 60
    )

    # ========================================================
    # SEARCH ALTERNATIVE
    # ========================================================

    alternative = (
        find_conflict_free_window(
            db=db,

            section_id=block.section_id,

            schedule_date=block.block_date,

            duration_hours=duration_hours,
        )
    )

    # ========================================================
    # NO ALTERNATIVE
    # ========================================================

    if alternative is None:

        return {
            **impact,

            "recommended_action": (
                "MANUAL_REVIEW"
            ),

            "recommendation": (
                "Train conflicts were detected, but no "
                "conflict-free alternative window is "
                "available during working hours."
            ),

            "alternative_start_time": None,

            "alternative_end_time": None,
        }

    alternative_start, alternative_end = (
        alternative
    )

    # ========================================================
    # RECOMMENDATION LEVEL
    # ========================================================

    if impact["impact_level"] == "HIGH":

        recommended_action = (
            "RESCHEDULE"
        )

        message = (
            "High train impact detected. "
            "Rescheduling is strongly recommended."
        )

    elif impact["impact_level"] == "MEDIUM":

        recommended_action = (
            "CONSIDER_RESCHEDULE"
        )

        message = (
            "Moderate train impact detected. "
            "Consider moving the block to the "
            "alternative window."
        )

    else:

        recommended_action = (
            "CONSIDER_RESCHEDULE"
        )

        message = (
            "Train conflict detected. "
            "An alternative conflict-free window "
            "is available."
        )

    return {
        **impact,

        "recommended_action": (
            recommended_action
        ),

        "recommendation": message,

        "alternative_start_time": (
            alternative_start
        ),

        "alternative_end_time": (
            alternative_end
        ),
    }


# ============================================================
# ALL BLOCK RESCHEDULING RECOMMENDATIONS
# ============================================================

def recommend_rescheduling_for_all_blocks(
    db: Session,
) -> list[dict]:
    """
    Generate recommendations for all non-cancelled blocks.
    """

    blocks = (
        db.query(Block)
        .filter(
            Block.status != "CANCELLED"
        )
        .order_by(
            Block.block_date,
            Block.start_time,
        )
        .all()
    )

    return [
        recommend_reschedule(
            db=db,
            block=block,
        )
        for block in blocks
    ]


# ============================================================
# PLAN OPTIMIZATION SCORE
# ============================================================

def calculate_plan_score(
    priority_score: int,
    impact_level: str,
    duration_hours: float,
    block_count: int,
) -> float:
    """
    Calculate overall optimization score.

    Higher score = better plan.
    """

    score = float(
        priority_score
    )

    impact_penalty = {
        "NONE": 0,
        "LOW": 10,
        "MEDIUM": 25,
        "HIGH": 45,
    }

    score -= impact_penalty.get(
        impact_level,
        20,
    )

    score -= (
        duration_hours * 2
    )

    score -= (
        max(
            block_count - 1,
            0,
        )
        * 5
    )

    return round(
        max(
            score,
            0,
        ),
        2,
    )


# ============================================================
# BUILD OPTIMIZATION CANDIDATE
# ============================================================

def build_optimization_candidate(
    plan: dict,
    priority_score: int,
    impact_level: str,
    duration_hours: float,
    block_count: int,
) -> dict:
    """
    Add optimization score to maintenance plan.
    """

    optimization_score = (
        calculate_plan_score(
            priority_score=priority_score,
            impact_level=impact_level,
            duration_hours=duration_hours,
            block_count=block_count,
        )
    )

    return {
        **plan,

        "optimization_score": (
            optimization_score
        ),

        "priority_score": (
            priority_score
        ),

        "impact_level": (
            impact_level
        ),

        "duration_hours": (
            duration_hours
        ),

        "block_count": (
            block_count
        ),
    }


# ============================================================
# CHOOSE BEST PLAN
# ============================================================

def choose_best_plan(
    candidates: list[dict],
) -> dict | None:
    """
    Select highest scoring plan.
    """

    if not candidates:
        return None

    ranked = sorted(
        candidates,
        key=lambda item: (
            item[
                "optimization_score"
            ],

            item[
                "priority_score"
            ],
        ),
        reverse=True,
    )

    return {
        "best_plan": ranked[0],
        "alternatives": ranked[1:],
    }


# ============================================================
# OPTIMIZE BLOCK RECOMMENDATION
# ============================================================

def optimize_block_recommendation(
    db: Session,
    block: Block,
    priority_score: int,
) -> dict:
    """
    Combine train impact with optimization score.
    """

    impact = analyze_block_impact(
        db=db,
        block=block,
    )

    duration_minutes = (
        time_to_minutes(
            block.end_time
        )
        - time_to_minutes(
            block.start_time
        )
    )

    duration_hours = (
        duration_minutes / 60
    )

    candidate = (
        build_optimization_candidate(
            plan={
                "block_id": (
                    block.block_id
                ),

                "block_code": (
                    block.block_code
                ),

                "section_id": (
                    block.section_id
                ),

                "block_date": (
                    block.block_date
                ),

                "start_time": (
                    block.start_time
                ),

                "end_time": (
                    block.end_time
                ),
            },

            priority_score=(
                priority_score
            ),

            impact_level=(
                impact["impact_level"]
            ),

            duration_hours=(
                duration_hours
            ),

            block_count=1,
        )
    )

    return {
        **candidate,

        "conflict_count": (
            impact["conflict_count"]
        ),

        "affected_train_ids": (
            impact["affected_train_ids"]
        ),

        "total_conflict_minutes": (
            impact[
                "total_conflict_minutes"
            ]
        ),

        "recommended_action": (
            "RESCHEDULE"
            if impact["impact_level"]
            in {"MEDIUM", "HIGH"}
            else "KEEP_BLOCK"
        ),
    }


# ============================================================
# OPTIMIZE ALL BLOCKS
# ============================================================

def optimize_all_blocks(
    db: Session,
) -> list[dict]:
    """
    Generate optimization results for all non-cancelled blocks.
    """

    blocks = (
        db.query(Block)
        .filter(
            Block.status != "CANCELLED"
        )
        .order_by(
            Block.block_date,
            Block.start_time,
        )
        .all()
    )

    results = []

    for block in blocks:

        task_priorities = []

        for block_task in block.block_tasks:

            task = (
                db.query(MaintenanceTask)
                .filter(
                    MaintenanceTask.task_id
                    == block_task.task_id
                )
                .first()
            )

            if task is None:
                continue

            priority = (
                calculate_task_priority(
                    db=db,
                    task=task,
                )
            )

            task_priorities.append(
                priority[
                    "priority_score"
                ]
            )

        priority_score = max(
            task_priorities,
            default=0,
        )

        result = (
            optimize_block_recommendation(
                db=db,
                block=block,
                priority_score=priority_score,
            )
        )

        results.append(result)

    return sorted(
        results,
        key=lambda item: (
            item[
                "optimization_score"
            ],

            item[
                "priority_score"
            ],
        ),
        reverse=True,
    )


# ============================================================
# EVENT-AWARE TASK RISK
# ============================================================

def calculate_event_aware_task_risk(
    db: Session,
    task: MaintenanceTask,
    event: OperationalEvent,
) -> dict:
    """
    Calculate rule + ML asset risk for a task
    and apply event context.

    The ML probability itself is NOT modified.

    Only the planning risk is adjusted when a DEFECT
    directly targets the task's asset.
    """

    asset = (
        db.query(Asset)
        .filter(
            Asset.asset_id
            == task.asset_id
        )
        .first()
    )

    if asset is None:

        return {
            "asset_risk_available": False,

            "rule_based_risk_score": 0.0,

            "rule_based_risk_level": "LOW",

            "ml_prediction_available": False,

            "ml_prediction": None,

            "ml_risk_probability": None,

            "ml_risk_percentage": None,

            "ml_risk_level": None,

            "combined_risk_score": 0.0,

            "combined_risk_level": "LOW",

            "event_risk_adjustment": 0.0,

            "event_adjusted_risk_score": 0.0,
        }

    # ========================================================
    # Existing rule + ML risk engine
    # ========================================================

    risk = calculate_asset_risk(
        db=db,
        asset=asset,
    )

    combined_risk_score = float(
        risk.get(
            "combined_risk_score",
            risk.get(
                "risk_score",
                0.0,
            ),
        )
    )

    # ========================================================
    # Event context
    # ========================================================

    event_adjustment = 0.0

    event_severity = (
        event.severity
        or "MEDIUM"
    ).upper()

    # A new defect directly affecting this asset
    # raises planning urgency.
    if (
        event.event_type == "DEFECT"
        and event.asset_id is not None
        and event.asset_id == task.asset_id
    ):

        event_adjustment = (
            EVENT_SEVERITY_BOOST.get(
                event_severity,
                5.0,
            )
        )

    event_adjusted_risk_score = round(
        min(
            combined_risk_score
            + event_adjustment,
            100.0,
        ),
        2,
    )

    return {
        "asset_risk_available": True,

        "rule_based_risk_score": float(
            risk.get(
                "rule_based_risk_score",
                risk.get(
                    "risk_score",
                    0.0,
                ),
            )
        ),

        "rule_based_risk_level": (
            risk.get(
                "rule_based_risk_level"
            )
        ),

        "ml_prediction_available": (
            risk.get(
                "ml_prediction_available",
                False,
            )
        ),

        "ml_prediction": (
            risk.get(
                "ml_prediction"
            )
        ),

        "ml_risk_probability": (
            risk.get(
                "ml_risk_probability"
            )
        ),

        "ml_risk_percentage": (
            risk.get(
                "ml_risk_percentage"
            )
        ),

        "ml_risk_level": (
            risk.get(
                "ml_risk_level"
            )
        ),

        "combined_risk_score": (
            combined_risk_score
        ),

        "combined_risk_level": (
            risk.get(
                "combined_risk_level"
            )
        ),

        "event_risk_adjustment": (
            event_adjustment
        ),

        "event_adjusted_risk_score": (
            event_adjusted_risk_score
        ),
    }


# ============================================================
# ML-AWARE TASK REPLANNING SCORE
# ============================================================

def get_task_replanning_score(
    db: Session,
    task: MaintenanceTask,
    event: OperationalEvent | None = None,
) -> dict:
    """
    Calculate the ranking score used during dynamic
    maintenance re-planning.

    Planning score:

        60% Task Priority
        40% Event-aware Combined Asset Risk

    When an event is not supplied:
        Normal combined risk is used.

    When a DEFECT directly targets the task asset:
        Event severity adds a small planning adjustment.
    """

    priority = calculate_task_priority(
        db=db,
        task=task,
    )

    base_priority_score = float(
        priority[
            "priority_score"
        ]
    )

    if event is not None:

        risk = calculate_event_aware_task_risk(
            db=db,
            task=task,
            event=event,
        )

        risk_score = float(
            risk[
                "event_adjusted_risk_score"
            ]
        )

    else:

        asset = (
            db.query(Asset)
            .filter(
                Asset.asset_id
                == task.asset_id
            )
            .first()
        )

        if asset is None:

            risk = {
                "combined_risk_score": 0.0,
                "ml_risk_percentage": None,
            }

        else:

            risk = calculate_asset_risk(
                db=db,
                asset=asset,
            )

        risk_score = float(
            risk.get(
                "combined_risk_score",
                risk.get(
                    "risk_score",
                    0.0,
                ),
            )
        )

    planning_score = round(
        (
            base_priority_score
            * TASK_PRIORITY_WEIGHT
        )
        +
        (
            risk_score
            * ASSET_RISK_WEIGHT
        ),
        2,
    )

    return {
        "task_id": task.task_id,

        "task_code": (
            task.task_code
        ),

        "section_id": (
            task.section_id
        ),

        "asset_id": (
            task.asset_id
        ),

        "priority_score": (
            base_priority_score
        ),

        "risk_score": (
            risk_score
        ),

        "planning_score": (
            planning_score
        ),

        "ml_risk_percentage": (
            risk.get(
                "ml_risk_percentage"
            )
        ),

        "ml_risk_level": (
            risk.get(
                "ml_risk_level"
            )
        ),

        "combined_risk_score": (
            risk.get(
                "combined_risk_score"
            )
        ),

        "event_risk_adjustment": (
            risk.get(
                "event_risk_adjustment",
                0.0,
            )
        ),

        "event_adjusted_risk_score": (
            risk.get(
                "event_adjusted_risk_score",
                risk_score,
            )
        ),
    }


# ============================================================
# DYNAMIC RE-PLANNING AFTER OPERATIONAL EVENT
# ============================================================

def replan_after_event(
    db: Session,
    event: OperationalEvent,
) -> dict:
    """
    ML-aware dynamic maintenance re-planning.

    Supported:
        TRAIN_DELAY
        DEFECT
        BLOCK_CHANGE

    After an event:

        1. Recalculate task priority
        2. Recalculate rule + ML asset risk
        3. Apply event context
        4. Rank tasks using ML-aware planning score
        5. Generate new safe windows
        6. Re-analyze existing blocks
        7. Return complete re-planning result
    """

    section_id = event.section_id

    # ========================================================
    # 1. ACTIVE MAINTENANCE TASKS
    # ========================================================

    tasks = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.section_id
            == section_id,

            MaintenanceTask.status.notin_(
                [
                    "COMPLETED",
                    "CANCELLED",
                ]
            ),
        )
        .all()
    )

    # ========================================================
    # 2. ML-AWARE PRIORITY RECALCULATION
    # ========================================================

    priority_results = []

    task_ranking = []

    for task in tasks:

        planning = get_task_replanning_score(
            db=db,
            task=task,
            event=event,
        )

        task_ranking.append(
            planning
        )

        priority_results.append(
            {
                "task_id": (
                    task.task_id
                ),

                "task_code": (
                    task.task_code
                ),

                "priority_score": (
                    planning[
                        "priority_score"
                    ]
                ),

                "priority_level": (
                    calculate_task_priority(
                        db=db,
                        task=task,
                    )[
                        "priority_level"
                    ]
                ),

                "rule_based_risk_score": (
                    planning.get(
                        "combined_risk_score"
                    )
                ),

                "ml_prediction_available": (
                    planning.get(
                        "ml_risk_percentage"
                    )
                    is not None
                ),

                "ml_risk_percentage": (
                    planning.get(
                        "ml_risk_percentage"
                    )
                ),

                "ml_risk_level": (
                    planning.get(
                        "ml_risk_level"
                    )
                ),

                "event_risk_adjustment": (
                    planning.get(
                        "event_risk_adjustment",
                        0.0,
                    )
                ),

                "event_adjusted_risk_score": (
                    planning.get(
                        "event_adjusted_risk_score"
                    )
                ),

                "planning_score": (
                    planning[
                        "planning_score"
                    ]
                ),

                "section_id": (
                    task.section_id
                ),
            }
        )

    # ========================================================
    # 3. RANK TASKS
    # ========================================================

    task_ranking.sort(
        key=lambda item: (
            item[
                "planning_score"
            ],

            item[
                "priority_score"
            ],

            item[
                "risk_score"
            ],

            item[
                "task_id"
            ],
        ),
        reverse=True,
    )

    priority_results.sort(
        key=lambda item: (
            item[
                "planning_score"
            ],

            item[
                "priority_score"
            ],

            item[
                "task_id"
            ],
        ),
        reverse=True,
    )

    # ========================================================
    # 4. GENERATE ML-AWARE REPLANNED WINDOWS
    # ========================================================

    maintenance_plan = (
        generate_replanned_tasks(
            db=db,

            tasks=tasks,

            schedule_date=event.event_date,

            event=event,
        )
    )

    # ========================================================
    # 5. FIND AFFECTED BLOCKS
    # ========================================================

    affected_blocks = (
        db.query(Block)
        .filter(
            Block.section_id
            == section_id,

            Block.block_date
            == event.event_date,

            Block.status.in_(
                [
                    "PLANNED",
                    "APPROVED",
                    "IN_PROGRESS",
                ]
            ),
        )
        .order_by(
            Block.start_time
        )
        .all()
    )

    # ========================================================
    # 6. ANALYZE BLOCKS
    # ========================================================

    block_results = []

    for block in affected_blocks:

        impact = analyze_block_impact(
            db=db,
            block=block,
        )

        recommendation = (
            recommend_reschedule(
                db=db,
                block=block,
            )
        )

        action = recommendation[
            "recommended_action"
        ]

        # ----------------------------------------------------
        # Save recommendation
        # ----------------------------------------------------

        if action in {
            "RESCHEDULE",
            "CONSIDER_RESCHEDULE",
            "MANUAL_REVIEW",
        }:

            block.replan_required = True

            block.recommended_start_time = (
                recommendation[
                    "alternative_start_time"
                ]
            )

            block.recommended_end_time = (
                recommendation[
                    "alternative_end_time"
                ]
            )

        else:

            block.replan_required = False

            block.recommended_start_time = None

            block.recommended_end_time = None

        # ----------------------------------------------------
        # Find block task planning information
        # ----------------------------------------------------

        block_task_ids = {
            block_task.task_id
            for block_task
            in block.block_tasks
        }

        block_task_plans = [
            item
            for item in task_ranking
            if item["task_id"]
            in block_task_ids
        ]

        max_block_planning_score = max(
            [
                item[
                    "planning_score"
                ]
                for item in block_task_plans
            ],
            default=0.0,
        )

        max_ml_risk = max(
            [
                item[
                    "ml_risk_percentage"
                ]
                for item in block_task_plans
                if item[
                    "ml_risk_percentage"
                ] is not None
            ],
            default=None,
        )

        max_event_adjusted_risk = max(
            [
                item[
                    "event_adjusted_risk_score"
                ]
                for item in block_task_plans
            ],
            default=0.0,
        )

        # ----------------------------------------------------
        # Build block result
        # ----------------------------------------------------

        block_results.append(
            {
                "block_id": (
                    block.block_id
                ),

                "block_code": (
                    block.block_code
                ),

                "section_id": (
                    block.section_id
                ),

                "current_start_time": (
                    impact["start_time"]
                ),

                "current_end_time": (
                    impact["end_time"]
                ),

                "conflict_count": (
                    impact[
                        "conflict_count"
                    ]
                ),

                "affected_train_ids": (
                    impact[
                        "affected_train_ids"
                    ]
                ),

                "total_conflict_minutes": (
                    impact[
                        "total_conflict_minutes"
                    ]
                ),

                "impact_level": (
                    impact[
                        "impact_level"
                    ]
                ),

                "recommended_action": (
                    recommendation[
                        "recommended_action"
                    ]
                ),

                "recommendation": (
                    recommendation[
                        "recommendation"
                    ]
                ),

                "alternative_start_time": (
                    recommendation[
                        "alternative_start_time"
                    ]
                ),

                "alternative_end_time": (
                    recommendation[
                        "alternative_end_time"
                    ]
                ),

                "replan_required": (
                    block.replan_required
                ),

                "ml_aware_priority_score": (
                    max_block_planning_score
                ),

                "max_ml_risk_percentage": (
                    max_ml_risk
                ),

                "max_event_adjusted_risk_score": (
                    max_event_adjusted_risk
                ),
            }
        )

    # ========================================================
    # 7. SAVE LATEST RECOMMENDATIONS
    # ========================================================

    db.commit()

    # ========================================================
    # 8. FINAL EVENT DECISION
    # ========================================================

    has_block_replanning = any(
        item[
            "replan_required"
        ]
        for item in block_results
    )

    requires_replanning = (
        event.event_type
        in {
            "TRAIN_DELAY",
            "DEFECT",
            "BLOCK_CHANGE",
        }

        and (
            has_block_replanning

            or len(
                maintenance_plan
            ) > 0
        )
    )

    if has_block_replanning:

        event_action = (
            "REPLAN_REQUIRED"
        )

    elif len(maintenance_plan) > 0:

        event_action = (
            "PLAN_RECALCULATED"
        )

    else:

        event_action = (
            "NO_ACTION"
        )

    # ========================================================
    # 9. RETURN COMPLETE RESULT
    # ========================================================

    return {
        "event_id": (
            event.event_id
        ),

        "event_type": (
            event.event_type
        ),

        "event_date": (
            event.event_date
        ),

        "section_id": (
            section_id
        ),

        "event_severity": (
            event.severity
        ),

        "event_asset_id": (
            event.asset_id
        ),

        "event_train_id": (
            event.train_id
        ),

        "event_delay_minutes": (
            event.delay_minutes
        ),

        # ----------------------------------------------------
        # ML / AI status
        # ----------------------------------------------------

        "ml_aware_replanning": True,

        "ml_recalculated": True,

        "ml_risk_used_for_ranking": True,

        "planning_formula": (
            "60% task priority + "
            "40% event-aware combined asset risk"
        ),

        # ----------------------------------------------------
        # Priority
        # ----------------------------------------------------

        "priority_recalculated": True,

        "maintenance_tasks": (
            priority_results
        ),

        # ----------------------------------------------------
        # Replanned windows
        # ----------------------------------------------------

        "replanned_tasks": (
            maintenance_plan
        ),

        # ----------------------------------------------------
        # Blocks
        # ----------------------------------------------------

        "affected_blocks": (
            block_results
        ),

        # ----------------------------------------------------
        # Final decision
        # ----------------------------------------------------

        "replanning_required": (
            requires_replanning
        ),

        "event_action": (
            event_action
        ),
    }


# ============================================================
# REPLAN TASK WINDOWS
# ============================================================

def generate_replanned_tasks(
    db: Session,
    tasks: list[MaintenanceTask],
    schedule_date,
    event: OperationalEvent | None = None,
) -> list[dict]:
    """
    Generate fresh maintenance windows after an event.

    ML-aware ranking is used before window assignment.

    Ranking considers:

        1. Maintenance priority
        2. Combined rule + ML asset risk
        3. Event context

    Train conflicts and reserved maintenance windows
    are respected.
    """

    if not tasks:
        return []

    # ========================================================
    # ML-AWARE TASK RANKING
    # ========================================================

    ranked_tasks = []

    for task in tasks:

        planning = get_task_replanning_score(
            db=db,
            task=task,
            event=event,
        )

        ranked_tasks.append(
            (
                task,
                planning,
            )
        )

    ranked_tasks.sort(
        key=lambda item: (
            item[1][
                "planning_score"
            ],

            item[1][
                "priority_score"
            ],

            item[1][
                "risk_score"
            ],

            item[1][
                "task_id"
            ],
        ),
        reverse=True,
    )

    # ========================================================
    # RESERVED WINDOWS
    # ========================================================

    reserved_by_section: dict[
        int,
        list[tuple[int, int]],
    ] = {}

    results = []

    # ========================================================
    # ASSIGN SAFE WINDOWS
    # ========================================================

    for task, planning in ranked_tasks:

        section_reserved = (
            reserved_by_section.setdefault(
                task.section_id,
                [],
            )
        )

        duration_hours = float(
            task.duration_hours
        )

        window = (
            find_conflict_free_window(
                db=db,

                section_id=(
                    task.section_id
                ),

                schedule_date=(
                    schedule_date
                ),

                duration_hours=(
                    duration_hours
                ),

                reserved_intervals=(
                    section_reserved
                ),
            )
        )

        # ----------------------------------------------------
        # No available window
        # ----------------------------------------------------

        if window is None:

            results.append(
                {
                    "task_id": (
                        task.task_id
                    ),

                    "task_code": (
                        task.task_code
                    ),

                    "section_id": (
                        task.section_id
                    ),

                    "recommended": False,

                    "priority_score": (
                        planning[
                            "priority_score"
                        ]
                    ),

                    "ml_risk_percentage": (
                        planning[
                            "ml_risk_percentage"
                        ]
                    ),

                    "ml_risk_level": (
                        planning[
                            "ml_risk_level"
                        ]
                    ),

                    "combined_risk_score": (
                        planning[
                            "combined_risk_score"
                        ]
                    ),

                    "event_risk_adjustment": (
                        planning[
                            "event_risk_adjustment"
                        ]
                    ),

                    "event_adjusted_risk_score": (
                        planning[
                            "event_adjusted_risk_score"
                        ]
                    ),

                    "planning_score": (
                        planning[
                            "planning_score"
                        ]
                    ),

                    "reason": (
                        "No conflict-free and "
                        "non-overlapping maintenance "
                        "window is available after "
                        "the operational event."
                    ),
                }
            )

            continue

        start_time, end_time = window

        start_minutes = (
            time_to_minutes(
                start_time
            )
        )

        end_minutes = (
            time_to_minutes(
                end_time
            )
        )

        section_reserved.append(
            (
                start_minutes,
                end_minutes,
            )
        )

        # ----------------------------------------------------
        # Recommended task
        # ----------------------------------------------------

        results.append(
            {
                "task_id": (
                    task.task_id
                ),

                "task_code": (
                    task.task_code
                ),

                "section_id": (
                    task.section_id
                ),

                "recommended": True,

                "start_time": (
                    start_time
                ),

                "end_time": (
                    end_time
                ),

                "duration_hours": (
                    duration_hours
                ),

                "priority": (
                    task.severity
                ),

                # ------------------------------------------------
                # ML information
                # ------------------------------------------------

                "priority_score": (
                    planning[
                        "priority_score"
                    ]
                ),

                "ml_risk_percentage": (
                    planning[
                        "ml_risk_percentage"
                    ]
                ),

                "ml_risk_level": (
                    planning[
                        "ml_risk_level"
                    ]
                ),

                "combined_risk_score": (
                    planning[
                        "combined_risk_score"
                    ]
                ),

                "event_risk_adjustment": (
                    planning[
                        "event_risk_adjustment"
                    ]
                ),

                "event_adjusted_risk_score": (
                    planning[
                        "event_adjusted_risk_score"
                    ]
                ),

                "planning_score": (
                    planning[
                        "planning_score"
                    ]
                ),
            }
        )

    return results