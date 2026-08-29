import { useEffect, useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
} from "recharts";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  // ============================================================
  // STATE
  // ============================================================

  const [stations, setStations] = useState([]);
  const [sections, setSections] = useState([]);
  const [assets, setAssets] = useState([]);
  const [maintenanceTasks, setMaintenanceTasks] = useState([]);
  const [defects, setDefects] = useState([]);
  const [trains, setTrains] = useState([]);
  const [trainSchedule, setTrainSchedule] = useState([]);
  const [goodsForecast, setGoodsForecast] = useState([]);

  const [priorityTasks, setPriorityTasks] = useState([]);
  const [plannedBlocks, setPlannedBlocks] = useState([]);
  const [blockFilter, setBlockFilter] = useState("ALL");
  const [timelineDate, setTimelineDate] = useState("");
  const [blockRecommendations, setBlockRecommendations] = useState([]);
  const [optimizedBlocks, setOptimizedBlocks] = useState([]);

  const [operationalEvents, setOperationalEvents] = useState([]);

  const [assetRisks, setAssetRisks] = useState([]);
  const [smartPriorities, setSmartPriorities] = useState([]);
  const [aiDecisions, setAiDecisions] = useState([]);
  const [aiBestPlan, setAiBestPlan] = useState(null);

  const [adminAnalytics, setAdminAnalytics] = useState(null);

  const [replanResults, setReplanResults] = useState({});
  const [replanningEventId, setReplanningEventId] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [aiAgent, setAiAgent] = useState(null);

  const [agentQuestion, setAgentQuestion] = useState("");
  const [agentAnswer, setAgentAnswer] = useState("");
  const [agentAskLoading, setAgentAskLoading] = useState(false);

  const [agentActionLoading, setAgentActionLoading] = useState(false);
  const [agentActionMessage, setAgentActionMessage] = useState("");

  const [showCreateBlock, setShowCreateBlock] = useState(false);

  const [newBlock, setNewBlock] = useState({
    section_id: "",
    block_date: "",
    start_time: "",
    end_time: "",
    task_ids: [],
  });

  const [createBlockLoading, setCreateBlockLoading] = useState(false);
  const [createBlockMessage, setCreateBlockMessage] = useState("");

  // ============================================================
  // LOAD ALL DASHBOARD DATA
  // ============================================================

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError("");

      const endpointNames = [
        "stations",
        "sections",
        "assets",
        "maintenance-tasks",
        "defects",
        "trains",
        "train-schedule",
        "goods-forecast",
        "priority/tasks",
        "planner/blocks",
        "planner/blocks/recommendations",
        "planner/optimization",
        "events",
        "ai/risk/assets",
        "ai/smart-priority",
        "ai/decisions",
        "ai/best-plan",
        "admin/analytics",
        "ai/agent",
      ];

      const responses = await Promise.all(
        endpointNames.map((endpoint) =>
          fetch(`${API_BASE}/${endpoint}`)
        )
      );

      const failedResponse = responses.find(
        (response) => !response.ok
      );

      if (failedResponse) {
        throw new Error(
          `API request failed with status ${failedResponse.status}`
        );
      }

      const data = await Promise.all(
        responses.map((response) => response.json())
      );

      // ----------------------------------------------------------
      // BASIC DATA
      // ----------------------------------------------------------

      setStations(data[0] || []);
      setSections(data[1] || []);
      setAssets(data[2] || []);
      setMaintenanceTasks(data[3] || []);
      setDefects(data[4] || []);
      setTrains(data[5] || []);
      setTrainSchedule(data[6] || []);
      setGoodsForecast(data[7] || []);

      // ----------------------------------------------------------
      // PLANNING
      // ----------------------------------------------------------

      setPriorityTasks(data[8]?.tasks || []);
      setPlannedBlocks(data[9] || []);
      setBlockRecommendations(
        data[10]?.recommendations || []
      );
      setOptimizedBlocks(
        data[11]?.optimized_blocks || []
      );

      // ----------------------------------------------------------
      // EVENTS
      // ----------------------------------------------------------

      setOperationalEvents(data[12] || []);

      // ----------------------------------------------------------
      // AI
      // ----------------------------------------------------------

      setAssetRisks(data[13]?.assets || []);
      setSmartPriorities(data[14]?.tasks || []);
      setAiDecisions(data[15]?.decisions || []);
      setAiBestPlan(data[16]?.best_plan || null);

      // ----------------------------------------------------------
      // ANALYTICS
      // ----------------------------------------------------------

      setAdminAnalytics(data[17] || null);

      // ----------------------------------------------------------
      // AI AGENT
      // ----------------------------------------------------------

      setAiAgent(data[18] || null);
    } catch (err) {
      console.error("Dashboard error:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // INITIAL LOAD
  // ============================================================

  useEffect(() => {
    loadDashboard();
  }, []);

  // ============================================================
  // DYNAMIC RE-PLANNING
  // ============================================================

  const handleReplan = async (eventId) => {
    try {
      setReplanningEventId(eventId);
      setError("");

      const response = await fetch(
        `${API_BASE}/events/${eventId}/replan`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
          },
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => null);

        throw new Error(
          errorData?.detail ||
            `Re-planning failed with status ${response.status}`
        );
      }

      const data = await response.json();

      setReplanResults((previous) => ({
        ...previous,
        [eventId]: data.replanning_result,
      }));
    } catch (err) {
      console.error("Re-planning error:", err);
      setError(err.message);
    } finally {
      setReplanningEventId(null);
    }
  };

  // ============================================================
  // ASK AI OPERATIONS AGENT
  // ============================================================

  const handleAskAgent = async () => {
    const question = agentQuestion.trim();

    if (!question) {
      setAgentAnswer("Please enter a question.");
      return;
    }

    try {
      setAgentAskLoading(true);
      setAgentAnswer("");
      setError("");

      const response = await fetch(
        `${API_BASE}/ai/agent/ask?question=${encodeURIComponent(
          question
        )}`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
          },
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => null);

        throw new Error(
          errorData?.detail ||
            `AI Agent request failed with status ${response.status}`
        );
      }

      const data = await response.json();

      setAgentAnswer(
        data.answer ||
          "No answer received from AI Agent."
      );
    } catch (err) {
      console.error("Ask Agent error:", err);

      setAgentAnswer(
        `Unable to contact AI Agent: ${err.message}`
      );
    } finally {
      setAgentAskLoading(false);
    }
  };

  // ============================================================
  // AI AGENT REPLAN
  // ============================================================

  const handleAgentReplan = async (eventId) => {
    try {
      setAgentActionLoading(true);
      setAgentActionMessage("");
      setError("");

      const response = await fetch(
        `${API_BASE}/events/${eventId}/replan`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
          },
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => null);

        throw new Error(
          errorData?.detail ||
            `Agent re-plan failed with status ${response.status}`
        );
      }

      const data = await response.json();

      setReplanResults((previous) => ({
        ...previous,
        [eventId]: data.replanning_result,
      }));

      setAgentActionMessage(
        `✅ AI Agent completed re-planning for Event #${eventId}.`
      );
    } catch (err) {
      console.error("Agent re-plan error:", err);

      setAgentActionMessage(
        `❌ Agent action failed: ${err.message}`
      );
    } finally {
      setAgentActionLoading(false);
    }
  };

  // ============================================================
  // APPLY AI AGENT REPLAN
  // ============================================================

  const handleApplyAgentReplan = async (eventId) => {
    try {
      setAgentActionLoading(true);
      setAgentActionMessage("");
      setError("");

      const response = await fetch(
        `${API_BASE}/events/${eventId}/apply-replan`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
          },
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => null);

        throw new Error(
          errorData?.detail ||
            `Apply re-plan failed with status ${response.status}`
        );
      }

      const data = await response.json();

      setAgentActionMessage(
        data.applied_blocks?.length
          ? `✅ AI Agent applied re-planning to ${data.applied_blocks.length} block(s).`
          : "ℹ️ No block required a timing change."
      );

      await loadDashboard();
    } catch (err) {
      console.error(
        "Apply agent re-plan error:",
        err
      );

      setAgentActionMessage(
        `❌ Apply action failed: ${err.message}`
      );
    } finally {
      setAgentActionLoading(false);
    }
  };

  // ============================================================
  // CREATE MAINTENANCE BLOCK
  // ============================================================

  const handleCreateBlock = async () => {
    if (
      !newBlock.section_id ||
      !newBlock.block_date ||
      !newBlock.start_time ||
      !newBlock.end_time ||
      newBlock.task_ids.length === 0
    ) {
      setCreateBlockMessage(
        "Please fill all fields and select at least one task."
      );
      return;
    }

    try {
      setCreateBlockLoading(true);
      setCreateBlockMessage("");
      setError("");

      const response = await fetch(
        `${API_BASE}/planner/create-block?section_id=${newBlock.section_id}&block_date=${newBlock.block_date}&start_time=${newBlock.start_time}&end_time=${newBlock.end_time}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(newBlock.task_ids),
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => null);

        throw new Error(
          errorData?.detail ||
            `Block creation failed with status ${response.status}`
        );
      }

      const data = await response.json();

      setCreateBlockMessage(
        `✅ ${
          data.message ||
          "Maintenance block created successfully."
        }`
      );

      setNewBlock({
        section_id: "",
        block_date: "",
        start_time: "",
        end_time: "",
        task_ids: [],
      });

      await loadDashboard();
    } catch (err) {
      console.error("Create block error:", err);

      setCreateBlockMessage(
        `❌ ${err.message}`
      );
    } finally {
      setCreateBlockLoading(false);
    }
  };

  // ============================================================
  // UPDATE BLOCK STATUS
  // ============================================================

  const handleBlockStatusChange = async (
    blockId,
    newStatus
  ) => {
    try {
      setError("");

      const response = await fetch(
        `${API_BASE}/planner/blocks/${blockId}/status?new_status=${encodeURIComponent(
          newStatus
        )}`,
        {
          method: "PATCH",
          headers: {
            Accept: "application/json",
          },
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => null);

        throw new Error(
          errorData?.detail ||
            `Status update failed with status ${response.status}`
        );
      }

      await response.json();
      await loadDashboard();
    } catch (err) {
      console.error(
        "Block status update error:",
        err
      );

      setError(err.message);
    }
  };

  // ============================================================
  // DERIVED DATA
  // ============================================================

  const stationMap = useMemo(() => {
    return Object.fromEntries(
      stations.map((station) => [
        station.station_id,
        station.station_name,
      ])
    );
  }, [stations]);

  const networkStations = useMemo(() => {
    if (sections.length === 0) {
      return [];
    }

    const result = [];
    const firstSection = sections[0];

    result.push({
      type: "station",
      name:
        stationMap[firstSection.from_station_id] ||
        `Station ${firstSection.from_station_id}`,
    });

    sections.forEach((section) => {
      result.push({
        type: "section",
        name: section.section_code,
      });

      result.push({
        type: "station",
        name:
          stationMap[section.to_station_id] ||
          `Station ${section.to_station_id}`,
      });
    });

    return result;
  }, [sections, stationMap]);

  const openDefects = defects.filter(
    (defect) => defect.status === "OPEN"
  );

  const overdueTasks = maintenanceTasks.filter(
    (task) => task.status === "OVERDUE"
  );

  const criticalAssets = assets.filter(
    (asset) => asset.criticality === "CRITICAL"
  );

  // ============================================================
  // BLOCK FILTERING
  // ============================================================

  const filteredBlocks = useMemo(() => {
    if (blockFilter === "ALL") {
      return plannedBlocks;
    }

    if (blockFilter === "REPLAN_REQUIRED") {
      return plannedBlocks.filter(
        (block) => block.replan_required === true
      );
    }

    return plannedBlocks.filter(
      (block) => block.status === blockFilter
    );
  }, [plannedBlocks, blockFilter]);

  // ============================================================
// TIMELINE FILTERING
// ============================================================


const timelineBlocks = useMemo(() => {
  if (!timelineDate) {
    return plannedBlocks;
  }

  return plannedBlocks.filter(
    (block) => block.block_date === timelineDate
  );
}, [plannedBlocks, timelineDate]);

  // ============================================================
  // CHART DATA
  // ============================================================

  const riskChartData = adminAnalytics
    ? [
        {
          name: "Low",
          value:
            adminAnalytics.ai?.risk_distribution?.LOW || 0,
        },
        {
          name: "Medium",
          value:
            adminAnalytics.ai?.risk_distribution?.MEDIUM || 0,
        },
        {
          name: "High",
          value:
            adminAnalytics.ai?.risk_distribution?.HIGH || 0,
        },
        {
          name: "Critical",
          value:
            adminAnalytics.ai?.risk_distribution?.CRITICAL ||
            0,
        },
      ]
    : [];

  const maintenanceChartData = adminAnalytics
    ? [
        {
          name: "Pending",
          value:
            adminAnalytics.maintenance?.status_counts
              ?.PENDING || 0,
        },
        {
          name: "Completed",
          value:
            adminAnalytics.maintenance?.status_counts
              ?.COMPLETED || 0,
        },
        {
          name: "Overdue",
          value:
            adminAnalytics.maintenance?.status_counts
              ?.OVERDUE || 0,
        },
        {
          name: "Cancelled",
          value:
            adminAnalytics.maintenance?.status_counts
              ?.CANCELLED || 0,
        },
      ]
    : [];

  const aiDecisionChartData = adminAnalytics
    ? [
        {
          name: "Urgent",
          value:
            adminAnalytics.ai?.decision_distribution
              ?.URGENT || 0,
        },
        {
          name: "High",
          value:
            adminAnalytics.ai?.decision_distribution
              ?.HIGH || 0,
        },
        {
          name: "Medium",
          value:
            adminAnalytics.ai?.decision_distribution
              ?.MEDIUM || 0,
        },
        {
          name: "Low",
          value:
            adminAnalytics.ai?.decision_distribution
              ?.LOW || 0,
        },
      ]
    : [];

  // ============================================================
// EXECUTIVE SYSTEM HEALTH
// ============================================================

const systemHealth = useMemo(() => {
  if (!adminAnalytics) {
    return {
      operational: "LOADING",
      maintenance: "LOADING",
      assetRisk: "LOADING",
      trainImpact: "LOADING",
      aiPlanning: "LOADING",
    };
  }

  const kpis =
    adminAnalytics.operational_kpis || {};

  const ai =
    adminAnalytics.ai || {};

  const impact =
    adminAnalytics.train_block_impact || {};

  return {
    operational:
      (kpis.open_operational_events || 0) === 0
        ? "HEALTHY"
        : "ATTENTION",

    maintenance:
      (kpis.overdue_tasks || 0) === 0
        ? "HEALTHY"
        : "ATTENTION",

    assetRisk:
      (ai.risk_distribution?.CRITICAL || 0) === 0
        ? "HEALTHY"
        : "CRITICAL",

    trainImpact:
      (impact.high_impact_blocks || 0) === 0 &&
      (impact.total_conflicts || 0) === 0
        ? "HEALTHY"
        : "ATTENTION",

    aiPlanning:
      (ai.urgent_ai_decisions || 0) > 0
        ? "ACTIVE"
        : "NORMAL",
  };
}, [adminAnalytics]);


// ============================================================
// TIMELINE BLOCK POSITION
// ============================================================

const getTimelineBlockStyle = (block) => {
  const TIMELINE_START = 8 * 60;   // 08:00
  const TIMELINE_END = 20 * 60;    // 20:00

  const TOTAL_MINUTES =
    TIMELINE_END - TIMELINE_START;

  const parseTime = (value) => {
    if (!value) {
      return 0;
    }

    const [hours, minutes] = String(value)
      .split(":")
      .map(Number);

    return hours * 60 + minutes;
  };

  const blockStart = parseTime(
    block.start_time
  );

  const blockEnd = parseTime(
    block.end_time
  );

  const safeStart = Math.max(
    blockStart,
    TIMELINE_START
  );

  const safeEnd = Math.min(
    blockEnd,
    TIMELINE_END
  );

  const left =
    ((safeStart - TIMELINE_START) /
      TOTAL_MINUTES) *
    100;

  const width =
    ((safeEnd - safeStart) /
      TOTAL_MINUTES) *
    100;

  return {
    left: `${Math.max(left, 0)}%`,
    width: `${Math.max(width, 1)}%`,
  };
};


// ============================================================
// TIMELINE TRAIN POSITION
// ============================================================

const getTimelineTrainStyle = (train) => {
  const TIMELINE_START = 8 * 60;   // 08:00
  const TIMELINE_END = 20 * 60;    // 20:00

  const TOTAL_MINUTES =
    TIMELINE_END - TIMELINE_START;

  const parseTime = (value) => {
    if (!value) {
      return 0;
    }

    const [hours, minutes] = String(value)
      .split(":")
      .map(Number);

    return hours * 60 + minutes;
  };

  const arrival = parseTime(
    train.arrival_time
  );

  const departure = parseTime(
    train.departure_time
  );

  const safeStart = Math.max(
    arrival,
    TIMELINE_START
  );

  const safeEnd = Math.min(
    departure,
    TIMELINE_END
  );

  const left =
    ((safeStart - TIMELINE_START) /
      TOTAL_MINUTES) *
    100;

  const width =
    ((safeEnd - safeStart) /
      TOTAL_MINUTES) *
    100;

  return {
    left: `${Math.max(left, 0)}%`,
    width: `${Math.max(width, 1)}%`,
  };
};


// ============================================================
// TIMELINE BLOCK IMPACT
// ============================================================

const getBlockImpact = (block) => {
  const recommendation =
    blockRecommendations.find(
      (item) =>
        item.block_id === block.block_id
    );

  if (!recommendation) {
    return {
      conflict: false,
      impact: "NONE",
      affectedTrains: [],
      recommendation: null,
    };
  }

  return {
    conflict:
      (recommendation.conflict_count || 0) > 0,

    impact:
      recommendation.impact_level || "NONE",

    affectedTrains:
      recommendation.affected_train_ids || [],

    recommendation:
      recommendation.recommendation || null,
  };
};


// ============================================================
// ACTIVE AI AGENT ALERTS
// ============================================================

const activeAgentAlerts =
  aiAgent?.alerts?.filter(
    (alert) => alert?.status === "OPEN"
  ) || [];


// ============================================================
// RETURN
// ============================================================

return (
  <div className="app">

    {/* ========================================================
        HEADER
        ======================================================== */}

    <header className="header">

      <div>

        <h1>
          🚆 AI Automatic Railway Block Planner
        </h1>

        <p>
          Railway Maintenance & Operations Dashboard
        </p>

      </div>

      <div className="header-status">

        <span className="status-dot"></span>

        System Online

      </div>

    </header>

    <main className="container">

      {/* ======================================================
          GLOBAL ERROR
          ====================================================== */}

      {error && (

        <div className="global-error">

          <strong>
            Backend connection error:
          </strong>{" "}

          {error}

        </div>

      )}

      {/* ======================================================
          TOP STATS
          ====================================================== */}

      <section className="stats-grid">

        <div className="stat-card">

          <span className="stat-icon">
            🚉
          </span>

          <div>

            <h3>
              Stations
            </h3>

            <strong>
              {stations.length}
            </strong>

          </div>

        </div>


        <div className="stat-card">

          <span className="stat-icon">
            🛤️
          </span>

          <div>

            <h3>
              Sections
            </h3>

            <strong>
              {sections.length}
            </strong>

          </div>

        </div>


        <div className="stat-card">

          <span className="stat-icon">
            ⚙️
          </span>

          <div>

            <h3>
              Assets
            </h3>

            <strong>
              {assets.length}
            </strong>

          </div>

        </div>


        <div className="stat-card">

          <span className="stat-icon">
            🔧
          </span>

          <div>

            <h3>
              Maintenance Tasks
            </h3>

            <strong>
              {maintenanceTasks.length}
            </strong>

          </div>

        </div>


        <div className="stat-card">

          <span className="stat-icon">
            ⚠️
          </span>

          <div>

            <h3>
              Open Defects
            </h3>

            <strong>
              {openDefects.length}
            </strong>

          </div>

        </div>


        <div className="stat-card">

          <span className="stat-icon">
            🚆
          </span>

          <div>

            <h3>
              Trains
            </h3>

            <strong>
              {trains.length}
            </strong>

          </div>

        </div>

      </section>
        {/* ======================================================
            EXECUTIVE MANAGEMENT SUMMARY
            ====================================================== */}

        <section className="executive-panel">

          <div className="executive-header">

            <div>
              <h2>
                🎯 Executive Management Summary
              </h2>

              <p>
                Real-time overview of operational health,
                asset risk and AI maintenance decisions
              </p>
            </div>

            <span className="executive-live">
              ● LIVE SYSTEM
            </span>

          </div>

          <div className="executive-cards">

            <div className="executive-card">
              <span>🏆 AI Best Plan</span>

              <strong>
                {aiBestPlan?.task_code || "N/A"}
              </strong>

              <small>
                Score:{" "}
                {aiBestPlan?.ai_plan_score ?? "N/A"}
              </small>
            </div>

            <div className="executive-card">
              <span>
                ⚠️ Critical Risk Assets
              </span>

              <strong>
                {adminAnalytics?.ai?.risk_distribution
                  ?.CRITICAL ?? 0}
              </strong>

              <small>
                Assets requiring attention
              </small>
            </div>

            <div className="executive-card">
              <span>🛤️ Active Blocks</span>

              <strong>
                {adminAnalytics?.operational_kpis
                  ?.active_blocks ?? 0}
              </strong>

              <small>
                Currently active
              </small>
            </div>

            <div className="executive-card">
              <span>
                🤖 Urgent AI Decisions
              </span>

              <strong>
                {adminAnalytics?.ai
                  ?.urgent_ai_decisions ?? 0}
              </strong>

              <small>
                Immediate attention
              </small>
            </div>

          </div>

          <div className="system-health">

            <h3>
              🩺 Overall System Health
            </h3>

            <div className="health-grid">

              <div
                className={`health-item health-${systemHealth.operational.toLowerCase()}`}
              >
                <span>
                  Operational Status
                </span>

                <strong>
                  {systemHealth.operational}
                </strong>
              </div>

              <div
                className={`health-item health-${systemHealth.maintenance.toLowerCase()}`}
              >
                <span>
                  Maintenance Status
                </span>

                <strong>
                  {systemHealth.maintenance}
                </strong>
              </div>

              <div
                className={`health-item health-${systemHealth.assetRisk.toLowerCase()}`}
              >
                <span>Asset Risk</span>

                <strong>
                  {systemHealth.assetRisk}
                </strong>
              </div>

              <div
                className={`health-item health-${systemHealth.trainImpact.toLowerCase()}`}
              >
                <span>
                  Train Impact
                </span>

                <strong>
                  {systemHealth.trainImpact}
                </strong>
              </div>

              <div
                className={`health-item health-${systemHealth.aiPlanning.toLowerCase()}`}
              >
                <span>
                  AI Planning
                </span>

                <strong>
                  {systemHealth.aiPlanning}
                </strong>
              </div>

            </div>

          </div>

          <div className="management-message">

            <strong>
              💡 Management Recommendation
            </strong>

            <p>
              {aiBestPlan?.recommendation ||
                "No AI recommendation is currently available."}
            </p>

          </div>

        </section>

        {/* ======================================================
            OPERATIONS CONTROL CENTER
            ====================================================== */}

        <section className="panel operations-control-panel">

          <div className="panel-header">

            <div>
              <h2>
                👷 Operations Control Center
              </h2>

              <p>
                Real-time maintenance block workflow
                and operational status
              </p>
            </div>

            <span className="panel-count">
              Live Operations
            </span>

          </div>

          {/* OPERATIONS KPIs */}

          <div className="analytics-kpi-grid">

            <div className="analytics-kpi">
              <span>📋 Planned</span>

              <strong>
                {
                  plannedBlocks.filter(
                    (block) =>
                      block.status === "PLANNED"
                  ).length
                }
              </strong>
            </div>

            <div className="analytics-kpi">
              <span>✅ Approved</span>

              <strong>
                {
                  plannedBlocks.filter(
                    (block) =>
                      block.status === "APPROVED"
                  ).length
                }
              </strong>
            </div>

            <div className="analytics-kpi">
              <span>🚧 In Progress</span>

              <strong>
                {
                  plannedBlocks.filter(
                    (block) =>
                      block.status === "IN_PROGRESS"
                  ).length
                }
              </strong>
            </div>

            <div className="analytics-kpi">
              <span>✔ Completed</span>

              <strong>
                {
                  plannedBlocks.filter(
                    (block) =>
                      block.status === "COMPLETED"
                  ).length
                }
              </strong>
            </div>

            <div className="analytics-kpi">
              <span>❌ Cancelled</span>

              <strong>
                {
                  plannedBlocks.filter(
                    (block) =>
                      block.status === "CANCELLED"
                  ).length
                }
              </strong>
            </div>

            <div className="analytics-kpi">
              <span>⚠️ Re-plan Required</span>

              <strong>
                {
                  plannedBlocks.filter(
                    (block) =>
                      block.replan_required === true
                  ).length
                }
              </strong>
            </div>

          </div>

          {/* ACTIVE OPERATIONS */}

          <div className="analytics-section">

            <h3>
              🚦 Active Maintenance Operations
            </h3>

            {plannedBlocks.filter(
              (block) =>
                block.status === "APPROVED" ||
                block.status === "IN_PROGRESS"
            ).length === 0 ? (

              <p className="empty-state">
                No approved or in-progress
                maintenance blocks.
              </p>

            ) : (

              <div className="table-container">

                <table>

                  <thead>
                    <tr>
                      <th>Block</th>
                      <th>Section</th>
                      <th>Date</th>
                      <th>Time</th>
                      <th>Tasks</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>

                  <tbody>

                    {plannedBlocks
                      .filter(
                        (block) =>
                          block.status === "APPROVED" ||
                          block.status === "IN_PROGRESS"
                      )
                      .map((block) => (

                        <tr
                          key={block.block_id}
                        >

                          <td>
                            <strong>
                              {block.block_code}
                            </strong>
                          </td>

                          <td>
                            SEC
                            {String(
                              block.section_id
                            ).padStart(2, "0")}
                          </td>

                          <td>
                            {block.block_date}
                          </td>

                          <td>
                            {block.start_time}{" "}
                            –{" "}
                            {block.end_time}
                          </td>

                          <td>
                            {block.task_ids?.join(", ") ||
                              "—"}
                          </td>

                          <td>
                            <span
                              className={`badge status-${block.status?.toLowerCase()}`}
                            >
                              {block.status}
                            </span>
                          </td>

                          <td>

                            {block.status ===
                              "APPROVED" && (

                              <button
                                className="replan-button"
                                onClick={() =>
                                  handleBlockStatusChange(
                                    block.block_id,
                                    "IN_PROGRESS"
                                  )
                                }
                              >
                                ▶ Start Work
                              </button>

                            )}

                            {block.status ===
                              "IN_PROGRESS" && (

                              <button
                                className="replan-button"
                                onClick={() =>
                                  handleBlockStatusChange(
                                    block.block_id,
                                    "COMPLETED"
                                  )
                                }
                              >
                                ✅ Complete
                              </button>

                            )}

                          </td>

                        </tr>

                      ))}

                  </tbody>

                </table>

              </div>

            )}

          </div>

        </section>

        {/* ======================================================
            ASK AI OPERATIONS AGENT
            ====================================================== */}

        <section className="panel ask-agent-panel">

          <div className="panel-header">

            <div>
              <h2>
                💬 Ask AI Operations Agent
              </h2>

              <p>
                Ask questions about railway operations,
                maintenance, risks and scheduling
              </p>
            </div>

            <span className="panel-count">
              AI Assistant
            </span>

          </div>

          <div className="ask-agent-box">

            <input
              type="text"
              value={agentQuestion}
              onChange={(event) =>
                setAgentQuestion(event.target.value)
              }
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  handleAskAgent();
                }
              }}
              placeholder="Ask: Why is SMMS001 urgent?"
            />

            <button
              className="ask-agent-button"
              onClick={handleAskAgent}
              disabled={agentAskLoading}
            >
              {agentAskLoading
                ? "⏳ Thinking..."
                : "🤖 Ask Agent"}
            </button>

          </div>

          <div className="example-questions">

            <button
              onClick={() =>
                setAgentQuestion(
                  "Why is SMMS001 urgent?"
                )
              }
            >
              Why is SMMS001 urgent?
            </button>

            <button
              onClick={() =>
                setAgentQuestion(
                  "What is the current system status?"
                )
              }
            >
              System status?
            </button>

            <button
              onClick={() =>
                setAgentQuestion(
                  "Are there any train delays?"
                )
              }
            >
              Train delays?
            </button>

            <button
              onClick={() =>
                setAgentQuestion(
                  "What is the best maintenance plan?"
                )
              }
            >
              Best maintenance plan?
            </button>

          </div>

          {agentAnswer && (
            <div className="agent-answer-box">

              <div className="agent-answer-title">
                🤖 AI Agent
              </div>

              <p>
                {agentAnswer}
              </p>

            </div>
          )}

        </section>

        {/* ======================================================
            AI OPERATIONS AGENT
            ====================================================== */}

        {aiAgent && (
          <section className="panel ai-agent-panel">

            <div className="panel-header">

              <div>
                <h2>
                  🤖 AI Operations Agent
                </h2>

                <p>
                  Intelligent monitoring, diagnosis
                  and maintenance recommendations
                </p>
              </div>

              <span
                className={`badge ${
                  aiAgent.agent_status ===
                  "URGENT"
                    ? "critical"
                    : aiAgent.agent_status ===
                      "ATTENTION"
                    ? "high"
                    : "low"
                }`}
              >
                ● {aiAgent.agent_status}
              </span>

            </div>

            {/* AGENT SUMMARY */}

            <div className="agent-summary">

              <div className="agent-summary-card">
                <span>Open Events</span>
                <strong>
                  {aiAgent.open_events ?? 0}
                </strong>
              </div>

              <div className="agent-summary-card">
                <span>Critical Assets</span>
                <strong>
                  {aiAgent.critical_assets ?? 0}
                </strong>
              </div>

              <div className="agent-summary-card">
                <span>
                  Urgent AI Decisions
                </span>

                <strong>
                  {aiAgent.urgent_ai_decisions ?? 0}
                </strong>
              </div>

              <div className="agent-summary-card">
                <span>
                  Conflicted Blocks
                </span>

                <strong>
                  {aiAgent.conflicted_blocks ?? 0}
                </strong>
              </div>

            </div>

            {/* AGENT ANALYSIS */}

            <div className="agent-message">

              <strong>
                🧠 Agent Analysis
              </strong>

              <p>
                {aiAgent.summary}
              </p>

            </div>

            {/* BEST PLAN */}

            {aiAgent.best_plan && (
              <div className="agent-best-plan">

                <div className="agent-best-header">

                  <div>

                    <span>
                      🏆 Recommended Maintenance Plan
                    </span>

                    <h3>
                      {aiAgent.best_plan.task_code}
                    </h3>

                    <p>
                      Asset{" "}
                      {aiAgent.best_plan.asset_id}
                      {" · "}
                      Section{" "}
                      {aiAgent.best_plan.section_id}
                    </p>

                  </div>

                  <div className="agent-plan-score">

                    <span>
                      AI Plan Score
                    </span>

                    <strong>
                      {aiAgent.best_plan.ai_plan_score}
                    </strong>

                  </div>

                </div>

                <div className="agent-plan-details">

                  <div>
                    <span>Risk</span>

                    <strong>
                      {aiAgent.best_plan.risk_level}
                    </strong>
                  </div>

                  <div>
                    <span>AI Decision</span>

                    <strong>
                      {aiAgent.best_plan.ai_decision_score}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Smart Priority
                    </span>

                    <strong>
                      {aiAgent.best_plan.smart_priority_score}
                    </strong>
                  </div>

                  <div>
                    <span>Final Action</span>

                    <strong>
                      {aiAgent.best_plan.final_action}
                    </strong>
                  </div>

                </div>

                <div className="agent-recommendation">

                  <strong>
                    💡 Agent Recommendation
                  </strong>

                  <p>
                    {aiAgent.best_plan.recommendation}
                  </p>

                </div>

              </div>
            )}

{/* ================= ACTIVE OPERATIONAL ALERTS ================= */}

{/* ============================================================
    ACTIVE OPERATIONAL ALERTS
    ============================================================ */}

{(() => {
  const activeAlerts =
    aiAgent?.alerts?.filter(
      (alert) => alert?.status === "OPEN"
    ) || [];

  return (
    <div className="agent-section">

      <h3>
        🚨 Active Operational Alerts
      </h3>

      {activeAlerts.length === 0 ? (

        <p className="empty-state">
          ✅ No active operational alerts.
        </p>

      ) : (

        <div className="agent-alert-list">

          {activeAlerts.map((alert) => (

            <div
              className="agent-alert-card"
              key={alert.event_id}
            >

              {/* ALERT INFORMATION */}

              <div>

                <strong>
                  {alert.event_type === "TRAIN_DELAY"
                    ? "🚆 Train Delay"
                    : alert.event_type === "DEFECT"
                    ? "🔧 Defect"
                    : "⚠️ Operational Event"}
                </strong>

                <p>
                  {alert.description ||
                    `Event #${alert.event_id}`}
                </p>

                <small>
                  Section {alert.section_id}

                  {alert.train_id !== null &&
                    alert.train_id !== undefined
                    ? ` · Train ${alert.train_id}`
                    : ""}
                </small>

              </div>

              {/* SEVERITY */}

              <span
                className={`badge ${(
                  alert.severity || "MEDIUM"
                ).toLowerCase()}`}
              >
                {alert.severity || "MEDIUM"}
              </span>

            </div>

          ))}

        </div>

      )}

    </div>
  );
})()}
           {/* ================= AGENT ACTION CENTER ================= */}

<div className="agent-section">

  <h3>
    ⚙️ AI Agent Action Center
  </h3>

  {activeAgentAlerts.length === 0 ? (

    <p className="empty-state">
      ✅ No operational action is currently required.
    </p>

  ) : (

    <div className="agent-action-list">

      {activeAgentAlerts.map((alert) => (

        <div
          className="agent-action-card"
          key={alert.event_id}
        >

          <div className="agent-action-info">

            <strong>
              {alert.event_type === "TRAIN_DELAY"
                ? "🚆 Train Delay Event"
                : alert.event_type === "DEFECT"
                ? "🔧 Defect Event"
                : "⚠️ Operational Event"}
            </strong>

            <p>
              {alert.description ||
                `Event #${alert.event_id}`}
            </p>

            <small>
              Section {alert.section_id}

              {alert.train_id !== null &&
                alert.train_id !== undefined
                ? ` · Train ${alert.train_id}`
                : ""}
            </small>

          </div>

          <div className="agent-action-buttons">

            {replanResults[alert.event_id] ? (

              <button
                className="replan-button"
                onClick={() =>
                  handleApplyAgentReplan(
                    alert.event_id
                  )
                }
                disabled={agentActionLoading}
              >
                {agentActionLoading
                  ? "⏳ Applying..."
                  : "✅ Apply Replan"}
              </button>

            ) : (

              <button
                className="replan-button"
                onClick={() =>
                  handleAgentReplan(
                    alert.event_id
                  )
                }
                disabled={agentActionLoading}
              >
                {agentActionLoading
                  ? "⏳ Processing..."
                  : "🔄 AI Replan"}
              </button>

            )}

          </div>

        </div>

      ))}

    </div>

  )}

  {agentActionMessage && (

    <div className="agent-action-message">
      {agentActionMessage}
    </div>

  )}

</div>

            {/* AGENT RECOMMENDED ACTIONS */}

            {aiAgent.agent_actions?.length > 0 && (
              <div className="agent-section">

                <h3>
                  ⚙️ Agent Recommended Actions
                </h3>

                <div className="agent-actions">

                  {aiAgent.agent_actions.map(
                    (action, index) => (

                      <div
                        className="agent-action-item"
                        key={index}
                      >

                        <span>→</span>

                        <p>
                          {action}
                        </p>

                      </div>

                    )
                  )}

                </div>

              </div>
            )}

          </section>
        )}

        {/* ======================================================
            LOADING
            ====================================================== */}

        {loading && (
          <section className="panel loading-panel">

            <div className="loader"></div>

            <p>
              Loading railway data...
            </p>

          </section>
        )}

        {!loading && (
          <>

            {/* ==================================================
                RAILWAY NETWORK
                ================================================== */}

            <section className="panel">

              <div className="panel-header">

                <div>
                  <h2>
                    Railway Network
                  </h2>

                  <p>
                    Connected railway sections
                  </p>
                </div>

                <span className="panel-count">
                  {sections.length} Sections
                </span>

              </div>

              <div className="network">

                {networkStations.map(
                  (item, index) =>
                    item.type === "station" ? (

                      <div
                        className="network-station"
                        key={`station-${index}`}
                      >
                        <span>🚉</span>
                        {item.name}
                      </div>

                    ) : (

                      <div
                        className="network-section"
                        key={`section-${index}`}
                      >
                        {item.name}
                      </div>

                    )
                )}

              </div>

            </section>

            {/* ==================================================
                BASIC DATA GRID
                ================================================== */}

            <section className="dashboard-grid">

              {/* MAINTENANCE */}

              <div className="panel">

                <div className="panel-header">

                  <div>
                    <h2>
                      Maintenance Tasks
                    </h2>

                    <p>
                      Current maintenance workload
                    </p>
                  </div>

                  <span className="panel-count">
                    {maintenanceTasks.length}
                  </span>

                </div>

                <div className="table-container">

                  <table>

                    <thead>
                      <tr>
                        <th>Task</th>
                        <th>Source</th>
                        <th>Severity</th>
                        <th>Status</th>
                      </tr>
                    </thead>

                    <tbody>

                      {maintenanceTasks.map(
                        (task) => (

                          <tr
                            key={task.task_id}
                          >

                            <td>
                              <strong>
                                {task.task_code}
                              </strong>

                              <small>
                                {task.task_type}
                              </small>
                            </td>

                            <td>
                              {task.source_system}
                            </td>

                            <td>
                              <span
                                className={`badge ${(
                                  task.severity ||
                                  "MEDIUM"
                                ).toLowerCase()}`}
                              >
                                {task.severity}
                              </span>
                            </td>

                            <td>
                              <span
                                className={`badge status-${(
                                  task.status || ""
                                ).toLowerCase()}`}
                              >
                                {task.status}
                              </span>
                            </td>

                          </tr>

                        )
                      )}

                    </tbody>

                  </table>

                </div>

              </div>

              {/* DEFECTS */}

              <div className="panel">

                <div className="panel-header">

                  <div>
                    <h2>
                      Open Defects
                    </h2>

                    <p>
                      Safety-related issues
                    </p>
                  </div>

                  <span className="panel-count danger-count">
                    {openDefects.length}
                  </span>

                </div>

                <div className="defect-list">

                  {openDefects.map(
                    (defect) => (

                      <div
                        className="defect-card"
                        key={defect.defect_id}
                      >

                        <div className="defect-main">

                          <div className="defect-code">
                            {defect.defect_code}
                          </div>

                          <div>

                            <h3>
                              {defect.description}
                            </h3>

                            <p>
                              Asset{" "}
                              {defect.asset_id}
                              {" · "}
                              Section{" "}
                              {defect.section_id}
                            </p>

                          </div>

                        </div>

                        <span
                          className={`badge ${(
                            defect.severity ||
                            "MEDIUM"
                          ).toLowerCase()}`}
                        >
                          {defect.severity}
                        </span>

                      </div>

                    )
                  )}

                  {openDefects.length === 0 && (
                    <p className="empty-state">
                      No open defects.
                    </p>
                  )}

                </div>

              </div>

              {/* TRAINS */}

              <div className="panel">

                <div className="panel-header">

                  <div>
                    <h2>
                      Train Operations
                    </h2>

                    <p>
                      Active train information
                    </p>
                  </div>

                  <span className="panel-count">
                    {trains.length}
                  </span>

                </div>

                <div className="train-list">

                  {trains.map(
                    (train) => (

                      <div
                        className="train-card"
                        key={train.train_id}
                      >

                        <div className="train-number">
                          🚆 {train.train_no}
                        </div>

                        <div className="train-info">

                          <h3>
                            {train.train_name}
                          </h3>

                          <p>
                            {train.train_type}
                          </p>

                        </div>

                        <span
                          className={`badge ${(
                            train.priority ||
                            "MEDIUM"
                          ).toLowerCase()}`}
                        >
                          {train.priority}
                        </span>

                      </div>

                    )
                  )}

                </div>

              </div>

              {/* GOODS FORECAST */}

              <div className="panel">

                <div className="panel-header">

                  <div>
                    <h2>
                      Goods Forecast
                    </h2>

                    <p>
                      Expected goods train movement
                    </p>
                  </div>

                  <span className="panel-count">
                    {goodsForecast.length}
                  </span>

                </div>

                <div className="forecast-list">

                  {goodsForecast.map(
                    (forecast) => (

                      <div
                        className="forecast-card"
                        key={forecast.forecast_id}
                      >

                        <div>

                          <h3>
                            Section{" "}
                            {forecast.section_id}
                          </h3>

                          <p>
                            {forecast.forecast_date}
                          </p>

                        </div>

                        <strong>
                          {
                            forecast.expected_goods_trains
                          }
                        </strong>

                      </div>

                    )
                  )}

                </div>

              </div>

            </section>

            {/* ==================================================
                PRIORITY QUEUE
                ================================================== */}

            <section className="panel">

              <div className="panel-header">

                <div>
                  <h2>
                    🔥 Maintenance Priority Queue
                  </h2>

                  <p>
                    Tasks ranked by operational urgency
                  </p>
                </div>

                <span className="panel-count">
                  {priorityTasks.length} Tasks
                </span>

              </div>

              {priorityTasks.length > 0 && (

                <div className="top-priority">

                  <div>
                    <span>
                      Highest Priority Task
                    </span>

                    <strong>
                      {priorityTasks[0].task_code}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Priority Score
                    </span>

                    <strong className="top-score">
                      {
                        priorityTasks[0]
                          .priority_score
                      }
                    </strong>
                  </div>

                  <div>
                    <span>
                      Priority Level
                    </span>

                    <span
                      className={`badge priority-${(
                        priorityTasks[0]
                          .priority_level ||
                        "LOW"
                      ).toLowerCase()}`}
                    >
                      {
                        priorityTasks[0]
                          .priority_level
                      }
                    </span>
                  </div>

                </div>

              )}

              {priorityTasks.length === 0 ? (

                <p className="empty-state">
                  No priority tasks available.
                </p>

              ) : (

                <div className="priority-table-container">

                  <table>

                    <thead>

                      <tr>
                        <th>Rank</th>
                        <th>Task</th>
                        <th>Source</th>
                        <th>Severity</th>
                        <th>Status</th>
                        <th>Score</th>
                        <th>Priority</th>
                      </tr>

                    </thead>

                    <tbody>

                      {priorityTasks.map(
                        (task) => (

                          <tr
                            key={task.task_id}
                          >

                            <td>
                              <strong>
                                #
                                {
                                  task.priority_rank
                                }
                              </strong>
                            </td>

                            <td>
                              <strong>
                                {task.task_code}
                              </strong>

                              <small>
                                {task.task_type}
                              </small>
                            </td>

                            <td>
                              {task.source_system}
                            </td>

                            <td>
                              <span
                                className={`badge ${(
                                  task.severity ||
                                  "MEDIUM"
                                ).toLowerCase()}`}
                              >
                                {task.severity}
                              </span>
                            </td>

                            <td>
                              <span
                                className={`badge status-${(
                                  task.status ||
                                  ""
                                ).toLowerCase()}`}
                              >
                                {task.status}
                              </span>
                            </td>

                            <td>
                              <strong className="priority-score">
                                {
                                  task.priority_score
                                }
                              </strong>
                            </td>

                            <td>
                              <span
                                className={`badge priority-${(
                                  task.priority_level ||
                                  "LOW"
                                ).toLowerCase()}`}
                              >
                                {
                                  task.priority_level
                                }
                              </span>
                            </td>

                          </tr>

                        )
                      )}

                    </tbody>

                  </table>

                </div>

              )}

            </section>

            {/* ==================================================
                AI RISK
                ================================================== */}

            <section className="panel">

              <div className="panel-header">

                <div>
                  <h2>
                    🤖 AI Maintenance Risk
                  </h2>

                  <p>
                    Predicted asset risk based on
                    defects and maintenance workload
                  </p>
                </div>

                <span className="panel-count">
                  {assetRisks.length} Assets
                </span>

              </div>

              {assetRisks.length === 0 ? (

                <p className="empty-state">
                  No asset risk data available.
                </p>

              ) : (

                <div className="risk-list">

                  {assetRisks.map(
                    (asset) => (

                      <div
                        className={`risk-card risk-${(
                          asset.risk_level ||
                          "LOW"
                        ).toLowerCase()}`}
                        key={asset.asset_id}
                      >

                        <div className="risk-header">

                          <div>

                            <h3>
                              {asset.asset_code}
                            </h3>

                            <p>
                              {asset.asset_type}
                              {" · "}
                              Section{" "}
                              {asset.section_id}
                            </p>

                          </div>

                          <div className="risk-score">

                            <span>
                              Risk Score
                            </span>

                            <strong>
                              {asset.risk_score}
                            </strong>

                          </div>

                        </div>

                        <div className="risk-summary">

                          <div>
                            <span>
                              Risk Level
                            </span>

                            <strong>
                              {asset.risk_level}
                            </strong>
                          </div>

                          <div>
                            <span>
                              Open Defects
                            </span>

                            <strong>
                              {asset.open_defect_count}
                            </strong>
                          </div>

                          <div>
                            <span>
                              Active Tasks
                            </span>

                            <strong>
                              {asset.active_task_count}
                            </strong>
                          </div>

                          <div>
                            <span>
                              Criticality
                            </span>

                            <strong>
                              {asset.criticality}
                            </strong>
                          </div>

                        </div>

                        <div className="risk-factors">

                          <strong>
                            Risk Factors
                          </strong>

                          {asset.risk_factors?.map(
                            (factor, index) => (
                              <p key={index}>
                                • {factor}
                              </p>
                            )
                          )}

                        </div>

                        <div className="risk-recommendation">

                          <strong>
                            🤖 Recommendation
                          </strong>

                          <p>
                            {asset.recommendation}
                          </p>

                        </div>

                      </div>

                    )
                  )}

                </div>

              )}

            </section>

            {/* ==================================================
                SMART PRIORITY
                ================================================== */}

            <section className="panel">

              <div className="panel-header">

                <div>
                  <h2>
                    🧠 Smart Maintenance Priority
                  </h2>

                  <p>
                    Task priority combined with AI
                    asset risk
                  </p>
                </div>

                <span className="panel-count">
                  {smartPriorities.length} Tasks
                </span>

              </div>

              {smartPriorities.length === 0 ? (

                <p className="empty-state">
                  No smart priority data available.
                </p>

              ) : (

                <div className="smart-priority-list">

                  {smartPriorities.map(
                    (task, index) => (

                      <div
                        className={`smart-priority-card smart-${(
                          task.smart_priority_level ||
                          "LOW"
                        ).toLowerCase()}`}
                        key={task.task_id}
                      >

                        {index === 0 && (
                          <div className="smart-best-label">
                            ⭐ TOP PRIORITY
                          </div>
                        )}

                        <div className="smart-priority-header">

                          <div>

                            <h3>
                              {task.task_code}
                            </h3>

                            <p>
                              Asset{" "}
                              {task.asset_id}
                              {" · "}
                              Section{" "}
                              {task.section_id}
                            </p>

                          </div>

                          <div className="smart-score">

                            <span>
                              Smart Score
                            </span>

                            <strong>
                              {
                                task.smart_priority_score
                              }
                            </strong>

                          </div>

                        </div>

                        <div className="smart-priority-details">

                          <div>
                            <span>
                              Base Priority
                            </span>

                            <strong>
                              {
                                task.base_priority_score
                              }
                            </strong>
                          </div>

                          <div>
                            <span>
                              Asset Risk
                            </span>

                            <strong>
                              {
                                task.asset_risk_score
                              }
                            </strong>
                          </div>

                          <div>
                            <span>
                              Risk Level
                            </span>

                            <strong>
                              {task.risk_level}
                            </strong>
                          </div>

                          <div>
                            <span>
                              Smart Priority
                            </span>

                            <strong>
                              {
                                task.smart_priority_level
                              }
                            </strong>
                          </div>

                        </div>

                        <div className="smart-risk-factors">

                          <strong>
                            Risk Factors
                          </strong>

                          {task.risk_factors?.map(
                            (factor, index) => (
                              <p key={index}>
                                • {factor}
                              </p>
                            )
                          )}

                        </div>

                        <div className="smart-recommendation">

                          <strong>
                            🤖 Recommendation
                          </strong>

                          <p>
                            {task.recommendation}
                          </p>

                        </div>

                      </div>

                    )
                  )}

                </div>

              )}

            </section>

            {/* ==================================================
                AI DECISION CENTER
                ================================================== */}

            <section className="panel">

              <div className="panel-header">

                <div>

                  <h2>
                    🤖 AI Maintenance Decision Center
                  </h2>

                  <p>
                    AI-assisted maintenance decisions
                    based on priority, asset risk and
                    train impact
                  </p>

                </div>

                <span className="panel-count">
                  {aiDecisions.length} Decisions
                </span>

              </div>

              {aiDecisions.length === 0 ? (

                <p className="empty-state">
                  No AI decisions available.
                </p>

              ) : (

                <div className="ai-decision-list">

                  {aiDecisions.map(
                    (decision, index) => (

                      <div
                        className={`ai-decision-card ai-${(
                          decision.decision_level ||
                          "LOW"
                        ).toLowerCase()}`}
                        key={decision.task_id}
                      >

                        {index === 0 && (
                          <div className="ai-top-label">
                            ⭐ TOP AI RECOMMENDATION
                          </div>
                        )}

                        <div className="ai-decision-header">

                          <div>

                            <h3>
                              {decision.task_code}
                            </h3>

                            <p>
                              Asset{" "}
                              {decision.asset_id}
                              {" · "}
                              Section{" "}
                              {decision.section_id}
                            </p>

                          </div>

                          <div className="ai-score">

                            <span>
                              AI Decision Score
                            </span>

                            <strong>
                              {
                                decision.ai_decision_score
                              }
                            </strong>

                          </div>

                        </div>

                        <div className="ai-decision-details">

                          <div>
                            <span>
                              Base Priority
                            </span>

                            <strong>
                              {
                                decision.base_priority_score
                              }
                            </strong>
                          </div>

                          <div>
                            <span>
                              Asset Risk
                            </span>

                            <strong>
                              {
                                decision.asset_risk_score
                              }
                            </strong>
                          </div>

                          <div>
                            <span>
                              Train Impact
                            </span>

                            <strong>
                              {
                                decision.train_impact_level
                              }
                            </strong>
                          </div>

                          <div>
                            <span>
                              Decision Level
                            </span>

                            <strong>
                              {
                                decision.decision_level
                              }
                            </strong>
                          </div>

                        </div>

                        <div className="ai-action-box">

                          <span>
                            Recommended Action
                          </span>

                          <strong>
                            {
                              decision.final_action
                            }
                          </strong>

                        </div>

                        {decision.decision_reasons
                          ?.length > 0 && (

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
                                  key={reasonIndex}
                                >
                                  • {reason}
                                </p>
                              )
                            )}

                          </div>

                        )}

                        <div className="ai-recommendation">

                          <strong>
                            🤖 Recommendation
                          </strong>

                          <p>
                            {
                              decision.recommendation
                            }
                          </p>

                        </div>

                        {decision.affected_train_ids
                          ?.length > 0 && (

                          <div className="affected-trains">

                            <strong>
                              Affected Trains:
                            </strong>{" "}

                            {decision.affected_train_ids.join(
                              ", "
                            )}

                          </div>

                        )}

                        {decision.alternative_start_time &&
                          decision.alternative_end_time && (

                            <div className="ai-window">

                              <strong>
                                Recommended Safe Window:
                              </strong>{" "}
                              {
                                decision.alternative_start_time
                              }{" "}
                              –{" "}
                              {
                                decision.alternative_end_time
                              }

                            </div>

                          )}

                      </div>

                    )
                  )}

                </div>

              )}

            </section>

            {/* ==================================================
                AI BEST PLAN
                ================================================== */}

            <section className="panel">

              <div className="panel-header">

                <div>

                  <h2>
                    🏆 AI Best Maintenance Plan
                  </h2>

                  <p>
                    Final AI recommendation combining
                    risk, priority and operational impact
                  </p>

                </div>

                <span className="panel-count">
                  {aiBestPlan
                    ? "1 Best Plan"
                    : "No Plan"}
                </span>

              </div>

              {!aiBestPlan ? (

                <p className="empty-state">
                  No AI best plan available.
                </p>

              ) : (

                <div className="ai-best-plan">

                  <div className="ai-best-header">

                    <div>

                      <span className="ai-top-label">
                        ⭐ RECOMMENDED PLAN
                      </span>

                      <h3>
                        {aiBestPlan.task_code}
                      </h3>

                      <p>
                        Asset{" "}
                        {aiBestPlan.asset_id}
                        {" · "}
                        Section{" "}
                        {aiBestPlan.section_id}
                      </p>

                    </div>

                    <div className="ai-best-score">

                      <span>
                        AI Plan Score
                      </span>

                      <strong>
                        {aiBestPlan.ai_plan_score}
                      </strong>

                    </div>

                  </div>

                  <div className="ai-best-details">

                    <div>
                      <span>
                        AI Decision
                      </span>

                      <strong>
                        {
                          aiBestPlan.ai_decision_score
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Smart Priority
                      </span>

                      <strong>
                        {
                          aiBestPlan.smart_priority_score
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Asset Risk
                      </span>

                      <strong>
                        {
                          aiBestPlan.asset_risk_score
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Train Impact
                      </span>

                      <strong>
                        {
                          aiBestPlan.train_impact_level
                        }
                      </strong>
                    </div>

                  </div>

                  <div className="ai-best-action">

                    <span>
                      Final AI Action
                    </span>

                    <strong>
                      {aiBestPlan.final_action}
                    </strong>

                  </div>

                  <div className="ai-best-recommendation">

                    <strong>
                      🤖 AI Recommendation
                    </strong>

                    <p>
                      {aiBestPlan.recommendation}
                    </p>

                  </div>

                </div>

              )}

            </section>

            {/* ==================================================
                ADMIN ANALYTICS
                ================================================== */}

            <section className="panel">

              <div className="panel-header">

                <div>

                  <h2>
                    📊 Admin Analytics
                  </h2>

                  <p>
                    Management overview of railway
                    maintenance and operations
                  </p>

                </div>

                <span className="panel-count">
                  {adminAnalytics
                    ? "Live"
                    : "Loading"}
                </span>

              </div>

              {!adminAnalytics ? (

                <p className="empty-state">
                  Analytics data unavailable.
                </p>

              ) : (

                <>

                  {/* OPERATIONAL KPIs */}

                  <div className="analytics-kpi-grid">

                    <div className="analytics-kpi">
                      <span>Stations</span>
                      <strong>
                        {
                          adminAnalytics
                            .operational_kpis
                            .stations
                        }
                      </strong>
                    </div>

                    <div className="analytics-kpi">
                      <span>Sections</span>
                      <strong>
                        {
                          adminAnalytics
                            .operational_kpis
                            .sections
                        }
                      </strong>
                    </div>

                    <div className="analytics-kpi">
                      <span>Assets</span>
                      <strong>
                        {
                          adminAnalytics
                            .operational_kpis
                            .assets
                        }
                      </strong>
                    </div>

                    <div className="analytics-kpi">
                      <span>
                        Maintenance Tasks
                      </span>
                      <strong>
                        {
                          adminAnalytics
                            .operational_kpis
                            .maintenance_tasks
                        }
                      </strong>
                    </div>

                    <div className="analytics-kpi">
                      <span>
                        Open Defects
                      </span>
                      <strong>
                        {
                          adminAnalytics
                            .operational_kpis
                            .open_defects
                        }
                      </strong>
                    </div>

                    <div className="analytics-kpi">
                      <span>Blocks</span>
                      <strong>
                        {
                          adminAnalytics
                            .operational_kpis
                            .blocks
                        }
                      </strong>
                    </div>

                    <div className="analytics-kpi">
                      <span>
                        Active Blocks
                      </span>
                      <strong>
                        {
                          adminAnalytics
                            .operational_kpis
                            .active_blocks
                        }
                      </strong>
                    </div>

                    <div className="analytics-kpi">
                      <span>
                        Open Events
                      </span>
                      <strong>
                        {
                          adminAnalytics
                            .operational_kpis
                            .open_operational_events
                        }
                      </strong>
                    </div>

                  </div>

                  {/* MAINTENANCE ANALYTICS */}

                  <div className="analytics-section">

                    <h3>
                      🔧 Maintenance Analytics
                    </h3>

                    <div className="analytics-grid">

                      <div className="analytics-box">
                        <span>Pending</span>
                        <strong>
                          {
                            adminAnalytics
                              .maintenance
                              .status_counts
                              .PENDING
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>Completed</span>
                        <strong>
                          {
                            adminAnalytics
                              .maintenance
                              .status_counts
                              .COMPLETED
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>Overdue</span>
                        <strong>
                          {
                            adminAnalytics
                              .maintenance
                              .status_counts
                              .OVERDUE
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          Critical Tasks
                        </span>
                        <strong>
                          {
                            adminAnalytics
                              .maintenance
                              .severity_counts
                              .CRITICAL
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          High Tasks
                        </span>
                        <strong>
                          {
                            adminAnalytics
                              .maintenance
                              .severity_counts
                              .HIGH
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          Medium Tasks
                        </span>
                        <strong>
                          {
                            adminAnalytics
                              .maintenance
                              .severity_counts
                              .MEDIUM
                          }
                        </strong>
                      </div>

                    </div>

                  </div>

                  {/* AI ANALYTICS */}

                  <div className="analytics-section">

                    <h3>
                      🤖 AI Risk & Decision Analytics
                    </h3>

                    <div className="analytics-grid">

                      <div className="analytics-box">
                        <span>
                          Critical Risk Assets
                        </span>

                        <strong>
                          {
                            adminAnalytics.ai
                              .risk_distribution
                              .CRITICAL
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          High Risk Assets
                        </span>

                        <strong>
                          {
                            adminAnalytics.ai
                              .risk_distribution
                              .HIGH
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          Medium Risk Assets
                        </span>

                        <strong>
                          {
                            adminAnalytics.ai
                              .risk_distribution
                              .MEDIUM
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          Average Risk Score
                        </span>

                        <strong>
                          {
                            adminAnalytics.ai
                              .average_risk_score
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          Urgent AI Decisions
                        </span>

                        <strong>
                          {
                            adminAnalytics.ai
                              .urgent_ai_decisions
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          Average AI Score
                        </span>

                        <strong>
                          {
                            adminAnalytics.ai
                              .average_ai_decision_score
                          }
                        </strong>
                      </div>

                    </div>

                  </div>

                  {/* BLOCK ANALYTICS */}

                  <div className="analytics-section">

                    <h3>
                      🛤️ Block Analytics
                    </h3>

                    <div className="analytics-grid">

                      <div className="analytics-box">
                        <span>
                          Total Blocks
                        </span>

                        <strong>
                          {
                            adminAnalytics.blocks
                              .total_blocks
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>Planned</span>

                        <strong>
                          {
                            adminAnalytics.blocks
                              .planned
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>Completed</span>

                        <strong>
                          {
                            adminAnalytics.blocks
                              .completed
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>Replanned</span>

                        <strong>
                          {
                            adminAnalytics.blocks
                              .replanned
                          }
                        </strong>
                      </div>

                    </div>

                  </div>

                  {/* VISUAL ANALYTICS */}

                  <div className="visual-analytics">

                    <div className="chart-card">

                      <h3>
                        🤖 AI Risk Distribution
                      </h3>

                      <div className="chart-wrapper">

                        <ResponsiveContainer
                          width="100%"
                          height={280}
                        >

                          <BarChart
                            data={riskChartData}
                          >

                            <XAxis
                              dataKey="name"
                            />

                            <YAxis
                              allowDecimals={false}
                            />

                            <Tooltip />

                            <Bar
                              dataKey="value"
                            />

                          </BarChart>

                        </ResponsiveContainer>

                      </div>

                    </div>

                    <div className="chart-card">

                      <h3>
                        🔧 Maintenance Status
                      </h3>

                      <div className="chart-wrapper">

                        <ResponsiveContainer
                          width="100%"
                          height={280}
                        >

                          <BarChart
                            data={
                              maintenanceChartData
                            }
                          >

                            <XAxis
                              dataKey="name"
                            />

                            <YAxis
                              allowDecimals={false}
                            />

                            <Tooltip />

                            <Bar
                              dataKey="value"
                            />

                          </BarChart>

                        </ResponsiveContainer>

                      </div>

                    </div>

                    <div className="chart-card">

                      <h3>
                        🧠 AI Decision Distribution
                      </h3>

                      <div className="chart-wrapper">

                        <ResponsiveContainer
                          width="100%"
                          height={280}
                        >

                          <PieChart>

                            <Pie
                              data={
                                aiDecisionChartData
                              }
                              dataKey="value"
                              nameKey="name"
                              cx="50%"
                              cy="50%"
                              outerRadius={90}
                              label
                            />

                            <Tooltip />

                          </PieChart>

                        </ResponsiveContainer>

                      </div>

                    </div>

                  </div>

                  {/* TRAIN & BLOCK PERFORMANCE */}

                  <div className="analytics-section">

                    <h3>
                      🚆 Train & Block Performance
                    </h3>

                    <div className="analytics-grid">

                      <div className="analytics-box">
                        <span>
                          Blocks Analyzed
                        </span>

                        <strong>
                          {
                            adminAnalytics
                              .train_block_impact
                              .total_blocks_analyzed
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          Conflict-Free Blocks
                        </span>

                        <strong>
                          {
                            adminAnalytics
                              .train_block_impact
                              .conflict_free_blocks
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          High-Impact Blocks
                        </span>

                        <strong>
                          {
                            adminAnalytics
                              .train_block_impact
                              .high_impact_blocks
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          Total Conflicts
                        </span>

                        <strong>
                          {
                            adminAnalytics
                              .train_block_impact
                              .total_conflicts
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          Affected Trains
                        </span>

                        <strong>
                          {
                            adminAnalytics
                              .train_block_impact
                              .affected_trains
                          }
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          Conflict Time
                        </span>

                        <strong>
                          {
                            adminAnalytics
                              .train_block_impact
                              .total_conflict_minutes
                          }{" "}
                          min
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          Block Utilization
                        </span>

                        <strong>
                          {
                            adminAnalytics
                              .train_block_impact
                              .block_utilization_percent
                          }%
                        </strong>
                      </div>

                      <div className="analytics-box">
                        <span>
                          Affected Train IDs
                        </span>

                        <strong>
                          {
                            adminAnalytics
                              .train_block_impact
                              .affected_train_ids
                              ?.length
                              ? adminAnalytics
                                  .train_block_impact
                                  .affected_train_ids
                                  .join(", ")
                              : "None"
                          }
                        </strong>
                      </div>

                    </div>

                  </div>

                </>
              )}

            </section>

            {/* ==================================================
                CREATE MAINTENANCE BLOCK
                ================================================== */}

            <section className="panel create-block-panel">

              <div className="panel-header">

                <div>

                  <h2>
                    ➕ Create Maintenance Block
                  </h2>

                  <p>
                    Manually create a maintenance block
                    for selected tasks
                  </p>

                </div>

                <button
                  className="create-block-toggle"
                  onClick={() => {
                    setShowCreateBlock(
                      (previous) => !previous
                    );

                    setCreateBlockMessage("");
                  }}
                >
                  {showCreateBlock
                    ? "✖ Close"
                    : "➕ New Block"}
                </button>

              </div>

              {showCreateBlock && (

                <div className="create-block-form">

                  {/* SECTION */}

                  <div className="form-group">

                    <label>
                      Railway Section
                    </label>

                    <select
                      value={newBlock.section_id}
                      onChange={(event) =>
                        setNewBlock(
                          (previous) => ({
                            ...previous,
                            section_id:
                              event.target.value,
                          })
                        )
                      }
                    >

                      <option value="">
                        Select Section
                      </option>

                      {sections.map(
                        (section) => (

                          <option
                            key={
                              section.section_id
                            }
                            value={
                              section.section_id
                            }
                          >
                            {
                              section.section_code
                            }
                          </option>

                        )
                      )}

                    </select>

                  </div>

                  {/* DATE */}

                  <div className="form-group">

                    <label>
                      Block Date
                    </label>

                    <input
                      type="date"
                      value={
                        newBlock.block_date
                      }
                      onChange={(event) =>
                        setNewBlock(
                          (previous) => ({
                            ...previous,
                            block_date:
                              event.target.value,
                          })
                        )
                      }
                    />

                  </div>

                  {/* START */}

                  <div className="form-group">

                    <label>
                      Start Time
                    </label>

                    <input
                      type="time"
                      value={
                        newBlock.start_time
                      }
                      onChange={(event) =>
                        setNewBlock(
                          (previous) => ({
                            ...previous,
                            start_time:
                              event.target.value,
                          })
                        )
                      }
                    />

                  </div>

                  {/* END */}

                  <div className="form-group">

                    <label>
                      End Time
                    </label>

                    <input
                      type="time"
                      value={
                        newBlock.end_time
                      }
                      onChange={(event) =>
                        setNewBlock(
                          (previous) => ({
                            ...previous,
                            end_time:
                              event.target.value,
                          })
                        )
                      }
                    />

                  </div>

                  {/* TASKS */}

                  <div className="form-group full-width">

                    <label>
                      Maintenance Tasks
                    </label>

                    <div className="task-selection">

                      {maintenanceTasks.map(
                        (task) => (

                          <label
                            className="task-checkbox"
                            key={task.task_id}
                          >

                            <input
                              type="checkbox"
                              checked={newBlock.task_ids.includes(
                                task.task_id
                              )}
                              onChange={(event) => {

                                if (
                                  event.target
                                    .checked
                                ) {

                                  setNewBlock(
                                    (previous) => ({
                                      ...previous,
                                      task_ids: [
                                        ...previous.task_ids,
                                        task.task_id,
                                      ],
                                    })
                                  );

                                } else {

                                  setNewBlock(
                                    (previous) => ({
                                      ...previous,
                                      task_ids:
                                        previous.task_ids.filter(
                                          (id) =>
                                            id !==
                                            task.task_id
                                        ),
                                    })
                                  );

                                }

                              }}
                            />

                            <span>

                              <strong>
                                {task.task_code}
                              </strong>

                              {" · "}

                              {task.task_type}

                              {" · "}

                              {task.severity}

                            </span>

                          </label>

                        )
                      )}

                    </div>

                  </div>

                  {/* BUTTON */}

                  <div className="create-block-actions">

                    <button
                      className="create-block-button"
                      onClick={
                        handleCreateBlock
                      }
                      disabled={
                        createBlockLoading
                      }
                    >
                      {createBlockLoading
                        ? "⏳ Creating..."
                        : "🚧 Create Block"}
                    </button>

                  </div>

                  {createBlockMessage && (
                    <div className="create-block-message">
                      {createBlockMessage}
                    </div>
                  )}

                </div>

              )}

            </section>

{/* ============================================================
    RAILWAY SCHEDULING TIMELINE
    ============================================================ */}

<section className="panel timeline-panel">

  <div className="panel-header">

    <div>

      <h2>
        📅 Railway Scheduling Timeline
      </h2>

      <p>
        Visual maintenance schedule across the railway network
      </p>

    </div>

    <span className="panel-count">
      {timelineBlocks.length} Blocks
    </span>

  </div>


  {/* ================= DATE FILTER ================= */}

  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: "10px",
      flexWrap: "wrap",
      marginBottom: "20px",
    }}
  >

    <strong>
      📅 Select Date
    </strong>

    <input
      type="date"
      value={timelineDate}
      onChange={(event) =>
        setTimelineDate(event.target.value)
      }
    />

    <button
      type="button"
      className="replan-button"
      onClick={() =>
        setTimelineDate("")
      }
    >
      📋 All Dates
    </button>

  </div>


  {/* ================= TIMELINE CONTENT ================= */}

  {timelineBlocks.length === 0 ? (

    <p className="empty-state">
      No maintenance blocks available for the selected date.
    </p>

  ) : (

    <div className="timeline-container">

      {/* ================= TIME HEADER ================= */}

      <div className="timeline-header-row">

        <div className="timeline-label">
          Block
        </div>

        <div className="timeline-hours">

          <span>08:00</span>
          <span>09:00</span>
          <span>10:00</span>
          <span>11:00</span>
          <span>12:00</span>
          <span>13:00</span>
          <span>14:00</span>
          <span>15:00</span>
          <span>16:00</span>
          <span>17:00</span>
          <span>18:00</span>
          <span>19:00</span>

          <span className="timeline-end-time">
            20:00
          </span>

        </div>

      </div>


      {/* ================= MAINTENANCE BLOCK ROWS ================= */}

      {timelineBlocks.map((block) => (

        <div
          className="timeline-row"
          key={block.block_id}
        >

          {/* BLOCK INFO */}

          <div className="timeline-label">

            <strong>
              {block.block_code}
            </strong>

            <small>
              SEC
              {String(
                block.section_id
              ).padStart(2, "0")}
            </small>

          </div>


          {/* TIMELINE TRACK */}

          <div className="timeline-track">

            {/* GRID */}

            <div className="timeline-grid">

              {Array.from(
                { length: 12 },
                (_, index) => (
                  <div
                    key={index}
                    className="timeline-grid-cell"
                  />
                )
              )}

            </div>


{/* ============================================================
    MAINTENANCE BLOCK WITH IMPACT
    ============================================================ */}

{(() => {
  const impact = getBlockImpact(block);

  return (
    <div
      className={`timeline-block timeline-${(
        block.status || "PLANNED"
      ).toLowerCase()} ${
        impact.conflict
          ? `timeline-impact-${impact.impact.toLowerCase()}`
          : ""
      }`}
      style={getTimelineBlockStyle(block)}
    >

      <strong>
        {block.start_time}
        {" – "}
        {block.end_time}
      </strong>

      <span>
        {impact.conflict
          ? `⚠️ ${impact.impact} IMPACT`
          : block.status}
      </span>

      {impact.conflict &&
        impact.affectedTrains.length > 0 && (
          <small>
            🚆 Train{" "}
            {impact.affectedTrains.join(", ")}
          </small>
        )}

    </div>
  );
})()}

          </div>

        </div>

      ))}


      {/* ============================================================
          TRAIN MOVEMENT TIMELINE
          ============================================================ */}

      <div className="timeline-train-section">

        <div className="timeline-train-title">
          🚆 Train Movements
        </div>


        {trainSchedule
          .filter((train) => {

            if (!timelineDate) {
              return true;
            }

            return (
              train.schedule_date ===
              timelineDate
            );

          })
          .map((train) => (

            <div
              className="timeline-row timeline-train-row"
              key={`train-${train.schedule_id}`}
            >

              {/* TRAIN INFO */}

              <div className="timeline-label">

                <strong>
                  🚆 Train {train.train_id}
                </strong>

                <small>
                  SEC
                  {String(
                    train.section_id
                  ).padStart(2, "0")}
                </small>

              </div>


              {/* TRAIN TRACK */}

              <div className="timeline-track">

                {/* GRID */}

                <div className="timeline-grid">

                  {Array.from(
                    { length: 12 },
                    (_, index) => (
                      <div
                        key={index}
                        className="timeline-grid-cell"
                      />
                    )
                  )}

                </div>


                {/* TRAIN MOVEMENT */}

                <div
                  className="timeline-train"
                  style={getTimelineTrainStyle(train)}
                >

                  <strong>
                    {train.arrival_time}
                    {" – "}
                    {train.departure_time}
                  </strong>

                  <span>
                    🚆 Train {train.train_id}
                  </span>

                </div>

              </div>

            </div>

          ))}

      </div>

    </div>

  )}

</section>


{/* ==================================================
    PLANNED MAINTENANCE BLOCKS
    ================================================== */}
<section className="panel">

  <div className="panel-header">

    <div>

      <h2>
        🛠️ Planned Maintenance Blocks
      </h2>

      <p>
        Maintenance blocks saved in the system
      </p>

      {/* ================= BLOCK FILTERS ================= */}

      <div
        style={{
          display: "flex",
          gap: "8px",
          flexWrap: "wrap",
          marginTop: "12px",
        }}
      >

        {[
          "ALL",
          "PLANNED",
          "APPROVED",
          "IN_PROGRESS",
          "COMPLETED",
          "CANCELLED",
          "REPLAN_REQUIRED",
        ].map((filter) => (

          <button
            key={filter}
            type="button"
            onClick={() => setBlockFilter(filter)}
            className="replan-button"
            style={{
              opacity:
                blockFilter === filter
                  ? 1
                  : 0.65,
            }}
          >

            {filter === "ALL"
              ? "📋 All"
              : filter === "PLANNED"
              ? "📝 Planned"
              : filter === "APPROVED"
              ? "✅ Approved"
              : filter === "IN_PROGRESS"
              ? "🚧 In Progress"
              : filter === "COMPLETED"
              ? "✔ Completed"
              : filter === "CANCELLED"
              ? "❌ Cancelled"
              : "⚠️ Re-plan"}

          </button>

        ))}

      </div>

    </div>

    <span className="panel-count">
      {filteredBlocks.length} Blocks
    </span>

  </div>


  {/* ================= EMPTY STATE ================= */}

  {filteredBlocks.length === 0 ? (

    <p className="empty-state">

      {plannedBlocks.length === 0
        ? "No maintenance blocks have been created yet."
        : "No blocks match the selected filter."}

    </p>

  ) : (

    <div className="table-container">

      <table>

        <thead>

          <tr>
            <th>Block</th>
            <th>Section</th>
            <th>Date</th>
            <th>Time</th>
            <th>Tasks</th>
            <th>Status</th>
            <th>Re-plan</th>
            <th>Actions</th>
          </tr>

        </thead>


        <tbody>

          {filteredBlocks.map((block) => (

            <tr
              key={block.block_id}
            >

              {/* ================= BLOCK ================= */}

              <td>
                <strong>
                  {block.block_code}
                </strong>
              </td>


              {/* ================= SECTION ================= */}

              <td>
                SEC
                {String(
                  block.section_id
                ).padStart(2, "0")}
              </td>


              {/* ================= DATE ================= */}

              <td>
                {block.block_date}
              </td>


              {/* ================= TIME ================= */}

              <td>

                <div>
                  {block.start_time}{" "}
                  –{" "}
                  {block.end_time}
                </div>

                {block.recommended_start_time &&
                  block.recommended_end_time && (

                    <small>
                      Recommended:{" "}
                      {block.recommended_start_time}{" "}
                      –{" "}
                      {block.recommended_end_time}
                    </small>

                  )}

              </td>


              {/* ================= TASKS ================= */}

              <td>
                {block.task_ids?.length
                  ? block.task_ids.join(", ")
                  : "—"}
              </td>


              {/* ================= STATUS ================= */}

              <td>

                <span
                  className={`badge status-${
                    block.status?.toLowerCase() || "pending"
                  }`}
                >
                  {block.status}
                </span>

              </td>


              {/* ================= RE-PLAN ================= */}

              <td>

                {block.replan_required ? (

                  <span className="badge priority-high">
                    ⚠️ REPLAN REQUIRED
                  </span>

                ) : block.recommended_start_time &&
                  block.recommended_end_time ? (

                  <span className="badge status-approved">
                    🔄 REPLANNED
                  </span>

                ) : (

                  <span className="badge status-completed">
                    ✅ NORMAL
                  </span>

                )}

              </td>


              {/* ================= ACTIONS ================= */}

              <td>

                <div
                  style={{
                    display: "flex",
                    gap: "8px",
                    flexWrap: "wrap",
                  }}
                >

                  {/* ------------------------------------------
                      PLANNED → APPROVED / CANCELLED
                      ------------------------------------------ */}

                  {block.status === "PLANNED" && (

                    <>

                      <button
                        type="button"
                        className="replan-button"
                        onClick={() =>
                          handleBlockStatusChange(
                            block.block_id,
                            "APPROVED"
                          )
                        }
                      >
                        ✅ Approve
                      </button>

                      <button
                        type="button"
                        className="replan-button"
                        onClick={() =>
                          handleBlockStatusChange(
                            block.block_id,
                            "CANCELLED"
                          )
                        }
                      >
                        ❌ Cancel
                      </button>

                    </>

                  )}


                  {/* ------------------------------------------
                      APPROVED → IN_PROGRESS / CANCELLED
                      ------------------------------------------ */}

                  {block.status === "APPROVED" && (

                    <>

                      <button
                        type="button"
                        className="replan-button"
                        onClick={() =>
                          handleBlockStatusChange(
                            block.block_id,
                            "IN_PROGRESS"
                          )
                        }
                      >
                        ▶ Start Work
                      </button>

                      <button
                        type="button"
                        className="replan-button"
                        onClick={() =>
                          handleBlockStatusChange(
                            block.block_id,
                            "CANCELLED"
                          )
                        }
                      >
                        ❌ Cancel
                      </button>

                    </>

                  )}


                  {/* ------------------------------------------
                      IN_PROGRESS → COMPLETED / CANCELLED
                      ------------------------------------------ */}

                  {block.status === "IN_PROGRESS" && (

                    <>

                      <button
                        type="button"
                        className="replan-button"
                        onClick={() =>
                          handleBlockStatusChange(
                            block.block_id,
                            "COMPLETED"
                          )
                        }
                      >
                        ✅ Complete
                      </button>

                      <button
                        type="button"
                        className="replan-button"
                        onClick={() =>
                          handleBlockStatusChange(
                            block.block_id,
                            "CANCELLED"
                          )
                        }
                      >
                        ❌ Cancel
                      </button>

                    </>

                  )}


                  {/* ------------------------------------------
                      COMPLETED
                      ------------------------------------------ */}

                  {block.status === "COMPLETED" && (

                    <span className="badge status-completed">
                      ✅ COMPLETED
                    </span>

                  )}


                  {/* ------------------------------------------
                      CANCELLED
                      ------------------------------------------ */}

                  {block.status === "CANCELLED" && (

                    <span className="badge status-pending">
                      ❌ CANCELLED
                    </span>

                  )}

                </div>

              </td>

            </tr>

          ))}

        </tbody>

      </table>

    </div>

  )}

</section>

            {/* ==================================================
                TRAIN IMPACT
                ================================================== */}

            <section className="panel">

              <div className="panel-header">

                <div>

                  <h2>
                    🚆 Train Impact & Rescheduling
                  </h2>

                  <p>
                    Automatic train conflict analysis
                  </p>

                </div>

                <span className="panel-count">
                  {blockRecommendations.length}{" "}
                  Blocks
                </span>

              </div>

              {blockRecommendations.length ===
              0 ? (

                <p className="empty-state">
                  No block impact analysis
                  available.
                </p>

              ) : (

                <div className="impact-list">

                  {blockRecommendations.map(
                    (item) => (

                      <div
                        className="impact-card"
                        key={item.block_id}
                      >

                        <div className="impact-header">

                          <div>

                            <h3>
                              {item.block_code}
                            </h3>

                            <p>
                              Section{" "}
                              {item.section_id}
                              {" · "}
                              {item.start_time}
                              {" – "}
                              {item.end_time}
                            </p>

                          </div>

                          <span
                            className={`badge impact-${(
                              item.impact_level ||
                              "NONE"
                            ).toLowerCase()}`}
                          >
                            {
                              item.impact_level
                            }
                          </span>

                        </div>

                        <div className="impact-details">

                          <div>
                            <span>
                              Conflicts
                            </span>

                            <strong>
                              {
                                item.conflict_count
                              }
                            </strong>
                          </div>

                          <div>
                            <span>
                              Affected Trains
                            </span>

                            <strong>
                              {item.affected_train_ids
                                ?.length || 0}
                            </strong>
                          </div>

                          <div>
                            <span>
                              Conflict Time
                            </span>

                            <strong>
                              {
                                item.total_conflict_minutes
                              }{" "}
                              min
                            </strong>
                          </div>

                          <div>
                            <span>
                              Action
                            </span>

                            <strong>
                              {
                                item.recommended_action
                              }
                            </strong>
                          </div>

                        </div>

                        <div className="recommendation-box">

                          <strong>
                            Recommendation:
                          </strong>

                          <p>
                            {
                              item.recommendation
                            }
                          </p>

                          {item.alternative_start_time &&
                            item.alternative_end_time && (

                              <p>

                                <strong>
                                  Alternative Window:
                                </strong>{" "}

                                {
                                  item.alternative_start_time
                                }{" "}
                                –{" "}
                                {
                                  item.alternative_end_time
                                }

                              </p>

                            )}

                        </div>

                        {item.affected_train_ids
                          ?.length > 0 && (

                          <div className="affected-trains">

                            <strong>
                              Affected Train IDs:
                            </strong>{" "}

                            {item.affected_train_ids.join(
                              ", "
                            )}

                          </div>

                        )}

                      </div>

                    )
                  )}

                </div>

              )}

            </section>

            {/* ==================================================
                OPTIMIZATION
                ================================================== */}

            <section className="panel">

              <div className="panel-header">

                <div>

                  <h2>
                    🎯 Maintenance Plan Optimization
                  </h2>

                  <p>
                    Best available plan based on
                    priority and train impact
                  </p>

                </div>

                <span className="panel-count">
                  {optimizedBlocks.length} Plans
                </span>

              </div>

              {optimizedBlocks.length ===
              0 ? (

                <p className="empty-state">
                  No optimization results
                  available.
                </p>

              ) : (

                <div className="optimization-list">

                  {optimizedBlocks.map(
                    (item, index) => (

                      <div
                        className={`optimization-card ${
                          index === 0
                            ? "best-plan"
                            : ""
                        }`}
                        key={item.block_id}
                      >

                        {index === 0 && (
                          <div className="best-label">
                            ⭐ BEST CURRENT PLAN
                          </div>
                        )}

                        <div className="optimization-header">

                          <div>

                            <h3>
                              {item.block_code}
                            </h3>

                            <p>
                              Section{" "}
                              {item.section_id}
                              {" · "}
                              {item.start_time}
                              {" – "}
                              {item.end_time}
                            </p>

                          </div>

                          <div className="optimization-score">

                            <span>
                              Optimization Score
                            </span>

                            <strong>
                              {
                                item.optimization_score
                              }
                            </strong>

                          </div>

                        </div>

                        <div className="optimization-details">

                          <div>
                            <span>
                              Priority Score
                            </span>

                            <strong>
                              {
                                item.priority_score
                              }
                            </strong>
                          </div>

                          <div>
                            <span>
                              Impact
                            </span>

                            <strong>
                              {item.impact_level}
                            </strong>
                          </div>

                          <div>
                            <span>
                              Duration
                            </span>

                            <strong>
                              {
                                item.duration_hours
                              }{" "}
                              h
                            </strong>
                          </div>

                          <div>
                            <span>
                              Action
                            </span>

                            <strong>
                              {
                                item.recommended_action
                              }
                            </strong>
                          </div>

                        </div>

                        {item.affected_train_ids
                          ?.length > 0 && (

                          <div className="affected-trains">

                            <strong>
                              Affected Trains:
                            </strong>{" "}

                            {
                              item.affected_train_ids.join(
                                ", "
                              )
                            }

                          </div>

                        )}

                      </div>

                    )
                  )}

                </div>

              )}

            </section>

            {/* ==================================================
                DYNAMIC RE-PLANNING
                ================================================== */}

            <section className="panel">

              <div className="panel-header">

                <div>

                  <h2>
                    ⚠️ Dynamic Re-Planning Alerts
                  </h2>

                  <p>
                    Operational events requiring
                    plan review
                  </p>

                </div>

                <span className="panel-count">
                  {operationalEvents.length} Events
                </span>

              </div>

              {operationalEvents.length ===
              0 ? (

                <p className="empty-state">
                  No active operational events.
                </p>

              ) : (

                <div className="event-list">

                  {operationalEvents.map(
                    (event) => (

                      <div
                        className={`event-card event-${(
                          event.severity ||
                          "MEDIUM"
                        ).toLowerCase()}`}
                        key={event.event_id}
                      >

                        <div className="event-header">

                          <div>

                            <h3>

                              {event.event_type ===
                              "TRAIN_DELAY"
                                ? "🚆 Train Delay"
                                : event.event_type ===
                                  "DEFECT"
                                ? "🔧 Defect"
                                : "⚠️ Block Change"}

                            </h3>

                            <p>
                              Event #
                              {event.event_id}
                              {" · "}
                              Section{" "}
                              {event.section_id}
                            </p>

                          </div>

                          <div
                            style={{
                              display: "flex",
                              gap: "8px",
                              alignItems:
                                "center",
                            }}
                          >

                            <span
                              className={`badge ${(
                                event.severity ||
                                "MEDIUM"
                              ).toLowerCase()}`}
                            >
                              {event.severity}
                            </span>

                            <span
                              className={`badge ${
                                event.status ===
                                "RESOLVED"
                                  ? "status-resolved"
                                  : "status-pending"
                              }`}
                            >
                              {event.status}
                            </span>

                          </div>

                        </div>

                        <div className="event-details">

                          {event.train_id !==
                            null &&
                            event.train_id !==
                              undefined && (

                            <div>

                              <span>
                                Train ID
                              </span>

                              <strong>
                                {event.train_id}
                              </strong>

                            </div>

                          )}

                          {event.delay_minutes !==
                            null &&
                            event.delay_minutes !==
                              undefined && (

                            <div>

                              <span>
                                Delay
                              </span>

                              <strong>
                                {
                                  event.delay_minutes
                                }{" "}
                                min
                              </strong>

                            </div>

                          )}

                          {event.asset_id !==
                            null &&
                            event.asset_id !==
                              undefined && (

                            <div>

                              <span>
                                Asset ID
                              </span>

                              <strong>
                                {event.asset_id}
                              </strong>

                            </div>

                          )}

                          <div>

                            <span>
                              Status
                            </span>

                            <strong>
                              {event.status}
                            </strong>

                          </div>

                        </div>

                        {event.description && (
                          <div className="event-description">
                            {event.description}
                          </div>
                        )}

                        <div className="replan-alert">

                          {event.status ===
                          "OPEN" ? (

                            <>
                              <strong>
                                ⚠️ Dynamic
                                re-planning
                                required
                              </strong>

                              <p>
                                This event may
                                affect the
                                current
                                maintenance plan
                                and train
                                operations.
                              </p>

                              <button
                                className="replan-button"
                                onClick={() =>
                                  handleReplan(
                                    event.event_id
                                  )
                                }
                                disabled={
                                  replanningEventId ===
                                  event.event_id
                                }
                              >
                                {replanningEventId ===
                                event.event_id
                                  ? "⏳ Re-planning..."
                                  : "🔄 Replan Now"}
                              </button>
                            </>

                          ) : (

                            <>
                              <strong>
                                ✅ Event resolved
                              </strong>

                              <p>
                                Re-planning has
                                already been
                                applied
                                successfully.
                              </p>

                              <span className="badge status-resolved">
                                RESOLVED
                              </span>
                            </>

                          )}

                        </div>

                        {/* REPLAN RESULT */}

                        {replanResults[
                          event.event_id
                        ] && (

                          <>

                            <div className="replan-result">

                              <div className="replan-result-header">

                                <strong>
                                  ✅ Latest
                                  Re-planning
                                  Result
                                </strong>

                                <span className="badge status-approved">
                                  {
                                    replanResults[
                                      event.event_id
                                    ]
                                      .event_action
                                  }
                                </span>

                              </div>

                              {replanResults[
                                event.event_id
                              ]
                                .affected_blocks
                                ?.map(
                                  (block) => (

                                    <div
                                      className="replan-block"
                                      key={
                                        block.block_id
                                      }
                                    >

                                      <strong>
                                        {
                                          block.block_code
                                        }
                                      </strong>

                                      <p>
                                        Current
                                        Window:{" "}
                                        {
                                          block.current_start_time
                                        }{" "}
                                        –{" "}
                                        {
                                          block.current_end_time
                                        }
                                      </p>

                                      <p>
                                        Conflicts:{" "}
                                        <strong>
                                          {
                                            block.conflict_count
                                          }
                                        </strong>
                                      </p>

                                      <p>
                                        Impact:{" "}
                                        <strong>
                                          {
                                            block.impact_level
                                          }
                                        </strong>
                                      </p>

                                      <p>
                                        Affected
                                        Trains:{" "}
                                        <strong>
                                          {block.affected_train_ids?.join(
                                            ", "
                                          ) ||
                                            "None"}
                                        </strong>
                                      </p>

                                      <p>
                                        Action:{" "}
                                        <strong>
                                          {
                                            block.recommended_action
                                          }
                                        </strong>
                                      </p>

                                      {block.alternative_start_time &&
                                        block.alternative_end_time && (

                                          <p>
                                            Recommended
                                            Window:{" "}
                                            <strong>
                                              {
                                                block.alternative_start_time
                                              }{" "}
                                              –{" "}
                                              {
                                                block.alternative_end_time
                                              }
                                            </strong>
                                          </p>

                                        )}

                                      <p>
                                        {
                                          block.recommendation
                                        }
                                      </p>

                                    </div>

                                  )
                                )}

                            </div>

                            {/* APPLY BUTTON */}

                            {event.status ===
                              "OPEN" && (

                              <div
                                className="agent-action-buttons"
                                style={{
                                  marginTop:
                                    "12px",
                                }}
                              >

                                <button
                                  className="replan-button"
                                  onClick={() =>
                                    handleApplyAgentReplan(
                                      event.event_id
                                    )
                                  }
                                  disabled={
                                    agentActionLoading
                                  }
                                >
                                  {agentActionLoading
                                    ? "⏳ Applying..."
                                    : "✅ Apply Replan"}
                                </button>

                              </div>

                            )}

                          </>

                        )}

                      </div>

                    )
                  )}

                </div>

              )}

            </section>

            {/* ==================================================
                SYSTEM SUMMARY
                ================================================== */}

            <section className="panel">

              <div className="panel-header">

                <div>

                  <h2>
                    System Summary
                  </h2>

                  <p>
                    Operational overview
                  </p>

                </div>

              </div>

              <div className="summary-grid">

                <div className="summary-item">

                  <span>
                    Train Schedules
                  </span>

                  <strong>
                    {trainSchedule.length}
                  </strong>

                </div>

                <div className="summary-item">

                  <span>
                    Goods Forecasts
                  </span>

                  <strong>
                    {goodsForecast.length}
                  </strong>

                </div>

                <div className="summary-item">

                  <span>
                    Critical Assets
                  </span>

                  <strong>
                    {criticalAssets.length}
                  </strong>

                </div>

                <div className="summary-item">

                  <span>
                    Overdue Tasks
                  </span>

                  <strong>
                    {overdueTasks.length}
                  </strong>

                </div>

              </div>

            </section>

          </>
        )}

      </main>
    </div>
  );
}

export default App;