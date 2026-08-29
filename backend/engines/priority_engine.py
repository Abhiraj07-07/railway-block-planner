
from datetime import date

from sqlalchemy.orm import Session

from backend.database.models import (
    Asset,
    Defect,
    MaintenanceTask,
    TrainSchedule,
)


# ============================================================
# PRIORITY WEIGHTS
# ============================================================

SEVERITY_SCORE = {
    "CRITICAL": 40,
    "HIGH": 30,
    "MEDIUM": 20,
    "LOW": 10,
}

CRITICALITY_SCORE = {
    "CRITICAL": 25,
    "HIGH": 20,
    "MEDIUM": 12,
    "LOW": 5,
}

STATUS_SCORE = {
    "OVERDUE": 20,
    "PENDING": 5,
    "IN_PROGRESS": 3,
    "COMPLETED": 0,
    "CANCELLED": 0,
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_overdue_score(
    due_date: date | None,
) -> tuple[int, int]:
    """
    Returns:
        (score, overdue_days)

    Score increases with the number of overdue days.
    Maximum overdue contribution = 10 points.
    """

    if due_date is None:
        return 0, 0

    today = date.today()

    if due_date >= today:
        return 0, 0

    overdue_days = (today - due_date).days

    score = min(overdue_days * 2, 10)

    return score, overdue_days


def get_defect_score(
    db: Session,
    asset_id: int,
) -> tuple[int, int]:
    """
    Checks open defects attached to the same asset.

    Returns:
        (score, open_defect_count)
    """

    open_defects = (
        db.query(Defect)
        .filter(
            Defect.asset_id == asset_id,
            Defect.status == "OPEN",
        )
        .all()
    )

    if not open_defects:
        return 0, 0

    highest_score = 0

    defect_severity_score = {
        "CRITICAL": 15,
        "HIGH": 10,
        "MEDIUM": 5,
        "LOW": 2,
    }

    for defect in open_defects:
        score = defect_severity_score.get(
            defect.severity,
            0,
        )

        highest_score = max(
            highest_score,
            score,
        )

    return highest_score, len(open_defects)


def get_train_impact_score(
    db: Session,
    section_id: int,
) -> tuple[int, int]:
    """
    Checks train schedules operating on the same section.

    Returns:
        (score, train_count)

    More scheduled trains means greater operational impact.
    """

    train_count = (
        db.query(TrainSchedule)
        .filter(
            TrainSchedule.section_id == section_id
        )
        .count()
    )

    if train_count == 0:
        return 0, 0

    if train_count >= 5:
        return 15, train_count

    if train_count >= 3:
        return 10, train_count

    return 5, train_count


def get_priority_level(score: int) -> str:
    """
    Converts a numeric score into a readable priority level.
    """

    if score >= 80:
        return "CRITICAL"

    if score >= 60:
        return "HIGH"

    if score >= 40:
        return "MEDIUM"

    return "LOW"


# ============================================================
# SINGLE TASK PRIORITY
# ============================================================

def calculate_task_priority(
    db: Session,
    task: MaintenanceTask,
) -> dict:
    """
    Calculates priority for one maintenance task.
    """

    severity_score = SEVERITY_SCORE.get(
        task.severity,
        0,
    )

    criticality_score = 0

    asset = (
        db.query(Asset)
        .filter(
            Asset.asset_id == task.asset_id
        )
        .first()
    )

    if asset:
        criticality_score = CRITICALITY_SCORE.get(
            asset.criticality,
            0,
        )

    status_score = STATUS_SCORE.get(
        task.status,
        0,
    )

    overdue_score, overdue_days = get_overdue_score(
        task.due_date
    )

    defect_score, open_defect_count = get_defect_score(
        db,
        task.asset_id,
    )

    train_impact_score, train_count = (
        get_train_impact_score(
            db,
            task.section_id,
        )
    )

    total_score = min(
        severity_score
        + criticality_score
        + status_score
        + overdue_score
        + defect_score
        + train_impact_score,
        100,
    )

    priority_level = get_priority_level(
        total_score
    )

    return {
        "task_id": task.task_id,
        "task_code": task.task_code,
        "source_system": task.source_system,
        "asset_id": task.asset_id,
        "section_id": task.section_id,
        "task_type": task.task_type,
        "severity": task.severity,
        "status": task.status,
        "due_date": task.due_date,
        "duration_hours": (
            float(task.duration_hours)
            if task.duration_hours is not None
            else 0
        ),

        "score_breakdown": {
            "severity": severity_score,
            "asset_criticality": criticality_score,
            "status": status_score,
            "overdue": overdue_score,
            "defect": defect_score,
            "train_impact": train_impact_score,
        },

        "overdue_days": overdue_days,
        "open_defects": open_defect_count,
        "scheduled_trains": train_count,

        "priority_score": total_score,
        "priority_level": priority_level,
    }


# ============================================================
# ALL TASK PRIORITIES
# ============================================================

def calculate_all_priorities(
    db: Session,
) -> list[dict]:
    """
    Calculates priority for all active maintenance tasks.

    Tasks are returned from highest to lowest priority.
    """

    tasks = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.status.notin_(
                ["COMPLETED", "CANCELLED"]
            )
        )
        .all()
    )

    results = [
        calculate_task_priority(
            db,
            task,
        )
        for task in tasks
    ]

    results.sort(
        key=lambda item: (
            item["priority_score"],
            item["overdue_days"],
        ),
        reverse=True,
    )

    for index, item in enumerate(
        results,
        start=1,
    ):
        item["priority_rank"] = index

    return results


# ============================================================
# TOP PRIORITY TASKS
# ============================================================

def get_top_priority_tasks(
    db: Session,
    limit: int = 10,
) -> list[dict]:
    """
    Returns the highest-priority maintenance tasks.
    """

    priorities = calculate_all_priorities(
        db
    )

    return priorities[:limit]

