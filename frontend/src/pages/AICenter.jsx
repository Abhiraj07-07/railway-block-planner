
import {
  useEffect,
  useMemo,
  useState,
} from "react";

import { authFetch } from "../App";
import "./AICenter.css";

/* =========================================================
   API CONFIG
========================================================= */

const API_BASE =
  import.meta.env.VITE_API_BASE ||
  "http://127.0.0.1:8000";

/* =========================================================
   HELPERS
========================================================= */

const normalizeArray = (value) => {
  if (Array.isArray(value)) {
    return value;
  }

  if (
    value?.data &&
    Array.isArray(value.data)
  ) {
    return value.data;
  }

  if (
    value?.assets &&
    Array.isArray(value.assets)
  ) {
    return value.assets;
  }

  if (
    value?.tasks &&
    Array.isArray(value.tasks)
  ) {
    return value.tasks;
  }

  if (
    value?.decisions &&
    Array.isArray(value.decisions)
  ) {
    return value.decisions;
  }

  return [];
};

const safeNumber = (value, fallback = 0) => {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
};

const numberValue = (...values) => {
  for (const value of values) {
    if (
      value !== undefined &&
      value !== null &&
      value !== ""
    ) {
      return value;
    }
  }

  return "—";
};

const formatScore = (value) => {
  if (
    value === undefined ||
    value === null ||
    value === ""
  ) {
    return "—";
  }

  const number = Number(value);

  if (Number.isNaN(number)) {
    return value;
  }

  return Number.isInteger(number)
    ? number
    : number.toFixed(2);
};

const statusClass = (value) => {
  return String(
    value || "LOW"
  )
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-");
};

const normalizeLevel = (value) => {
  return String(
    value || "LOW"
  )
    .trim()
    .toUpperCase();
};

/* =========================================================
   COMPONENT
========================================================= */

function AICenter() {
  /* =======================================================
     DATA
  ======================================================= */

  const [
    assetRisks,
    setAssetRisks,
  ] = useState([]);

  const [
    smartPriorities,
    setSmartPriorities,
  ] = useState([]);

  const [
    aiDecisions,
    setAiDecisions,
  ] = useState([]);

  const [
    aiBestPlan,
    setAiBestPlan,
  ] = useState(null);

  const [
    aiAgent,
    setAiAgent,
  ] = useState(null);

  /* =======================================================
     LOADING / ERROR
  ======================================================= */

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    refreshing,
    setRefreshing,
  ] = useState(false);

  const [
    aiAgentLoading,
    setAiAgentLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");

  /* =======================================================
     AI AGENT QUESTION
  ======================================================= */

  const [
    agentQuestion,
    setAgentQuestion,
  ] = useState("");

  const [
    agentAnswer,
    setAgentAnswer,
  ] = useState("");

  const [
    agentLoading,
    setAgentLoading,
  ] = useState(false);

  /* =======================================================
     LOAD MAIN AI DATA
  ======================================================= */

  const loadAIData = async ({
    initial = false,
    refresh = false,
  } = {}) => {
    try {
      if (initial) {
        setLoading(true);
      }

      if (refresh) {
        setRefreshing(true);
      }

      setError("");

     const results = await Promise.allSettled([
  authFetch(`${API_BASE}/ai/risk/assets`, {
    loaderMessage: "Analyzing railway asset risk...",
  }),

  authFetch(`${API_BASE}/ai/smart-priority`, {
    loaderMessage: "Calculating smart maintenance priorities...",
  }),

  authFetch(`${API_BASE}/ai/decisions`, {
    loaderMessage: "Generating AI operational decisions...",
  }),

  authFetch(`${API_BASE}/ai/best-plan`, {
    loaderMessage: "Finding the best maintenance plan...",
  }),
]);

let successfulRequests = 0;

      /* =====================================================
         ASSET RISK
      ===================================================== */

      if (
        results[0].status ===
        "fulfilled"
      ) {
        const response =
          results[0].value;

        const data =
          response?.data ??
          response;

        if (
          response?.ok !== false
        ) {
          setAssetRisks(
            normalizeArray(data)
          );

          successfulRequests += 1;
        }
      }

      /* =====================================================
         SMART PRIORITY
      ===================================================== */

      if (
        results[1].status ===
        "fulfilled"
      ) {
        const response =
          results[1].value;

        const data =
          response?.data ??
          response;

        if (
          response?.ok !== false
        ) {
          setSmartPriorities(
            normalizeArray(data)
          );

          successfulRequests += 1;
        }
      }

      /* =====================================================
         AI DECISIONS
      ===================================================== */

      if (
        results[2].status ===
        "fulfilled"
      ) {
        const response =
          results[2].value;

        const data =
          response?.data ??
          response;

        if (
          response?.ok !== false
        ) {
          setAiDecisions(
            normalizeArray(data)
          );

          successfulRequests += 1;
        }
      }

      /* =====================================================
         BEST PLAN

         App.jsx authFetch returns parsed JSON,
         so no response.json() is required.
      ===================================================== */

      if (
        results[3].status ===
        "fulfilled"
      ) {
        const data =
          results[3].value;

        if (
          data &&
          typeof data ===
            "object"
        ) {
          setAiBestPlan(
            data?.best_plan ??
              data?.data?.best_plan ??
              data?.plan ??
              data?.data?.plan ??
              null
          );

          successfulRequests += 1;
        }
      }

      if (
        successfulRequests ===
        0
      ) {
        throw new Error(
          "Unable to load AI services."
        );
      }
    } catch (err) {
      console.error(
        "AI Center error:",
        err
      );

      setError(
        err?.message ||
          "Unable to load AI Center data."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  /* =======================================================
     LOAD AI AGENT STATUS
  ======================================================= */

  const loadAgentStatus =
    async () => {
      try {
        setAiAgentLoading(true);

        const data = await authFetch(`${API_BASE}/ai/agent`, {
  loaderMessage: "Checking AI agent status...",
});

        setAiAgent(
          data &&
            typeof data ===
              "object"
            ? data
            : null
        );
      } catch (err) {
        console.error(
          "AI Agent status error:",
          err
        );

        setAiAgent(null);
      } finally {
        setAiAgentLoading(false);
      }
    };

  /* =======================================================
     INITIAL LOAD
  ======================================================= */

  useEffect(() => {
    loadAIData({
      initial: true,
    });

    loadAgentStatus();
  }, []);

  /* =======================================================
     ASK AI AGENT
  ======================================================= */

  const handleAskAgent =
    async () => {
      const question =
        agentQuestion.trim();

      if (!question) {
        setAgentAnswer(
          "Please enter a question."
        );

        return;
      }

      try {
        setAgentLoading(true);
        setAgentAnswer("");

        const data = await authFetch(
  `${API_BASE}/ai/agent/ask?question=${encodeURIComponent(question)}`,
  {
    method: "POST",
    loaderMessage: "AI agent is thinking...",
  }
);

        if (
          !data ||
          typeof data !==
            "object"
        ) {
          throw new Error(
            "Invalid AI Agent response."
          );
        }

        setAgentAnswer(
          data.answer ||
            data.response ||
            "No answer received."
        );
      } catch (err) {
        console.error(
          "AI Agent error:",
          err
        );

        setAgentAnswer(
          `❌ ${
            err?.message ||
            "AI Agent request failed."
          }`
        );
      } finally {
        setAgentLoading(false);
      }
    };

  /* =======================================================
     SUMMARY
  ======================================================= */

  const criticalRiskCount =
    useMemo(() => {
      return assetRisks.filter(
        (asset) => {
          const level =
            normalizeLevel(
              asset.risk_level ??
                asset.ml_risk_level
            );

          return (
            level === "CRITICAL"
          );
        }
      ).length;
    }, [assetRisks]);

  const highRiskCount =
    useMemo(() => {
      return assetRisks.filter(
        (asset) => {
          const level =
            normalizeLevel(
              asset.risk_level ??
                asset.ml_risk_level
            );

          return (
            level === "HIGH"
          );
        }
      ).length;
    }, [assetRisks]);

  const urgentDecisionCount =
    useMemo(() => {
      return aiDecisions.filter(
        (decision) => {
          const level =
            normalizeLevel(
              decision.decision_level ??
                decision.ai_decision_level
            );

          return (
            level === "URGENT"
          );
        }
      ).length;
    }, [aiDecisions]);

  /* =======================================================
     SORTED DATA
  ======================================================= */

  const topRiskAssets =
    useMemo(() => {
      return [
        ...assetRisks,
      ].sort(
        (a, b) =>
          safeNumber(
            b.risk_score ??
              b.ml_risk_percentage
          ) -
          safeNumber(
            a.risk_score ??
              a.ml_risk_percentage
          )
      );
    }, [assetRisks]);

  const sortedPriorities =
    useMemo(() => {
      return [
        ...smartPriorities,
      ].sort(
        (a, b) =>
          safeNumber(
            b.smart_priority_score
          ) -
          safeNumber(
            a.smart_priority_score
          )
      );
    }, [smartPriorities]);

  const sortedDecisions =
    useMemo(() => {
      return [
        ...aiDecisions,
      ].sort(
        (a, b) =>
          safeNumber(
            b.ai_decision_score
          ) -
          safeNumber(
            a.ai_decision_score
          )
      );
    }, [aiDecisions]);

  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="ai-center-page">

      {/* =================================================
          HERO
      ================================================= */}

      <section className="ai-center-hero">

        <div>
          <span className="ai-center-eyebrow">
            ARTIFICIAL INTELLIGENCE
          </span>

          <h1>
            🤖 AI Operations Center
          </h1>

          <p>
            Intelligent railway
            maintenance risk analysis,
            smart prioritization,
            operational decisions and
            AI-assisted planning.
          </p>
        </div>

        <div className="ai-hero-actions">

          <button
            className="ai-refresh-button"
            type="button"
            onClick={() => {
              loadAIData({
                refresh: true,
              });

              loadAgentStatus();
            }}
            disabled={refreshing}
          >
            {refreshing
              ? "⏳ Refreshing..."
              : "🔄 Refresh AI"}
          </button>

          <div className="ai-status-badge">

            <span className="ai-pulse-dot" />

            AI SYSTEM ACTIVE

          </div>

        </div>

      </section>

      {/* =================================================
          ERROR
      ================================================= */}

      {error && (
        <div className="global-error">

          <strong>
            AI Center Notice:
          </strong>{" "}

          {error}

        </div>
      )}

      {/* =================================================
          SUMMARY
      ================================================= */}

      <section className="ai-summary-grid">

        <div className="ai-summary-card">

          <span>
            🔴 Critical Risk Assets
          </span>

          <strong>
            {loading
              ? "..."
              : criticalRiskCount}
          </strong>

          <small>
            High-priority asset risk
          </small>

        </div>

        <div className="ai-summary-card">

          <span>
            🟠 High Risk Assets
          </span>

          <strong>
            {loading
              ? "..."
              : highRiskCount}
          </strong>

          <small>
            Elevated maintenance risk
          </small>

        </div>

        <div className="ai-summary-card">

          <span>
            ⚡ Urgent AI Decisions
          </span>

          <strong>
            {loading
              ? "..."
              : urgentDecisionCount}
          </strong>

          <small>
            Immediate attention
          </small>

        </div>

        <div className="ai-summary-card">

          <span>
            🧠 Smart Priorities
          </span>

          <strong>
            {loading
              ? "..."
              : smartPriorities.length}
          </strong>

          <small>
            AI-ranked maintenance tasks
          </small>

        </div>

      </section>

      {/* =================================================
          BEST PLAN
      ================================================= */}

      <section className="ai-panel ai-best-panel">

        <div className="ai-panel-header">

          <div>

            <span className="ai-section-label">
              AI PLANNING ENGINE
            </span>

            <h2>
              🏆 AI Best Maintenance Plan
            </h2>

            <p>
              Highest-ranked maintenance
              recommendation generated by
              the AI planning engine.
            </p>

          </div>

          <span className="ai-panel-badge">
            TOP PLAN
          </span>

        </div>

        {aiBestPlan ? (

          <div className="ai-best-plan-card">

            <div className="ai-best-plan-main">

              <span className="ai-plan-label">
                ⭐ RECOMMENDED
              </span>

              <h3>
                {aiBestPlan.task_code ??
                  aiBestPlan.task_id ??
                  "Maintenance Task"}
              </h3>

              <p>
                Asset{" "}
                {aiBestPlan.asset_id ??
                  "—"}
                {" · "}
                Section{" "}
                {aiBestPlan.section_id ??
                  "—"}
              </p>

            </div>

            <div className="ai-plan-score">

              <span>
                AI Plan Score
              </span>

              <strong>
                {formatScore(
                  aiBestPlan.ai_plan_score ??
                    aiBestPlan.plan_score
                )}
              </strong>

            </div>

            <div className="ai-plan-details">

              <div>

                <span>
                  AI Decision
                </span>

                <strong>
                  {formatScore(
                    aiBestPlan.ai_decision_score
                  )}
                </strong>

              </div>

              <div>

                <span>
                  Smart Priority
                </span>

                <strong>
                  {formatScore(
                    aiBestPlan.smart_priority_score
                  )}
                </strong>

              </div>

              <div>

                <span>
                  Asset Risk
                </span>

                <strong>
                  {formatScore(
                    aiBestPlan.asset_risk_score
                  )}
                </strong>

              </div>

              <div>

                <span>
                  Train Impact
                </span>

                <strong>
                  {numberValue(
                    aiBestPlan.train_impact_level,
                    aiBestPlan.train_impact,
                    "NONE"
                  )}
                </strong>

              </div>

            </div>

            <div className="ai-action-box">

              <span>
                Final AI Action
              </span>

              <strong>
                {numberValue(
                  aiBestPlan.final_action,
                  aiBestPlan.recommended_action,
                  "PLAN"
                )}
              </strong>

            </div>

            <div className="ai-recommendation-box">

              <strong>
                💡 AI Recommendation
              </strong>

              <p>
                {aiBestPlan.recommendation ??
                  aiBestPlan.reason ??
                  "AI-generated recommendation based on current maintenance and operational conditions."}
              </p>

            </div>

          </div>

        ) : loading ? (

          <div className="ai-loading">

            <div className="loader" />

            Loading AI best plan...

          </div>

        ) : (

          <p className="empty-state">
            No AI best plan available.
          </p>

        )}

      </section>

      {/* =================================================
          ASSET RISK
      ================================================= */}

      <section className="ai-panel">

        <div className="ai-panel-header">

          <div>

            <span className="ai-section-label">
              MACHINE LEARNING
            </span>

            <h2>
              🔴 AI Maintenance Risk
            </h2>

            <p>
              Predicted asset risk based
              on defects and maintenance
              workload.
            </p>

          </div>

          <span className="ai-panel-badge">
            {assetRisks.length} Assets
          </span>

        </div>

        {loading ? (

          <div className="ai-loading">

            <div className="loader" />

            Loading risk analysis...

          </div>

        ) : topRiskAssets.length ===
          0 ? (

          <p className="empty-state">
            No asset risk data available.
          </p>

        ) : (

          <div className="ai-card-list">

            {topRiskAssets.map(
              (asset) => {

                const level =
                  normalizeLevel(
                    asset.risk_level ??
                      asset.ml_risk_level
                  );

                const score =
                  asset.risk_score ??
                  asset.ml_risk_percentage ??
                  0;

                const assetKey =
                  asset.asset_id ??
                  asset.asset_code ??
                  asset.id;

                return (
                  <div
                    className={`ai-risk-card ai-risk-${statusClass(
                      level
                    )}`}
                    key={
                      assetKey
                    }
                  >

                    <div className="ai-risk-header">

                      <div>

                        <h3>
                          {asset.asset_code ??
                            `Asset ${asset.asset_id ?? "—"}`}
                        </h3>

                        <p>
                          {asset.asset_type ??
                            "Railway Asset"}
                          {" · "}
                          Section{" "}
                          {asset.section_id ??
                            "—"}
                        </p>

                      </div>

                      <div className="ai-score-box">

                        <span>
                          Risk Score
                        </span>

                        <strong>
                          {formatScore(
                            score
                          )}
                          %
                        </strong>

                      </div>

                    </div>

                    <div className="ai-mini-grid">

                      <div>
                        <span>
                          Risk Level
                        </span>

                        <strong>
                          {level}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Open Defects
                        </span>

                        <strong>
                          {numberValue(
                            asset.open_defect_count,
                            asset.defect_count,
                            0
                          )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Active Tasks
                        </span>

                        <strong>
                          {numberValue(
                            asset.active_task_count,
                            asset.task_count,
                            0
                          )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Criticality
                        </span>

                        <strong>
                          {numberValue(
                            asset.criticality,
                            level
                          )}
                        </strong>
                      </div>

                    </div>

                    {Array.isArray(
                      asset.risk_factors
                    ) &&
                      asset.risk_factors
                        .length >
                        0 && (

                        <div className="ai-reasons">

                          <strong>
                            Risk Factors
                          </strong>

                          {asset.risk_factors.map(
                            (
                              factor,
                              index
                            ) => (
                              <p
                                key={
                                  index
                                }
                              >
                                •{" "}
                                {factor}
                              </p>
                            )
                          )}

                        </div>

                      )}

                    {asset.recommendation && (
                      <div className="ai-recommendation-box">

                        <strong>
                          🤖 Recommendation
                        </strong>

                        <p>
                          {
                            asset.recommendation
                          }
                        </p>

                      </div>
                    )}

                  </div>
                );
              }
            )}

          </div>

        )}

      </section>

      {/* =================================================
          SMART PRIORITY
      ================================================= */}

      <section className="ai-panel">

        <div className="ai-panel-header">

          <div>

            <span className="ai-section-label">
              PRIORITIZATION ENGINE
            </span>

            <h2>
              🧠 Smart Maintenance Priority
            </h2>

            <p>
              Combined maintenance priority
              and AI asset-risk ranking.
            </p>

          </div>

          <span className="ai-panel-badge">
            {smartPriorities.length} Tasks
          </span>

        </div>

        {loading ? (

          <div className="ai-loading">

            <div className="loader" />

            Loading smart priorities...

          </div>

        ) : sortedPriorities.length ===
          0 ? (

          <p className="empty-state">
            No smart priority data available.
          </p>

        ) : (

          <div className="ai-card-list">

            {sortedPriorities.map(
              (
                task,
                index
              ) => {

                const level =
                  normalizeLevel(
                    task.smart_priority_level ??
                      task.priority_level ??
                      task.risk_level
                  );

                return (
                  <div
                    className={`ai-smart-card ai-risk-${statusClass(
                      level
                    )}`}
                    key={
                      task.task_id ??
                      task.task_code ??
                      index
                    }
                  >

                    {index === 0 && (
                      <span className="ai-top-label">
                        ⭐ TOP PRIORITY
                      </span>
                    )}

                    <div className="ai-risk-header">

                      <div>

                        <h3>
                          {task.task_code ??
                            `Task ${task.task_id ?? "—"}`}
                        </h3>

                        <p>
                          Asset{" "}
                          {task.asset_id ??
                            "—"}
                          {" · "}
                          Section{" "}
                          {task.section_id ??
                            "—"}
                        </p>

                      </div>

                      <div className="ai-score-box">

                        <span>
                          Smart Score
                        </span>

                        <strong>
                          {formatScore(
                            task.smart_priority_score
                          )}
                        </strong>

                      </div>

                    </div>

                    <div className="ai-mini-grid">

                      <div>

                        <span>
                          Base Priority
                        </span>

                        <strong>
                          {formatScore(
                            task.base_priority_score
                          )}
                        </strong>

                      </div>

                      <div>

                        <span>
                          Asset Risk
                        </span>

                        <strong>
                          {formatScore(
                            task.asset_risk_score
                          )}
                        </strong>

                      </div>

                      <div>

                        <span>
                          Risk Level
                        </span>

                        <strong>
                          {task.risk_level ??
                            "—"}
                        </strong>

                      </div>

                      <div>

                        <span>
                          Priority
                        </span>

                        <strong>
                          {level}
                        </strong>

                      </div>

                    </div>

                    {task.recommendation && (
                      <div className="ai-recommendation-box">

                        <strong>
                          🤖 Recommendation
                        </strong>

                        <p>
                          {
                            task.recommendation
                          }
                        </p>

                      </div>
                    )}

                  </div>
                );
              }
            )}

          </div>

        )}

      </section>

      {/* =================================================
          AI DECISION CENTER
      ================================================= */}

      <section className="ai-panel">

        <div className="ai-panel-header">

          <div>

            <span className="ai-section-label">
              DECISION ENGINE
            </span>

            <h2>
              🎯 AI Decision Center
            </h2>

            <p>
              AI-assisted decisions
              considering priority, asset
              risk and train impact.
            </p>

          </div>

          <span className="ai-panel-badge">
            {aiDecisions.length} Decisions
          </span>

        </div>

        {loading ? (

          <div className="ai-loading">

            <div className="loader" />

            Loading AI decisions...

          </div>

        ) : sortedDecisions.length ===
          0 ? (

          <p className="empty-state">
            No AI decisions available.
          </p>

        ) : (

          <div className="ai-card-list">

            {sortedDecisions.map(
              (
                decision,
                index
              ) => {

                const level =
                  normalizeLevel(
                    decision.decision_level ??
                      decision.ai_decision_level
                  );

                return (
                  <div
                    className={`ai-decision-card ai-decision-${statusClass(
                      level
                    )}`}
                    key={
                      decision.task_id ??
                      decision.task_code ??
                      index
                    }
                  >

                    {index === 0 && (
                      <span className="ai-top-label">
                        ⭐ TOP AI RECOMMENDATION
                      </span>
                    )}

                    <div className="ai-risk-header">

                      <div>

                        <h3>
                          {decision.task_code ??
                            `Task ${decision.task_id ?? "—"}`}
                        </h3>

                        <p>
                          Asset{" "}
                          {decision.asset_id ??
                            "—"}
                          {" · "}
                          Section{" "}
                          {decision.section_id ??
                            "—"}
                        </p>

                      </div>

                      <div className="ai-score-box">

                        <span>
                          AI Decision Score
                        </span>

                        <strong>
                          {formatScore(
                            decision.ai_decision_score
                          )}
                        </strong>

                      </div>

                    </div>

                    <div className="ai-mini-grid">

                      <div>

                        <span>
                          Base Priority
                        </span>

                        <strong>
                          {formatScore(
                            decision.base_priority_score
                          )}
                        </strong>

                      </div>

                      <div>

                        <span>
                          Asset Risk
                        </span>

                        <strong>
                          {formatScore(
                            decision.asset_risk_score
                          )}
                        </strong>

                      </div>

                      <div>

                        <span>
                          Train Impact
                        </span>

                        <strong>
                          {decision.train_impact_level ??
                            decision.train_impact ??
                            "NONE"}
                        </strong>

                      </div>

                      <div>

                        <span>
                          Decision
                        </span>

                        <strong>
                          {level}
                        </strong>

                      </div>

                    </div>

                    <div className="ai-action-box">

                      <span>
                        Recommended Action
                      </span>

                      <strong>
                        {decision.final_action ??
                          decision.recommended_action ??
                          "PLAN"}
                      </strong>

                    </div>

                    {Array.isArray(
                      decision.decision_reasons
                    ) &&
                      decision
                        .decision_reasons
                        .length >
                        0 && (

                        <div className="ai-reasons">

                          <strong>
                            Why AI recommends this
                          </strong>

                          {decision.decision_reasons.map(
                            (
                              reason,
                              reasonIndex
                            ) => (

                              <p
                                key={
                                  reasonIndex
                                }
                              >
                                •{" "}
                                {reason}
                              </p>

                            )
                          )}

                        </div>

                      )}

                    {decision.recommendation && (
                      <div className="ai-recommendation-box">

                        <strong>
                          🤖 Recommendation
                        </strong>

                        <p>
                          {
                            decision.recommendation
                          }
                        </p>

                      </div>
                    )}

                    {Array.isArray(
                      decision.affected_train_ids
                    ) &&
                      decision
                        .affected_train_ids
                        .length >
                        0 && (

                        <div className="affected-trains">

                          <strong>
                            🚆 Affected Trains:
                          </strong>{" "}

                          {
                            decision
                              .affected_train_ids
                              .join(", ")
                          }

                        </div>

                      )}

                  </div>
                );
              }
            )}

          </div>

        )}

      </section>

      {/* =================================================
          ASK AI
      ================================================= */}

      <section className="ai-panel ai-agent-panel">

        <div className="ai-panel-header">

          <div>

            <span className="ai-section-label">
              AI ASSISTANT
            </span>

            <h2>
              💬 Ask AI Operations Agent
            </h2>

            <p>
              Ask questions about railway
              maintenance, risk and
              scheduling.
            </p>

          </div>

          <span className="ai-panel-badge">
            AI ASSISTANT
          </span>

        </div>

        <div className="ai-ask-box">

          <input
            type="text"
            value={
              agentQuestion
            }
            onChange={(event) =>
              setAgentQuestion(
                event.target.value
              )
            }
            onKeyDown={(event) => {
              if (
                event.key ===
                "Enter"
              ) {
                handleAskAgent();
              }
            }}
            placeholder="Ask: Why is SMMS001 urgent?"
            disabled={
              agentLoading
            }
          />

          <button
            className="ai-ask-button"
            type="button"
            onClick={
              handleAskAgent
            }
            disabled={
              agentLoading
            }
          >
            {agentLoading
              ? "⏳ Thinking..."
              : "🤖 Ask AI"}
          </button>

        </div>

        <div className="ai-example-questions">

          {[
            "Why is SMMS001 urgent?",
            "What is the current system status?",
            "Are there any train delays?",
            "What is the best maintenance plan?",
          ].map(
            (question) => (
              <button
                key={
                  question
                }
                type="button"
                onClick={() =>
                  setAgentQuestion(
                    question
                  )
                }
              >
                {question}
              </button>
            )
          )}

        </div>

        {agentAnswer && (
          <div className="ai-answer-box">

            <strong>
              🤖 AI Agent Response
            </strong>

            <p>
              {agentAnswer}
            </p>

          </div>
        )}

      </section>

      {/* =================================================
          AI AGENT STATUS
      ================================================= */}

      <section className="ai-panel">

        <div className="ai-panel-header">

          <div>

            <span className="ai-section-label">
              AUTONOMOUS MONITORING
            </span>

            <h2>
              🧠 AI Agent Status
            </h2>

            <p>
              Current AI operational
              monitoring summary.
            </p>

          </div>

          <span
            className={`ai-agent-status ${
              aiAgent
                ? statusClass(
                    aiAgent.agent_status ??
                      "NORMAL"
                  )
                : "normal"
            }`}
          >
            ●{" "}
            {aiAgentLoading
              ? "CHECKING"
              : aiAgent?.agent_status ??
                "NORMAL"}
          </span>

        </div>

        {aiAgentLoading ? (

          <div className="ai-loading compact-loading">

            <div className="loader" />

            Checking AI agent status...

          </div>

        ) : (

          <>

            <div className="ai-agent-summary">

              <div>

                <span>
                  Open Events
                </span>

                <strong>
                  {numberValue(
                    aiAgent?.open_events,
                    0
                  )}
                </strong>

              </div>

              <div>

                <span>
                  Critical Assets
                </span>

                <strong>
                  {numberValue(
                    aiAgent?.critical_assets,
                    0
                  )}
                </strong>

              </div>

              <div>

                <span>
                  Urgent Decisions
                </span>

                <strong>
                  {numberValue(
                    aiAgent?.urgent_ai_decisions,
                    0
                  )}
                </strong>

              </div>

              <div>

                <span>
                  Conflicted Blocks
                </span>

                <strong>
                  {numberValue(
                    aiAgent?.conflicted_blocks,
                    0
                  )}
                </strong>

              </div>

            </div>

            {aiAgent?.summary && (
              <div className="ai-agent-summary-text">

                <strong>
                  🧠 Agent Analysis
                </strong>

                <p>
                  {aiAgent.summary}
                </p>

              </div>
            )}

          </>
        )}

      </section>

    </div>
  );
}

export default AICenter;

