from datetime import date

from sqlalchemy.orm import Session

from backend.database.models import (
    Asset,
    MaintenanceTask,
    Defect,
)


# ============================================================
# RISK WEIGHTS
# ============================================================

CRITICALITY_SCORE = {
    "LOW": 10,
    "MEDIUM": 25,
    "HIGH": 40,
    "CRITICAL": 50,
}

SEVERITY_SCORE = {
    "LOW": 5,
    "MEDIUM": 15,
    "HIGH": 25,
    "CRITICAL": 35,
}


# ============================================================
# CALCULATE ASSET RISK
# ============================================================

def calculate_asset_risk(
    db: Session,
    asset: Asset,
) -> dict:
    """
    Calculate an explainable maintenance risk score
    for one asset.

    Risk factors:
        - Asset criticality
        - Open defect severity
        - Active maintenance task severity
        - Number of open defects
        - Number of active maintenance tasks
    """

    # --------------------------------------------------------
    # Asset criticality
    # --------------------------------------------------------

    criticality = (
        asset.criticality or "LOW"
    ).upper()

    criticality_score = CRITICALITY_SCORE.get(
        criticality,
        10,
    )

    # --------------------------------------------------------
    # Open defects
    # --------------------------------------------------------

    open_defects = (
        db.query(Defect)
        .filter(
            Defect.asset_id == asset.asset_id,
            Defect.status == "OPEN",
        )
        .all()
    )

    defect_score = 0

    highest_defect_severity = "LOW"

    for defect in open_defects:

        severity = (
            defect.severity or "LOW"
        ).upper()

        defect_score += SEVERITY_SCORE.get(
            severity,
            5,
        )

        severity_rank = {
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
            "CRITICAL": 4,
        }

        if (
            severity_rank.get(
                severity,
                1,
            )
            > severity_rank.get(
                highest_defect_severity,
                1,
            )
        ):
            highest_defect_severity = severity

    # --------------------------------------------------------
    # Active maintenance tasks
    # --------------------------------------------------------

    active_tasks = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.asset_id == asset.asset_id,
            MaintenanceTask.status.notin_(
                [
                    "COMPLETED",
                    "CANCELLED",
                ]
            ),
        )
        .all()
    )

    task_score = 0

    highest_task_severity = "LOW"

    for task in active_tasks:

        severity = (
            task.severity or "LOW"
        ).upper()

        task_score += SEVERITY_SCORE.get(
            severity,
            5,
        )

        severity_rank = {
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
            "CRITICAL": 4,
        }

        if (
            severity_rank.get(
                severity,
                1,
            )
            > severity_rank.get(
                highest_task_severity,
                1,
            )
        ):
            highest_task_severity = severity

    # --------------------------------------------------------
    # Count-based risk contribution
    # --------------------------------------------------------

    defect_count_score = min(
        len(open_defects) * 5,
        15,
    )

    task_count_score = min(
        len(active_tasks) * 3,
        10,
    )

    # --------------------------------------------------------
    # Total score
    # --------------------------------------------------------

    raw_score = (
        criticality_score
        + defect_score
        + task_score
        + defect_count_score
        + task_count_score
    )

    risk_score = min(
        raw_score,
        100,
    )

    # --------------------------------------------------------
    # Risk level
    # --------------------------------------------------------

    if risk_score >= 80:
        risk_level = "CRITICAL"

    elif risk_score >= 60:
        risk_level = "HIGH"

    elif risk_score >= 35:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    # --------------------------------------------------------
    # Explainability
    # --------------------------------------------------------

    risk_factors = []

    if criticality in {
        "HIGH",
        "CRITICAL",
    }:
        risk_factors.append(
            f"Asset criticality is {criticality}"
        )

    if open_defects:
        risk_factors.append(
            f"{len(open_defects)} open defect(s)"
        )

    if highest_defect_severity in {
        "HIGH",
        "CRITICAL",
    }:
        risk_factors.append(
            f"Highest defect severity is "
            f"{highest_defect_severity}"
        )

    if active_tasks:
        risk_factors.append(
            f"{len(active_tasks)} active maintenance task(s)"
        )

    if highest_task_severity in {
        "HIGH",
        "CRITICAL",
    }:
        risk_factors.append(
            f"Highest task severity is "
            f"{highest_task_severity}"
        )

    if not risk_factors:
        risk_factors.append(
            "No significant active risk factors detected"
        )

    # --------------------------------------------------------
    # Recommendation
    # --------------------------------------------------------

    if risk_level == "CRITICAL":
        recommendation = (
            "Immediate maintenance attention is recommended."
        )

    elif risk_level == "HIGH":
        recommendation = (
            "Schedule maintenance at the earliest safe window."
        )

    elif risk_level == "MEDIUM":
        recommendation = (
            "Monitor the asset and plan maintenance proactively."
        )

    else:
        recommendation = (
            "Routine monitoring is sufficient."
        )

    return {
        "asset_id": asset.asset_id,
        "asset_code": asset.asset_code,
        "asset_type": asset.asset_type,
        "section_id": asset.section_id,
        "criticality": criticality,

        "risk_score": risk_score,
        "risk_level": risk_level,

        "open_defect_count": len(open_defects),
        "active_task_count": len(active_tasks),

        "highest_defect_severity": (
            highest_defect_severity
            if open_defects
            else None
        ),

        "highest_task_severity": (
            highest_task_severity
            if active_tasks
            else None
        ),

        "risk_factors": risk_factors,

        "recommendation": recommendation,
    }


# ============================================================
# CALCULATE ALL ASSET RISKS
# ============================================================

def calculate_all_asset_risks(
    db: Session,
) -> list[dict]:
    """
    Calculate risk scores for all active assets.
    """

    assets = (
        db.query(Asset)
        .filter(
            Asset.status == "ACTIVE"
        )
        .order_by(
            Asset.asset_id
        )
        .all()
    )

    results = [
        calculate_asset_risk(
            db=db,
            asset=asset,
        )
        for asset in assets
    ]

    return sorted(
        results,
        key=lambda item: (
            item["risk_score"],
            item["asset_id"],
        ),
        reverse=True,
    )
    
    
# ============================================================
# SMART MAINTENANCE PRIORITY
# ============================================================

def calculate_smart_priority(
    db: Session,
    task: MaintenanceTask,
) -> dict:
    """
    Combine maintenance task priority with AI asset risk.

    Smart Priority considers:
        - Existing task priority score
        - Asset risk score
    """

    # --------------------------------------------------------
    # Existing maintenance priority
    # --------------------------------------------------------

    from backend.engines.priority_engine import (
        calculate_task_priority,
    )

    priority = calculate_task_priority(
        db=db,
        task=task,
    )

    base_priority_score = priority["priority_score"]

    # --------------------------------------------------------
    # Asset risk
    # --------------------------------------------------------

    asset = (
        db.query(Asset)
        .filter(
            Asset.asset_id == task.asset_id
        )
        .first()
    )

    if asset is None:
        raise ValueError(
            f"Asset {task.asset_id} not found."
        )

    risk = calculate_asset_risk(
        db=db,
        asset=asset,
    )

    risk_score = risk["risk_score"]

    # --------------------------------------------------------
    # Combined smart score
    # --------------------------------------------------------

    smart_score = round(
        (base_priority_score * 0.6)
        + (risk_score * 0.4),
        2,
    )

    # --------------------------------------------------------
    # Smart priority level
    # --------------------------------------------------------

    if smart_score >= 85:
        smart_level = "URGENT"

    elif smart_score >= 70:
        smart_level = "HIGH"

    elif smart_score >= 50:
        smart_level = "MEDIUM"

    else:
        smart_level = "LOW"

    # --------------------------------------------------------
    # Recommendation
    # --------------------------------------------------------

    if smart_level == "URGENT":
        recommendation = (
            "Immediate maintenance scheduling is recommended "
            "because task priority and asset risk are both high."
        )

    elif smart_level == "HIGH":
        recommendation = (
            "Prioritize this maintenance task in the next "
            "available safe maintenance window."
        )

    elif smart_level == "MEDIUM":
        recommendation = (
            "Include this task in proactive maintenance planning."
        )

    else:
        recommendation = (
            "Routine maintenance scheduling is sufficient."
        )

    return {
        "task_id": task.task_id,
        "task_code": task.task_code,
        "asset_id": task.asset_id,
        "section_id": task.section_id,

        "base_priority_score": base_priority_score,
        "asset_risk_score": risk_score,

        "smart_priority_score": smart_score,
        "smart_priority_level": smart_level,

        "risk_level": risk["risk_level"],
        "risk_factors": risk["risk_factors"],

        "recommendation": recommendation,
    }


# ============================================================
# SMART PRIORITY FOR ALL ACTIVE TASKS
# ============================================================

def calculate_all_smart_priorities(
    db: Session,
) -> list[dict]:
    """
    Calculate smart priority for all active maintenance tasks.
    """

    tasks = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.status.notin_(
                [
                    "COMPLETED",
                    "CANCELLED",
                ]
            )
        )
        .order_by(
            MaintenanceTask.task_id
        )
        .all()
    )

    results = [
        calculate_smart_priority(
            db=db,
            task=task,
        )
        for task in tasks
    ]

    return sorted(
        results,
        key=lambda item: (
            item["smart_priority_score"],
            item["task_id"],
        ),
        reverse=True,
    )    