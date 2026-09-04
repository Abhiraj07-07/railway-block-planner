from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database.models import (
    Station,
    Section,
    Asset,
    MaintenanceTask,
    Defect,
    Train,
    Block,
    OperationalEvent,
)


# ============================================================
# BASIC OPERATIONAL KPIs
# ============================================================

def get_operational_kpis(
    db: Session,
) -> dict:
    """
    Calculate operational KPIs using grouped SQL queries
    instead of many individual COUNT queries.
    """

    # --------------------------------------------------------
    # Total records
    # --------------------------------------------------------

    total_stations = db.query(
        func.count(Station.station_id)
    ).scalar() or 0

    total_sections = db.query(
        func.count(Section.section_id)
    ).scalar() or 0

    total_assets = db.query(
        func.count(Asset.asset_id)
    ).scalar() or 0

    total_tasks = db.query(
        func.count(MaintenanceTask.task_id)
    ).scalar() or 0

    total_defects = db.query(
        func.count(Defect.defect_id)
    ).scalar() or 0

    total_trains = db.query(
        func.count(Train.train_id)
    ).scalar() or 0

    total_blocks = db.query(
        func.count(Block.block_id)
    ).scalar() or 0

    # --------------------------------------------------------
    # Defect status
    # --------------------------------------------------------

    defect_status_rows = (
        db.query(
            Defect.status,
            func.count(Defect.defect_id),
        )
        .group_by(Defect.status)
        .all()
    )

    defect_status = {
        str(status): int(count)
        for status, count in defect_status_rows
        if status is not None
    }

    open_defects = defect_status.get(
        "OPEN",
        0,
    )

    # --------------------------------------------------------
    # Maintenance task status
    # --------------------------------------------------------

    task_status_rows = (
        db.query(
            MaintenanceTask.status,
            func.count(MaintenanceTask.task_id),
        )
        .group_by(MaintenanceTask.status)
        .all()
    )

    task_status = {
        str(status): int(count)
        for status, count in task_status_rows
        if status is not None
    }

    completed_tasks = task_status.get(
        "COMPLETED",
        0,
    )

    overdue_tasks = task_status.get(
        "OVERDUE",
        0,
    )

    pending_tasks = task_status.get(
        "PENDING",
        0,
    )

    # --------------------------------------------------------
    # Critical assets
    # --------------------------------------------------------

    critical_assets = (
        db.query(
            func.count(Asset.asset_id)
        )
        .filter(
            Asset.criticality == "CRITICAL"
        )
        .scalar()
        or 0
    )

    # --------------------------------------------------------
    # Block status
    # --------------------------------------------------------

    block_status_rows = (
        db.query(
            Block.status,
            func.count(Block.block_id),
        )
        .group_by(Block.status)
        .all()
    )

    block_status = {
        str(status): int(count)
        for status, count in block_status_rows
        if status is not None
    }

    planned_blocks = block_status.get(
        "PLANNED",
        0,
    )

    active_blocks = sum(
        block_status.get(status, 0)
        for status in (
            "PLANNED",
            "APPROVED",
            "IN_PROGRESS",
        )
    )

    # --------------------------------------------------------
    # Replanned blocks
    # --------------------------------------------------------

    replanned_blocks = (
        db.query(
            func.count(Block.block_id)
        )
        .filter(
            Block.recommended_start_time.isnot(None),
            Block.recommended_end_time.isnot(None),
        )
        .scalar()
        or 0
    )

    # --------------------------------------------------------
    # Open events
    # --------------------------------------------------------

    open_events = (
        db.query(
            func.count(
                OperationalEvent.event_id
            )
        )
        .filter(
            OperationalEvent.status == "OPEN"
        )
        .scalar()
        or 0
    )

    return {
        "stations": total_stations,
        "sections": total_sections,
        "assets": total_assets,
        "maintenance_tasks": total_tasks,
        "defects": total_defects,
        "trains": total_trains,
        "blocks": total_blocks,

        "open_defects": open_defects,

        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks,

        "critical_assets": critical_assets,

        "planned_blocks": planned_blocks,
        "active_blocks": active_blocks,
        "replanned_blocks": replanned_blocks,

        "open_operational_events": open_events,
    }


# ============================================================
# MAINTENANCE ANALYTICS
# ============================================================

def get_maintenance_analytics(
    db: Session,
) -> dict:
    """
    Calculate maintenance statistics with grouped SQL.
    """

    status_rows = (
        db.query(
            MaintenanceTask.status,
            func.count(MaintenanceTask.task_id),
        )
        .group_by(MaintenanceTask.status)
        .all()
    )

    status_counts = {
        status: int(count)
        for status, count in status_rows
        if status is not None
    }

    # Keep the original expected keys even if a status
    # does not currently exist in the database.
    for status in (
        "PENDING",
        "COMPLETED",
        "OVERDUE",
        "CANCELLED",
    ):
        status_counts.setdefault(
            status,
            0,
        )

    severity_rows = (
        db.query(
            MaintenanceTask.severity,
            func.count(MaintenanceTask.task_id),
        )
        .group_by(MaintenanceTask.severity)
        .all()
    )

    severity_counts = {
        severity: int(count)
        for severity, count in severity_rows
        if severity is not None
    }

    for severity in (
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    ):
        severity_counts.setdefault(
            severity,
            0,
        )

    return {
        "status_counts": status_counts,
        "severity_counts": severity_counts,
    }


# ============================================================
# DEFECT ANALYTICS
# ============================================================

def get_defect_analytics(
    db: Session,
) -> dict:
    """
    Calculate defect statistics with grouped SQL.
    """

    severity_rows = (
        db.query(
            Defect.severity,
            func.count(Defect.defect_id),
        )
        .group_by(Defect.severity)
        .all()
    )

    severity_counts = {
        severity: int(count)
        for severity, count in severity_rows
        if severity is not None
    }

    for severity in (
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    ):
        severity_counts.setdefault(
            severity,
            0,
        )

    status_rows = (
        db.query(
            Defect.status,
            func.count(Defect.defect_id),
        )
        .group_by(Defect.status)
        .all()
    )

    status_counts = {
        status: int(count)
        for status, count in status_rows
        if status is not None
    }

    for status in (
        "OPEN",
        "CLOSED",
    ):
        status_counts.setdefault(
            status,
            0,
        )

    return {
        "severity_counts": severity_counts,
        "status_counts": status_counts,
    }


# ============================================================
# BLOCK ANALYTICS
# ============================================================

def get_block_analytics(
    db: Session,
) -> dict:
    """
    Calculate block statistics with grouped SQL.
    """

    status_rows = (
        db.query(
            Block.status,
            func.count(Block.block_id),
        )
        .group_by(Block.status)
        .all()
    )

    status_counts = {
        status: int(count)
        for status, count in status_rows
        if status is not None
    }

    for status in (
        "PLANNED",
        "APPROVED",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
    ):
        status_counts.setdefault(
            status,
            0,
        )

    total_blocks = sum(
        status_counts.values()
    )

    replanned = (
        db.query(
            func.count(Block.block_id)
        )
        .filter(
            Block.recommended_start_time.isnot(None),
            Block.recommended_end_time.isnot(None),
        )
        .scalar()
        or 0
    )

    return {
        "total_blocks": total_blocks,
        "planned": status_counts["PLANNED"],
        "approved": status_counts["APPROVED"],
        "in_progress": status_counts["IN_PROGRESS"],
        "completed": status_counts["COMPLETED"],
        "cancelled": status_counts["CANCELLED"],
        "replanned": int(replanned),
    }


# ============================================================
# TRAIN & BLOCK IMPACT ANALYTICS
# ============================================================

def get_train_block_impact_analytics(
    db: Session,
) -> dict:
    """
    Calculate train/block impact.
    This remains engine-based because train conflict
    analysis requires actual scheduling logic.
    """

    from backend.engines.optimization_engine import (
        analyze_all_blocks,
    )

    block_impacts = analyze_all_blocks(
        db=db
    )

    total_blocks = len(
        block_impacts
    )

    conflict_free_blocks = 0
    low_impact_blocks = 0
    medium_impact_blocks = 0
    high_impact_blocks = 0

    total_conflict_count = 0
    total_conflict_minutes = 0

    affected_train_ids = set()

    for block in block_impacts:

        impact_level = block.get(
            "impact_level"
        )

        conflict_count = block.get(
            "conflict_count",
            0,
        )

        if conflict_count == 0:
            conflict_free_blocks += 1

        if impact_level == "LOW":
            low_impact_blocks += 1

        elif impact_level == "MEDIUM":
            medium_impact_blocks += 1

        elif impact_level == "HIGH":
            high_impact_blocks += 1

        total_conflict_count += (
            conflict_count
        )

        total_conflict_minutes += (
            block.get(
                "total_conflict_minutes",
                0,
            )
            or 0
        )

        for train_id in (
            block.get(
                "affected_train_ids",
                []
            )
            or []
        ):
            affected_train_ids.add(
                train_id
            )

    block_utilization = (
        round(
            (
                conflict_free_blocks
                / total_blocks
            )
            * 100,
            2,
        )
        if total_blocks
        else 0
    )

    return {
        "total_blocks_analyzed":
            total_blocks,

        "conflict_free_blocks":
            conflict_free_blocks,

        "low_impact_blocks":
            low_impact_blocks,

        "medium_impact_blocks":
            medium_impact_blocks,

        "high_impact_blocks":
            high_impact_blocks,

        "total_conflicts":
            total_conflict_count,

        "total_conflict_minutes":
            total_conflict_minutes,

        "affected_trains":
            len(affected_train_ids),

        "affected_train_ids":
            sorted(affected_train_ids),

        "block_utilization_percent":
            block_utilization,
    }


# ============================================================
# AI / RISK ANALYTICS
# ============================================================

def get_ai_analytics(
    db: Session,
) -> dict:
    """
    Calculate AI risk and decision statistics.
    """

    from backend.engines.risk_engine import (
        calculate_all_asset_risks,
    )

    from backend.engines.ai_decision_engine import (
        calculate_all_ai_decisions,
    )

    risk_results = calculate_all_asset_risks(
        db=db
    )

    decision_results = calculate_all_ai_decisions(
        db=db
    )

    risk_distribution = {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
    }

    total_risk_score = 0

    for item in risk_results:

        level = item.get(
            "risk_level"
        )

        if level in risk_distribution:
            risk_distribution[level] += 1

        total_risk_score += (
            item.get(
                "risk_score",
                0,
            )
            or 0
        )

    average_risk_score = (
        round(
            total_risk_score
            / len(risk_results),
            2,
        )
        if risk_results
        else 0
    )

    decision_distribution = {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "URGENT": 0,
    }

    total_ai_score = 0

    for item in decision_results:

        level = item.get(
            "decision_level"
        )

        if level in decision_distribution:
            decision_distribution[level] += 1

        total_ai_score += (
            item.get(
                "ai_decision_score",
                0,
            )
            or 0
        )

    average_ai_score = (
        round(
            total_ai_score
            / len(decision_results),
            2,
        )
        if decision_results
        else 0
    )

    return {
        "risk_distribution":
            risk_distribution,

        "average_risk_score":
            average_risk_score,

        "decision_distribution":
            decision_distribution,

        "average_ai_decision_score":
            average_ai_score,

        "urgent_ai_decisions":
            decision_distribution["URGENT"],
    }


# ============================================================
# COMPLETE ADMIN ANALYTICS
# ============================================================

def get_admin_analytics(
    db: Session,
) -> dict:
    """
    Generate complete admin analytics.
    """

    return {
        "operational_kpis":
            get_operational_kpis(
                db=db
            ),

        "maintenance":
            get_maintenance_analytics(
                db=db
            ),

        "defects":
            get_defect_analytics(
                db=db
            ),

        "blocks":
            get_block_analytics(
                db=db
            ),

        "train_block_impact":
            get_train_block_impact_analytics(
                db=db
            ),

        "ai":
            get_ai_analytics(
                db=db
            ),
    }