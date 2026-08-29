from sqlalchemy.orm import Session

from backend.database.models import (
    MaintenanceTask,
    Asset,
    Block,
    BlockTask,
)

from backend.engines.priority_engine import (
    calculate_task_priority,
)

from backend.engines.risk_engine import (
    calculate_asset_risk,
)

from backend.engines.optimization_engine import (
    recommend_reschedule,
)


# ============================================================
# AI DECISION WEIGHTS
# ============================================================

SMART_PRIORITY_WEIGHT = 0.40
ASSET_RISK_WEIGHT = 0.35
TRAIN_IMPACT_WEIGHT = 0.25


# ============================================================
# IMPACT SCORE
# ============================================================

IMPACT_SCORE = {
    "NONE": 100,
    "LOW": 75,
    "MEDIUM": 50,
    "HIGH": 20,
}


# ============================================================
# AI DECISION FOR ONE TASK
# ============================================================

def calculate_ai_decision(
    db: Session,
    task: MaintenanceTask,
) -> dict:
    """
    Generate an explainable AI-assisted maintenance decision.

    Combines:
        - Existing maintenance priority
        - Asset risk
        - Train impact
        - Current block recommendation
    """

    # --------------------------------------------------------
    # 1. Existing task priority
    # --------------------------------------------------------

    priority = calculate_task_priority(
        db=db,
        task=task,
    )

    base_priority_score = priority[
        "priority_score"
    ]

    # --------------------------------------------------------
    # 2. Asset risk
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

    asset_risk_score = risk[
        "risk_score"
    ]

    # --------------------------------------------------------
    # 3. Find related maintenance block
    # --------------------------------------------------------

    block = (
        db.query(Block)
        .join(
            Block.block_tasks
        )
        .filter(
            BlockTask.task_id == task.task_id
        )
        .first()
    )

    # --------------------------------------------------------
    # 4. Calculate train impact
    # --------------------------------------------------------

    if block is not None:

        recommendation = recommend_reschedule(
            db=db,
            block=block,
        )

        impact_level = recommendation[
            "impact_level"
        ]

        impact_score = IMPACT_SCORE.get(
            impact_level,
            50,
        )

        recommended_action = recommendation[
            "recommended_action"
        ]

        alternative_start_time = recommendation[
            "alternative_start_time"
        ]

        alternative_end_time = recommendation[
            "alternative_end_time"
        ]

        conflict_count = recommendation[
            "conflict_count"
        ]

        affected_train_ids = recommendation[
            "affected_train_ids"
        ]

    else:

        impact_level = "NONE"

        impact_score = IMPACT_SCORE[
            "NONE"
        ]

        recommended_action = "SCHEDULE"

        alternative_start_time = None
        alternative_end_time = None

        conflict_count = 0
        affected_train_ids = []

    # --------------------------------------------------------
    # 5. AI decision score
    # --------------------------------------------------------

    ai_decision_score = round(
        (
            base_priority_score
            * SMART_PRIORITY_WEIGHT
        )
        + (
            asset_risk_score
            * ASSET_RISK_WEIGHT
        )
        + (
            impact_score
            * TRAIN_IMPACT_WEIGHT
        ),
        2,
    )

    # --------------------------------------------------------
    # 6. Final AI action
    # --------------------------------------------------------

    if (
        asset_risk_score >= 80
        and impact_level in {
            "NONE",
            "LOW",
        }
    ):
        final_action = (
            "SCHEDULE_IMMEDIATELY"
        )

        decision_level = "URGENT"

    elif (
        asset_risk_score >= 80
        and impact_level in {
            "MEDIUM",
            "HIGH",
        }
    ):
        final_action = (
            "RESCHEDULE_TO_SAFE_WINDOW"
        )

        decision_level = "URGENT"

    elif (
        base_priority_score >= 80
        and impact_level == "NONE"
    ):
        final_action = (
            "SCHEDULE_NEXT_SAFE_WINDOW"
        )

        decision_level = "HIGH"

    elif impact_level == "HIGH":

        final_action = (
            "RESCHEDULE"
        )

        decision_level = "HIGH"

    elif asset_risk_score >= 60:

        final_action = (
            "PRIORITIZE_MAINTENANCE"
        )

        decision_level = "HIGH"

    elif ai_decision_score >= 50:

        final_action = (
            "PLAN_PROACTIVELY"
        )

        decision_level = "MEDIUM"

    else:

        final_action = (
            "ROUTINE_MONITORING"
        )

        decision_level = "LOW"

    # --------------------------------------------------------
    # 7. Explainable decision
    # --------------------------------------------------------

    decision_reasons = []

    if base_priority_score >= 80:
        decision_reasons.append(
            "High maintenance task priority"
        )

    if asset_risk_score >= 80:
        decision_reasons.append(
            "Critical asset risk detected"
        )

    elif asset_risk_score >= 60:
        decision_reasons.append(
            "High asset risk detected"
        )

    if impact_level == "HIGH":
        decision_reasons.append(
            "High train operational impact"
        )

    elif impact_level == "MEDIUM":
        decision_reasons.append(
            "Moderate train operational impact"
        )

    if not decision_reasons:
        decision_reasons.append(
            "No major operational risk detected"
        )

    # --------------------------------------------------------
    # 8. Final recommendation text
    # --------------------------------------------------------

    if final_action == "SCHEDULE_IMMEDIATELY":

        recommendation_text = (
            "AI recommends immediate scheduling "
            "because the asset risk is high and "
            "train impact is manageable."
        )

    elif final_action == "RESCHEDULE_TO_SAFE_WINDOW":

        recommendation_text = (
            "AI recommends moving maintenance to "
            "a safer window because asset risk is high "
            "and current train impact is significant."
        )

    elif final_action == "RESCHEDULE":

        recommendation_text = (
            "AI recommends rescheduling the maintenance "
            "block to reduce train disruption."
        )

    elif final_action == "PRIORITIZE_MAINTENANCE":

        recommendation_text = (
            "AI recommends prioritizing this task "
            "because the asset has elevated risk."
        )

    elif final_action == "PLAN_PROACTIVELY":

        recommendation_text = (
            "AI recommends proactive maintenance planning."
        )

    else:

        recommendation_text = (
            "AI recommends routine monitoring "
            "and normal maintenance scheduling."
        )

    return {
        "task_id": task.task_id,
        "task_code": task.task_code,

        "asset_id": task.asset_id,
        "section_id": task.section_id,

        "base_priority_score": base_priority_score,

        "asset_risk_score": asset_risk_score,
        "risk_level": risk["risk_level"],

        "train_impact_level": impact_level,
        "train_impact_score": impact_score,

        "ai_decision_score": ai_decision_score,
        "decision_level": decision_level,

        "final_action": final_action,

        "recommended_action": recommended_action,

        "conflict_count": conflict_count,

        "affected_train_ids": (
            affected_train_ids
        ),

        "alternative_start_time": (
            alternative_start_time
        ),

        "alternative_end_time": (
            alternative_end_time
        ),

        "decision_reasons": (
            decision_reasons
        ),

        "recommendation": (
            recommendation_text
        ),
    }


# ============================================================
# AI DECISION FOR ALL ACTIVE TASKS
# ============================================================

def calculate_all_ai_decisions(
    db: Session,
) -> list[dict]:
    """
    Generate AI-assisted maintenance decisions
    for all active tasks.
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

    results = []

    for task in tasks:

        result = calculate_ai_decision(
            db=db,
            task=task,
        )

        results.append(result)

    return sorted(
        results,
        key=lambda item: (
            item["ai_decision_score"],
            item["task_id"],
        ),
        reverse=True,
    )