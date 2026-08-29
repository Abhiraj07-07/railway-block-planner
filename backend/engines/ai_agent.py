from sqlalchemy.orm import Session

from backend.database.models import (
    OperationalEvent,
    Asset,
)

from backend.engines.risk_engine import (
    calculate_asset_risk,
    calculate_all_smart_priorities,
)

from backend.engines.ai_decision_engine import (
    calculate_all_ai_decisions,
)

from backend.engines.ai_planner import (
    generate_ai_best_plan,
)

from backend.engines.optimization_engine import (
    analyze_all_blocks,
    recommend_rescheduling_for_all_blocks,
)


# ============================================================
# AI OPERATIONS AGENT
# ============================================================

def run_ai_operations_agent(
    db: Session,
) -> dict:
    """
    Run the Railway AI Operations Agent.

    The agent combines:
        - Operational events
        - Asset risk
        - Smart maintenance priority
        - AI maintenance decisions
        - AI best plan
        - Block impact
        - Rescheduling recommendations

    The agent does NOT directly apply critical operational
    changes. It produces recommendations and explanations.
    """

    # --------------------------------------------------------
    # 1. READ ALL OPERATIONAL EVENTS
    # --------------------------------------------------------

    all_events = (
        db.query(OperationalEvent)
        .order_by(
            OperationalEvent.created_at.desc()
        )
        .all()
    )

    # Only OPEN events affect current operational status.
    open_events = [
        event
        for event in all_events
        if event.status == "OPEN"
    ]

    # --------------------------------------------------------
    # 2. GET ASSET RISKS
    # --------------------------------------------------------

    assets = (
        db.query(Asset)
        .order_by(Asset.asset_id)
        .all()
    )

    asset_risks = []

    for asset in assets:
        asset_risks.append(
            calculate_asset_risk(
                db=db,
                asset=asset,
            )
        )

    # --------------------------------------------------------
    # 3. SMART PRIORITY
    # --------------------------------------------------------

    smart_priorities = calculate_all_smart_priorities(
        db=db
    )

    # --------------------------------------------------------
    # 4. AI DECISIONS
    # --------------------------------------------------------

    ai_decisions = calculate_all_ai_decisions(
        db=db
    )

    # --------------------------------------------------------
    # 5. AI BEST PLAN
    # --------------------------------------------------------

    best_plan_result = generate_ai_best_plan(
        db=db
    )

    best_plan = best_plan_result.get(
        "best_plan"
    )

    # --------------------------------------------------------
    # 6. BLOCK IMPACT
    # --------------------------------------------------------

    block_impacts = analyze_all_blocks(
        db=db
    )

    # --------------------------------------------------------
    # 7. RESCHEDULING RECOMMENDATIONS
    # --------------------------------------------------------

    rescheduling = recommend_rescheduling_for_all_blocks(
        db=db
    )

    # --------------------------------------------------------
    # AGENT ANALYSIS
    # --------------------------------------------------------

    alerts = []
    recommendations = []
    agent_actions = []

    # ========================================================
    # BUILD ALERT LIST FROM ALL EVENTS
    # ========================================================
    # IMPORTANT:
    # We keep resolved events visible for the frontend so that
    # the Action Center can show "RESOLVED".
    #
    # Only OPEN events are used for active recommendations.
    # ========================================================

    for event in all_events:

        event_info = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "severity": event.severity,
            "section_id": event.section_id,
            "asset_id": event.asset_id,
            "train_id": event.train_id,
            "delay_minutes": event.delay_minutes,
            "description": event.description,
            "status": event.status,
        }

        alerts.append(event_info)

    # ========================================================
    # ANALYZE ONLY OPEN OPERATIONAL EVENTS
    # ========================================================

    for event in open_events:

        # ----------------------------------------------------
        # CRITICAL EVENT
        # ----------------------------------------------------

        if event.severity == "CRITICAL":

            recommendations.append(
                {
                    "type": "CRITICAL_EVENT",
                    "event_id": event.event_id,
                    "priority": "URGENT",
                    "message": (
                        "Critical operational event detected. "
                        "Immediate maintenance and operational "
                        "review is recommended."
                    ),
                }
            )

            agent_actions.append(
                "Escalate critical operational event."
            )

        # ----------------------------------------------------
        # TRAIN DELAY
        # ----------------------------------------------------

        elif event.event_type == "TRAIN_DELAY":

            recommendations.append(
                {
                    "type": "TRAIN_DELAY",
                    "event_id": event.event_id,
                    "priority": "HIGH",
                    "message": (
                        "Train delay detected. "
                        "Re-evaluate affected maintenance "
                        "blocks and train conflicts."
                    ),
                }
            )

            agent_actions.append(
                "Analyze train impact and maintenance conflicts."
            )

        # ----------------------------------------------------
        # DEFECT
        # ----------------------------------------------------

        elif event.event_type == "DEFECT":

            recommendations.append(
                {
                    "type": "DEFECT",
                    "event_id": event.event_id,
                    "priority": "HIGH",
                    "message": (
                        "New asset defect detected. "
                        "Recalculate asset risk and "
                        "maintenance priority."
                    ),
                }
            )

            agent_actions.append(
                "Recalculate asset risk and maintenance priority."
            )

        # ----------------------------------------------------
        # BLOCK CHANGE
        # ----------------------------------------------------

        elif event.event_type == "BLOCK_CHANGE":

            recommendations.append(
                {
                    "type": "BLOCK_CHANGE",
                    "event_id": event.event_id,
                    "priority": "HIGH",
                    "message": (
                        "Maintenance block change detected. "
                        "Review the affected maintenance plan "
                        "and operational impact."
                    ),
                }
            )

            agent_actions.append(
                "Review block timing and operational impact."
            )

    # ========================================================
    # ANALYZE CRITICAL ASSETS
    # ========================================================

    critical_assets = [
        item
        for item in asset_risks
        if item["risk_level"] == "CRITICAL"
    ]

    if critical_assets:

        recommendations.append(
            {
                "type": "ASSET_RISK",
                "priority": "URGENT",
                "message": (
                    f"{len(critical_assets)} critical-risk "
                    "asset(s) detected."
                ),
                "asset_ids": [
                    item["asset_id"]
                    for item in critical_assets
                ],
            }
        )

        agent_actions.append(
            "Prioritize maintenance on critical-risk assets."
        )

    # ========================================================
    # ANALYZE URGENT AI DECISIONS
    # ========================================================

    urgent_decisions = [
        item
        for item in ai_decisions
        if item["decision_level"] == "URGENT"
    ]

    if urgent_decisions:

        recommendations.append(
            {
                "type": "AI_DECISION",
                "priority": "URGENT",
                "message": (
                    f"{len(urgent_decisions)} urgent AI "
                    "maintenance decision(s) detected."
                ),
                "task_ids": [
                    item["task_id"]
                    for item in urgent_decisions
                ],
            }
        )

        agent_actions.append(
            "Prioritize urgent AI maintenance decisions."
        )

    # ========================================================
    # ANALYZE BLOCK CONFLICTS
    # ========================================================

    conflicted_blocks = [
        item
        for item in block_impacts
        if item["conflict_count"] > 0
    ]

    if conflicted_blocks:

        recommendations.append(
            {
                "type": "BLOCK_CONFLICT",
                "priority": "HIGH",
                "message": (
                    f"{len(conflicted_blocks)} maintenance "
                    "block(s) have train conflicts."
                ),
                "block_ids": [
                    item["block_id"]
                    for item in conflicted_blocks
                ],
            }
        )

        agent_actions.append(
            "Review conflicting maintenance blocks."
        )

    # ========================================================
    # ANALYZE RESCHEDULING
    # ========================================================

    reschedule_candidates = [
        item
        for item in rescheduling
        if item.get("recommended_action")
        in {
            "RESCHEDULE",
            "CONSIDER_RESCHEDULE",
        }
    ]

    if reschedule_candidates:

        recommendations.append(
            {
                "type": "RESCHEDULING",
                "priority": "HIGH",
                "message": (
                    f"{len(reschedule_candidates)} block(s) "
                    "have rescheduling recommendations."
                ),
                "block_ids": [
                    item["block_id"]
                    for item in reschedule_candidates
                ],
            }
        )

        agent_actions.append(
            "Review recommended safe maintenance windows."
        )

    # ========================================================
    # BEST PLAN
    # ========================================================

    if best_plan:

        recommendations.append(
            {
                "type": "BEST_PLAN",
                "priority": (
                    "URGENT"
                    if best_plan.get("decision_level")
                    == "URGENT"
                    else "HIGH"
                ),
                "task_id": best_plan["task_id"],
                "task_code": best_plan["task_code"],
                "message": (
                    best_plan_result.get(
                        "recommendation",
                        "AI recommended maintenance plan available.",
                    )
                ),
            }
        )

        agent_actions.append(
            "Use AI best plan as the primary maintenance recommendation."
        )

    # ========================================================
    # DETERMINE AGENT STATUS
    # ========================================================

    if critical_assets or urgent_decisions:
        agent_status = "URGENT"

    elif open_events or conflicted_blocks:
        agent_status = "ATTENTION"

    else:
        agent_status = "NORMAL"

    # ========================================================
    # FINAL AGENT MESSAGE
    # ========================================================

    if agent_status == "URGENT":

        summary = (
            "AI Agent detected high operational risk. "
            "Immediate maintenance review is recommended."
        )

    elif agent_status == "ATTENTION":

        summary = (
            "AI Agent detected operational conditions "
            "requiring maintenance plan review."
        )

    else:

        summary = (
            "AI Agent found no major operational risk. "
            "Current maintenance plan can continue."
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "agent_status": agent_status,

        "summary": summary,

        # Active/open event count
        "open_events": len(open_events),

        "critical_assets": len(
            critical_assets
        ),

        "urgent_ai_decisions": len(
            urgent_decisions
        ),

        "conflicted_blocks": len(
            conflicted_blocks
        ),

        "rescheduling_candidates": len(
            reschedule_candidates
        ),

        "best_plan": best_plan,

        # ALL events are returned so frontend can display
        # OPEN + RESOLVED status correctly.
        "alerts": alerts,

        "recommendations": recommendations,

        "agent_actions": agent_actions,

        "message": (
            "AI Operations Agent analysis completed successfully."
        ),
    }


# ============================================================
# ASK AI OPERATIONS AGENT
# ============================================================

def ask_ai_agent(
    db: Session,
    question: str,
) -> dict:
    """
    Answer railway operational questions using
    the current AI Operations Agent analysis.
    """

    question = question.strip()

    if not question:
        return {
            "status": "ERROR",
            "question": question,
            "answer": "Please enter a question.",
        }

    # --------------------------------------------------------
    # Run current agent analysis
    # --------------------------------------------------------

    agent_result = run_ai_operations_agent(
        db=db
    )

    best_plan = agent_result.get(
        "best_plan"
    )

    alerts = agent_result.get(
        "alerts",
        []
    )

    # Only currently open alerts
    open_alerts = [
        alert
        for alert in alerts
        if alert.get("status") == "OPEN"
    ]

    q = question.lower()

    # ========================================================
    # BEST PLAN QUESTIONS
    # ========================================================

    if (
        "best plan" in q
        or "recommended plan" in q
        or "best maintenance" in q
        or "which task" in q
        or "first task" in q
    ):

        if best_plan:

            return {
                "status": "SUCCESS",
                "question": question,
                "answer": (
                    f"The current best maintenance plan is "
                    f"{best_plan['task_code']} "
                    f"(Task ID {best_plan['task_id']}). "
                    f"It has an AI plan score of "
                    f"{best_plan['ai_plan_score']} and "
                    f"risk level "
                    f"{best_plan['risk_level']}. "
                    f"The recommended action is "
                    f"{best_plan['final_action']}."
                ),
                "data": {
                    "task_id": best_plan["task_id"],
                    "task_code": best_plan["task_code"],
                    "ai_plan_score": best_plan[
                        "ai_plan_score"
                    ],
                    "risk_level": best_plan[
                        "risk_level"
                    ],
                    "final_action": best_plan[
                        "final_action"
                    ],
                },
            }

        return {
            "status": "SUCCESS",
            "question": question,
            "answer": (
                "There is currently no active "
                "maintenance plan available."
            ),
        }

    # ========================================================
    # RISK / URGENT QUESTIONS
    # ========================================================

    if (
        "urgent" in q
        or "critical" in q
        or "risk" in q
    ):

        return {
            "status": "SUCCESS",
            "question": question,
            "answer": (
                f"The system currently has "
                f"{agent_result['critical_assets']} "
                f"critical-risk asset(s) and "
                f"{agent_result['urgent_ai_decisions']} "
                f"urgent AI maintenance decision(s). "
                f"The overall AI Agent status is "
                f"{agent_result['agent_status']}."
            ),
            "data": {
                "agent_status": agent_result[
                    "agent_status"
                ],
                "critical_assets": agent_result[
                    "critical_assets"
                ],
                "urgent_ai_decisions": agent_result[
                    "urgent_ai_decisions"
                ],
            },
        }

    # ========================================================
    # TRAIN DELAY QUESTIONS
    # ========================================================

    if (
        "train" in q
        and (
            "delay" in q
            or "late" in q
        )
    ):

        train_alerts = [
            alert
            for alert in open_alerts
            if alert["event_type"] == "TRAIN_DELAY"
        ]

        if train_alerts:

            alert = train_alerts[0]

            return {
                "status": "SUCCESS",
                "question": question,
                "answer": (
                    f"Train ID {alert['train_id']} "
                    f"is currently delayed by "
                    f"{alert['delay_minutes']} minutes. "
                    f"The event has "
                    f"{alert['severity']} severity."
                ),
                "data": alert,
            }

        return {
            "status": "SUCCESS",
            "question": question,
            "answer": (
                "There is currently no active "
                "train-delay alert."
            ),
        }

    # ========================================================
    # EVENT / ALERT / PROBLEM QUESTIONS
    # ========================================================

    if (
        "event" in q
        or "alert" in q
        or "problem" in q
        or "issue" in q
    ):

        if open_alerts:

            latest = open_alerts[0]

            description = (
                latest["description"]
                or f"{latest['event_type']} event"
            )

            return {
                "status": "SUCCESS",
                "question": question,
                "answer": (
                    f"The latest open operational event is "
                    f"{description}. "
                    f"It has {latest['severity']} severity "
                    f"and affects section "
                    f"{latest['section_id']}."
                ),
                "data": latest,
            }

        return {
            "status": "SUCCESS",
            "question": question,
            "answer": (
                "There are currently no open "
                "operational events."
            ),
        }

    # ========================================================
    # BLOCK / CONFLICT / RESCHEDULE QUESTIONS
    # ========================================================

    if (
        "block" in q
        or "conflict" in q
        or "reschedule" in q
    ):

        return {
            "status": "SUCCESS",
            "question": question,
            "answer": (
                f"The AI Agent currently detects "
                f"{agent_result['conflicted_blocks']} "
                f"conflicted block(s) and "
                f"{agent_result['rescheduling_candidates']} "
                f"rescheduling candidate(s)."
            ),
            "data": {
                "conflicted_blocks": agent_result[
                    "conflicted_blocks"
                ],
                "rescheduling_candidates": agent_result[
                    "rescheduling_candidates"
                ],
            },
        }

    # ========================================================
    # SYSTEM STATUS / HEALTH
    # ========================================================

    if (
        "status" in q
        or "health" in q
        or "overall" in q
        or "system" in q
    ):

        return {
            "status": "SUCCESS",
            "question": question,
            "answer": agent_result["summary"],
            "data": {
                "agent_status": agent_result[
                    "agent_status"
                ],
                "open_events": agent_result[
                    "open_events"
                ],
                "critical_assets": agent_result[
                    "critical_assets"
                ],
                "urgent_ai_decisions": agent_result[
                    "urgent_ai_decisions"
                ],
                "conflicted_blocks": agent_result[
                    "conflicted_blocks"
                ],
            },
        }

    # ========================================================
    # RECOMMENDATION QUESTIONS
    # ========================================================

    if (
        "recommend" in q
        or "suggest" in q
        or "what should" in q
        or "what do" in q
    ):

        if best_plan:

            return {
                "status": "SUCCESS",
                "question": question,
                "answer": (
                    f"I recommend prioritizing "
                    f"{best_plan['task_code']} "
                    f"because its asset risk is "
                    f"{best_plan['risk_level']} "
                    f"and its AI plan score is "
                    f"{best_plan['ai_plan_score']}. "
                    f"Recommended action: "
                    f"{best_plan['final_action']}."
                ),
                "data": {
                    "task_code": best_plan[
                        "task_code"
                    ],
                    "recommendation": best_plan[
                        "recommendation"
                    ],
                },
            }

    # ========================================================
    # FALLBACK
    # ========================================================

    return {
        "status": "SUCCESS",
        "question": question,
        "answer": (
            "I analyzed the current railway system. "
            f"AI Agent status is "
            f"{agent_result['agent_status']}. "
            f"There are "
            f"{agent_result['open_events']} open event(s), "
            f"{agent_result['critical_assets']} "
            f"critical-risk asset(s), and "
            f"{agent_result['urgent_ai_decisions']} "
            f"urgent AI decision(s). "
            f"Current recommendation is "
            f"{best_plan['task_code'] if best_plan else 'No active plan'}."
        ),
        "data": {
            "agent_status": agent_result[
                "agent_status"
            ],
            "open_events": agent_result[
                "open_events"
            ],
            "critical_assets": agent_result[
                "critical_assets"
            ],
            "urgent_ai_decisions": agent_result[
                "urgent_ai_decisions"
            ],
        },
    }