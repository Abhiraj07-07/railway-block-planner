from datetime import time

from sqlalchemy.orm import Session

from backend.database.models import (
    MaintenanceTask,
    TrainSchedule,
)
from backend.engines.priority_engine import (
    calculate_task_priority,
)


# ============================================================
# PLANNING SETTINGS
# ============================================================

WORKING_START_MINUTES = 8 * 60       # 08:00
WORKING_END_MINUTES = 20 * 60        # 20:00

TRAIN_BUFFER_MINUTES = 15


# ============================================================
# TIME HELPERS
# ============================================================

def time_to_minutes(value: time) -> int:
    """Convert a time object to minutes from midnight."""

    return value.hour * 60 + value.minute


def minutes_to_time(total_minutes: int) -> time:
    """Convert minutes from midnight to a time object."""

    total_minutes = max(
        0,
        min(total_minutes, 24 * 60),
    )

    hours = total_minutes // 60
    minutes = total_minutes % 60

    return time(hours, minutes)


# ============================================================
# INTERVAL CHECK
# ============================================================

def intervals_overlap(
    start_a: int,
    end_a: int,
    start_b: int,
    end_b: int,
) -> bool:
    """Return True when two intervals overlap."""

    return (
        start_a < end_b
        and start_b < end_a
    )


# ============================================================
# TRAIN INTERVALS
# ============================================================

def get_train_intervals(
    db: Session,
    section_id: int,
    schedule_date,
) -> list[tuple[int, int]]:
    """
    Get train occupancy intervals for a section/date.

    A safety buffer is applied before train arrival
    and after train departure.
    """

    schedules = (
        db.query(TrainSchedule)
        .filter(
            TrainSchedule.section_id == section_id,
            TrainSchedule.schedule_date == schedule_date,
        )
        .order_by(
            TrainSchedule.arrival_time
        )
        .all()
    )

    intervals: list[tuple[int, int]] = []

    for schedule in schedules:

        train_start = (
            time_to_minutes(
                schedule.arrival_time
            )
            - TRAIN_BUFFER_MINUTES
        )

        train_end = (
            time_to_minutes(
                schedule.departure_time
            )
            + TRAIN_BUFFER_MINUTES
        )

        intervals.append(
            (
                max(train_start, 0),
                min(train_end, 24 * 60),
            )
        )

    return intervals


# ============================================================
# WINDOW CONFLICT
# ============================================================

def find_conflicting_interval(
    candidate_start: int,
    candidate_end: int,
    occupied_intervals: list[tuple[int, int]],
) -> tuple[int, int] | None:
    """
    Return the first occupied interval that conflicts
    with the candidate window.
    """

    for occupied_start, occupied_end in occupied_intervals:

        if intervals_overlap(
            candidate_start,
            candidate_end,
            occupied_start,
            occupied_end,
        ):
            return (
                occupied_start,
                occupied_end,
            )

    return None


# ============================================================
# FIND AVAILABLE WINDOW
# ============================================================

def find_available_window(
    db: Session,
    section_id: int,
    schedule_date,
    duration_hours: float,
    reserved_intervals: list[tuple[int, int]] | None = None,
) -> tuple[time, time] | None:
    """
    Find the earliest conflict-free maintenance window.

    Checks:
        1. Train occupancy.
        2. Train safety buffers.
        3. Already planned blocks/tasks for this planning run.
    """

    duration_minutes = max(
        1,
        int(round(duration_hours * 60)),
    )

    occupied_intervals = get_train_intervals(
        db=db,
        section_id=section_id,
        schedule_date=schedule_date,
    )

    if reserved_intervals:
        occupied_intervals.extend(
            reserved_intervals
        )

    occupied_intervals.sort(
        key=lambda interval: interval[0]
    )

    candidate_start = WORKING_START_MINUTES

    while (
        candidate_start + duration_minutes
        <= WORKING_END_MINUTES
    ):

        candidate_end = (
            candidate_start
            + duration_minutes
        )

        conflict = find_conflicting_interval(
            candidate_start,
            candidate_end,
            occupied_intervals,
        )

        if conflict is None:

            return (
                minutes_to_time(candidate_start),
                minutes_to_time(candidate_end),
            )

        # Jump directly after the conflicting interval.
        candidate_start = max(
            conflict[1],
            candidate_start + 1,
        )

    return None


# ============================================================
# PRIORITY SORTING
# ============================================================

def sort_tasks_by_priority(
    db: Session,
    tasks: list[MaintenanceTask],
) -> list[MaintenanceTask]:
    """
    Sort tasks using the existing maintenance priority engine.

    Ordering:
        1. Priority score
        2. Overdue days
        3. Severity
        4. Task ID
    """

    scored_tasks = []

    severity_rank = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    }

    for task in tasks:

        priority = calculate_task_priority(
            db=db,
            task=task,
        )

        scored_tasks.append(
            (
                float(
                    priority.get(
                        "priority_score",
                        0,
                    )
                ),
                int(
                    priority.get(
                        "overdue_days",
                        0,
                    )
                    or 0
                ),
                severity_rank.get(
                    str(
                        task.severity
                        or ""
                    ).upper(),
                    0,
                ),
                task.task_id,
                task,
            )
        )

    scored_tasks.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2],
            item[3],
        ),
        reverse=True,
    )

    return [
        item[4]
        for item in scored_tasks
    ]


# ============================================================
# GROUP TASKS BY SECTION
# ============================================================

def group_tasks_by_section(
    tasks: list[MaintenanceTask],
) -> dict[int, list[MaintenanceTask]]:
    """
    Group maintenance tasks by railway section.
    """

    grouped: dict[int, list[MaintenanceTask]] = {}

    for task in tasks:

        grouped.setdefault(
            task.section_id,
            [],
        ).append(task)

    return grouped


# ============================================================
# COMBINATION CHECK
# ============================================================

def can_combine_tasks(
    tasks: list[MaintenanceTask],
) -> bool:
    """
    Decide whether tasks can be represented by one sequential
    maintenance block.

    Current project rule:
        - All tasks must belong to the same section.
        - Tasks must have a valid positive duration.

    We intentionally keep execution sequential.
    Parallel work is NOT assumed without additional
    resource/safety dependency data.
    """

    if not tasks:
        return False

    section_ids = {
        task.section_id
        for task in tasks
    }

    if len(section_ids) != 1:
        return False

    for task in tasks:

        duration = float(
            task.duration_hours or 0
        )

        if duration <= 0:
            return False

    return True


# ============================================================
# BUILD COMBINED BLOCK
# ============================================================

def build_combined_block(
    db: Session,
    tasks: list[MaintenanceTask],
    schedule_date,
    reserved_intervals: list[tuple[int, int]],
) -> dict:
    """
    Build one sequential maintenance block for compatible
    tasks from the same section.
    """

    if not can_combine_tasks(tasks):
        return {
            "recommended": False,
            "reason": (
                "Tasks are not compatible for a "
                "combined maintenance block."
            ),
        }

    section_id = tasks[0].section_id

    # --------------------------------------------------------
    # Sequential execution model:
    # total block duration = sum of task durations.
    # --------------------------------------------------------

    total_duration = sum(
        float(task.duration_hours)
        for task in tasks
    )

    window = find_available_window(
        db=db,
        section_id=section_id,
        schedule_date=schedule_date,
        duration_hours=total_duration,
        reserved_intervals=reserved_intervals,
    )

    if window is None:

        return {
            "recommended": False,
            "section_id": section_id,
            "schedule_date": schedule_date,
            "task_ids": [
                task.task_id
                for task in tasks
            ],
            "task_codes": [
                task.task_code
                for task in tasks
            ],
            "total_duration_hours": total_duration,
            "task_count": len(tasks),
            "reason": (
                "No conflict-free window is available "
                "for the combined maintenance block."
            ),
        }

    start_time, end_time = window

    return {
        "recommended": True,
        "section_id": section_id,
        "schedule_date": schedule_date,
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
        "reason": (
            "Combined same-section maintenance block "
            "selected using priority-aware planning "
            "and train-conflict avoidance."
        ),
    }


# ============================================================
# FIND BEST GROUP FOR SECTION
# ============================================================

def find_best_section_group(
    db: Session,
    section_tasks: list[MaintenanceTask],
    schedule_date,
    reserved_intervals: list[tuple[int, int]],
) -> list[MaintenanceTask]:
    """
    Find the largest feasible same-section task group
    beginning with the highest-priority task.

    Important:
        The highest-priority task is always protected.

    Example:
        High task = 3h
        Critical task = 1h
        High task = 2h

    If all three fit:
        → combine all three.

    If all three do not fit:
        → continue with the highest-priority feasible group
        rather than immediately splitting the first task.
    """

    if not section_tasks:
        return []

    ordered_tasks = list(section_tasks)

    # Highest-priority task must be considered first.
    highest_priority_task = ordered_tasks[0]

    selected = [
        highest_priority_task
    ]

    selected_duration = float(
        highest_priority_task.duration_hours or 0
    )

    # --------------------------------------------------------
    # Try adding remaining tasks while the full group
    # remains feasible.
    # --------------------------------------------------------

    for task in ordered_tasks[1:]:

        duration = float(
            task.duration_hours or 0
        )

        candidate_duration = (
            selected_duration
            + duration
        )

        if duration <= 0:
            continue

        window = find_available_window(
            db=db,
            section_id=highest_priority_task.section_id,
            schedule_date=schedule_date,
            duration_hours=candidate_duration,
            reserved_intervals=reserved_intervals,
        )

        if window is None:
            continue

        selected.append(task)
        selected_duration = candidate_duration

    return selected


# ============================================================
# GENERATE OPTIMIZED DAILY PLAN
# ============================================================

def generate_maintenance_plan(
    db: Session,
    tasks: list[MaintenanceTask],
    schedule_date,
) -> list[dict]:
    """
    Generate an optimized single-day maintenance plan.

    Planning principles:
        1. High-priority tasks are protected.
        2. Same-section tasks are grouped.
        3. Combined blocks use sequential durations.
        4. Train conflicts are avoided.
        5. Generated blocks reserve their intervals.
        6. Every task is scheduled at most once.
    """

    if not tasks:
        return []

    # --------------------------------------------------------
    # Remove inactive tasks defensively.
    # --------------------------------------------------------

    active_tasks = [
        task
        for task in tasks
        if str(
            task.status or ""
        ).upper()
        not in {
            "COMPLETED",
            "CANCELLED",
        }
    ]

    if not active_tasks:
        return []

    # --------------------------------------------------------
    # Sort globally.
    # --------------------------------------------------------

    sorted_tasks = sort_tasks_by_priority(
        db=db,
        tasks=active_tasks,
    )

    # --------------------------------------------------------
    # Group by section.
    # --------------------------------------------------------

    grouped_tasks = group_tasks_by_section(
        sorted_tasks
    )

    # --------------------------------------------------------
    # Process sections by the priority of their highest-
    # priority task.
    # --------------------------------------------------------

    section_order = []

    for section_id, section_tasks in grouped_tasks.items():

        section_tasks = sort_tasks_by_priority(
            db=db,
            tasks=section_tasks,
        )

        if not section_tasks:
            continue

        top_task = section_tasks[0]

        global_priority_position = next(
            (
                index
                for index, task
                in enumerate(sorted_tasks)
                if task.task_id
                == top_task.task_id
            ),
            999999,
        )

        section_order.append(
            (
                global_priority_position,
                section_id,
                section_tasks,
            )
        )

    section_order.sort(
        key=lambda item: item[0]
    )

    recommendations = []

    # --------------------------------------------------------
    # Reservations are tracked per section because separate
    # railway sections/corridors may operate independently.
    # --------------------------------------------------------

    reserved_by_section: dict[
        int,
        list[tuple[int, int]]
    ] = {}

    # --------------------------------------------------------
    # Process one section at a time.
    # --------------------------------------------------------

    for (
        _,
        section_id,
        section_tasks,
    ) in section_order:

        section_reserved = (
            reserved_by_section.setdefault(
                section_id,
                [],
            )
        )

        remaining_tasks = list(
            section_tasks
        )

        while remaining_tasks:

            selected_tasks = find_best_section_group(
                db=db,
                section_tasks=remaining_tasks,
                schedule_date=schedule_date,
                reserved_intervals=section_reserved,
            )

            # ------------------------------------------------
            # Safety fallback.
            # ------------------------------------------------

            if not selected_tasks:

                selected_tasks = [
                    remaining_tasks[0]
                ]

            plan = build_combined_block(
                db=db,
                tasks=selected_tasks,
                schedule_date=schedule_date,
                reserved_intervals=section_reserved,
            )

            # ------------------------------------------------
            # If combined group failed, try the top task
            # independently.
            # ------------------------------------------------

            if not plan.get("recommended"):

                top_task = remaining_tasks[0]

                plan = build_combined_block(
                    db=db,
                    tasks=[top_task],
                    schedule_date=schedule_date,
                    reserved_intervals=section_reserved,
                )

                # ------------------------------------------------
                # If even the highest-priority task cannot fit,
                # report it and move to the next task.
                # ------------------------------------------------

                if not plan.get("recommended"):

                    recommendations.append(
                        plan
                    )

                    remaining_tasks.pop(0)

                    continue

                selected_tasks = [
                    top_task
                ]

            recommendations.append(
                plan
            )

            # ------------------------------------------------
            # Reserve this block.
            # ------------------------------------------------

            start_minutes = time_to_minutes(
                plan["start_time"]
            )

            end_minutes = time_to_minutes(
                plan["end_time"]
            )

            section_reserved.append(
                (
                    start_minutes,
                    end_minutes,
                )
            )

            section_reserved.sort(
                key=lambda interval: interval[0]
            )

            # ------------------------------------------------
            # Remove every successfully scheduled task.
            # ------------------------------------------------

            selected_ids = {
                task.task_id
                for task in selected_tasks
            }

            remaining_tasks = [
                task
                for task in remaining_tasks
                if task.task_id
                not in selected_ids
            ]

    return recommendations


# ============================================================
# PLAN SUMMARY
# ============================================================

def summarize_plan(
    recommendations: list[dict],
) -> dict:
    """
    Generate summary information for a maintenance plan.
    """

    successful = [
        item
        for item in recommendations
        if item.get("recommended") is True
    ]

    failed = [
        item
        for item in recommendations
        if item.get("recommended") is not True
    ]

    total_tasks = sum(
        int(
            item.get(
                "task_count",
                1,
            )
        )
        for item in successful
    )

    total_hours = sum(
        float(
            item.get(
                "total_duration_hours",
                item.get(
                    "duration_hours",
                    0,
                ),
            )
        )
        for item in successful
    )

    return {
        "total_blocks": len(successful),
        "total_tasks": total_tasks,
        "unscheduled_groups": len(failed),
        "total_planned_hours": total_hours,
    }