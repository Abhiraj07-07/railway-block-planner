
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
        min(total_minutes, 24 * 60)
    )

    hours = total_minutes // 60
    minutes = total_minutes % 60

    return time(
        hours,
        minutes
    )


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

    A safety buffer is applied before arrival and after
    departure.
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

    intervals = []

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
# WINDOW CONFLICT CHECK
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
    Find the earliest maintenance window that avoids:

    1. Scheduled trains.
    2. Previously planned maintenance tasks.
    """

    duration_minutes = max(
        1,
        int(round(duration_hours * 60))
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
                minutes_to_time(
                    candidate_start
                ),
                minutes_to_time(
                    candidate_end
                ),
            )

        # Jump after the conflicting interval.
        candidate_start = conflict[1]

    return None


# ============================================================
# PRIORITY SORTING
# ============================================================

def sort_tasks_by_priority(
    db: Session,
    tasks: list[MaintenanceTask],
) -> list[MaintenanceTask]:
    """
    Sort tasks using the Maintenance Priority Engine.
    """

    scored_tasks = []

    for task in tasks:

        priority = calculate_task_priority(
            db=db,
            task=task,
        )

        scored_tasks.append(
            (
                priority["priority_score"],
                priority["overdue_days"],
                task,
            )
        )

    scored_tasks.sort(
        key=lambda item: (
            item[0],
            item[1],
        ),
        reverse=True,
    )

    return [
        item[2]
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

    grouped: dict[
        int,
        list[MaintenanceTask]
    ] = {}

    for task in tasks:

        grouped.setdefault(
            task.section_id,
            [],
        ).append(task)

    return grouped


# ============================================================
# BUILD COMBINED TASK BLOCK
# ============================================================

def build_combined_block(
    db: Session,
    tasks: list[MaintenanceTask],
    schedule_date,
    reserved_intervals: list[tuple[int, int]],
) -> dict:
    """
    Try to schedule multiple compatible tasks from the same
    section inside one maintenance block.

    The tasks must belong to one section.
    """

    if not tasks:
        return {
            "recommended": False,
            "reason": "No tasks provided.",
        }

    section_ids = {
        task.section_id
        for task in tasks
    }

    if len(section_ids) != 1:
        return {
            "recommended": False,
            "reason": (
                "Tasks from different sections "
                "cannot share one block."
            ),
        }

    section_id = tasks[0].section_id

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
            "reason": (
                "No common conflict-free window "
                "is available for these tasks."
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
    }


# ============================================================
# GENERATE OPTIMIZED PLAN
# ============================================================

def generate_maintenance_plan(
    db: Session,
    tasks: list[MaintenanceTask],
    schedule_date,
) -> list[dict]:
    """
    Generate a maintenance plan using:

    1. Priority ordering.
    2. Same-section grouping.
    3. Train conflict avoidance.
    4. Maintenance conflict avoidance.
    5. Combined blocks whenever feasible.

    The algorithm tries to keep high-priority tasks first while
    reducing the number of maintenance blocks.
    """

    if not tasks:
        return []

    sorted_tasks = sort_tasks_by_priority(
        db=db,
        tasks=tasks,
    )

    grouped_tasks = group_tasks_by_section(
        sorted_tasks
    )

    # Tracks already reserved maintenance windows.
    reserved_by_section: dict[
        int,
        list[tuple[int, int]]
    ] = {}

    recommendations = []

    for section_id in sorted(
        grouped_tasks.keys()
    ):

        section_tasks = grouped_tasks[
            section_id
        ]

        section_reserved = (
            reserved_by_section.setdefault(
                section_id,
                [],
            )
        )

        # ----------------------------------------------------
        # Try to build larger combined blocks first.
        # ----------------------------------------------------

        remaining_tasks = list(
            section_tasks
        )

        while remaining_tasks:

            selected_tasks = []
            selected_duration = 0.0

            # Start from the highest-priority remaining task
            # and keep adding tasks while their combined block
            # remains feasible.
            for task in remaining_tasks:

                candidate_duration = (
                    selected_duration
                    + float(task.duration_hours)
                )

                window = find_available_window(
                    db=db,
                    section_id=section_id,
                    schedule_date=schedule_date,
                    duration_hours=candidate_duration,
                    reserved_intervals=section_reserved,
                )

                if window is None:
                    continue

                selected_tasks.append(task)
                selected_duration = candidate_duration

            # Safety fallback: schedule the first remaining
            # task independently if nothing could be grouped.
            if not selected_tasks:

                task = remaining_tasks[0]

                single_plan = build_combined_block(
                    db=db,
                    tasks=[task],
                    schedule_date=schedule_date,
                    reserved_intervals=section_reserved,
                )

                recommendations.append(
                    single_plan
                )

                if single_plan["recommended"]:

                    start_minutes = time_to_minutes(
                        single_plan["start_time"]
                    )

                    end_minutes = time_to_minutes(
                        single_plan["end_time"]
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

                remaining_tasks.remove(task)

                continue

            # ------------------------------------------------
            # Build the final combined block.
            # ------------------------------------------------

            combined_plan = build_combined_block(
                db=db,
                tasks=selected_tasks,
                schedule_date=schedule_date,
                reserved_intervals=section_reserved,
            )

            recommendations.append(
                combined_plan
            )

            # Reserve successful block.
            if combined_plan["recommended"]:

                start_minutes = time_to_minutes(
                    combined_plan["start_time"]
                )

                end_minutes = time_to_minutes(
                    combined_plan["end_time"]
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

            # Remove selected tasks from remaining list.
            selected_ids = {
                task.task_id
                for task in selected_tasks
            }

            remaining_tasks = [
                task
                for task in remaining_tasks
                if task.task_id not in selected_ids
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
        item.get("task_count", 1)
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

