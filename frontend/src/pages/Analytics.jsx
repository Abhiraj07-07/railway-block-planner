import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

import "./Analytics.css";

const API_BASE =
  import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const TOKEN_KEY = "railway_admin_token";

const authFetch = (url, options = {}) => {
  const token = localStorage.getItem(TOKEN_KEY);

  return fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Accept: "application/json",
      ...(token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {}),
    },
  });
};

function Analytics() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // ============================================================
  // LOAD ANALYTICS
  // ============================================================

  useEffect(() => {
    const loadAnalytics = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await authFetch(
          `${API_BASE}/admin/analytics`
        );

        const data = await response
          .json()
          .catch(() => null);

        if (!response.ok) {
          throw new Error(
            data?.detail ||
              `Analytics API failed with status ${response.status}`
          );
        }

        setAnalytics(data || null);
      } catch (err) {
        console.error(
          "Analytics page error:",
          err
        );

        setError(
          err.message ||
            "Unable to load analytics."
        );
      } finally {
        setLoading(false);
      }
    };

    loadAnalytics();
  }, []);

  // ============================================================
  // SAFE DATA
  // ============================================================

  const operational =
    analytics?.operational_kpis || {};

  const maintenance =
    analytics?.maintenance || {};

  const ai =
    analytics?.ai || {};

  const blocks =
    analytics?.blocks || {};

  const trainImpact =
    analytics?.train_block_impact || {};

  // ============================================================
  // CHART DATA
  // ============================================================

  const riskDistribution = [
    {
      name: "Low",
      value:
        ai.risk_distribution?.LOW || 0,
    },
    {
      name: "Medium",
      value:
        ai.risk_distribution?.MEDIUM || 0,
    },
    {
      name: "High",
      value:
        ai.risk_distribution?.HIGH || 0,
    },
    {
      name: "Critical",
      value:
        ai.risk_distribution?.CRITICAL || 0,
    },
  ];

  const maintenanceStatus = [
    {
      name: "Pending",
      value:
        maintenance.status_counts?.PENDING || 0,
    },
    {
      name: "Completed",
      value:
        maintenance.status_counts?.COMPLETED || 0,
    },
    {
      name: "Overdue",
      value:
        maintenance.status_counts?.OVERDUE || 0,
    },
    {
      name: "Cancelled",
      value:
        maintenance.status_counts?.CANCELLED || 0,
    },
  ];

  const aiDecisionDistribution = [
    {
      name: "Urgent",
      value:
        ai.decision_distribution?.URGENT || 0,
    },
    {
      name: "High",
      value:
        ai.decision_distribution?.HIGH || 0,
    },
    {
      name: "Medium",
      value:
        ai.decision_distribution?.MEDIUM || 0,
    },
    {
      name: "Low",
      value:
        ai.decision_distribution?.LOW || 0,
    },
  ];

  const blockStatusData = [
    {
      name: "Planned",
      value: blocks.planned || 0,
    },
    {
      name: "Completed",
      value: blocks.completed || 0,
    },
    {
      name: "Replanned",
      value: blocks.replanned || 0,
    },
  ];

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="analytics-page">

      {/* ======================================================
          HERO
          ====================================================== */}

      <section className="analytics-hero">

        <div>

          <span className="analytics-eyebrow">
            MANAGEMENT INTELLIGENCE
          </span>

          <h1>
            📊 Admin Analytics
          </h1>

          <p>
            Real-time overview of railway
            maintenance, block utilization,
            AI decisions and train impact.
          </p>

        </div>

        <div className="analytics-live">
          <span className="status-dot"></span>
          LIVE ANALYTICS
        </div>

      </section>


      {/* ======================================================
          ERROR
          ====================================================== */}

      {error && (
        <div className="global-error">
          <strong>
            Analytics Error:
          </strong>{" "}
          {error}
        </div>
      )}


      {loading ? (

        <section className="analytics-loading-panel">

          <div className="loader"></div>

          <p>
            Loading management analytics...
          </p>

        </section>

      ) : !analytics ? (

        <section className="analytics-card">
          <p className="empty-state">
            No analytics data available.
          </p>
        </section>

      ) : (

        <>

          {/* ==================================================
              OPERATIONAL KPI
              ================================================== */}

          <section className="analytics-kpi-grid">

            <div className="analytics-kpi-card">
              <span>🚉 Stations</span>
              <strong>
                {operational.stations ?? 0}
              </strong>
            </div>

            <div className="analytics-kpi-card">
              <span>🛤️ Sections</span>
              <strong>
                {operational.sections ?? 0}
              </strong>
            </div>

            <div className="analytics-kpi-card">
              <span>⚙️ Assets</span>
              <strong>
                {operational.assets ?? 0}
              </strong>
            </div>

            <div className="analytics-kpi-card">
              <span>🔧 Maintenance Tasks</span>
              <strong>
                {operational.maintenance_tasks ?? 0}
              </strong>
            </div>

            <div className="analytics-kpi-card">
              <span>⚠️ Open Defects</span>
              <strong>
                {operational.open_defects ?? 0}
              </strong>
            </div>

            <div className="analytics-kpi-card">
              <span>🛠️ Total Blocks</span>
              <strong>
                {operational.blocks ?? 0}
              </strong>
            </div>

            <div className="analytics-kpi-card">
              <span>🚧 Active Blocks</span>
              <strong>
                {operational.active_blocks ?? 0}
              </strong>
            </div>

            <div className="analytics-kpi-card">
              <span>🚨 Open Events</span>
              <strong>
                {operational.open_operational_events ?? 0}
              </strong>
            </div>

          </section>


          {/* ==================================================
              MAINTENANCE + AI
              ================================================== */}

          <section className="analytics-two-column">

            {/* MAINTENANCE */}

            <div className="analytics-card">

              <div className="analytics-card-header">

                <div>
                  <h2>
                    🔧 Maintenance Analytics
                  </h2>

                  <p>
                    Maintenance workload and severity
                  </p>
                </div>

              </div>


              <div className="analytics-mini-grid">

                <div>
                  <span>Pending</span>
                  <strong>
                    {maintenance.status_counts?.PENDING ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Completed</span>
                  <strong>
                    {maintenance.status_counts?.COMPLETED ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Overdue</span>
                  <strong>
                    {maintenance.status_counts?.OVERDUE ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Cancelled</span>
                  <strong>
                    {maintenance.status_counts?.CANCELLED ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Critical</span>
                  <strong>
                    {maintenance.severity_counts?.CRITICAL ?? 0}
                  </strong>
                </div>

                <div>
                  <span>High</span>
                  <strong>
                    {maintenance.severity_counts?.HIGH ?? 0}
                  </strong>
                </div>

              </div>

            </div>


            {/* AI */}

            <div className="analytics-card analytics-ai-card">

              <div className="analytics-card-header">

                <div>
                  <h2>
                    🤖 AI Intelligence
                  </h2>

                  <p>
                    Risk and decision analytics
                  </p>
                </div>

              </div>


              <div className="analytics-mini-grid">

                <div>
                  <span>Critical Risk</span>
                  <strong>
                    {ai.risk_distribution?.CRITICAL ?? 0}
                  </strong>
                </div>

                <div>
                  <span>High Risk</span>
                  <strong>
                    {ai.risk_distribution?.HIGH ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Medium Risk</span>
                  <strong>
                    {ai.risk_distribution?.MEDIUM ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Avg Risk Score</span>
                  <strong>
                    {ai.average_risk_score ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Urgent Decisions</span>
                  <strong>
                    {ai.urgent_ai_decisions ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Avg AI Score</span>
                  <strong>
                    {ai.average_ai_decision_score ?? 0}
                  </strong>
                </div>

              </div>

            </div>

          </section>


          {/* ==================================================
              BLOCK + TRAIN PERFORMANCE
              ================================================== */}

          <section className="analytics-two-column">

            <div className="analytics-card">

              <div className="analytics-card-header">

                <div>
                  <h2>
                    🛤️ Block Performance
                  </h2>

                  <p>
                    Maintenance block utilization
                  </p>
                </div>

              </div>


              <div className="analytics-performance-grid">

                <div>
                  <span>Total Blocks</span>
                  <strong>
                    {blocks.total_blocks ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Planned</span>
                  <strong>
                    {blocks.planned ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Completed</span>
                  <strong>
                    {blocks.completed ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Replanned</span>
                  <strong>
                    {blocks.replanned ?? 0}
                  </strong>
                </div>

              </div>

            </div>


            <div className="analytics-card">

              <div className="analytics-card-header">

                <div>
                  <h2>
                    🚆 Train & Block Impact
                  </h2>

                  <p>
                    Operational conflict performance
                  </p>
                </div>

              </div>


              <div className="analytics-performance-grid">

                <div>
                  <span>
                    Blocks Analyzed
                  </span>

                  <strong>
                    {
                      trainImpact.total_blocks_analyzed ??
                      0
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    Conflict-Free
                  </span>

                  <strong>
                    {
                      trainImpact.conflict_free_blocks ??
                      0
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    High Impact
                  </span>

                  <strong>
                    {
                      trainImpact.high_impact_blocks ??
                      0
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    Conflicts
                  </span>

                  <strong>
                    {
                      trainImpact.total_conflicts ??
                      0
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    Affected Trains
                  </span>

                  <strong>
                    {
                      trainImpact.affected_trains ??
                      0
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    Conflict Time
                  </span>

                  <strong>
                    {
                      trainImpact.total_conflict_minutes ??
                      0
                    }{" "}
                    min
                  </strong>
                </div>

              </div>

            </div>

          </section>


          {/* ==================================================
              CHARTS
              ================================================== */}

          <section className="analytics-chart-grid">

            {/* AI RISK */}

            <div className="analytics-chart-card">

              <h3>
                🤖 AI Risk Distribution
              </h3>

              <div className="analytics-chart">

                <ResponsiveContainer
                  width="100%"
                  height={280}
                >

                  <BarChart
                    data={riskDistribution}
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


            {/* MAINTENANCE */}

            <div className="analytics-chart-card">

              <h3>
                🔧 Maintenance Status
              </h3>

              <div className="analytics-chart">

                <ResponsiveContainer
                  width="100%"
                  height={280}
                >

                  <BarChart
                    data={
                      maintenanceStatus
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


            {/* AI DECISIONS */}

            <div className="analytics-chart-card">

              <h3>
                🧠 AI Decision Distribution
              </h3>

              <div className="analytics-chart">

                <ResponsiveContainer
                  width="100%"
                  height={280}
                >

                  <PieChart>

                    <Pie
                      data={
                        aiDecisionDistribution
                      }
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      label
                    >
                      {aiDecisionDistribution.map(
                        (_, index) => (
                          <Cell
                            key={index}
                          />
                        )
                      )}
                    </Pie>

                    <Tooltip />

                    <Legend />

                  </PieChart>

                </ResponsiveContainer>

              </div>

            </div>


            {/* BLOCK PERFORMANCE */}

            <div className="analytics-chart-card">

              <h3>
                🛤️ Block Performance
              </h3>

              <div className="analytics-chart">

                <ResponsiveContainer
                  width="100%"
                  height={280}
                >

                  <BarChart
                    data={blockStatusData}
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

          </section>


          {/* ==================================================
              EXECUTIVE INSIGHT
              ================================================== */}

          <section className="analytics-insight">

            <div className="analytics-insight-icon">
              💡
            </div>

            <div>

              <h3>
                Management Insight
              </h3>

              <p>

                {(
                  trainImpact.total_conflicts || 0
                ) > 0
                  ? "Train movement conflicts are present. Review affected blocks and consider AI-generated alternative maintenance windows."
                  : (
                      ai.urgent_ai_decisions || 0
                    ) > 0
                  ? "Urgent AI maintenance decisions require operational attention."
                  : (
                      maintenance.status_counts
                        ?.OVERDUE || 0
                    ) > 0
                  ? "Overdue maintenance tasks require scheduling attention."
                  : "Railway operations are currently within normal monitored conditions."}

              </p>

            </div>

          </section>

        </>

      )}

    </div>
  );
}

export default Analytics;