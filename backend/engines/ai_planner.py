from sqlalchemy.orm import Session

from backend.engines.ai_decision_engine import (
    calculate_all_ai_decisions,
)

from backend.engines.risk_engine import (
    calculate_all_smart_priorities,
)


# ============================================================
# PLAN SCORE WEIGHTS
# ============================================================

AI_DECISION_WEIGHT = 0.40
SMART_PRIORITY_WEIGHT = 0.25
ASSET_RISK_WEIGHT = 0.20
OPERATIONAL_SCORE_WEIGHT = 0.15


# ============================================================
# OPERATIONAL / SAFE WINDOW SCORE
# ============================================================

IMPACT_SCORE = {
    "NONE": 100.0,
    "LOW": 80.0,
    "MEDIUM": 50.0,
    "HIGH": 20.0,
}


# ============================================================
# HELPER — SAFE FLOAT
# ============================================================

def safe_float(
    value,
    default: float = 0.0,
) -> float:
    """
    Convert a value safely to float.

    Prevents one malformed/null field from breaking
    the complete AI planning response.
    """

    try:
        if value is None:
            return default

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


# ============================================================
# CALCULATE OPERATIONAL SCORE
# ============================================================

def calculate_operational_score(
    decision: dict,
) -> float:
    """
    Calculate operational suitability of a maintenance plan.

    Factors:
        - Train impact level
        - Conflict count
        - Availability of an alternative window
    """

    impact_level = (
        str(
            decision.get(
                "train_impact_level",
                "NONE",
            )
        )
        .upper()
        .strip()
    )

    score = IMPACT_SCORE.get(
        impact_level,
        50.0,
    )

    # --------------------------------------------------------
    # Conflict penalty
    # --------------------------------------------------------

    conflict_count = safe_float(
        decision.get(
            "conflict_count",
            0,
        )
    )

    if conflict_count > 0:

        score -= min(
            conflict_count * 10.0,
            30.0,
        )

    # --------------------------------------------------------
    # Alternative safe window bonus
    # --------------------------------------------------------

    alternative_start = decision.get(
        "alternative_start_time"
    )

    alternative_end = decision.get(
        "alternative_end_time"
    )

    if (
        alternative_start is not None
        and alternative_end is not None
    ):

        score += 5.0

    return round(
        max(
            min(
                score,
                100.0,
            ),
            0.0,
        ),
        2,
    )


# ============================================================
# CALCULATE FINAL AI PLAN SCORE
# ============================================================

def calculate_ai_plan_score(
    ai_decision_score: float,
    smart_priority_score: float,
    asset_risk_score: float,
    operational_score: float,
) -> float:
    """
    Final AI maintenance planning score.

    Higher score = stronger candidate for planning.

    Components:
        AI Decision       40%
        Smart Priority    25%
        Asset Risk        20%
        Operations        15%
    """

    score = (
        safe_float(
            ai_decision_score
        )
        * AI_DECISION_WEIGHT
        +
        safe_float(
            smart_priority_score
        )
        * SMART_PRIORITY_WEIGHT
        +
        safe_float(
            asset_risk_score
        )
        * ASSET_RISK_WEIGHT
        +
        safe_float(
            operational_score
        )
        * OPERATIONAL_SCORE_WEIGHT
    )

    return round(
        max(
            min(
                score,
                100.0,
            ),
            0.0,
        ),
        2,
    )


# ============================================================
# BUILD ONE AI PLAN CANDIDATE
# ============================================================

def build_ai_plan_candidate(
    decision: dict,
    smart_priority: dict | None,
) -> dict:
    """
    Merge AI decision + smart priority into
    one final maintenance planning candidate.
    """

    smart_priority_score = safe_float(
        (
            smart_priority.get(
                "smart_priority_score",
                0,
            )
            if smart_priority is not None
            else 0
        )
    )

    asset_risk_score = safe_float(
        decision.get(
            "asset_risk_score",
            0,
        )
    )

    ai_decision_score = safe_float(
        decision.get(
            "ai_decision_score",
            0,
        )
    )

    operational_score = (
        calculate_operational_score(
            decision
        )
    )

    ai_plan_score = calculate_ai_plan_score(
        ai_decision_score=ai_decision_score,
        smart_priority_score=smart_priority_score,
        asset_risk_score=asset_risk_score,
        operational_score=operational_score,
    )

    return {
        **decision,

        "smart_priority_score":
            smart_priority_score,

        "smart_priority_level": (
            smart_priority.get(
                "smart_priority_level"
            )
            if smart_priority is not None
            else None
        ),

        "operational_score":
            operational_score,

        "ai_plan_score":
            ai_plan_score,
    }


# ============================================================
# BUILD FINAL RECOMMENDATION MESSAGE
# ============================================================

def build_recommendation_message(
    best_plan: dict,
) -> str:
    """
    Generate a human-readable explanation for
    the top-ranked maintenance plan.
    """

    final_action = (
        best_plan.get(
            "final_action"
        )
    )

    operational_score = safe_float(
        best_plan.get(
            "operational_score",
            0,
        )
    )

    train_impact_level = (
        str(
            best_plan.get(
                "train_impact_level",
                "NONE",
            )
        )
        .upper()
        .strip()
    )

    if final_action == "SCHEDULE_IMMEDIATELY":

        if train_impact_level in {
            "NONE",
            "LOW",
        }:

            return (
                "AI recommends immediate maintenance "
                "attention for the highest-risk task "
                "within the safest available operational window."
            )

        return (
            "AI identifies the task as high priority "
            "but recommends execution only within a "
            "safe operational window to control train impact."
        )

    if final_action == "RESCHEDULE_TO_SAFE_WINDOW":

        return (
            "AI recommends moving the highest-priority "
            "maintenance task to a safer window to "
            "reduce train operational impact."
        )

    if final_action == "RESCHEDULE":

        return (
            "AI recommends rescheduling the maintenance "
            "block because of train operational impact."
        )

    if final_action == "PRIORITIZE_MAINTENANCE":

        return (
            "AI recommends prioritizing this maintenance "
            "task because of elevated combined asset risk."
        )

    if final_action == "SCHEDULE_NEXT_SAFE_WINDOW":

        return (
            "AI recommends scheduling this maintenance "
            "task in the next safe operational window."
        )

    if final_action == "PLAN_PROACTIVELY":

        return (
            "AI recommends proactive maintenance planning "
            "based on current risk and operational conditions."
        )

    if final_action == "ROUTINE_MONITORING":

        return (
            "AI recommends routine monitoring because "
            "current maintenance risk and operational "
            "impact are relatively low."
        )

    if operational_score >= 80:

        return (
            "AI recommends proactive maintenance planning "
            "in a favorable operational window."
        )

    return (
        "AI recommends the best available maintenance "
        "plan based on current risk and operational conditions."
    )


# ============================================================
# GENERATE AI BEST MAINTENANCE PLAN
# ============================================================

def generate_ai_best_plan(
    db: Session,
) -> dict:
    """
    Generate the best maintenance plan by combining:

        - AI decision score
        - Smart priority
        - Rule-based risk
        - ML risk
        - Combined asset risk
        - Train impact
        - Operational suitability
        - Safe-window recommendation
    """

    # ========================================================
    # 1. CALCULATE AI DECISIONS
    # ========================================================

    ai_decisions = (
        calculate_all_ai_decisions(
            db=db
        )
    )

    if not ai_decisions:

        return {
            "best_plan": None,
            "alternatives": [],
            "total_candidates": 0,
            "planning_method": (
                "AI Decision + Smart Priority + "
                "Combined ML Risk + Operational Impact"
            ),
            "weights": {
                "ai_decision":
                    AI_DECISION_WEIGHT,

                "smart_priority":
                    SMART_PRIORITY_WEIGHT,

                "asset_risk":
                    ASSET_RISK_WEIGHT,

                "operational":
                    OPERATIONAL_SCORE_WEIGHT,
            },
            "recommendation": (
                "No active maintenance tasks available."
            ),
        }

    # ========================================================
    # 2. CALCULATE SMART PRIORITIES
    # ========================================================

    smart_priorities = (
        calculate_all_smart_priorities(
            db=db
        )
    )

    # O(1) task lookup
    smart_priority_map = {
        item.get(
            "task_id"
        ): item
        for item in smart_priorities
        if item.get(
            "task_id"
        ) is not None
    }

    # ========================================================
    # 3. BUILD PLAN CANDIDATES
    # ========================================================

    candidates = []

    for decision in ai_decisions:

        if not isinstance(
            decision,
            dict,
        ):
            continue

        task_id = decision.get(
            "task_id"
        )

        if task_id is None:
            continue

        smart_priority = (
            smart_priority_map.get(
                task_id
            )
        )

        candidate = build_ai_plan_candidate(
            decision=decision,
            smart_priority=smart_priority,
        )

        candidates.append(
            candidate
        )

    # ========================================================
    # NO VALID CANDIDATES
    # ========================================================

    if not candidates:

        return {
            "best_plan": None,
            "alternatives": [],
            "total_candidates": 0,
            "planning_method": (
                "AI Decision + Smart Priority + "
                "Combined ML Risk + Operational Impact"
            ),
            "weights": {
                "ai_decision":
                    AI_DECISION_WEIGHT,

                "smart_priority":
                    SMART_PRIORITY_WEIGHT,

                "asset_risk":
                    ASSET_RISK_WEIGHT,

                "operational":
                    OPERATIONAL_SCORE_WEIGHT,
            },
            "recommendation": (
                "No valid AI maintenance planning "
                "candidates were generated."
            ),
        }

    # ========================================================
    # 4. RANK CANDIDATES
    # ========================================================

    ranked = sorted(
        candidates,

        key=lambda item: (
            safe_float(
                item.get(
                    "ai_plan_score"
                )
            ),

            safe_float(
                item.get(
                    "ai_decision_score"
                )
            ),

            safe_float(
                item.get(
                    "smart_priority_score"
                )
            ),

            safe_float(
                item.get(
                    "asset_risk_score"
                )
            ),

            safe_float(
                item.get(
                    "operational_score"
                )
            ),

            safe_float(
                item.get(
                    "task_id"
                )
            ),
        ),

        reverse=True,
    )

    best_plan = ranked[0]

    alternatives = ranked[1:]

    # ========================================================
    # 5. FINAL RECOMMENDATION
    # ========================================================

    message = build_recommendation_message(
        best_plan
    )

    # ========================================================
    # 6. RETURN
    # ========================================================

    return {
        "best_plan":
            best_plan,

        "alternatives":
            alternatives,

        "total_candidates":
            len(ranked),

        "planning_method": (
            "AI Decision + Smart Priority + "
            "Combined ML Risk + Operational Impact"
        ),

        "weights": {
            "ai_decision":
                AI_DECISION_WEIGHT,

            "smart_priority":
                SMART_PRIORITY_WEIGHT,

            "asset_risk":
                ASSET_RISK_WEIGHT,

            "operational":
                OPERATIONAL_SCORE_WEIGHT,
        },

        "recommendation":
            message,
    }


# ============================================================
# COMPACT PLAN SUMMARY
# ============================================================

def get_ai_plan_summary(
    db: Session,
) -> dict:
    """
    Return a compact summary of the current
    best AI maintenance plan.

    This function intentionally derives its result
    from generate_ai_best_plan() so that the scoring
    logic remains in one place.
    """

    result = generate_ai_best_plan(
        db=db
    )

    best = result.get(
        "best_plan"
    )

    if best is None:

        return {
            "status":
                "NO_PLAN",

            "message":
                (
                    result.get(
                        "recommendation"
                    )
                    or
                    "No maintenance plan available."
                ),
        }

    return {
        "status":
            "PLAN_AVAILABLE",

        "task_id":
            best.get(
                "task_id"
            ),

        "task_code":
            best.get(
                "task_code"
            ),

        "asset_id":
            best.get(
                "asset_id"
            ),

        "section_id":
            best.get(
                "section_id"
            ),

        # ----------------------------------------------------
        # FINAL PLAN SCORE
        # ----------------------------------------------------

        "ai_plan_score":
            best.get(
                "ai_plan_score"
            ),

        # ----------------------------------------------------
        # AI DECISION
        # ----------------------------------------------------

        "ai_decision_score":
            best.get(
                "ai_decision_score"
            ),

        "decision_level":
            best.get(
                "decision_level"
            ),

        "final_action":
            best.get(
                "final_action"
            ),

        # ----------------------------------------------------
        # SMART PRIORITY
        # ----------------------------------------------------

        "smart_priority_score":
            best.get(
                "smart_priority_score"
            ),

        "smart_priority_level":
            best.get(
                "smart_priority_level"
            ),

        # ----------------------------------------------------
        # RULE + ML + COMBINED RISK
        # ----------------------------------------------------

        "rule_based_risk_score":
            best.get(
                "rule_based_risk_score"
            ),

        "ml_risk_percentage":
            best.get(
                "ml_risk_percentage"
            ),

        "ml_risk_level":
            best.get(
                "ml_risk_level"
            ),

        "asset_risk_score":
            best.get(
                "asset_risk_score"
            ),

        "combined_risk_score":
            best.get(
                "combined_risk_score"
            ),

        "combined_risk_level":
            best.get(
                "combined_risk_level"
            ),

        # ----------------------------------------------------
        # OPERATIONAL PLANNING
        # ----------------------------------------------------

        "train_impact_level":
            best.get(
                "train_impact_level"
            ),

        "conflict_count":
            best.get(
                "conflict_count",
                0,
            ),

        "affected_train_ids":
            best.get(
                "affected_train_ids",
                [],
            ),

        "operational_score":
            best.get(
                "operational_score"
            ),

        "alternative_start_time":
            best.get(
                "alternative_start_time"
            ),

        "alternative_end_time":
            best.get(
                "alternative_end_time"
            ),

        # ----------------------------------------------------
        # FINAL RECOMMENDATION
        # ----------------------------------------------------

        "recommendation":
            result.get(
                "recommendation"
            ),
    }