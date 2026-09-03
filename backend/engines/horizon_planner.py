from datetime import date, timedelta

from sqlalchemy.orm import Session

from backend.database.models import (
    MaintenanceTask,
    Block,
    GoodsForecast,
)

from backend.engines.block_planner import (
    find_available_window,
    sort_tasks_by_priority,
    time_to_minutes,
)

from backend.engines.priority_engine import (
    calculate_task_priority,
)


# ============================================================
# HORIZON SETTINGS
# ============================================================

WEEKLY_DAYS = 7
MONTHLY_DAYS = 30

# Maximum maintenance workload per section per day.
MAX_DAILY_PLANNED_HOURS = 8.0

INACTIVE_STATUSES = {
    "COMPLETED",
    "CANCELLED",
}

# Goods traffic scoring weight.
# Higher expected goods trains = less preferred planning day.
GOODS_TRAFFIC_WEIGHT = 20.0


# ============================================================
# DATE HELPERS
# ============================================================

def get_horizon_dates(
    start_date: date,
    end_date: date,
) -> list[date]:
    """Return all dates in the inclusive planning horizon."""

    if end_date < start_date:
        return []

    return [
        start_date + timedelta(days=offset)
        for offset in range(
            (end_date - start_date).days + 1
        )
    ]


# ============================================================
# ACTIVE TASKS
# ============================================================

def get_active_tasks(
    db: Session,
) -> list[MaintenanceTask]:
    """Return maintenance tasks still requiring planning."""

    return (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.status.notin_(
                list(INACTIVE_STATUSES)
            )
        )
        .all()
    )


# ============================================================
# PRIORITY
# ============================================================

def get_task_priority_data(
    db: Session,
    task: MaintenanceTask,
) -> dict:
    """Return priority information for one task."""

    result = calculate_task_priority(
        db=db,
        task=task,
    )

    return {
        "priority_score": float(
            result.get(
                "priority_score",
                0,
            )
        ),
        "overdue_days": int(
            result.get(
                "overdue_days",
                0,
            )
            or 0
        ),
    }


def sort_horizon_tasks(
    db: Session,
    tasks: list[MaintenanceTask],
) -> list[MaintenanceTask]:
    """Sort tasks using the existing priority engine."""

    return sort_tasks_by_priority(
        db=db,
        tasks=tasks,
    )


# ============================================================
# SECTION GROUPING
# ============================================================

def group_tasks_by_section(
    tasks: list[MaintenanceTask],
) -> dict[int, list[MaintenanceTask]]:
    """Group tasks by railway section."""

    grouped: dict[
        int,
        list[MaintenanceTask],
    ] = {}

    for task in tasks:
        grouped.setdefault(
            task.section_id,
            [],
        ).append(task)

    return grouped


# ============================================================
# GOODS TRAIN FORECAST
# ============================================================

def get_goods_forecast(
    db: Session,
    section_id: int,
    planning_date: date,
) -> int:
    """
    Return expected goods trains for a section/date.

    If no forecast is available, return 0 so that the planner
    remains usable.
    """

    forecast = (
        db.query(GoodsForecast)
        .filter(
            GoodsForecast.section_id == section_id,
            GoodsForecast.forecast_date == planning_date,
        )
        .first()
    )

    if forecast is None:
        return 0

    try:
        return int(
            forecast.expected_goods_trains or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0


def get_goods_traffic_level(
    expected_goods_trains: int,
) -> str:
    """
    Convert expected goods-train count into a simple
    planning traffic level.

    This is a demo/prototype rule because the source data
    contains counts rather than exact hourly traffic windows.
    """

    if expected_goods_trains >= 5:
        return "HIGH"

    if expected_goods_trains >= 3:
        return "MEDIUM"

    if expected_goods_trains >= 1:
        return "LOW"

    return "NONE"


def get_goods_planning_reason(
    expected_goods_trains: int,
) -> str:
    """
    Return a human-readable explanation for goods traffic.
    """

    traffic_level = get_goods_traffic_level(
        expected_goods_trains
    )

    if traffic_level == "HIGH":
        return (
            f"High goods traffic forecast "
            f"({expected_goods_trains} goods trains)"
        )

    if traffic_level == "MEDIUM":
        return (
            f"Moderate goods traffic forecast "
            f"({expected_goods_trains} goods trains)"
        )

    if traffic_level == "LOW":
        return (
            f"Low goods traffic forecast "
            f"({expected_goods_trains} goods train"
            f"{'' if expected_goods_trains == 1 else 's'})"
        )

    return "No goods train traffic forecast."


# ============================================================
# EXISTING DATABASE BLOCKS
# ============================================================

def get_existing_block_intervals(
    db: Session,
    section_id: int,
    planning_date: date,
) -> list[tuple[int, int]]:
    """
    Return intervals already occupied by saved non-cancelled
    blocks for the same section/date.
    """

    blocks = (
        db.query(Block)
        .filter(
            Block.section_id == section_id,
            Block.block_date == planning_date,
            Block.status != "CANCELLED",
        )
        .order_by(Block.start_time)
        .all()
    )

    intervals = []

    for block in blocks:
        start_minutes = time_to_minutes(
            block.start_time
        )

        end_minutes = time_to_minutes(
            block.end_time
        )

        intervals.append(
            (
                start_minutes,
                end_minutes,
            )
        )

    return intervals


def get_existing_block_hours(
    db: Session,
    section_id: int,
    planning_date: date,
) -> float:
    """
    Return total already-used hours for a section/date.
    """

    intervals = get_existing_block_intervals(
        db=db,
        section_id=section_id,
        planning_date=planning_date,
    )

    total_hours = 0.0

    for start_minutes, end_minutes in intervals:
        total_hours += (
            max(
                0,
                end_minutes - start_minutes,
            )
            / 60.0
        )

    return total_hours


# ============================================================
# GROUP INFORMATION
# ============================================================

def get_group_priority(
    db: Session,
    tasks: list[MaintenanceTask],
) -> tuple[float, int, float]:
    """
    Return:

        highest priority score
        maximum overdue days
        total duration
    """

    highest_priority = 0.0
    maximum_overdue = 0
    total_duration = 0.0

    for task in tasks:

        priority = get_task_priority_data(
            db=db,
            task=task,
        )

        highest_priority = max(
            highest_priority,
            priority["priority_score"],
        )

        maximum_overdue = max(
            maximum_overdue,
            priority["overdue_days"],
        )

        total_duration += float(
            task.duration_hours or 0
        )

    return (
        highest_priority,
        maximum_overdue,
        total_duration,
    )


# ============================================================
# FIND WINDOW
# ============================================================

def find_group_window(
    db: Session,
    tasks: list[MaintenanceTask],
    planning_date: date,
    generated_reserved_intervals: list[
        tuple[int, int]
    ],
) -> dict | None:
    """
    Find a conflict-free window for the complete task group.

    Checks:
        - Existing database blocks
        - Previously generated horizon blocks
        - Passenger train schedule + safety buffer

    Goods traffic is represented in the returned planning
    metadata because the source forecast contains daily counts.
    """

    if not tasks:
        return None

    section_ids = {
        task.section_id
        for task in tasks
    }

    if len(section_ids) != 1:
        return None

    section_id = tasks[0].section_id

    total_duration = sum(
        float(task.duration_hours or 0)
        for task in tasks
    )

    if total_duration <= 0:
        return None

    existing_intervals = (
        get_existing_block_intervals(
            db=db,
            section_id=section_id,
            planning_date=planning_date,
        )
    )

    all_reserved = [
        *existing_intervals,
        *generated_reserved_intervals,
    ]

    window = find_available_window(
        db=db,
        section_id=section_id,
        schedule_date=planning_date,
        duration_hours=total_duration,
        reserved_intervals=all_reserved,
    )

    if window is None:
        return None

    start_time, end_time = window

    expected_goods_trains = get_goods_forecast(
        db=db,
        section_id=section_id,
        planning_date=planning_date,
    )

    goods_reason = get_goods_planning_reason(
        expected_goods_trains
    )

    if len(tasks) > 1:
        base_reason = (
            "Same-section maintenance tasks combined into "
            "one conflict-free block."
        )
    else:
        base_reason = (
            "Task scheduled in a conflict-free "
            "maintenance window."
        )

    return {
        "recommended": True,

        "section_id": section_id,

        "schedule_date": planning_date,

        "start_time": start_time,

        "end_time": end_time,

        "total_duration_hours": total_duration,

        "task_ids": [
            task.task_id
            for task in tasks
        ],

        "task_codes": [
            task.task_code
            for task in tasks
        ],

        "task_count": len(tasks),

        "grouped": len(tasks) > 1,

        "expected_goods_trains": (
            expected_goods_trains
        ),

        "goods_traffic_level": (
            get_goods_traffic_level(
                expected_goods_trains
            )
        ),

        "reason": (
            f"{base_reason} "
            f"Goods forecast: {goods_reason}"
        ),
    }


# ============================================================
# FIND BEST DAY FOR COMPLETE GROUP
# ============================================================

def find_best_day_for_group(
    db: Session,
    tasks: list[MaintenanceTask],
    horizon_dates: list[date],
    daily_planned_hours: dict[
        tuple[date, int],
        float,
    ],
    daily_reserved_intervals: dict[
        tuple[date, int],
        list[tuple[int, int]],
    ],
) -> dict | None:
    """
    Compare the complete task group across the entire horizon.

    Candidate-day scoring considers:

        - urgency / priority
        - overdue days
        - existing planned workload
        - passenger train conflict-free availability
        - goods train forecast

    IMPORTANT:
    The goods forecast currently contains a daily count,
    therefore it influences which day is preferred rather
    than an exact intraday goods-train interval.
    """

    if not tasks:
        return None

    section_id = tasks[0].section_id

    (
        highest_priority,
        maximum_overdue,
        total_duration,
    ) = get_group_priority(
        db=db,
        tasks=tasks,
    )

    candidates = []

    for planning_date in horizon_dates:

        key = (
            planning_date,
            section_id,
        )

        already_planned = (
            daily_planned_hours.get(
                key,
                0.0,
            )
        )

        remaining_capacity = (
            MAX_DAILY_PLANNED_HOURS
            - already_planned
        )

        if (
            total_duration
            > remaining_capacity
        ):
            continue

        reserved_intervals = (
            daily_reserved_intervals.get(
                key,
                [],
            )
        )

        plan = find_group_window(
            db=db,
            tasks=tasks,
            planning_date=planning_date,
            generated_reserved_intervals=(
                reserved_intervals
            ),
        )

        if plan is None:
            continue

        expected_goods_trains = (
            get_goods_forecast(
                db=db,
                section_id=section_id,
                planning_date=planning_date,
            )
        )

        day_index = (
            planning_date
            - horizon_dates[0]
        ).days

        # ----------------------------------------------------
        # Candidate score
        #
        # Lower = better
        #
        # Earlier day is preferred.
        # High priority / overdue tasks can pull the task
        # toward an earlier day.
        # High goods traffic pushes the planner away from
        # that day.
        # ----------------------------------------------------

        candidate_score = (
            (day_index * 100.0)

            + (
                already_planned * 8.0
            )

            + (
                expected_goods_trains
                * GOODS_TRAFFIC_WEIGHT
            )

            - (
                highest_priority * 1.5
            )

            - (
                maximum_overdue * 5.0
            )
        )

        candidates.append(
            (
                candidate_score,
                day_index,
                expected_goods_trains,
                plan,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    selected = candidates[0]

    selected_plan = selected[3]

    selected_goods_trains = selected[2]

    selected_plan[
        "goods_forecast_considered"
    ] = True

    selected_plan[
        "expected_goods_trains"
    ] = selected_goods_trains

    selected_plan[
        "goods_traffic_level"
    ] = get_goods_traffic_level(
        selected_goods_trains
    )

    return selected_plan


# ============================================================
# PRIORITY-PRESERVING SPLIT
# ============================================================

def split_group_by_daily_capacity(
    db: Session,
    tasks: list[MaintenanceTask],
) -> list[list[MaintenanceTask]]:
    """
    Split a section group only when the complete group
    cannot be kept together.

    Tasks remain in priority order.
    """

    ordered = sort_horizon_tasks(
        db=db,
        tasks=tasks,
    )

    groups: list[
        list[MaintenanceTask]
    ] = []

    current_group: list[
        MaintenanceTask
    ] = []

    current_hours = 0.0

    for task in ordered:

        duration = float(
            task.duration_hours or 0
        )

        if duration <= 0:
            continue

        if (
            current_group
            and
            current_hours + duration
            > MAX_DAILY_PLANNED_HOURS
        ):
            groups.append(
                current_group
            )

            current_group = []
            current_hours = 0.0

        current_group.append(task)

        current_hours += duration

    if current_group:
        groups.append(
            current_group
        )

    return groups


# ============================================================
# GENERATE HORIZON PLAN
# ============================================================

def generate_horizon_plan(
    db: Session,
    start_date: date,
    end_date: date,
    horizon: str = "WEEKLY",
) -> dict:
    """
    Generate a smart weekly/monthly maintenance plan.

    Planner factors:

        1. Active maintenance tasks
        2. Priority / criticality
        3. Overdue status
        4. Section grouping
        5. Complete-group preference
        6. Whole-horizon comparison
        7. Passenger train conflicts
        8. Existing database blocks
        9. Generated same-day reservations
       10. Daily capacity
       11. Goods train forecast

    The function creates recommendations only.
    It does NOT create database Block records.
    """

    horizon = (
        horizon.upper().strip()
    )

    if horizon not in {
        "WEEKLY",
        "MONTHLY",
    }:
        raise ValueError(
            "horizon must be WEEKLY or MONTHLY."
        )

    if end_date < start_date:
        raise ValueError(
            "end_date must be greater than "
            "or equal to start_date."
        )

    total_days = (
        end_date -
        start_date
    ).days + 1

    if (
        horizon == "WEEKLY"
        and total_days > WEEKLY_DAYS
    ):
        raise ValueError(
            "Weekly planning cannot exceed 7 days."
        )

    if (
        horizon == "MONTHLY"
        and total_days > MONTHLY_DAYS
    ):
        raise ValueError(
            "Monthly planning cannot exceed 30 days."
        )

    horizon_dates = get_horizon_dates(
        start_date=start_date,
        end_date=end_date,
    )

    # ========================================================
    # LOAD ACTIVE TASKS
    # ========================================================

    active_tasks = get_active_tasks(
        db=db
    )

    original_task_ids = {
        task.task_id
        for task in active_tasks
    }

    # ========================================================
    # GROUP BY SECTION
    # ========================================================

    section_groups = (
        group_tasks_by_section(
            active_tasks
        )
    )

    # ========================================================
    # ORDER SECTIONS BY PRIORITY
    # ========================================================

    ordered_section_groups = []

    for (
        section_id,
        section_tasks,
    ) in section_groups.items():

        ordered_tasks = sort_horizon_tasks(
            db=db,
            tasks=section_tasks,
        )

        if not ordered_tasks:
            continue

        (
            highest_priority,
            maximum_overdue,
            total_duration,
        ) = get_group_priority(
            db=db,
            tasks=ordered_tasks,
        )

        ordered_section_groups.append(
            (
                highest_priority,
                maximum_overdue,
                total_duration,
                section_id,
                ordered_tasks,
            )
        )

    ordered_section_groups.sort(
        key=lambda item: (
            item[0],
            item[1],
        ),
        reverse=True,
    )

    # ========================================================
    # HORIZON STATE
    # ========================================================

    daily_planned_hours: dict[
        tuple[date, int],
        float,
    ] = {}

    daily_reserved_intervals: dict[
        tuple[date, int],
        list[tuple[int, int]],
    ] = {}

    daily_plans: dict[
        date,
        list[dict],
    ] = {
        planning_date: []
        for planning_date in horizon_dates
    }

    scheduled_task_ids: set[int] = set()

    # ========================================================
    # PROCESS EACH SECTION
    # ========================================================

    for (
        _highest_priority,
        _overdue,
        _total_duration,
        section_id,
        section_tasks,
    ) in ordered_section_groups:

        section_tasks = [
            task
            for task in section_tasks
            if task.task_id
            not in scheduled_task_ids
        ]

        if not section_tasks:
            continue

        # ----------------------------------------------------
        # FIRST:
        # Try complete section group
        # ----------------------------------------------------

        best_full_plan = (
            find_best_day_for_group(
                db=db,
                tasks=section_tasks,
                horizon_dates=horizon_dates,
                daily_planned_hours=(
                    daily_planned_hours
                ),
                daily_reserved_intervals=(
                    daily_reserved_intervals
                ),
            )
        )

        if best_full_plan is not None:

            planning_date = (
                best_full_plan[
                    "schedule_date"
                ]
            )

            key = (
                planning_date,
                section_id,
            )

            block_hours = float(
                best_full_plan[
                    "total_duration_hours"
                ]
            )

            daily_plans[
                planning_date
            ].append(
                best_full_plan
            )

            daily_planned_hours[
                key
            ] = (
                daily_planned_hours.get(
                    key,
                    0.0,
                )
                + block_hours
            )

            start_minutes = (
                time_to_minutes(
                    best_full_plan[
                        "start_time"
                    ]
                )
            )

            end_minutes = (
                time_to_minutes(
                    best_full_plan[
                        "end_time"
                    ]
                )
            )

            daily_reserved_intervals.setdefault(
                key,
                [],
            ).append(
                (
                    start_minutes,
                    end_minutes,
                )
            )

            daily_reserved_intervals[
                key
            ].sort(
                key=lambda interval:
                    interval[0]
            )

            scheduled_task_ids.update(
                task.task_id
                for task in section_tasks
            )

            continue

        # ----------------------------------------------------
        # FALLBACK:
        # Split group
        # ----------------------------------------------------

        partial_groups = (
            split_group_by_daily_capacity(
                db=db,
                tasks=section_tasks,
            )
        )

        for partial_group in partial_groups:

            if not partial_group:
                continue

            partial_plan = (
                find_best_day_for_group(
                    db=db,
                    tasks=partial_group,
                    horizon_dates=horizon_dates,
                    daily_planned_hours=(
                        daily_planned_hours
                    ),
                    daily_reserved_intervals=(
                        daily_reserved_intervals
                    ),
                )
            )

            if partial_plan is None:

                # --------------------------------------------
                # FINAL FALLBACK:
                # Individual task
                # --------------------------------------------

                for task in partial_group:

                    single_plan = (
                        find_best_day_for_group(
                            db=db,
                            tasks=[task],
                            horizon_dates=horizon_dates,
                            daily_planned_hours=(
                                daily_planned_hours
                            ),
                            daily_reserved_intervals=(
                                daily_reserved_intervals
                            ),
                        )
                    )

                    if single_plan is None:
                        continue

                    planning_date = (
                        single_plan[
                            "schedule_date"
                        ]
                    )

                    key = (
                        planning_date,
                        section_id,
                    )

                    single_plan[
                        "grouped"
                    ] = False

                    goods_reason = (
                        get_goods_planning_reason(
                            single_plan.get(
                                "expected_goods_trains",
                                0,
                            )
                        )
                    )

                    single_plan[
                        "reason"
                    ] = (
                        "Task scheduled individually because "
                        "a larger section group could not fit "
                        "into a conflict-free horizon window. "
                        f"Goods forecast considered: "
                        f"{goods_reason}"
                    )

                    daily_plans[
                        planning_date
                    ].append(
                        single_plan
                    )

                    block_hours = float(
                        single_plan[
                            "total_duration_hours"
                        ]
                    )

                    daily_planned_hours[
                        key
                    ] = (
                        daily_planned_hours.get(
                            key,
                            0.0,
                        )
                        + block_hours
                    )

                    start_minutes = (
                        time_to_minutes(
                            single_plan[
                                "start_time"
                            ]
                        )
                    )

                    end_minutes = (
                        time_to_minutes(
                            single_plan[
                                "end_time"
                            ]
                        )
                    )

                    daily_reserved_intervals.setdefault(
                        key,
                        [],
                    ).append(
                        (
                            start_minutes,
                            end_minutes,
                        )
                    )

                    daily_reserved_intervals[
                        key
                    ].sort(
                        key=lambda interval:
                            interval[0]
                    )

                    scheduled_task_ids.add(
                        task.task_id
                    )

                continue

            # ----------------------------------------------
            # Save partial group
            # ----------------------------------------------

            planning_date = (
                partial_plan[
                    "schedule_date"
                ]
            )

            key = (
                planning_date,
                section_id,
            )

            partial_plan[
                "grouped"
            ] = (
                len(partial_group) > 1
            )

            goods_reason = (
                get_goods_planning_reason(
                    partial_plan.get(
                        "expected_goods_trains",
                        0,
                    )
                )
            )

            partial_plan[
                "reason"
            ] = (
                "Priority-preserving subset scheduled "
                "because the complete section group could "
                "not fit into one conflict-free window. "
                f"Goods forecast considered: "
                f"{goods_reason}"
            )

            daily_plans[
                planning_date
            ].append(
                partial_plan
            )

            block_hours = float(
                partial_plan[
                    "total_duration_hours"
                ]
            )

            daily_planned_hours[
                key
            ] = (
                daily_planned_hours.get(
                    key,
                    0.0,
                )
                + block_hours
            )

            start_minutes = (
                time_to_minutes(
                    partial_plan[
                        "start_time"
                    ]
                )
            )

            end_minutes = (
                time_to_minutes(
                    partial_plan[
                        "end_time"
                    ]
                )
            )

            daily_reserved_intervals.setdefault(
                key,
                [],
            ).append(
                (
                    start_minutes,
                    end_minutes,
                )
            )

            daily_reserved_intervals[
                key
            ].sort(
                key=lambda interval:
                    interval[0]
            )

            scheduled_task_ids.update(
                task.task_id
                for task in partial_group
            )

    # ========================================================
    # BUILD DAY RESULTS
    # ========================================================

    day_results = []

    for planning_date in horizon_dates:

        blocks = daily_plans[
            planning_date
        ]

        planned_hours = sum(
            float(
                item.get(
                    "total_duration_hours",
                    0,
                )
            )
            for item in blocks
        )

        task_count = sum(
            int(
                item.get(
                    "task_count",
                    0,
                )
            )
            for item in blocks
        )

        goods_forecast = {}

        for block in blocks:

            section_id = block.get(
                "section_id"
            )

            expected_goods = int(
                block.get(
                    "expected_goods_trains",
                    0,
                )
                or 0
            )

            if section_id is not None:
                goods_forecast[
                    str(section_id)
                ] = expected_goods

        day_results.append(
            {
                "date": planning_date,

                "blocks": blocks,

                "summary": {
                    "blocks": len(blocks),
                    "tasks": task_count,
                    "planned_hours": planned_hours,
                    "goods_forecast": goods_forecast,
                },
            }
        )

    # ========================================================
    # UNSCHEDULED
    # ========================================================

    unscheduled_tasks = []

    for task in active_tasks:

        if task.task_id in scheduled_task_ids:
            continue

        unscheduled_tasks.append(
            {
                "task_id": task.task_id,
                "task_code": task.task_code,
                "section_id": task.section_id,
                "asset_id": task.asset_id,
                "department_id": task.department_id,
                "severity": task.severity,
                "status": task.status,
                "due_date": task.due_date,
                "duration_hours": (
                    float(
                        task.duration_hours
                    )
                    if task.duration_hours
                    is not None
                    else None
                ),
                "reason": (
                    "No suitable conflict-free window, "
                    "daily capacity, or acceptable planning "
                    "day was available within the selected "
                    "horizon."
                ),
            }
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    total_blocks = sum(
        len(day["blocks"])
        for day in day_results
    )

    total_planned_hours = sum(
        float(
            day["summary"][
                "planned_hours"
            ]
        )
        for day in day_results
    )

    total_planned_tasks = len(
        scheduled_task_ids
    )

    # ========================================================
    # GOODS FORECAST SUMMARY
    # ========================================================

    goods_forecast_summary = {}

    for planning_date in horizon_dates:

        for section_id in section_groups.keys():

            expected_goods = (
                get_goods_forecast(
                    db=db,
                    section_id=section_id,
                    planning_date=planning_date,
                )
            )

            goods_forecast_summary[
                f"{planning_date.isoformat()}_section_{section_id}"
            ] = {
                "date": planning_date,
                "section_id": section_id,
                "expected_goods_trains": (
                    expected_goods
                ),
                "traffic_level": (
                    get_goods_traffic_level(
                        expected_goods
                    )
                ),
            }

    return {
        "horizon": horizon,

        "start_date": start_date,

        "end_date": end_date,

        "total_days": total_days,

        "planning_rules": {
            "max_daily_planned_hours":
                MAX_DAILY_PLANNED_HOURS,

            "priority_based":
                True,

            "overdue_aware":
                True,

            "train_conflict_check":
                True,

            "section_grouping":
                True,

            "whole_horizon_comparison":
                True,

            "same_section_overlap_prevention":
                True,

            "existing_block_awareness":
                True,

            "combined_block_preferred":
                True,

            "goods_train_forecast_used":
                True,

            "goods_traffic_scoring_weight":
                GOODS_TRAFFIC_WEIGHT,

            "goods_forecast_mode":
                "daily_section_based",
        },

        "goods_forecast_summary":
            goods_forecast_summary,

        "summary": {
            "total_tasks_considered":
                len(original_task_ids),

            "tasks_planned":
                total_planned_tasks,

            "tasks_unscheduled":
                len(unscheduled_tasks),

            "total_blocks":
                total_blocks,

            "total_planned_hours":
                total_planned_hours,
        },

        "days":
            day_results,

        "unscheduled_tasks":
            unscheduled_tasks,
    }