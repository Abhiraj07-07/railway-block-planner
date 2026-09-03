# ============================================================
# RAILWAY AI RISK ENGINE
# Rule Risk + ML Risk + Combined Risk
# Shared in-memory snapshot cache for fast AI APIs
# ============================================================

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.database.models import (
    Asset,
    Defect,
    MaintenanceTask,
)


# ============================================================
# SETTINGS
# ============================================================

RULE_RISK_WEIGHT = 0.60
ML_RISK_WEIGHT = 0.40

CRITICAL_THRESHOLD = 80.0
HIGH_THRESHOLD = 60.0
MEDIUM_THRESHOLD = 35.0

TASK_PRIORITY_WEIGHT = 0.60
ASSET_RISK_WEIGHT = 0.40


# ============================================================
# SIMPLE IN-MEMORY CACHE
#
# Prototype / SIH optimization.
#
# Cache is automatically invalidated whenever data-changing
# endpoints call invalidate_risk_cache().
# ============================================================

_RISK_CACHE: Dict[int, Dict[str, Any]] = {}


# ============================================================
# BASIC HELPERS
# ============================================================

def _upper(value: Any) -> str:
    return str(value or "").strip().upper()


def _number(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def _today() -> date:
    return date.today()


def _parse_date(
    value: Any,
) -> Optional[date]:

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value)

    try:
        return datetime.fromisoformat(
            text.replace("Z", "")
        ).date()

    except ValueError:
        pass

    try:
        return datetime.strptime(
            text[:10],
            "%Y-%m-%d",
        ).date()

    except ValueError:
        return None


# ============================================================
# CACHE CONTROL
# ============================================================

def invalidate_risk_cache(
    asset_id: Optional[int] = None,
) -> None:
    """
    Clear cached risk calculations.

    Call without asset_id after any general maintenance /
    defect / asset data change.

    Call with asset_id when only one asset changed.
    """

    global _RISK_CACHE

    if asset_id is None:
        _RISK_CACHE.clear()
        return

    _RISK_CACHE.pop(
        int(asset_id),
        None,
    )


def get_cached_risk(
    asset_id: int,
) -> Optional[Dict[str, Any]]:

    return _RISK_CACHE.get(
        int(asset_id)
    )


def set_cached_risk(
    asset_id: int,
    result: Dict[str, Any],
) -> None:

    _RISK_CACHE[
        int(asset_id)
    ] = result


# ============================================================
# RISK LEVEL
# ============================================================

def get_risk_level(
    score: float,
) -> str:

    score = _number(score)

    if score >= CRITICAL_THRESHOLD:
        return "CRITICAL"

    if score >= HIGH_THRESHOLD:
        return "HIGH"

    if score >= MEDIUM_THRESHOLD:
        return "MEDIUM"

    return "LOW"


# ============================================================
# TASK PRIORITY
# ============================================================

def get_priority_score(
    task_or_severity: Any,
    asset_criticality: Any = None,
    days_overdue: int = 0,
) -> float:
    """
    Lightweight fallback priority calculator.

    The main project priority_engine remains the authoritative
    task-priority source for AI decisions.
    """

    if isinstance(
        task_or_severity,
        str,
    ):

        severity = _upper(
            task_or_severity
        )

    else:

        severity = _upper(
            getattr(
                task_or_severity,
                "severity",
                None,
            )
        )

    severity_scores = {
        "CRITICAL": 95,
        "HIGH": 85,
        "MEDIUM": 60,
        "LOW": 35,
    }

    score = severity_scores.get(
        severity,
        25,
    )

    criticality = _upper(
        asset_criticality
    )

    if criticality == "CRITICAL":
        score += 10

    elif criticality == "HIGH":
        score += 7

    elif criticality == "MEDIUM":
        score += 4

    overdue = max(
        0,
        int(
            _number(
                days_overdue
            )
        ),
    )

    if overdue >= 30:
        score += 10

    elif overdue >= 15:
        score += 7

    elif overdue > 0:
        score += 4

    return min(
        100.0,
        float(score),
    )


# ============================================================
# DAYS OVERDUE
# ============================================================

def calculate_days_overdue(
    task: MaintenanceTask,
) -> int:

    due_date = _parse_date(
        getattr(
            task,
            "due_date",
            None,
        )
    )

    if due_date is None:
        return 0

    return max(
        0,
        (
            _today() - due_date
        ).days,
    )


# ============================================================
# GET ASSET DEFECTS
# ============================================================

def get_asset_defects(
    db: Session,
    asset_id: int,
) -> List[Defect]:

    return (
        db.query(Defect)
        .filter(
            Defect.asset_id
            == asset_id
        )
        .all()
    )


# ============================================================
# GET ASSET TASKS
# ============================================================

def get_asset_tasks(
    db: Session,
    asset_id: int,
) -> List[MaintenanceTask]:

    return (
        db.query(
            MaintenanceTask
        )
        .filter(
            MaintenanceTask.asset_id
            == asset_id
        )
        .all()
    )


# ============================================================
# RULE-BASED RISK
# ============================================================

def calculate_rule_risk(
    db: Session,
    asset: Asset,
) -> Dict[str, Any]:

    defects = get_asset_defects(
        db,
        asset.asset_id,
    )

    tasks = get_asset_tasks(
        db,
        asset.asset_id,
    )

    closed_statuses = {
        "CLOSED",
        "RESOLVED",
        "COMPLETED",
        "CANCELLED",
    }

    open_defects = [
        defect
        for defect in defects
        if _upper(
            getattr(
                defect,
                "status",
                None,
            )
        )
        not in closed_statuses
    ]

    active_tasks = [
        task
        for task in tasks
        if _upper(
            getattr(
                task,
                "status",
                None,
            )
        )
        not in closed_statuses
    ]

    score = 0.0
    factors: List[str] = []

    criticality = _upper(
        getattr(
            asset,
            "criticality",
            None,
        )
    )

    criticality_scores = {
        "CRITICAL": 35,
        "HIGH": 25,
        "MEDIUM": 15,
        "LOW": 5,
    }

    criticality_score = (
        criticality_scores.get(
            criticality,
            5,
        )
    )

    score += criticality_score

    if criticality:
        factors.append(
            f"Asset criticality: {criticality}"
        )

    # --------------------------------------------------------
    # Defects
    # --------------------------------------------------------

    defect_scores = {
        "CRITICAL": 30,
        "HIGH": 22,
        "MEDIUM": 12,
        "LOW": 5,
    }

    highest_defect_score = 0

    for defect in open_defects:

        severity = _upper(
            getattr(
                defect,
                "severity",
                None,
            )
        )

        highest_defect_score = max(
            highest_defect_score,
            defect_scores.get(
                severity,
                5,
            ),
        )

    if highest_defect_score > 0:

        score += (
            highest_defect_score
        )

        factors.append(
            "Open defect severity contributes "
            f"{highest_defect_score} risk points"
        )

    if len(open_defects) >= 3:

        score += 18

        factors.append(
            f"Multiple open defects: "
            f"{len(open_defects)}"
        )

    elif len(open_defects) == 2:

        score += 12

        factors.append(
            "Multiple open defects detected"
        )

    elif len(open_defects) == 1:

        score += 5

        factors.append(
            "Open defect present"
        )

    # --------------------------------------------------------
    # Active maintenance
    # --------------------------------------------------------

    if len(active_tasks) >= 3:

        score += 15

        factors.append(
            f"High maintenance workload: "
            f"{len(active_tasks)} active tasks"
        )

    elif len(active_tasks) == 2:

        score += 10

        factors.append(
            "Multiple active maintenance tasks"
        )

    elif len(active_tasks) == 1:

        score += 5

        factors.append(
            "Active maintenance task present"
        )

    # --------------------------------------------------------
    # Task severity
    # --------------------------------------------------------

    highest_task_severity = ""

    severity_rank = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    }

    for task in active_tasks:

        severity = _upper(
            getattr(
                task,
                "severity",
                None,
            )
        )

        if severity_rank.get(
            severity,
            0,
        ) > severity_rank.get(
            highest_task_severity,
            0,
        ):

            highest_task_severity = severity

    if (
        highest_task_severity
        == "CRITICAL"
    ):

        score += 20

        factors.append(
            "Critical maintenance task is active"
        )

    elif (
        highest_task_severity
        == "HIGH"
    ):

        score += 12

        factors.append(
            "High-severity maintenance task is active"
        )

    # --------------------------------------------------------
    # Overdue
    # --------------------------------------------------------

    max_days_overdue = 0

    for task in active_tasks:

        max_days_overdue = max(
            max_days_overdue,
            calculate_days_overdue(
                task
            ),
        )

    if max_days_overdue >= 30:

        score += 20

        factors.append(
            f"Maintenance overdue by "
            f"{max_days_overdue} days"
        )

    elif max_days_overdue >= 15:

        score += 12

        factors.append(
            f"Maintenance overdue by "
            f"{max_days_overdue} days"
        )

    elif max_days_overdue > 0:

        score += 7

        factors.append(
            f"Maintenance overdue by "
            f"{max_days_overdue} days"
        )

    return {
        "rule_risk_score": round(
            min(score, 100.0),
            2,
        ),

        "open_defect_count": len(
            open_defects
        ),

        "active_task_count": len(
            active_tasks
        ),

        "max_days_overdue": (
            max_days_overdue
        ),

        "risk_factors": factors,
    }


# ============================================================
# ML PREDICTION
# ============================================================

def _run_ml_prediction(
    db: Session,
    asset: Asset,
) -> Dict[str, Any]:

    try:

        from backend.ml.predict import (
            predict_asset_risk,
        )

        result = predict_asset_risk(
            db=db,
            asset=asset,
        )

        if isinstance(
            result,
            dict,
        ):

            percentage = (
                result.get(
                    "ml_risk_percentage"
                )
            )

            if percentage is None:

                percentage = result.get(
                    "risk_percentage"
                )

            if percentage is None:

                probability = result.get(
                    "ml_risk_probability"
                )

                if probability is not None:

                    percentage = (
                        float(
                            probability
                        )
                        * 100
                    )

            if percentage is not None:

                result[
                    "ml_risk_percentage"
                ] = round(
                    float(
                        percentage
                    ),
                    2,
                )

            result.setdefault(
                "model_available",
                True,
            )

            result.setdefault(
                "ml_prediction_available",
                True,
            )

            return result

    except Exception as exc:

        print(
            "[RiskEngine] ML prediction "
            f"unavailable for asset "
            f"{getattr(asset, 'asset_id', '?')}: "
            f"{exc}"
        )

    return {
        "ml_prediction_available": False,
        "model_available": False,
        "ml_risk_probability": None,
        "ml_risk_percentage": None,
        "ml_risk_level": None,
        "ml_prediction": None,
    }


# ============================================================
# SINGLE ASSET RISK
# ============================================================

def calculate_asset_risk(
    db: Session,
    asset: Asset,
    use_cache: bool = True,
) -> Dict[str, Any]:

    asset_id = int(
        asset.asset_id
    )

    # --------------------------------------------------------
    # Cache lookup
    # --------------------------------------------------------

    if use_cache:

        cached = get_cached_risk(
            asset_id
        )

        if cached is not None:
            return cached

    # --------------------------------------------------------
    # Rule risk
    # --------------------------------------------------------

    rule = calculate_rule_risk(
        db=db,
        asset=asset,
    )

    rule_score = _number(
        rule.get(
            "rule_risk_score"
        )
    )

    rule_level = get_risk_level(
        rule_score
    )

    # --------------------------------------------------------
    # ML
    # --------------------------------------------------------

    ml = _run_ml_prediction(
        db=db,
        asset=asset,
    )

    ml_percentage = ml.get(
        "ml_risk_percentage"
    )

    ml_available = (
        ml_percentage is not None
    )

    ml_score = _number(
        ml_percentage
    )

    if ml_available:

        combined_score = (
            rule_score
            * RULE_RISK_WEIGHT
        ) + (
            ml_score
            * ML_RISK_WEIGHT
        )

        risk_source = (
            "RULE_AND_ML"
        )

    else:

        combined_score = (
            rule_score
        )

        risk_source = "RULE_ONLY"

    combined_score = min(
        100.0,
        max(
            0.0,
            combined_score,
        ),
    )

    combined_level = get_risk_level(
        combined_score
    )

    ml_level = ml.get(
        "ml_risk_level"
    )

    if (
        ml_level is None
        and ml_available
    ):

        ml_level = get_risk_level(
            ml_score
        )

    # --------------------------------------------------------
    # Recommendation
    # --------------------------------------------------------

    if combined_level == "CRITICAL":

        recommendation = (
            "Schedule maintenance immediately "
            "and prioritize a safe operational block."
        )

    elif combined_level == "HIGH":

        recommendation = (
            "Prioritize maintenance in the next "
            "safe available block window."
        )

    elif combined_level == "MEDIUM":

        recommendation = (
            "Plan maintenance proactively while "
            "monitoring asset condition."
        )

    else:

        recommendation = (
            "Continue routine monitoring and "
            "schedule maintenance in a suitable window."
        )

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    result = {

        "asset_id":
            asset.asset_id,

        "asset_code":
            getattr(
                asset,
                "asset_code",
                None,
            ),

        "asset_type":
            getattr(
                asset,
                "asset_type",
                None,
            ),

        "section_id":
            getattr(
                asset,
                "section_id",
                None,
            ),

        "department_id":
            getattr(
                asset,
                "department_id",
                None,
            ),

        "criticality":
            getattr(
                asset,
                "criticality",
                None,
            ),

        # Rule
        "rule_based_risk_score":
            rule_score,

        "rule_based_risk_level":
            rule_level,

        "rule_risk_score":
            rule_score,

        # ML
        "ml_prediction_available":
            ml_available,

        "ml_prediction":
            ml.get(
                "ml_prediction"
            ),

        "ml_risk_probability":
            ml.get(
                "ml_risk_probability"
            ),

        "ml_risk_percentage":
            (
                round(
                    ml_score,
                    2,
                )
                if ml_available
                else None
            ),

        "ml_risk_level":
            ml_level,

        "ml_model_validation_accuracy":
            ml.get(
                "ml_model_validation_accuracy"
            ),

        # Combined
        "combined_risk_score":
            round(
                combined_score,
                2,
            ),

        "combined_risk_level":
            combined_level,

        "risk_score":
            round(
                combined_score,
                2,
            ),

        "risk_level":
            combined_level,

        "risk_source":
            risk_source,

        # Operational
        "open_defect_count":
            rule[
                "open_defect_count"
            ],

        "active_task_count":
            rule[
                "active_task_count"
            ],

        "max_days_overdue":
            rule[
                "max_days_overdue"
            ],

        "risk_factors":
            rule[
                "risk_factors"
            ],

        "recommendation":
            recommendation,

        "model_available":
            bool(
                ml.get(
                    "model_available",
                    False,
                )
            ),
    }

    # --------------------------------------------------------
    # Save cache
    # --------------------------------------------------------

    if use_cache:
        set_cached_risk(
            asset_id,
            result,
        )

    return result


# ============================================================
# ALL ASSET RISKS
# ============================================================

def calculate_all_asset_risks(
    db: Session,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:

    assets = (
        db.query(Asset)
        .order_by(
            Asset.asset_id
        )
        .all()
    )

    results = []

    for asset in assets:

        try:

            results.append(
                calculate_asset_risk(
                    db=db,
                    asset=asset,
                    use_cache=use_cache,
                )
            )

        except Exception as exc:

            print(
                "[RiskEngine] Asset risk failed "
                f"for asset {asset.asset_id}: "
                f"{exc}"
            )

    results.sort(
        key=lambda item:
            _number(
                item.get(
                    "risk_score"
                )
            ),
        reverse=True,
    )

    return results


# ============================================================
# ASSET RISK MAP
# ============================================================

def calculate_asset_risk_map(
    db: Session,
    use_cache: bool = True,
) -> Dict[int, Dict[str, Any]]:

    results = (
        calculate_all_asset_risks(
            db=db,
            use_cache=use_cache,
        )
    )

    return {
        int(
            item[
                "asset_id"
            ]
        ): item
        for item in results
        if item.get(
            "asset_id"
        ) is not None
    }


# ============================================================
# SMART PRIORITY FOR ONE TASK
# ============================================================

def calculate_smart_priority_for_task(
    db: Session,
    task: MaintenanceTask,
    asset_risk: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:

    asset = None

    if task.asset_id is not None:

        asset = (
            db.query(Asset)
            .filter(
                Asset.asset_id
                == task.asset_id
            )
            .first()
        )

    if (
        asset_risk is None
        and asset is not None
    ):

        asset_risk = (
            calculate_asset_risk(
                db=db,
                asset=asset,
            )
        )

    if asset_risk is None:

        asset_risk = {
            "risk_score": 0.0,
            "risk_level": "LOW",
            "ml_risk_percentage": None,
            "ml_risk_level": None,
            "combined_risk_score": 0.0,
        }

    base_priority = (
        get_priority_score(
            task,
            getattr(
                asset,
                "criticality",
                None,
            ),
            calculate_days_overdue(
                task
            ),
        )
    )

    asset_risk_score = _number(
        asset_risk.get(
            "combined_risk_score",
            asset_risk.get(
                "risk_score",
                0,
            ),
        )
    )

    smart_score = (
        base_priority
        * TASK_PRIORITY_WEIGHT
    ) + (
        asset_risk_score
        * ASSET_RISK_WEIGHT
    )

    smart_score = min(
        100.0,
        max(
            0.0,
            smart_score,
        ),
    )

    if smart_score >= 85:
        level = "URGENT"

    elif smart_score >= 70:
        level = "HIGH"

    elif smart_score >= 50:
        level = "MEDIUM"

    else:
        level = "LOW"

    if level == "URGENT":

        recommendation = (
            "Prioritize immediately and "
            "assign the safest available block."
        )

    elif level == "HIGH":

        recommendation = (
            "Schedule in the next safe maintenance window."
        )

    elif level == "MEDIUM":

        recommendation = (
            "Plan proactively while monitoring "
            "operational constraints."
        )

    else:

        recommendation = (
            "Routine monitoring and planned maintenance."
        )

    return {

        "task_id":
            task.task_id,

        "task_code":
            task.task_code,

        "asset_id":
            task.asset_id,

        "section_id":
            task.section_id,

        "task_type":
            getattr(
                task,
                "task_type",
                None,
            ),

        "severity":
            getattr(
                task,
                "severity",
                None,
            ),

        "base_priority_score":
            round(
                base_priority,
                2,
            ),

        "asset_risk_score":
            round(
                asset_risk_score,
                2,
            ),

        "risk_level":
            asset_risk.get(
                "combined_risk_level",
                asset_risk.get(
                    "risk_level",
                    "LOW",
                ),
            ),

        "ml_risk_percentage":
            asset_risk.get(
                "ml_risk_percentage"
            ),

        "ml_risk_level":
            asset_risk.get(
                "ml_risk_level"
            ),

        "combined_risk_score":
            asset_risk.get(
                "combined_risk_score"
            ),

        "smart_priority_score":
            round(
                smart_score,
                2,
            ),

        "smart_priority_level":
            level,

        "days_overdue":
            calculate_days_overdue(
                task
            ),

        "recommendation":
            recommendation,
    }


# ============================================================
# ALL SMART PRIORITIES
# ============================================================

def calculate_all_smart_priorities(
    db: Session,
) -> List[Dict[str, Any]]:

    tasks = (
        db.query(
            MaintenanceTask
        )
        .order_by(
            MaintenanceTask.task_id
        )
        .all()
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Calculate all asset risks ONCE.
    # --------------------------------------------------------

    asset_risks = (
        calculate_asset_risk_map(
            db=db,
        )
    )

    results = []

    for task in tasks:

        status = _upper(
            getattr(
                task,
                "status",
                None,
            )
        )

        if status in {
            "COMPLETED",
            "CANCELLED",
            "CLOSED",
        }:
            continue

        asset_risk = (
            asset_risks.get(
                task.asset_id
            )
        )

        try:

            results.append(
                calculate_smart_priority_for_task(
                    db=db,
                    task=task,
                    asset_risk=asset_risk,
                )
            )

        except Exception as exc:

            print(
                "[RiskEngine] Smart priority "
                f"failed for task {task.task_id}: "
                f"{exc}"
            )

    results.sort(
        key=lambda item: (
            _number(
                item.get(
                    "smart_priority_score"
                )
            ),
            _number(
                item.get(
                    "base_priority_score"
                )
            ),
        ),
        reverse=True,
    )

    return results


# ============================================================
# SINGLE TASK SMART PRIORITY
# ============================================================

def get_task_smart_priority(
    db: Session,
    task: MaintenanceTask,
) -> Dict[str, Any]:

    asset_risk = None

    if task.asset_id is not None:

        asset = (
            db.query(Asset)
            .filter(
                Asset.asset_id
                == task.asset_id
            )
            .first()
        )

        if asset is not None:

            asset_risk = (
                calculate_asset_risk(
                    db=db,
                    asset=asset,
                )
            )

    return calculate_smart_priority_for_task(
        db=db,
        task=task,
        asset_risk=asset_risk,
    )