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

    Decision combines:

        1. Existing maintenance task priority
        2. Rule-based asset risk
        3. ML predicted asset risk
        4. Combined asset risk
        5. Train operational impact
        6. Current block recommendation

    ML is an additional decision signal.
    Existing rule-based risk remains the safety fallback.
    """

    # ========================================================
    # 1. EXISTING TASK PRIORITY
    # ========================================================

    priority = calculate_task_priority(
        db=db,
        task=task,
    )

    base_priority_score = float(
        priority["priority_score"]
    )

    # ========================================================
    # 2. ASSET
    # ========================================================

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

    # ========================================================
    # 3. ASSET RISK
    # ========================================================

    risk = calculate_asset_risk(
        db=db,
        asset=asset,
    )

    # --------------------------------------------------------
    # Rule-based risk
    # --------------------------------------------------------

    rule_based_risk_score = float(
        risk.get(
            "rule_based_risk_score",
            risk.get(
                "risk_score",
                0,
            ),
        )
    )

    rule_based_risk_level = risk.get(
        "rule_based_risk_level",
        risk.get(
            "risk_level",
            "LOW",
        ),
    )

    # --------------------------------------------------------
    # ML risk
    # --------------------------------------------------------

    ml_prediction_available = bool(
        risk.get(
            "ml_prediction_available",
            False,
        )
    )

    ml_risk_percentage = risk.get(
        "ml_risk_percentage"
    )

    ml_risk_probability = risk.get(
        "ml_risk_probability"
    )

    ml_risk_level = risk.get(
        "ml_risk_level"
    )

    ml_prediction = risk.get(
        "ml_prediction"
    )

    ml_model_validation_accuracy = risk.get(
        "ml_model_validation_accuracy"
    )

    # --------------------------------------------------------
    # Combined risk
    # --------------------------------------------------------

    asset_risk_score = float(
        risk.get(
            "combined_risk_score",
            risk.get(
                "risk_score",
                0,
            ),
        )
    )

    combined_risk_level = risk.get(
        "combined_risk_level",
        risk.get(
            "risk_level",
            "LOW",
        ),
    )

    # ========================================================
    # 4. FIND RELATED BLOCK
    # ========================================================

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

    # ========================================================
    # 5. TRAIN IMPACT
    # ========================================================

    if block is not None:

        recommendation = recommend_reschedule(
            db=db,
            block=block,
        )

        impact_level = recommendation.get(
            "impact_level",
            "NONE",
        )

        impact_score = IMPACT_SCORE.get(
            impact_level,
            50,
        )

        recommended_action = recommendation.get(
            "recommended_action",
            "SCHEDULE",
        )

        alternative_start_time = recommendation.get(
            "alternative_start_time"
        )

        alternative_end_time = recommendation.get(
            "alternative_end_time"
        )

        conflict_count = recommendation.get(
            "conflict_count",
            0,
        )

        affected_train_ids = recommendation.get(
            "affected_train_ids",
            [],
        )

    else:

        impact_level = "NONE"

        impact_score = IMPACT_SCORE["NONE"]

        recommended_action = "SCHEDULE"

        alternative_start_time = None
        alternative_end_time = None

        conflict_count = 0
        affected_train_ids = []

    # ========================================================
    # 6. AI DECISION SCORE
    # ========================================================

    ai_decision_score = round(
        (
            base_priority_score
            * SMART_PRIORITY_WEIGHT
        )
        +
        (
            asset_risk_score
            * ASSET_RISK_WEIGHT
        )
        +
        (
            impact_score
            * TRAIN_IMPACT_WEIGHT
        ),
        2,
    )

    # ========================================================
    # 7. FINAL AI ACTION
    # ========================================================

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

    # ========================================================
    # 8. EXPLAINABLE DECISION REASONS
    # ========================================================

    decision_reasons = []

    # --------------------------------------------------------
    # Task priority
    # --------------------------------------------------------

    if base_priority_score >= 80:

        decision_reasons.append(
            "High maintenance task priority"
        )

    elif base_priority_score >= 60:

        decision_reasons.append(
            "Moderate maintenance task priority"
        )

    # --------------------------------------------------------
    # Rule-based risk
    # --------------------------------------------------------

    if rule_based_risk_score >= 80:

        decision_reasons.append(
            "Critical rule-based asset risk detected"
        )

    elif rule_based_risk_score >= 60:

        decision_reasons.append(
            "High rule-based asset risk detected"
        )

    # --------------------------------------------------------
    # ML risk
    # --------------------------------------------------------

    if (
        ml_prediction_available
        and ml_risk_percentage is not None
    ):

        if ml_risk_percentage >= 80:

            decision_reasons.append(
                (
                    "ML model predicts very high "
                    f"asset risk ({ml_risk_percentage}%)"
                )
            )

        elif ml_risk_percentage >= 60:

            decision_reasons.append(
                (
                    "ML model predicts elevated "
                    f"asset risk ({ml_risk_percentage}%)"
                )
            )

        elif ml_risk_percentage >= 35:

            decision_reasons.append(
                (
                    "ML model indicates moderate "
                    f"asset risk ({ml_risk_percentage}%)"
                )
            )

    # --------------------------------------------------------
    # Train impact
    # --------------------------------------------------------

    if impact_level == "HIGH":

        decision_reasons.append(
            "High train operational impact"
        )

    elif impact_level == "MEDIUM":

        decision_reasons.append(
            "Moderate train operational impact"
        )

    elif impact_level == "LOW":

        decision_reasons.append(
            "Low train operational impact"
        )

    # --------------------------------------------------------
    # Fallback explanation
    # --------------------------------------------------------

    if not decision_reasons:

        decision_reasons.append(
            "No major operational risk detected"
        )

    # ========================================================
    # 9. FINAL RECOMMENDATION TEXT
    # ========================================================

    if final_action == "SCHEDULE_IMMEDIATELY":

        recommendation_text = (
            "AI recommends immediate scheduling "
            "because the combined asset risk is high "
            "and train impact is manageable."
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
            "because the asset has elevated combined risk."
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

    # ========================================================
    # 10. RETURN
    # ========================================================

    return {
        # ----------------------------------------------------
        # Task
        # ----------------------------------------------------

        "task_id": task.task_id,
        "task_code": task.task_code,

        "asset_id": task.asset_id,
        "section_id": task.section_id,

        # ----------------------------------------------------
        # Priority
        # ----------------------------------------------------

        "base_priority_score": round(
            base_priority_score,
            2,
        ),

        # ----------------------------------------------------
        # Rule-based risk
        # ----------------------------------------------------

        "rule_based_risk_score": round(
            rule_based_risk_score,
            2,
        ),

        "rule_based_risk_level": (
            rule_based_risk_level
        ),

        # ----------------------------------------------------
        # ML risk
        # ----------------------------------------------------

        "ml_prediction_available": (
            ml_prediction_available
        ),

        "ml_prediction": ml_prediction,

        "ml_risk_probability": (
            ml_risk_probability
        ),

        "ml_risk_percentage": (
            ml_risk_percentage
        ),

        "ml_risk_level": (
            ml_risk_level
        ),

        "ml_model_validation_accuracy": (
            ml_model_validation_accuracy
        ),

        # ----------------------------------------------------
        # Combined risk
        # ----------------------------------------------------

        "asset_risk_score": round(
            asset_risk_score,
            2,
        ),

        "combined_risk_score": round(
            asset_risk_score,
            2,
        ),

        "combined_risk_level": (
            combined_risk_level
        ),

        # ----------------------------------------------------
        # Train impact
        # ----------------------------------------------------

        "train_impact_level": impact_level,

        "train_impact_score": impact_score,

        "conflict_count": conflict_count,

        "affected_train_ids": (
            affected_train_ids
        ),

        # ----------------------------------------------------
        # AI decision
        # ----------------------------------------------------

        "ai_decision_score": (
            ai_decision_score
        ),

        "decision_level": decision_level,

        "final_action": final_action,

        "recommended_action": (
            recommended_action
        ),

        # ----------------------------------------------------
        # Recommended safe window
        # ----------------------------------------------------

        "alternative_start_time": (
            alternative_start_time
        ),

        "alternative_end_time": (
            alternative_end_time
        ),

        # ----------------------------------------------------
        # Explainability
        # ----------------------------------------------------

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

    Results are ranked by AI decision score.
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

        results.append(
            result
        )

    return sorted(
        results,
        key=lambda item: (
            item[
                "ai_decision_score"
            ],
            item["task_id"],
        ),
        reverse=True,
    )