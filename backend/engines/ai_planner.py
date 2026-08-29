from sqlalchemy.orm import Session

from backend.database.models import MaintenanceTask

from backend.engines.ai_decision_engine import (
    calculate_all_ai_decisions,
)

from backend.engines.risk_engine import (
    calculate_all_smart_priorities,
)


# ============================================================
# AI BEST PLAN SCORE
# ============================================================

def calculate_ai_plan_score(
    ai_decision_score: float,
    optimization_score: float,
) -> float:
    """
    Combine AI decision score with existing block optimization.

    Higher score = better maintenance plan.
    """

    score = (
        ai_decision_score * 0.6
        + optimization_score * 0.4
    )

    return round(
        score,
        2,
    )


# ============================================================
# BUILD AI PLAN CANDIDATE
# ============================================================

def build_ai_plan_candidate(
    decision: dict,
    optimization_score: float,
) -> dict:
    """
    Build one AI maintenance plan candidate.
    """

    ai_plan_score = calculate_ai_plan_score(
        ai_decision_score=decision[
            "ai_decision_score"
        ],
        optimization_score=optimization_score,
    )

    return {
        **decision,
        "optimization_score": optimization_score,
        "ai_plan_score": ai_plan_score,
    }


# ============================================================
# GENERATE AI BEST MAINTENANCE PLAN
# ============================================================

def generate_ai_best_plan(
    db: Session,
) -> dict:
    """
    Generate the best maintenance plan by combining:

        AI decision
        Smart priority
        Asset risk
        Train impact
        Existing optimization

    This is the final Phase 5 intelligence layer.
    """

    # --------------------------------------------------------
    # Get AI decisions
    # --------------------------------------------------------

    ai_decisions = calculate_all_ai_decisions(
        db=db
    )

    if not ai_decisions:
        return {
            "best_plan": None,
            "alternatives": [],
            "message": "No active maintenance tasks available.",
        }

    # --------------------------------------------------------
    # Get smart priorities
    # --------------------------------------------------------

    smart_priorities = (
        calculate_all_smart_priorities(
            db=db
        )
    )

    smart_priority_map = {
        item["task_id"]: item
        for item in smart_priorities
    }

    # --------------------------------------------------------
    # Build candidates
    # --------------------------------------------------------

    candidates = []

    for decision in ai_decisions:

        task_id = decision["task_id"]

        smart_priority = smart_priority_map.get(
            task_id
        )

        # Smart priority is included for explainability
        if smart_priority is not None:
            decision = {
                **decision,
                "smart_priority_score": (
                    smart_priority[
                        "smart_priority_score"
                    ]
                ),
                "smart_priority_level": (
                    smart_priority[
                        "smart_priority_level"
                    ]
                ),
            }

        # ----------------------------------------------------
        # Existing block optimization
        # ----------------------------------------------------

        optimization_score = 0.0

        if decision[
            "train_impact_level"
        ] == "NONE":
            optimization_score = 90.0

        elif decision[
            "train_impact_level"
        ] == "LOW":
            optimization_score = 75.0

        elif decision[
            "train_impact_level"
        ] == "MEDIUM":
            optimization_score = 50.0

        else:
            optimization_score = 20.0

        # ----------------------------------------------------
        # Build final candidate
        # ----------------------------------------------------

        candidate = build_ai_plan_candidate(
            decision=decision,
            optimization_score=optimization_score,
        )

        candidates.append(
            candidate
        )

    # --------------------------------------------------------
    # Rank plans
    # --------------------------------------------------------

    ranked = sorted(
        candidates,
        key=lambda item: (
            item["ai_plan_score"],
            item["ai_decision_score"],
            item["task_id"],
        ),
        reverse=True,
    )

    best_plan = ranked[0]

    alternatives = ranked[1:]

    # --------------------------------------------------------
    # Final recommendation
    # --------------------------------------------------------

    if (
        best_plan["final_action"]
        == "SCHEDULE_IMMEDIATELY"
    ):
        message = (
            "AI recommends immediate maintenance scheduling "
            "for the highest-risk task."
        )

    elif (
        best_plan["final_action"]
        == "RESCHEDULE_TO_SAFE_WINDOW"
    ):
        message = (
            "AI recommends moving the highest-priority "
            "maintenance task to a safer window."
        )

    elif (
        best_plan["final_action"]
        == "RESCHEDULE"
    ):
        message = (
            "AI recommends rescheduling to reduce "
            "train operational impact."
        )

    else:
        message = (
            "AI recommends proactive maintenance planning "
            "based on current asset and operational conditions."
        )

    return {
        "best_plan": best_plan,
        "alternatives": alternatives,
        "total_candidates": len(ranked),
        "recommendation": message,
    }


# ============================================================
# AI PLAN SUMMARY
# ============================================================

def get_ai_plan_summary(
    db: Session,
) -> dict:
    """
    Return a compact summary of the final AI plan.
    """

    result = generate_ai_best_plan(
        db=db
    )

    best = result["best_plan"]

    if best is None:
        return {
            "status": "NO_PLAN",
            "message": result["recommendation"]
            if "recommendation" in result
            else "No maintenance plan available.",
        }

    return {
        "status": "PLAN_AVAILABLE",

        "task_id": best["task_id"],
        "task_code": best["task_code"],

        "asset_id": best["asset_id"],
        "section_id": best["section_id"],

        "ai_plan_score": best[
            "ai_plan_score"
        ],

        "ai_decision_score": best[
            "ai_decision_score"
        ],

        "smart_priority_score": best.get(
            "smart_priority_score"
        ),

        "asset_risk_score": best[
            "asset_risk_score"
        ],

        "train_impact_level": best[
            "train_impact_level"
        ],

        "decision_level": best[
            "decision_level"
        ],

        "final_action": best[
            "final_action"
        ],

        "recommendation": result[
            "recommendation"
        ],
    }