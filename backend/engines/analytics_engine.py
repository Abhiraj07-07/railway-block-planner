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
    Calculate high-level operational KPIs.
    """

    total_stations = db.query(Station).count()

    total_sections = db.query(Section).count()

    total_assets = db.query(Asset).count()

    total_tasks = db.query(MaintenanceTask).count()

    total_defects = db.query(Defect).count()

    total_trains = db.query(Train).count()

    total_blocks = db.query(Block).count()

    open_defects = (
        db.query(Defect)
        .filter(
            Defect.status == "OPEN"
        )
        .count()
    )

    completed_tasks = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.status == "COMPLETED"
        )
        .count()
    )

    overdue_tasks = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.status == "OVERDUE"
        )
        .count()
    )

    pending_tasks = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.status == "PENDING"
        )
        .count()
    )

    critical_assets = (
        db.query(Asset)
        .filter(
            Asset.criticality == "CRITICAL"
        )
        .count()
    )

    planned_blocks = (
        db.query(Block)
        .filter(
            Block.status == "PLANNED"
        )
        .count()
    )

    active_blocks = (
        db.query(Block)
        .filter(
            Block.status.in_(
                [
                    "PLANNED",
                    "APPROVED",
                    "IN_PROGRESS",
                ]
            )
        )
        .count()
    )

    replanned_blocks = (
        db.query(Block)
        .filter(
            Block.recommended_start_time.isnot(None),
            Block.recommended_end_time.isnot(None),
        )
        .count()
    )

    open_events = (
        db.query(OperationalEvent)
        .filter(
            OperationalEvent.status == "OPEN"
        )
        .count()
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
    Calculate maintenance workload statistics.
    """

    statuses = [
        "PENDING",
        "COMPLETED",
        "OVERDUE",
        "CANCELLED",
    ]

    status_counts = {}

    for status in statuses:
        status_counts[status] = (
            db.query(MaintenanceTask)
            .filter(
                MaintenanceTask.status == status
            )
            .count()
        )

    severities = [
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    ]

    severity_counts = {}

    for severity in severities:
        severity_counts[severity] = (
            db.query(MaintenanceTask)
            .filter(
                MaintenanceTask.severity == severity
            )
            .count()
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
    Calculate defect statistics.
    """

    severities = [
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    ]

    severity_counts = {}

    for severity in severities:
        severity_counts[severity] = (
            db.query(Defect)
            .filter(
                Defect.severity == severity
            )
            .count()
        )

    status_counts = {}

    for status in [
        "OPEN",
        "CLOSED",
    ]:
        status_counts[status] = (
            db.query(Defect)
            .filter(
                Defect.status == status
            )
            .count()
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
    Calculate maintenance block statistics.
    """

    total_blocks = db.query(Block).count()

    planned = (
        db.query(Block)
        .filter(
            Block.status == "PLANNED"
        )
        .count()
    )

    approved = (
        db.query(Block)
        .filter(
            Block.status == "APPROVED"
        )
        .count()
    )

    completed = (
        db.query(Block)
        .filter(
            Block.status == "COMPLETED"
        )
        .count()
    )

    in_progress = (
        db.query(Block)
        .filter(
            Block.status == "IN_PROGRESS"
        )
        .count()
    )

    cancelled = (
        db.query(Block)
        .filter(
            Block.status == "CANCELLED"
        )
        .count()
    )

    replanned = (
        db.query(Block)
        .filter(
            Block.recommended_start_time.isnot(None),
            Block.recommended_end_time.isnot(None),
        )
        .count()
    )

    return {
        "total_blocks": total_blocks,
        "planned": planned,
        "approved": approved,
        "in_progress": in_progress,
        "completed": completed,
        "cancelled": cancelled,
        "replanned": replanned,
    }
    

# ============================================================
# TRAIN & BLOCK IMPACT ANALYTICS
# ============================================================

def get_train_block_impact_analytics(
    db: Session,
) -> dict:
    """
    Calculate train movement and maintenance block
    conflict statistics.
    """

    # Import here to avoid circular dependency.
    from backend.engines.optimization_engine import (
        analyze_all_blocks,
    )

    block_impacts = analyze_all_blocks(
        db=db
    )

    total_blocks = len(block_impacts)

    conflict_free_blocks = 0
    low_impact_blocks = 0
    medium_impact_blocks = 0
    high_impact_blocks = 0

    total_conflict_count = 0
    total_conflict_minutes = 0

    affected_train_ids = set()

    for block in block_impacts:

        impact_level = block["impact_level"]

        if block["conflict_count"] == 0:
            conflict_free_blocks += 1

        if impact_level == "LOW":
            low_impact_blocks += 1

        elif impact_level == "MEDIUM":
            medium_impact_blocks += 1

        elif impact_level == "HIGH":
            high_impact_blocks += 1

        total_conflict_count += (
            block["conflict_count"]
        )

        total_conflict_minutes += (
            block["total_conflict_minutes"]
        )

        for train_id in (
            block["affected_train_ids"] or []
        ):
            affected_train_ids.add(
                train_id
            )

    # --------------------------------------------------------
    # Block utilization
    # --------------------------------------------------------

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
        "total_blocks_analyzed": total_blocks,

        "conflict_free_blocks": (
            conflict_free_blocks
        ),

        "low_impact_blocks": (
            low_impact_blocks
        ),

        "medium_impact_blocks": (
            medium_impact_blocks
        ),

        "high_impact_blocks": (
            high_impact_blocks
        ),

        "total_conflicts": (
            total_conflict_count
        ),

        "total_conflict_minutes": (
            total_conflict_minutes
        ),

        "affected_trains": len(
            affected_train_ids
        ),

        "affected_train_ids": sorted(
            affected_train_ids
        ),

        "block_utilization_percent": (
            block_utilization
        ),
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

    # Local imports avoid unnecessary module coupling.
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
        level = item["risk_level"]

        if level in risk_distribution:
            risk_distribution[level] += 1

        total_risk_score += item["risk_score"]

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
        level = item["decision_level"]

        if level in decision_distribution:
            decision_distribution[level] += 1

        total_ai_score += item["ai_decision_score"]

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
        "risk_distribution": risk_distribution,
        "average_risk_score": average_risk_score,

        "decision_distribution": decision_distribution,
        "average_ai_decision_score": average_ai_score,

        "urgent_ai_decisions": decision_distribution[
            "URGENT"
        ],
    }


# ============================================================
# COMPLETE ADMIN ANALYTICS
# ============================================================

def get_admin_analytics(
    db: Session,
) -> dict:
    """
    Generate the complete Phase 6 admin analytics payload.
    """

    return {
        "operational_kpis": get_operational_kpis(
            db=db
        ),
        "maintenance": get_maintenance_analytics(
            db=db
        ),
        "defects": get_defect_analytics(
            db=db
        ),
        "blocks": get_block_analytics(
    db=db
),

"train_block_impact": get_train_block_impact_analytics(
    db=db
),

"ai": get_ai_analytics(
    db=db
),
    }