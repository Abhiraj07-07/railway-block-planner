from datetime import date

from sqlalchemy.orm import Session

from backend.database.models import (
    Asset,
    Defect,
    MaintenanceTask,
)


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


FEATURE_NAMES = [
    "asset_age_years",
    "criticality_score",
    "open_defect_count",
    "highest_defect_severity",
    "active_task_count",
    "highest_task_severity",
    "days_overdue",
    "total_task_duration",
]


def calculate_asset_age(
    installation_date,
    reference_date: date | None = None,
) -> int:
    """
    Calculate asset age in years.

    Missing installation date is handled safely.
    """

    if installation_date is None:
        return 0

    if reference_date is None:
        reference_date = date.today()

    age = (
        reference_date.year
        - installation_date.year
    )

    if (
        (
            reference_date.month,
            reference_date.day,
        )
        <
        (
            installation_date.month,
            installation_date.day,
        )
    ):
        age -= 1

    return max(
        age,
        0,
    )


def get_asset_features(
    db: Session,
    asset: Asset,
    reference_date: date | None = None,
) -> dict:
    """
    Convert the current database state of one asset
    into ML-compatible features.
    """

    if reference_date is None:
        reference_date = date.today()

    # ========================================================
    # 1. ASSET AGE
    # ========================================================

    asset_age_years = calculate_asset_age(
        asset.installation_date,
        reference_date=reference_date,
    )

    # ========================================================
    # 2. CRITICALITY
    # ========================================================

    criticality = (
        asset.criticality or "LOW"
    ).upper()

    criticality_score = (
        CRITICALITY_SCORE.get(
            criticality,
            10,
        )
    )

    # ========================================================
    # 3. OPEN DEFECTS
    # ========================================================

    open_defects = (
        db.query(Defect)
        .filter(
            Defect.asset_id == asset.asset_id,
            Defect.status == "OPEN",
        )
        .all()
    )

    highest_defect_score = 0

    for defect in open_defects:

        severity = (
            defect.severity or "LOW"
        ).upper()

        score = (
            SEVERITY_SCORE.get(
                severity,
                5,
            )
        )

        highest_defect_score = max(
            highest_defect_score,
            score,
        )

    # ========================================================
    # 4. ACTIVE MAINTENANCE TASKS
    # ========================================================

    active_tasks = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.asset_id
            == asset.asset_id,
            MaintenanceTask.status.notin_(
                [
                    "COMPLETED",
                    "CANCELLED",
                ]
            ),
        )
        .all()
    )

    highest_task_score = 0

    total_task_duration = 0.0

    maximum_overdue_days = 0

    for task in active_tasks:

        severity = (
            task.severity or "LOW"
        ).upper()

        score = (
            SEVERITY_SCORE.get(
                severity,
                5,
            )
        )

        highest_task_score = max(
            highest_task_score,
            score,
        )

        # ----------------------------------------------------
        # Duration
        # ----------------------------------------------------

        if task.duration_hours is not None:

            total_task_duration += float(
                task.duration_hours
            )

        # ----------------------------------------------------
        # Overdue days
        # ----------------------------------------------------

        if task.due_date is not None:

            overdue_days = (
                reference_date
                - task.due_date
            ).days

            maximum_overdue_days = max(
                maximum_overdue_days,
                max(
                    overdue_days,
                    0,
                ),
            )

    # ========================================================
    # 5. RETURN ML FEATURES
    # ========================================================

    return {
        "asset_age_years": (
            asset_age_years
        ),

        "criticality_score": (
            criticality_score
        ),

        "open_defect_count": (
            len(open_defects)
        ),

        "highest_defect_severity": (
            highest_defect_score
        ),

        "active_task_count": (
            len(active_tasks)
        ),

        "highest_task_severity": (
            highest_task_score
        ),

        "days_overdue": (
            maximum_overdue_days
        ),

        "total_task_duration": round(
            total_task_duration,
            2,
        ),
    }


def features_to_vector(
    features: dict,
) -> list[float]:
    """
    Convert feature dictionary into model input vector.
    """

    missing_features = [
        name
        for name in FEATURE_NAMES
        if name not in features
    ]

    if missing_features:
        raise ValueError(
            "Missing ML features: "
            + ", ".join(
                missing_features
            )
        )

    return [
        float(
            features[name]
        )
        for name in FEATURE_NAMES
    ]