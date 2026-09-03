import {
  useEffect,
  useMemo,
  useState,
} from "react";

import { authFetch } from "../App";
import "./Home.css";

const API_BASE = "http://127.0.0.1:8000";
const MIN_LOADING_TIME = 1000;

/* =========================================================
   HELPERS
========================================================= */

const normalizeArray = (value) => {
  if (Array.isArray(value)) return value;

  if (value?.data && Array.isArray(value.data)) {
    return value.data;
  }

  if (value?.items && Array.isArray(value.items)) {
    return value.items;
  }

  if (value?.results && Array.isArray(value.results)) {
    return value.results;
  }

  if (value?.assets && Array.isArray(value.assets)) {
    return value.assets;
  }

  if (value?.tasks && Array.isArray(value.tasks)) {
    return value.tasks;
  }

  if (value?.decisions && Array.isArray(value.decisions)) {
    return value.decisions;
  }

  if (value?.blocks && Array.isArray(value.blocks)) {
    return value.blocks;
  }

  if (value?.events && Array.isArray(value.events)) {
    return value.events;
  }

  return [];
};

const formatDate = (value) => {
  if (!value) return "—";

  const direct = String(value).match(
    /^(\d{4})-(\d{2})-(\d{2})/
  );

  if (direct) {
    return `${direct[3]}-${direct[2]}-${direct[1]}`;
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

const statusClass = (value) => {
  return String(value || "unknown")
    .toLowerCase()
    .replaceAll(" ", "-");
};

const wait = (ms) =>
  new Promise((resolve) => {
    setTimeout(resolve, ms);
  });

/* =========================================================
   COMPONENT
========================================================= */

function Home() {
  /* =======================================================
     PAGE LOADING
  ======================================================= */

  const [pageLoading, setPageLoading] = useState(true);
  const [loadProgress, setLoadProgress] = useState(0);

  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  /* =======================================================
     CORE DATA
  ======================================================= */

  const [blocks, setBlocks] = useState([]);
  const [maintenanceTasks, setMaintenanceTasks] = useState([]);
  const [events, setEvents] = useState([]);
  const [trains, setTrains] = useState([]);

  /* =======================================================
     NETWORK DATA
  ======================================================= */

  const [stations, setStations] = useState([]);
  const [sections, setSections] = useState([]);
  const [assets, setAssets] = useState([]);
  const [defects, setDefects] = useState([]);

  /* =======================================================
     AI DATA
  ======================================================= */

  const [mlAssets, setMlAssets] = useState([]);
  const [aiDecisions, setAiDecisions] = useState([]);
  const [aiBestPlan, setAiBestPlan] = useState(null);

  /* =======================================================
     INTEGRATION
  ======================================================= */

  const [integrationStatus, setIntegrationStatus] =
    useState(null);

  /* =======================================================
     LOAD EVERYTHING IN PARALLEL
  ======================================================= */

  useEffect(() => {
    let mounted = true;

    const loadHome = async () => {
      const startedAt = Date.now();

      setPageLoading(true);
      setLoadProgress(8);
      setError("");

      const requests = [
        {
          key: "blocks",
          request: authFetch(
            `${API_BASE}/planner/blocks`
          ),
        },
        {
          key: "maintenance",
          request: authFetch(
            `${API_BASE}/maintenance-tasks`
          ),
        },
        {
          key: "events",
          request: authFetch(
            `${API_BASE}/events`
          ),
        },
        {
          key: "trains",
          request: authFetch(
            `${API_BASE}/trains`
          ),
        },
        {
          key: "stations",
          request: authFetch(
            `${API_BASE}/stations`
          ),
        },
        {
          key: "sections",
          request: authFetch(
            `${API_BASE}/sections`
          ),
        },
        {
          key: "assets",
          request: authFetch(
            `${API_BASE}/assets`
          ),
        },
        {
          key: "defects",
          request: authFetch(
            `${API_BASE}/defects`
          ),
        },
        {
          key: "ml",
          request: authFetch(
            `${API_BASE}/ai/ml-risk/assets`
          ),
        },
        {
          key: "decisions",
          request: authFetch(
            `${API_BASE}/ai/decisions`
          ),
        },
        {
          key: "bestPlan",
          request: authFetch(
            `${API_BASE}/ai/best-plan`
          ),
        },
        {
          key: "integration",
          request: authFetch(
            `${API_BASE}/integration/status`
          ),
        },
      ];

      const results =
        await Promise.allSettled(
          requests.map(
            (item) => item.request
          )
        );

      if (!mounted) return;

      setLoadProgress(75);

      const data = {};

      requests.forEach(
        (item, index) => {
          const result = results[index];

          if (result.status === "fulfilled") {
            data[item.key] =
              result.value;
          } else {
            console.error(
              `Home API failed: ${item.key}`,
              result.reason
            );

            data[item.key] = null;
          }
        }
      );

      /* =====================================================
         SET CORE DATA
      ===================================================== */

      setBlocks(
        normalizeArray(data.blocks)
      );

      setMaintenanceTasks(
        normalizeArray(
          data.maintenance
        )
      );

      setEvents(
        normalizeArray(data.events)
      );

      setTrains(
        normalizeArray(data.trains)
      );

      /* =====================================================
         SET NETWORK DATA
      ===================================================== */

      setStations(
        normalizeArray(data.stations)
      );

      setSections(
        normalizeArray(data.sections)
      );

      setAssets(
        normalizeArray(data.assets)
      );

      setDefects(
        normalizeArray(data.defects)
      );

      /* =====================================================
         SET AI DATA
      ===================================================== */

      setMlAssets(
        normalizeArray(data.ml)
      );

      setAiDecisions(
        normalizeArray(data.decisions)
      );

      setAiBestPlan(
        data.bestPlan?.best_plan ??
        data.bestPlan?.data?.best_plan ??
        null
      );

      /* =====================================================
         SET INTEGRATION
      ===================================================== */

      setIntegrationStatus(
        data.integration
      );

      /* =====================================================
         MINIMUM 2.5 SECOND LOAD
      ===================================================== */

      const elapsed =
        Date.now() - startedAt;

      const remaining =
        Math.max(
          0,
          MIN_LOADING_TIME - elapsed
        );

      await wait(remaining);

      if (!mounted) return;

      setLoadProgress(100);

      setLastUpdated(
        new Date()
      );

      setPageLoading(false);
    };

    loadHome();

    return () => {
      mounted = false;
    };
  }, []);

  /* =======================================================
     FAKE SMOOTH LOADING PROGRESS
  ======================================================= */

  useEffect(() => {
    if (!pageLoading) return;

    const timer = setInterval(() => {
      setLoadProgress((current) => {
        if (current >= 92) {
          return current;
        }

        return current + 3;
      });
    }, 180);

    return () => {
      clearInterval(timer);
    };
  }, [pageLoading]);

  /* =======================================================
     DERIVED DATA
  ======================================================= */

  const activeBlocks = useMemo(() => {
    return blocks.filter(
      (block) =>
        block.status !== "CANCELLED"
    );
  }, [blocks]);

  const openEvents = useMemo(() => {
    return events.filter(
      (event) =>
        event.status === "OPEN"
    );
  }, [events]);

  const criticalEvents = useMemo(() => {
    return openEvents.filter(
      (event) =>
        event.severity === "CRITICAL"
    );
  }, [openEvents]);

  const overdueTasks = useMemo(() => {
    return maintenanceTasks.filter(
      (task) =>
        task.status === "OVERDUE"
    );
  }, [maintenanceTasks]);

  const openDefects = useMemo(() => {
    return defects.filter(
      (defect) =>
        defect.status === "OPEN"
    );
  }, [defects]);

  const criticalMlAssets = useMemo(() => {
    return [...mlAssets]
      .filter(
        (asset) =>
          Number(
            asset.ml_risk_percentage
          ) >= 80
      )
      .sort(
        (a, b) =>
          (Number(
            b.ml_risk_percentage
          ) || 0) -
          (Number(
            a.ml_risk_percentage
          ) || 0)
      );
  }, [mlAssets]);

  const urgentAiDecisions =
    useMemo(() => {
      return [...aiDecisions]
        .filter(
          (decision) =>
            decision.decision_level ===
              "URGENT" ||
            decision.decision_level ===
              "HIGH"
        )
        .sort(
          (a, b) =>
            (Number(
              b.ai_decision_score
            ) || 0) -
            (Number(
              a.ai_decision_score
            ) || 0)
        );
    }, [aiDecisions]);

  const connectedSystems =
    integrationStatus?.systems?.filter(
      (system) =>
        system.connected === true
    ).length ?? 0;

  const totalSystems =
    integrationStatus?.systems
      ?.length ?? 0;

  /* =======================================================
     SYSTEM STATUS
  ======================================================= */

  const systemState =
    criticalEvents.length > 0
      ? "CRITICAL"
      : openEvents.length > 0 ||
        overdueTasks.length > 0
      ? "ATTENTION"
      : "HEALTHY";

  const systemStateText =
    systemState === "CRITICAL"
      ? "Critical operational attention required"
      : systemState === "ATTENTION"
      ? "Operational attention required"
      : "All monitored systems healthy";

  /* =======================================================
     LOADING SCREEN
  ======================================================= */

  if (pageLoading) {
    return (
      <div
        style={{
          minHeight: "calc(100vh - 76px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background:
            "linear-gradient(135deg, #eef6ff 0%, #f8fbff 50%, #edf5ff 100%)",
          padding: "30px",
        }}
      >

        <div
          style={{
            width: "min(560px, 92vw)",
            background: "rgba(255,255,255,0.96)",
            border: "1px solid #d8e7fa",
            borderRadius: "24px",
            padding: "42px 38px",
            boxShadow:
              "0 20px 60px rgba(29,78,137,0.12)",
            textAlign: "center",
          }}
        >

          <div
            style={{
              width: "76px",
              height: "76px",
              margin: "0 auto 20px",
              borderRadius: "20px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background:
                "linear-gradient(135deg, #0d6efd, #1d4ed8)",
              color: "#fff",
              fontSize: "34px",
              boxShadow:
                "0 12px 30px rgba(13,110,253,0.25)",
            }}
          >
            🚆
          </div>

          <div
            style={{
              fontSize: "12px",
              fontWeight: "800",
              letterSpacing: "2px",
              color: "#2563eb",
              marginBottom: "10px",
            }}
          >
            RAILWAY OPERATIONS CONTROL
          </div>

          <h1
            style={{
              margin: "0 0 10px",
              fontSize: "30px",
              color: "#10213f",
            }}
          >
            Initializing Dashboard
          </h1>

          <p
            style={{
              margin: "0 0 28px",
              color: "#64748b",
              fontSize: "14px",
            }}
          >
            Loading railway operations,
            maintenance and AI intelligence...
          </p>

          <div
            style={{
              height: "8px",
              borderRadius: "999px",
              background: "#e8f0fa",
              overflow: "hidden",
              marginBottom: "12px",
            }}
          >

            <div
              style={{
                width: `${loadProgress}%`,
                height: "100%",
                borderRadius: "999px",
                background:
                  "linear-gradient(90deg, #2563eb, #60a5fa)",
                transition:
                  "width 180ms ease",
              }}
            />

          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "12px",
              color: "#64748b",
            }}
          >

            <span>
              Securing data connections
            </span>

            <strong
              style={{
                color: "#2563eb",
              }}
            >
              {loadProgress}%
            </strong>

          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(3, 1fr)",
              gap: "10px",
              marginTop: "28px",
            }}
          >

            <div
              style={{
                padding: "12px 8px",
                borderRadius: "12px",
                background: "#f4f8ff",
                fontSize: "11px",
                color: "#475569",
              }}
            >
              🚧
              <br />
              Blocks
            </div>

            <div
              style={{
                padding: "12px 8px",
                borderRadius: "12px",
                background: "#f4f8ff",
                fontSize: "11px",
                color: "#475569",
              }}
            >
              🧠
              <br />
              AI Engine
            </div>

            <div
              style={{
                padding: "12px 8px",
                borderRadius: "12px",
                background: "#f4f8ff",
                fontSize: "11px",
                color: "#475569",
              }}
            >
              🚆
              <br />
              Operations
            </div>

          </div>

        </div>

      </div>
    );
  }

  /* =======================================================
     DASHBOARD
  ======================================================= */

  return (
    <div className="home-page">

      {/* =================================================
          HERO
      ================================================= */}

      <section className="home-hero">

        <div className="home-hero-main">

          <span className="home-eyebrow">
            AI-POWERED RAILWAY OPERATIONS
          </span>

          <h1>
            Railway Operations
            Command Center
          </h1>

          <p>
            Unified maintenance planning,
            machine-learning risk analysis,
            dynamic re-planning and
            railway operations monitoring.
          </p>

          {lastUpdated && (
            <span className="home-last-updated">
              Live data loaded{" "}
              {lastUpdated.toLocaleTimeString(
                "en-IN",
                {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                }
              )}
            </span>
          )}

        </div>

        <div
          className={`home-system-status ${statusClass(
            systemState
          )}`}
        >

          <span className="home-system-dot" />

          <div>

            <strong>
              {systemState}
            </strong>

            <span>
              {systemStateText}
            </span>

          </div>

        </div>

      </section>

      {/* =================================================
          ERROR
      ================================================= */}

      {error && (
        <div className="home-error">

          <strong>
            Dashboard Notice:
          </strong>

          {" "}
          {error}

        </div>
      )}

      {/* =================================================
          KPI
      ================================================= */}

      <section className="home-kpi-grid">

        <div className="home-kpi-card">

          <span>
            🚧 Active Blocks
          </span>

          <strong>
            {activeBlocks.length}
          </strong>

          <small>
            {blocks.length} total blocks
          </small>

        </div>

        <div className="home-kpi-card">

          <span>
            🚨 Urgent Tasks
          </span>

          <strong>
            {urgentAiDecisions.length}
          </strong>

          <small>
            AI-prioritized maintenance
          </small>

        </div>

        <div className="home-kpi-card danger">

          <span>
            🧠 Critical ML Assets
          </span>

          <strong>
            {criticalMlAssets.length}
          </strong>

          <small>
            Risk ≥ 80%
          </small>

        </div>

        <div className="home-kpi-card warning">

          <span>
            ⚠️ Open Events
          </span>

          <strong>
            {openEvents.length}
          </strong>

          <small>
            {criticalEvents.length} critical
          </small>

        </div>

        <div className="home-kpi-card">

          <span>
            🚆 Train Services
          </span>

          <strong>
            {trains.length}
          </strong>

          <small>
            Monitored train services
          </small>

        </div>

        <div className="home-kpi-card">

          <span>
            🔧 Overdue Tasks
          </span>

          <strong>
            {overdueTasks.length}
          </strong>

          <small>
            Require maintenance action
          </small>

        </div>

      </section>

      {/* =================================================
          AI COMMAND
      ================================================= */}

      <section className="home-command-grid">

        {/* BEST PLAN */}

        <div className="home-panel">

          <div className="home-panel-header">

            <div>

              <span className="home-section-label">
                AI DECISION ENGINE
              </span>

              <h2>
                🏆 Best Maintenance Plan
              </h2>

              <p>
                Highest-scoring maintenance
                recommendation.
              </p>

            </div>

            <span className="home-panel-icon">
              AI
            </span>

          </div>

          {aiBestPlan ? (

            <div className="home-best-plan">

              <div className="home-best-plan-top">

                <div>

                  <span className="home-recommended-badge">
                    ⭐ AI RECOMMENDED
                  </span>

                  <h3>
                    {aiBestPlan.task_code ??
                      "Maintenance Task"}
                  </h3>

                  <p>
                    Asset{" "}
                    {aiBestPlan.asset_id ?? "—"}
                    {" • "}
                    Section{" "}
                    {aiBestPlan.section_id ?? "—"}
                  </p>

                </div>

                <div className="home-plan-score-circle">

                  <strong>
                    {aiBestPlan.ai_plan_score ??
                      "—"}
                  </strong>

                  <span>
                    PLAN SCORE
                  </span>

                </div>

              </div>

              <div className="home-plan-metrics">

                <div>

                  <span>
                    AI Decision
                  </span>

                  <strong>
                    {aiBestPlan.ai_decision_score ??
                      "—"}
                  </strong>

                </div>

                <div>

                  <span>
                    ML Risk
                  </span>

                  <strong>
                    {aiBestPlan.ml_risk_percentage ??
                      aiBestPlan.asset_risk_score ??
                      "—"}
                    %
                  </strong>

                </div>

                <div>

                  <span>
                    Risk Level
                  </span>

                  <strong>
                    {aiBestPlan.ml_risk_level ??
                      aiBestPlan.combined_risk_level ??
                      "—"}
                  </strong>

                </div>

              </div>

              <div className="home-final-action">

                <span>
                  FINAL ACTION
                </span>

                <strong>
                  {aiBestPlan.final_action ??
                    "PLAN"}
                </strong>

              </div>

              <div className="home-best-plan-reason">

                <strong>
                  AI Recommendation
                </strong>

                <p>
                  {aiBestPlan.recommendation ??
                    "AI-generated recommendation based on operational constraints."}
                </p>

              </div>

            </div>

          ) : (

            <div className="home-empty-panel">
              No AI best plan available.
            </div>

          )}

        </div>

        {/* ML */}

        <div className="home-panel">

          <div className="home-panel-header">

            <div>

              <span className="home-section-label">
                MACHINE LEARNING
              </span>

              <h2>
                🧠 Asset Risk Monitor
              </h2>

              <p>
                ML-predicted asset risk.
              </p>

            </div>

            <span className="home-panel-icon">
              ML
            </span>

          </div>

          <div className="home-risk-list">

            {criticalMlAssets.length >
            0 ? (

              criticalMlAssets
                .slice(0, 5)
                .map((asset) => (

                  <div
                    className="home-risk-item"
                    key={asset.asset_id}
                  >

                    <div>

                      <strong>
                        {asset.asset_code}
                      </strong>

                      <span>
                        {asset.asset_type}
                        {" • "}
                        Section{" "}
                        {asset.section_id}
                      </span>

                    </div>

                    <div className="home-risk-right">

                      <strong>
                        {asset.ml_risk_percentage}%
                      </strong>

                      <span
                        className={`home-risk-badge ${statusClass(
                          asset.ml_risk_level
                        )}`}
                      >
                        {asset.ml_risk_level}
                      </span>

                    </div>

                  </div>

                ))

            ) : (

              <div className="home-empty-panel">
                No critical ML risks detected.
              </div>

            )}

          </div>

          <div className="home-panel-footer">

            <span>
              Model
            </span>

            <strong>
              RandomForestClassifier
            </strong>

          </div>

        </div>

      </section>

      {/* =================================================
          OPERATIONS
      ================================================= */}

      <section className="home-three-grid">

        <div className="home-panel">

          <div className="home-panel-header compact">

            <div>

              <h2>
                🚧 Active Maintenance Blocks
              </h2>

              <p>
                Current operational blocks.
              </p>

            </div>

            <span className="home-count-badge">
              {activeBlocks.length}
            </span>

          </div>

          <div className="home-list">

            {activeBlocks.length > 0 ? (

              activeBlocks
                .slice(0, 5)
                .map((block) => (

                  <div
                    className="home-list-item"
                    key={block.block_id}
                  >

                    <div>

                      <strong>
                        {block.block_code}
                      </strong>

                      <span>
                        SEC
                        {String(
                          block.section_id
                        ).padStart(2, "0")}
                        {" • "}
                        {formatDate(
                          block.block_date
                        )}
                      </span>

                    </div>

                    <div>

                      <strong>
                        {String(
                          block.start_time ?? ""
                        ).slice(0, 5)}
                        {" – "}
                        {String(
                          block.end_time ?? ""
                        ).slice(0, 5)}
                      </strong>

                      <span>
                        {block.status}
                      </span>

                    </div>

                  </div>

                ))

            ) : (

              <div className="home-empty-panel">
                No active maintenance blocks.
              </div>

            )}

          </div>

        </div>

        <div className="home-panel">

          <div className="home-panel-header compact">

            <div>

              <h2>
                ⚠️ Operational Events
              </h2>

              <p>
                Latest operational alerts.
              </p>

            </div>

            <span className="home-count-badge warning">
              {openEvents.length}
            </span>

          </div>

          <div className="home-list">

            {openEvents.length > 0 ? (

              openEvents
                .slice(0, 5)
                .map((event) => (

                  <div
                    className="home-list-item"
                    key={event.event_id}
                  >

                    <div>

                      <strong>
                        {event.event_type}
                      </strong>

                      <span>
                        Section{" "}
                        {event.section_id}
                      </span>

                    </div>

                    <span
                      className={`home-event-badge ${statusClass(
                        event.severity
                      )}`}
                    >
                      {event.severity}
                    </span>

                  </div>

                ))

            ) : (

              <div className="home-empty-panel">
                ✅ No open operational events.
              </div>

            )}

          </div>

        </div>

        <div className="home-panel">

          <div className="home-panel-header compact">

            <div>

              <h2>
                🎯 AI Task Priorities
              </h2>

              <p>
                Highest-priority maintenance
                decisions.
              </p>

            </div>

            <span className="home-count-badge">
              {urgentAiDecisions.length}
            </span>

          </div>

          <div className="home-list">

            {urgentAiDecisions.length > 0 ? (

              urgentAiDecisions
                .slice(0, 5)
                .map((decision) => (

                  <div
                    className="home-list-item"
                    key={decision.task_id}
                  >

                    <div>

                      <strong>
                        {decision.task_code}
                      </strong>

                      <span>
                        {decision.final_action ??
                          "MAINTENANCE"}
                      </span>

                    </div>

                    <div className="home-ai-score">

                      <strong>
                        {decision.ai_decision_score}
                      </strong>

                      <span>
                        {decision.decision_level}
                      </span>

                    </div>

                  </div>

                ))

            ) : (

              <div className="home-empty-panel">
                No urgent AI decisions.
              </div>

            )}

          </div>

        </div>

      </section>

      {/* =================================================
          NETWORK + INTEGRATION
      ================================================= */}

      <section className="home-bottom-grid">

        <div className="home-panel">

          <div className="home-panel-header">

            <div>

              <span className="home-section-label">
                RAILWAY DATA
              </span>

              <h2>
                📊 Network Overview
              </h2>

            </div>

          </div>

          <div className="home-network-grid">

            <div>
              <span>
                Stations
              </span>

              <strong>
                {stations.length}
              </strong>
            </div>

            <div>
              <span>
                Sections
              </span>

              <strong>
                {sections.length}
              </strong>
            </div>

            <div>
              <span>
                Assets
              </span>

              <strong>
                {assets.length}
              </strong>
            </div>

            <div>
              <span>
                Maintenance
              </span>

              <strong>
                {maintenanceTasks.length}
              </strong>
            </div>

            <div>
              <span>
                Open Defects
              </span>

              <strong>
                {openDefects.length}
              </strong>
            </div>

            <div>
              <span>
                Train Services
              </span>

              <strong>
                {trains.length}
              </strong>
            </div>

          </div>

        </div>

        <div className="home-panel">

          <div className="home-panel-header">

            <div>

              <span className="home-section-label">
                INTEGRATION LAYER
              </span>

              <h2>
                🔗 Railway Systems
              </h2>

              <p>
                Unified railway data sources.
              </p>

            </div>

            {integrationStatus && (

              <span
                className={`home-integration-status ${
                  connectedSystems ===
                    totalSystems &&
                  totalSystems > 0
                    ? "connected"
                    : "attention"
                }`}
              >
                {connectedSystems}/
                {totalSystems}
              </span>

            )}

          </div>

          {integrationStatus ? (

            <div className="home-integration-list">

              {integrationStatus.systems?.map(
                (system) => (

                  <div
                    className="home-integration-item"
                    key={system.system}
                  >

                    <div>

                      <span className="home-system-small-dot" />

                      <strong>
                        {system.system}
                      </strong>

                    </div>

                    <span
                      className={
                        system.connected
                          ? "connected-text"
                          : "disconnected-text"
                      }
                    >
                      {system.connected
                        ? "CONNECTED"
                        : "OFFLINE"}
                    </span>

                  </div>

                )
              )}

            </div>

          ) : (

            <div className="home-empty-panel">
              Integration status unavailable.
            </div>

          )}

          {integrationStatus?.mode && (

            <div className="home-integration-note">

              <span>
                Mode
              </span>

              <strong>
                {integrationStatus.mode}
              </strong>

            </div>

          )}

        </div>

      </section>

      {/* =================================================
          AI PIPELINE
      ================================================= */}

      <section className="home-ai-pipeline">

        <div className="home-pipeline-heading">

          <span className="home-section-label">
            INTELLIGENCE PIPELINE
          </span>

          <h2>
            🧠 AI Planning Flow
          </h2>

          <p>
            Railway data moves through ML
            risk prediction, smart priority,
            AI decision making and optimized
            maintenance planning.
          </p>

        </div>

        <div className="home-pipeline">

          <div className="home-pipeline-step">
            <span>01</span>

            <strong>
              TMS / SMMS / TDMS
            </strong>

            <small>
              Maintenance Data
            </small>
          </div>

          <div className="home-pipeline-arrow">
            →
          </div>

          <div className="home-pipeline-step">
            <span>02</span>

            <strong>
              ML Risk
            </strong>

            <small>
              Asset Risk Prediction
            </small>
          </div>

          <div className="home-pipeline-arrow">
            →
          </div>

          <div className="home-pipeline-step">
            <span>03</span>

            <strong>
              Smart Priority
            </strong>

            <small>
              Task Ranking
            </small>
          </div>

          <div className="home-pipeline-arrow">
            →
          </div>

          <div className="home-pipeline-step">
            <span>04</span>

            <strong>
              AI Decision
            </strong>

            <small>
              Operational Action
            </small>
          </div>

          <div className="home-pipeline-arrow">
            →
          </div>

          <div className="home-pipeline-step">
            <span>05</span>

            <strong>
              Best Plan
            </strong>

            <small>
              Optimized Block
            </small>
          </div>

        </div>

      </section>

      {/* =================================================
          FOOTER
      ================================================= */}

      <div className="home-footer-note">

        <span>
          🚆 AI Automatic Railway Block Planner
        </span>

        <span>
          Project Leader:{" "}
          <strong>
            Abhishek Kumar
          </strong>
        </span>

      </div>

    </div>
  );
}

export default Home;