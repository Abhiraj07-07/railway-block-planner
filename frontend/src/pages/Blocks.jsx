import "./Blocks.css";
import { useEffect, useMemo, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const TOKEN_KEY = "railway_token";

/* =========================================================
   AUTH FETCH
========================================================= */

const authFetch = async (url, options = {}) => {
  const token = localStorage.getItem(TOKEN_KEY);

  const loaderMessage =
    options.loaderMessage ||
    "Loading railway data...";

  window.dispatchEvent(
    new CustomEvent("railway-loading-start", {
      detail: {
        message: loaderMessage,
      },
    })
  );

  try {
    return await fetch(url, {
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
  } finally {
    window.dispatchEvent(
      new Event("railway-loading-end")
    );
  }
};

/* =========================================================
   HELPERS
========================================================= */

const safeJson = async (response) => {
  try {
    return await response.json();
  } catch {
    return null;
  }
};

const normalizeArray = (value) => {
  if (Array.isArray(value)) {
    return value;
  }

  if (value?.data && Array.isArray(value.data)) {
    return value.data;
  }

  if (value?.items && Array.isArray(value.items)) {
    return value.items;
  }

  if (value?.results && Array.isArray(value.results)) {
    return value.results;
  }

  if (value?.blocks && Array.isArray(value.blocks)) {
    return value.blocks;
  }

  if (value?.tasks && Array.isArray(value.tasks)) {
    return value.tasks;
  }

  if (value?.decisions && Array.isArray(value.decisions)) {
    return value.decisions;
  }

  if (
    value?.recommendations &&
    Array.isArray(value.recommendations)
  ) {
    return value.recommendations;
  }

  return [];
};

const formatDate = (value) => {
  if (!value) {
    return "—";
  }

  const direct = String(value).match(
    /^(\d{4})-(\d{2})-(\d{2})/
  );

  if (direct) {
    return `${direct[3]}-${direct[2]}-${direct[1]}`;
  }

  return String(value);
};

const formatTime = (value) => {
  if (!value) {
    return "—";
  }

  return String(value).slice(0, 5);
};

/*
  Backend create-block endpoint expects HH:MM.
  AI recommendation may return HH:MM:SS.
*/
const toHHMM = (value) => {
  if (!value) {
    return "";
  }

  const text = String(value).trim();

  const match = text.match(
    /^(\d{1,2}):(\d{2})(?::\d{2})?$/
  );

  if (!match) {
    return "";
  }

  return `${match[1].padStart(2, "0")}:${match[2]}`;
};

const toMinutes = (value) => {
  if (!value) {
    return null;
  }

  const parts = String(value).split(":");

  if (parts.length < 2) {
    return null;
  }

  const hours = Number(parts[0]);
  const minutes = Number(parts[1]);

  if (
    Number.isNaN(hours) ||
    Number.isNaN(minutes)
  ) {
    return null;
  }

  return hours * 60 + minutes;
};

const statusClass = (value) => {
  return String(value || "unknown")
    .toLowerCase()
    .replaceAll(" ", "-");
};

const getBlockTaskIds = (block) => {
  if (Array.isArray(block?.task_ids)) {
    return block.task_ids;
  }

  if (Array.isArray(block?.tasks)) {
    return block.tasks
      .map((task) =>
        typeof task === "object"
          ? task.task_id
          : task
      )
      .filter(
        (value) =>
          value !== undefined &&
          value !== null
      );
  }

  if (
    block?.task_id !== undefined &&
    block?.task_id !== null
  ) {
    return [block.task_id];
  }

  return [];
};

const getTodayISO = () => {
  const date = new Date();

  const year = date.getFullYear();

  const month = String(
    date.getMonth() + 1
  ).padStart(2, "0");

  const day = String(
    date.getDate()
  ).padStart(2, "0");

  return `${year}-${month}-${day}`;
};

/* =========================================================
   COMPONENT
========================================================= */

function Blocks() {
  /* =======================================================
     DATA
  ======================================================= */

  const [blocks, setBlocks] = useState([]);
  const [sections, setSections] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [aiDecisions, setAiDecisions] = useState([]);
  const [aiRecommendations, setAiRecommendations] =
    useState([]);

  /* =======================================================
     LOADING
  ======================================================= */

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] =
    useState(false);

  const [aiLoading, setAiLoading] =
    useState(true);

  const [recommendationLoading, setRecommendationLoading] =
    useState(false);

  const [creatingRecommendation, setCreatingRecommendation] =
    useState(null);

  const [createLoading, setCreateLoading] =
    useState(false);

  const [statusLoading, setStatusLoading] =
    useState(null);

  /* =======================================================
     UI
  ======================================================= */

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [blockFilter, setBlockFilter] =
    useState("ALL");

  const [showCreateBlock, setShowCreateBlock] =
    useState(false);

  const [recommendationDate, setRecommendationDate] =
    useState(getTodayISO());

  const [newBlock, setNewBlock] = useState({
    section_id: "",
    block_date: "",
    start_time: "",
    end_time: "",
    task_ids: [],
  });

  /* =======================================================
     LOAD CORE DATA
  ======================================================= */

  const loadCoreData = async ({
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

      const results =
  await Promise.allSettled([
    authFetch(
      `${API_BASE}/planner/blocks`,
      {
        loaderMessage:
          "Loading maintenance blocks...",
      }
    ),

    authFetch(
      `${API_BASE}/sections`,
      {
        loaderMessage:
          "Loading railway sections...",
      }
    ),

    authFetch(
      `${API_BASE}/maintenance-tasks`,
      {
        loaderMessage:
          "Loading maintenance tasks...",
      }
    ),
  ]);

      /* -----------------------------------------------------
         BLOCKS
      ----------------------------------------------------- */

      const blocksResult = results[0];

      if (
        blocksResult.status ===
        "fulfilled"
      ) {
        const response =
          blocksResult.value;

        const data =
          await safeJson(response);

        if (!response.ok) {
          throw new Error(
            data?.detail ||
              `Blocks API failed: ${response.status}`
          );
        }

        setBlocks(
          normalizeArray(data)
        );
      } else {
        throw new Error(
          "Unable to load maintenance blocks."
        );
      }

      /* -----------------------------------------------------
         SECTIONS
      ----------------------------------------------------- */

      const sectionsResult = results[1];

      if (
        sectionsResult.status ===
        "fulfilled"
      ) {
        const response =
          sectionsResult.value;

        const data =
          await safeJson(response);

        if (response.ok) {
          setSections(
            normalizeArray(data)
          );
        }
      }

      /* -----------------------------------------------------
         TASKS
      ----------------------------------------------------- */

      const tasksResult = results[2];

      if (
        tasksResult.status ===
        "fulfilled"
      ) {
        const response =
          tasksResult.value;

        const data =
          await safeJson(response);

        if (response.ok) {
          setTasks(
            normalizeArray(data)
          );
        }
      }
    } catch (err) {
      console.error(
        "Blocks core load error:",
        err
      );

      setError(
        err?.message ||
          "Unable to load maintenance blocks."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  /* =======================================================
     LOAD AI DECISIONS
  ======================================================= */

  const loadAIDecisions = async () => {
    try {
      setAiLoading(true);

      const response =
  await authFetch(
    `${API_BASE}/ai/decisions`,
    {
      loaderMessage:
        "Running AI risk analysis...",
    }
  );

      const data =
        await safeJson(response);

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            `AI API failed: ${response.status}`
        );
      }

      setAiDecisions(
        normalizeArray(data)
      );
    } catch (err) {
      console.error(
        "AI decisions load error:",
        err
      );
    } finally {
      setAiLoading(false);
    }
  };

  /* =======================================================
     LOAD AI RECOMMENDATIONS
  ======================================================= */

  const loadAIRecommendations = async (
    date = recommendationDate
  ) => {
    try {
      setRecommendationLoading(true);
      setError("");

      const response =
  await authFetch(
    `${API_BASE}/planner/recommendations?schedule_date=${encodeURIComponent(
      date
    )}`,
    {
      loaderMessage:
        "AI is finding safe maintenance windows...",
    }
  );

      const data =
        await safeJson(response);

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            `Recommendation API failed: ${response.status}`
        );
      }

      const recommendations =
        normalizeArray(data);

      setAiRecommendations(
        recommendations.filter(
          (item) =>
            item?.recommended !== false
        )
      );
    } catch (err) {
      console.error(
        "AI recommendation load error:",
        err
      );

      setError(
        err?.message ||
          "Unable to load AI block recommendations."
      );

      setAiRecommendations([]);
    } finally {
      setRecommendationLoading(false);
    }
  };

  /* =======================================================
     INITIAL LOAD
  ======================================================= */

  useEffect(() => {
    loadCoreData({
      initial: true,
    });

    const timer = setTimeout(() => {
      loadAIDecisions();
      loadAIRecommendations();
    }, 150);

    return () => {
      clearTimeout(timer);
    };
  }, []);

  /* =======================================================
     LOOKUP MAPS
  ======================================================= */

  const taskMap = useMemo(() => {
    const map = {};

    tasks.forEach((task) => {
      map[task.task_id] = task;
    });

    return map;
  }, [tasks]);

  const sectionMap = useMemo(() => {
    const map = {};

    sections.forEach((section) => {
      map[section.section_id] =
        section;
    });

    return map;
  }, [sections]);

  const decisionMap = useMemo(() => {
    const map = {};

    aiDecisions.forEach(
      (decision) => {
        map[decision.task_id] =
          decision;
      }
    );

    return map;
  }, [aiDecisions]);

  /* =======================================================
     FILTER
  ======================================================= */

  const filteredBlocks = useMemo(() => {
  if (blockFilter === "ALL") {
    return blocks;
  }

  if (blockFilter === "REPLAN_REQUIRED") {
    return blocks.filter(
      (block) =>
        block.replan_required === true
    );
  }

  return blocks.filter(
    (block) =>
      block.status === blockFilter
  );
}, [blocks, blockFilter]);
  /* =======================================================
     COUNTS
  ======================================================= */

  const plannedCount = useMemo(
    () =>
      blocks.filter(
        (block) =>
          block.status ===
          "PLANNED"
      ).length,
    [blocks]
  );

  const approvedCount = useMemo(
    () =>
      blocks.filter(
        (block) =>
          block.status ===
          "APPROVED"
      ).length,
    [blocks]
  );

  const inProgressCount =
    useMemo(
      () =>
        blocks.filter(
          (block) =>
            block.status ===
            "IN_PROGRESS"
        ).length,
      [blocks]
    );

  const completedCount =
    useMemo(
      () =>
        blocks.filter(
          (block) =>
            block.status ===
            "COMPLETED"
        ).length,
      [blocks]
    );

  const cancelledCount =
    useMemo(
      () =>
        blocks.filter(
          (block) =>
            block.status ===
            "CANCELLED"
        ).length,
      [blocks]
    );

  const replanCount = useMemo(
    () =>
      blocks.filter(
        (block) =>
          block.replan_required ===
          true
      ).length,
    [blocks]
  );

  /* =======================================================
     TASK SELECTION
  ======================================================= */

  const toggleTask = (
    taskId
  ) => {
    setNewBlock(
      (previous) => {
        const exists =
          previous.task_ids.includes(
            taskId
          );

        return {
          ...previous,

          task_ids: exists
            ? previous.task_ids.filter(
                (id) =>
                  id !== taskId
              )
            : [
                ...previous.task_ids,
                taskId,
              ],
        };
      }
    );
  };

  /* =======================================================
     MANUAL BLOCK VALIDATION
  ======================================================= */

  const validateNewBlock =
    () => {
      if (!newBlock.section_id) {
        return "Please select a railway section.";
      }

      if (!newBlock.block_date) {
        return "Please select block date.";
      }

      if (!newBlock.start_time) {
        return "Please select start time.";
      }

      if (!newBlock.end_time) {
        return "Please select end time.";
      }

      if (
        newBlock.task_ids.length ===
        0
      ) {
        return "Please select at least one maintenance task.";
      }

      const start =
        toMinutes(
          newBlock.start_time
        );

      const end =
        toMinutes(
          newBlock.end_time
        );

      if (
        start !== null &&
        end !== null &&
        end <= start
      ) {
        return "End time must be later than start time.";
      }

      return null;
    };

  /* =======================================================
     CREATE MANUAL BLOCK
  ======================================================= */

  const handleCreateBlock =
    async () => {
      const validation =
        validateNewBlock();

      if (validation) {
        setMessage(
          `⚠️ ${validation}`
        );
        return;
      }

      try {
        setCreateLoading(true);
        setMessage("");
        setError("");

        const startTime =
          toHHMM(
            newBlock.start_time
          );

        const endTime =
          toHHMM(
            newBlock.end_time
          );

        const url =
          `${API_BASE}/planner/create-block` +
          `?section_id=${encodeURIComponent(
            newBlock.section_id
          )}` +
          `&block_date=${encodeURIComponent(
            newBlock.block_date
          )}` +
          `&start_time=${encodeURIComponent(
            startTime
          )}` +
          `&end_time=${encodeURIComponent(
            endTime
          )}` +
          `&admin=${encodeURIComponent(
            "Abhishek Pal"
          )}`;

        const response =
          await authFetch(
            url,
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json",
              },
              body: JSON.stringify(
                newBlock.task_ids
              ),
            }
          );

        const data =
          await safeJson(response);

        if (!response.ok) {
          throw new Error(
            data?.detail ||
              `Block creation failed: ${response.status}`
          );
        }

        setMessage(
          `✅ ${
            data?.message ||
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

        setShowCreateBlock(false);

        await loadCoreData({
          refresh: true,
        });

        await loadAIDecisions();

        await loadAIRecommendations(
          recommendationDate
        );
      } catch (err) {
        console.error(
          "Create block error:",
          err
        );

        setError(
          err?.message ||
            "Unable to create block."
        );
      } finally {
        setCreateLoading(false);
      }
    };

  /* =======================================================
     CREATE AI RECOMMENDED BLOCK
  ======================================================= */

  const handleCreateRecommendation =
    async (
      recommendation,
      index
    ) => {
      try {
        setCreatingRecommendation(
          index
        );

        setMessage("");
        setError("");

        const taskIds =
          Array.isArray(
            recommendation.task_ids
          )
            ? recommendation.task_ids
            : [];

        if (taskIds.length === 0) {
          throw new Error(
            "AI recommendation does not contain task IDs."
          );
        }

        const startTime =
          toHHMM(
            recommendation.start_time
          );

        const endTime =
          toHHMM(
            recommendation.end_time
          );

        if (!startTime || !endTime) {
          throw new Error(
            "AI recommendation contains an invalid time window."
          );
        }

        const blockDate =
          String(
            recommendation.schedule_date ||
              ""
          ).slice(0, 10);

        if (!blockDate) {
          throw new Error(
            "AI recommendation does not contain a valid planning date."
          );
        }

        const url =
          `${API_BASE}/planner/create-block` +
          `?section_id=${encodeURIComponent(
            recommendation.section_id
          )}` +
          `&block_date=${encodeURIComponent(
            blockDate
          )}` +
          `&start_time=${encodeURIComponent(
            startTime
          )}` +
          `&end_time=${encodeURIComponent(
            endTime
          )}` +
          `&admin=${encodeURIComponent(
            "Abhishek Pal"
          )}`;

        const response =
          await authFetch(
            url,
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json",
              },
              body: JSON.stringify(
                taskIds
              ),
            }
          );

        const data =
          await safeJson(response);

        if (!response.ok) {
          throw new Error(
            data?.detail ||
              `AI block creation failed: ${response.status}`
          );
        }

        setMessage(
          `✅ AI recommendation converted into a planned maintenance block.`
        );

        await loadCoreData({
          refresh: true,
        });

        await loadAIDecisions();

        await loadAIRecommendations(
          recommendationDate
        );
      } catch (err) {
        console.error(
          "Create AI recommendation error:",
          err
        );

        setError(
          err?.message ||
            "Unable to create AI recommended block."
        );
      } finally {
        setCreatingRecommendation(
          null
        );
      }
    };

  /* =======================================================
     STATUS WORKFLOW
  ======================================================= */

  const getAllowedActions =
    (status) => {
      switch (status) {
        case "PLANNED":
          return [
            {
              label: "✅ Approve",
              status: "APPROVED",
            },
            {
              label: "❌ Cancel",
              status: "CANCELLED",
            },
          ];

        case "APPROVED":
          return [
            {
              label: "▶ Start",
              status: "IN_PROGRESS",
            },
            {
              label: "❌ Cancel",
              status: "CANCELLED",
            },
          ];

        case "IN_PROGRESS":
          return [
            {
              label: "✅ Complete",
              status: "COMPLETED",
            },
          ];

        default:
          return [];
      }
    };

  /* =======================================================
     STATUS UPDATE
  ======================================================= */

  const handleStatusChange =
    async (
      blockId,
      newStatus
    ) => {
      try {
        setStatusLoading(
          `${blockId}-${newStatus}`
        );

        setError("");
        setMessage("");

        const response =
          await authFetch(
            `${API_BASE}/planner/blocks/${blockId}/status` +
              `?new_status=${encodeURIComponent(
                newStatus
              )}`,
            {
              method: "PATCH",
            }
          );

        const data =
          await safeJson(response);

        if (!response.ok) {
          throw new Error(
            data?.detail ||
              `Status update failed: ${response.status}`
          );
        }

        setBlocks(
          (previous) =>
            previous.map(
              (block) =>
                block.block_id ===
                blockId
                  ? {
                      ...block,
                      status:
                        newStatus,
                    }
                  : block
            )
        );

        setMessage(
          `✅ Block status updated to ${newStatus}.`
        );

        await loadCoreData();
        await loadAIDecisions();
      } catch (err) {
        console.error(
          "Status update error:",
          err
        );

        setError(
          err?.message ||
            "Unable to update block status."
        );
      } finally {
        setStatusLoading(null);
      }
    };

  /* =======================================================
     BLOCK TASKS
  ======================================================= */

  const getBlockTasks = (
    block
  ) => {
    const ids =
      getBlockTaskIds(block);

    return ids
      .map(
        (taskId) =>
          taskMap[taskId]
      )
      .filter(Boolean);
  };

  /* =======================================================
     BEST AI DECISION
  ======================================================= */

  const getBestBlockDecision =
    (block) => {
      const blockTasks =
        getBlockTasks(block);

      const decisions =
        blockTasks
          .map(
            (task) =>
              decisionMap[
                task.task_id
              ]
          )
          .filter(Boolean);

      if (
        decisions.length ===
        0
      ) {
        return null;
      }

      return [...decisions].sort(
        (a, b) =>
          (Number(
            b.ai_decision_score
          ) || 0) -
          (Number(
            a.ai_decision_score
          ) || 0)
      )[0];
    };

  /* =======================================================
     SECTION
  ======================================================= */

  const getSectionLabel =
    (sectionId) => {
      const section =
        sectionMap[sectionId];

      if (
        section?.section_code
      ) {
        return section.section_code;
      }

      return `SEC${String(
        sectionId ?? ""
      ).padStart(2, "0")}`;
    };

  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="page-container">

      {/* =================================================
          HEADER
      ================================================= */}

      <div className="page-title-row">

        <div>

          <span className="page-eyebrow">
            MAINTENANCE OPERATIONS
          </span>

          <h1>
            🛠️ Maintenance Blocks
          </h1>

          <p>
            Create, approve and manage
            AI-optimized railway
            maintenance blocks.
          </p>

        </div>

        <div
          style={{
            display: "flex",
            gap: "9px",
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >

          <button
            className="filter-button"
            type="button"
            onClick={() =>
              loadCoreData({
                refresh: true,
              })
            }
            disabled={refreshing}
          >
            {refreshing
              ? "⏳ Refreshing..."
              : "🔄 Refresh"}
          </button>

          <button
            className="primary-button"
            type="button"
            onClick={() => {
              setShowCreateBlock(
                (previous) =>
                  !previous
              );

              setMessage("");
              setError("");
            }}
          >
            {showCreateBlock
              ? "✖ Close"
              : "➕ New Block"}
          </button>

        </div>

      </div>

      {/* =================================================
          ALERTS
      ================================================= */}

      {error && (
        <div className="global-error">
          <strong>Error:</strong>{" "}
          {error}
        </div>
      )}

      {message && (
        <div className="action-message">
          {message}
        </div>
      )}

      {/* =================================================
          SUMMARY
      ================================================= */}

      <section className="block-summary-grid">

        <div className="block-summary-card">
          <span>
            📋 Total Blocks
          </span>

          <strong>
            {loading
              ? "..."
              : blocks.length}
          </strong>
        </div>

        <div className="block-summary-card">
          <span>
            📝 Planned
          </span>

          <strong>
            {loading
              ? "..."
              : plannedCount}
          </strong>
        </div>

        <div className="block-summary-card">
          <span>
            ✅ Approved
          </span>

          <strong>
            {loading
              ? "..."
              : approvedCount}
          </strong>
        </div>

        <div className="block-summary-card">
          <span>
            🚧 In Progress
          </span>

          <strong>
            {loading
              ? "..."
              : inProgressCount}
          </strong>
        </div>

        <div className="block-summary-card">
          <span>
            ✔ Completed
          </span>

          <strong>
            {loading
              ? "..."
              : completedCount}
          </strong>
        </div>

        <div className="block-summary-card">
          <span>
            ❌ Cancelled
          </span>

          <strong>
            {loading
              ? "..."
              : cancelledCount}
          </strong>
        </div>

      </section>

      {/* =================================================
          REPLAN ALERT
      ================================================= */}

      {replanCount > 0 && (
        <div
          style={{
            marginBottom: "20px",
            padding: "14px 16px",
            border:
              "1px solid #fed7aa",
            borderRadius: "12px",
            background: "#fff7ed",
            color: "#9a3412",
            fontSize: "13px",
            fontWeight: "750",
          }}
        >
          ⚠️ {replanCount} block
          {replanCount !== 1
            ? "s"
            : ""} require AI
          re-planning.
        </div>
      )}

      {/* =================================================
          AI RECOMMENDATIONS
      ================================================= */}

      <section className="page-card">

        <div
          className="page-card-header"
          style={{
            alignItems:
              "flex-start",
            gap: "15px",
            flexWrap:
              "wrap",
          }}
        >

          <div>

            <h2>
              🤖 AI Recommended Blocks
            </h2>

            <p>
              AI combines maintenance
              priority, asset risk and
              railway train schedules to
              recommend safer maintenance
              windows.
            </p>

          </div>

          <div
            style={{
              display: "flex",
              gap: "8px",
              alignItems:
                "center",
              flexWrap:
                "wrap",
            }}
          >

            <input
              type="date"
              value={
                recommendationDate
              }
              onChange={(event) =>
                setRecommendationDate(
                  event.target.value
                )
              }
              style={{
                padding:
                  "9px 11px",
                border:
                  "1px solid #cbd5e1",
                borderRadius:
                  "9px",
                background:
                  "#ffffff",
                color:
                  "#0f172a",
                fontWeight:
                  "700",
              }}
            />

            <button
              className="filter-button active"
              type="button"
              onClick={() =>
                loadAIRecommendations(
                  recommendationDate
                )
              }
              disabled={
                recommendationLoading ||
                !recommendationDate
              }
            >
              {recommendationLoading
                ? "⏳ Planning..."
                : "🧠 Generate AI Plan"}
            </button>

          </div>

        </div>

        <div
          style={{
            marginBottom:
              "16px",
            padding:
              "11px 13px",
            borderRadius:
              "10px",
            background:
              "#f8fafc",
            border:
              "1px solid #e2e8f0",
            fontSize:
              "12px",
            fontWeight:
              "800",
            color:
              "#475569",
          }}
        >
          📅 Planning date:{" "}
          <strong>
            {formatDate(
              recommendationDate
            )}
          </strong>
          {" · "}
          {recommendationLoading
            ? "Generating..."
            : `${aiRecommendations.length} AI recommendation${
                aiRecommendations.length !==
                1
                  ? "s"
                  : ""
              }`}
        </div>

        {recommendationLoading ? (

          <div className="page-loading">

            <div className="loader" />

            AI is analysing
            maintenance tasks,
            train traffic and safe
            maintenance windows...

          </div>

        ) : aiRecommendations.length ===
          0 ? (

          <div
            style={{
              padding:
                "25px 15px",
              textAlign:
                "center",
              color:
                "#64748b",
              fontWeight:
                "700",
            }}
          >
            No AI maintenance
            recommendations available
            for this date.
          </div>

        ) : (

          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(310px, 1fr))",
              gap: "15px",
            }}
          >

            {aiRecommendations.map(
              (
                recommendation,
                index
              ) => {

                const section =
                  sectionMap[
                    recommendation.section_id
                  ];

                const recommendationTasks =
                  Array.isArray(
                    recommendation.task_ids
                  )
                    ? recommendation.task_ids
                        .map(
                          (id) =>
                            taskMap[id]
                        )
                        .filter(Boolean)
                    : [];

                const isCreating =
                  creatingRecommendation ===
                  index;

                return (
                  <div
                    key={`${recommendation.section_id}-${recommendation.start_time}-${index}`}
                    style={{
                      border:
                        "1px solid #dbeafe",
                      borderRadius:
                        "15px",
                      padding:
                        "17px",
                      background:
                        "linear-gradient(145deg,#ffffff,#f8fbff)",
                      boxShadow:
                        "0 8px 22px rgba(15,23,42,0.06)",
                    }}
                  >

                    {/* TOP */}

                    <div
                      style={{
                        display:
                          "flex",
                        justifyContent:
                          "space-between",
                        alignItems:
                          "flex-start",
                        gap:
                          "10px",
                        marginBottom:
                          "13px",
                      }}
                    >

                      <div>

                        <div
                          style={{
                            fontSize:
                              "11px",
                            fontWeight:
                              "850",
                            color:
                              "#2563eb",
                            letterSpacing:
                              "0.07em",
                          }}
                        >
                          🤖 AI RECOMMENDED
                        </div>

                        <h3
                          style={{
                            margin:
                              "5px 0 2px",
                            fontSize:
                              "17px",
                            color:
                              "#0f172a",
                          }}
                        >
                          {getSectionLabel(
                            recommendation.section_id
                          )}
                        </h3>

                      </div>

                      <span
                        style={{
                          padding:
                            "6px 9px",
                          borderRadius:
                            "999px",
                          background:
                            "#eff6ff",
                          color:
                            "#1d4ed8",
                          fontSize:
                            "11px",
                          fontWeight:
                            "850",
                        }}
                      >
                        {recommendation.task_count ??
                          recommendationTasks.length}{" "}
                        task
                        {(recommendation.task_count ??
                          recommendationTasks.length) !==
                        1
                          ? "s"
                          : ""}
                      </span>

                    </div>

                    {/* DATE / TIME */}

                    <div
                      style={{
                        display:
                          "grid",
                        gridTemplateColumns:
                          "1fr 1fr",
                        gap:
                          "10px",
                        marginBottom:
                          "13px",
                      }}
                    >

                      <div
                        style={{
                          padding:
                            "10px",
                          borderRadius:
                            "10px",
                          background:
                            "#f8fafc",
                        }}
                      >

                        <span
                          style={{
                            display:
                              "block",
                            fontSize:
                              "10px",
                            fontWeight:
                              "800",
                            color:
                              "#64748b",
                            marginBottom:
                              "4px",
                          }}
                        >
                          DATE
                        </span>

                        <strong
                          style={{
                            fontSize:
                              "13px",
                            color:
                              "#0f172a",
                          }}
                        >
                          {formatDate(
                            recommendation.schedule_date
                          )}
                        </strong>

                      </div>

                      <div
                        style={{
                          padding:
                            "10px",
                          borderRadius:
                            "10px",
                          background:
                            "#f8fafc",
                        }}
                      >

                        <span
                          style={{
                            display:
                              "block",
                            fontSize:
                              "10px",
                            fontWeight:
                              "800",
                            color:
                              "#64748b",
                            marginBottom:
                              "4px",
                          }}
                        >
                          SAFE WINDOW
                        </span>

                        <strong
                          style={{
                            fontSize:
                              "13px",
                            color:
                              "#0f172a",
                          }}
                        >
                          {formatTime(
                            recommendation.start_time
                          )}
                          {" – "}
                          {formatTime(
                            recommendation.end_time
                          )}
                        </strong>

                      </div>

                    </div>

                    {/* SECTION DETAILS */}

                    <div
                      style={{
                        fontSize:
                          "12px",
                        color:
                          "#475569",
                        marginBottom:
                          "12px",
                      }}
                    >

                      <strong>
                        {section?.from_station ??
                          "Station"}
                      </strong>

                      {" → "}

                      <strong>
                        {section?.to_station ??
                          "Station"}
                      </strong>

                      {section?.distance_km !==
                        undefined && (
                        <>
                          {" · "}
                          {
                            section.distance_km
                          }{" "}
                          km
                        </>
                      )}

                    </div>

                    {/* TASKS */}

                    <div
                      style={{
                        marginBottom:
                          "13px",
                      }}
                    >

                      <div
                        style={{
                          fontSize:
                            "10px",
                          fontWeight:
                            "850",
                          color:
                            "#64748b",
                          marginBottom:
                            "7px",
                          letterSpacing:
                            "0.05em",
                        }}
                      >
                        MAINTENANCE TASKS
                      </div>

                      <div
                        style={{
                          display:
                            "flex",
                          gap:
                            "6px",
                          flexWrap:
                            "wrap",
                        }}
                      >

                        {(
                          recommendation.task_codes ||
                          []
                        ).map(
                          (code) => (
                            <span
                              key={
                                code
                              }
                              style={{
                                padding:
                                  "5px 8px",
                                borderRadius:
                                  "7px",
                                background:
                                  "#f1f5f9",
                                border:
                                  "1px solid #e2e8f0",
                                color:
                                  "#334155",
                                fontSize:
                                  "11px",
                                fontWeight:
                                  "800",
                              }}
                            >
                              {code}
                            </span>
                          )
                        )}

                      </div>

                    </div>

                    {/* REASON */}

                    <div
                      style={{
                        padding:
                          "10px",
                        borderRadius:
                          "9px",
                        background:
                          "#f0fdf4",
                        border:
                          "1px solid #dcfce7",
                        color:
                          "#166534",
                        fontSize:
                          "11px",
                        lineHeight:
                          "1.5",
                        marginBottom:
                          "13px",
                      }}
                    >

                      <strong>
                        🧠 Why this plan?
                      </strong>

                      <br />

                      {recommendation.reason ||
                        "Priority-aware AI planning with train-conflict avoidance."}

                    </div>

                    {/* CREATE */}

                    <button
                      type="button"
                      className="primary-button"
                      onClick={() =>
                        handleCreateRecommendation(
                          recommendation,
                          index
                        )
                      }
                      disabled={
                        isCreating
                      }
                      style={{
                        width:
                          "100%",
                      }}
                    >
                      {isCreating
                        ? "⏳ Creating Block..."
                        : "🚧 Create This AI Block"}
                    </button>

                  </div>
                );
              }
            )}

          </div>
        )}

      </section>

      {/* =================================================
          MANUAL CREATE BLOCK
      ================================================= */}

      {showCreateBlock && (
        <section className="page-card">

          <div className="page-card-header">

            <div>

              <h2>
                ➕ Create Maintenance
                Block
              </h2>

              <p>
                Select section, timing
                and maintenance tasks.
              </p>

            </div>

          </div>

          <div className="block-form">

            <div className="form-group">

              <label>
                Railway Section
              </label>

              <select
                value={
                  newBlock.section_id
                }
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

          </div>

          {/* TASK SELECTION */}

          <div className="form-group block-task-group">

            <label>
              Maintenance Tasks
            </label>

            <div className="block-task-list">

              {tasks.length === 0 ? (

                <p className="empty-state">
                  No maintenance tasks
                  available.
                </p>

              ) : (

                tasks.map((task) => {

                  const decision =
                    decisionMap[
                      task.task_id
                    ];

                  const selected =
                    newBlock.task_ids.includes(
                      task.task_id
                    );

                  return (
                    <label
                      className="block-task-item"
                      key={
                        task.task_id
                      }
                      style={
                        selected
                          ? {
                              borderColor:
                                "#2563eb",
                              background:
                                "#eff6ff",
                            }
                          : undefined
                      }
                    >

                      <input
                        type="checkbox"
                        checked={
                          selected
                        }
                        onChange={() =>
                          toggleTask(
                            task.task_id
                          )
                        }
                      />

                      <span>

                        <strong>
                          {
                            task.task_code
                          }
                        </strong>

                        {" · "}

                        {
                          task.task_type
                        }

                        {" · "}

                        {
                          task.severity
                        }

                        {decision ? (

                          <small className="task-ai-inline">
                            {" · "}AI{" "}
                            {
                              decision.decision_level
                            }
                            {" · "}ML{" "}
                            {
                              decision.ml_risk_percentage
                            }%
                          </small>

                        ) : aiLoading ? (

                          <small className="task-ai-inline">
                            {" · "}AI loading...
                          </small>

                        ) : null}

                      </span>

                    </label>
                  );
                })

              )}

            </div>

          </div>

          <div
            style={{
              display: "flex",
              alignItems:
                "center",
              justifyContent:
                "space-between",
              gap: "15px",
              flexWrap:
                "wrap",
            }}
          >

            <span
              style={{
                color:
                  "#64748b",
                fontSize:
                  "12px",
                fontWeight:
                  "700",
              }}
            >
              {newBlock.task_ids.length} task
              {newBlock.task_ids.length !==
              1
                ? "s"
                : ""}{" "}
              selected
            </span>

            <button
              className="primary-button"
              type="button"
              onClick={
                handleCreateBlock
              }
              disabled={
                createLoading
              }
            >
              {createLoading
                ? "⏳ Creating..."
                : "🚧 Create Block"}
            </button>

          </div>

        </section>
      )}

      {/* =================================================
          SAVED BLOCKS
      ================================================= */}

      <section className="page-card">

        <div className="page-card-header">

          <div>

            <h2>
              📋 Maintenance Blocks
            </h2>

            <p>
              Saved blocks, AI risk
              intelligence and
              operational status.
            </p>

          </div>

          <span className="page-count">
            {
              filteredBlocks.length
            }{" "}
            Blocks
          </span>

        </div>

        {/* FILTERS */}

        <div className="block-filter-bar">

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
              className={
                blockFilter ===
                filter
                  ? "filter-button active"
                  : "filter-button"
              }
              onClick={() =>
                setBlockFilter(
                  filter
                )
              }
            >

              {filter ===
              "ALL"
                ? "📋 All"
                : filter ===
                  "PLANNED"
                ? "📝 Planned"
                : filter ===
                  "APPROVED"
                ? "✅ Approved"
                : filter ===
                  "IN_PROGRESS"
                ? "🚧 In Progress"
                : filter ===
                  "COMPLETED"
                ? "✔ Completed"
                : filter ===
                  "CANCELLED"
                ? "❌ Cancelled"
                : "⚠️ Re-plan"}

            </button>

          ))}

        </div>

        {/* TABLE */}

        {loading ? (

          <div className="page-loading">

            <div className="loader" />

            Loading maintenance
            blocks...

          </div>

        ) : filteredBlocks.length ===
          0 ? (

          <div
            style={{
              padding:
                "30px 15px",
              textAlign:
                "center",
            }}
          >

            <div
              style={{
                fontSize:
                  "35px",
                marginBottom:
                  "8px",
              }}
            >
              🚧
            </div>

            <p
              className="empty-state"
              style={{
                margin:
                  "0 0 8px",
              }}
            >
              No maintenance blocks
              found.
            </p>

            <span
              style={{
                fontSize:
                  "12px",
                color:
                  "#64748b",
                fontWeight:
                  "650",
              }}
            >
              Create an AI-recommended
              block above to start the
              maintenance planning
              workflow.
            </span>

          </div>

        ) : (

          <div className="table-container">

            <table>

              <thead>

                <tr>

                  <th>
                    Block
                  </th>

                  <th>
                    Section
                  </th>

                  <th>
                    Date
                  </th>

                  <th>
                    Time
                  </th>

                  <th>
                    Tasks
                  </th>

                  <th>
                    AI Intelligence
                  </th>

                  <th>
                    Status
                  </th>

                  <th>
                    Action
                  </th>

                </tr>

              </thead>

              <tbody>

                {filteredBlocks.map(
                  (block) => {

                    const blockTasks =
                      getBlockTasks(
                        block
                      );

                    const bestDecision =
                      getBestBlockDecision(
                        block
                      );

                    const actions =
                      getAllowedActions(
                        block.status
                      );

                    const isStatusLoading =
                      statusLoading !==
                        null &&
                      statusLoading.startsWith(
                        `${block.block_id}-`
                      );

                    return (
                      <tr
                        key={
                          block.block_id
                        }
                        style={
                          block.replan_required
                            ? {
                                background:
                                  "#fffaf5",
                              }
                            : undefined
                        }
                      >

                        {/* BLOCK */}

                        <td>

                          <strong>
                            {
                              block.block_code
                            }
                          </strong>

                          {block.replan_required && (
                            <span className="replan-tag">
                              ⚠️ Re-plan
                            </span>
                          )}

                        </td>

                        {/* SECTION */}

                        <td>
                          {
                            getSectionLabel(
                              block.section_id
                            )
                          }
                        </td>

                        {/* DATE */}

                        <td>
                          {
                            formatDate(
                              block.block_date
                            )
                          }
                        </td>

                        {/* TIME */}

                        <td>

                          <strong>
                            {
                              formatTime(
                                block.start_time
                              )
                            }
                            {" – "}
                            {
                              formatTime(
                                block.end_time
                              )
                            }
                          </strong>

                          {block.recommended_start_time &&
                            block.recommended_end_time && (

                            <small className="recommended-time">

                              AI:
                              {" "}
                              {
                                formatTime(
                                  block.recommended_start_time
                                )
                              }
                              {" – "}
                              {
                                formatTime(
                                  block.recommended_end_time
                                )
                              }

                            </small>

                          )}

                        </td>

                        {/* TASKS */}

                        <td>

                          {blockTasks.length >
                          0 ? (

                            <div className="block-task-chip-list">

                              {blockTasks.map(
                                (
                                  task
                                ) => (
                                  <span
                                    className="task-code-chip"
                                    key={
                                      task.task_id
                                    }
                                    title={
                                      task.description ||
                                      task.task_type
                                    }
                                  >
                                    {
                                      task.task_code
                                    }
                                  </span>
                                )
                              )}

                            </div>

                          ) : (

                            <span>
                              —
                            </span>

                          )}

                        </td>

                        {/* AI */}

                        <td>

                          {bestDecision ? (

                            <div className="block-ai-info">

                              <div>

                                <span>
                                  ML Risk
                                </span>

                                <strong>
                                  {
                                    bestDecision.ml_risk_percentage ??
                                    "—"
                                  }%
                                </strong>

                              </div>

                              <div>

                                <span>
                                  Combined
                                </span>

                                <strong>
                                  {
                                    bestDecision.combined_risk_score ??
                                    "—"
                                  }
                                </strong>

                              </div>

                              <div>

                                <span>
                                  AI Score
                                </span>

                                <strong>
                                  {
                                    bestDecision.ai_decision_score ??
                                    "—"
                                  }
                                </strong>

                              </div>

                              {bestDecision.planning_score !==
                                undefined &&
                                bestDecision.planning_score !==
                                  null && (

                                <div>

                                  <span>
                                    Planning
                                  </span>

                                  <strong>
                                    {
                                      bestDecision.planning_score
                                    }
                                  </strong>

                                </div>

                              )}

                              <span
                                className={`badge ${statusClass(
                                  bestDecision.decision_level ||
                                    "MEDIUM"
                                )}`}
                              >
                                {
                                  bestDecision.decision_level ||
                                  "MEDIUM"
                                }
                              </span>

                            </div>

                          ) : aiLoading ? (

                            <span>
                              🧠 AI loading...
                            </span>

                          ) : (

                            <span>
                              —
                            </span>

                          )}

                        </td>

                        {/* STATUS */}

                        <td>

                          <span
                            className={`badge status-${statusClass(
                              block.status
                            )}`}
                          >
                            {
                              block.status ||
                              "UNKNOWN"
                            }
                          </span>

                        </td>

                        {/* ACTION */}

                        <td>

                          {actions.length >
                          0 ? (

                            actions.map(
                              (
                                action
                              ) => (

                                <button
                                  key={
                                    action.status
                                  }
                                  type="button"
                                  className="table-action-button"
                                  onClick={() =>
                                    handleStatusChange(
                                      block.block_id,
                                      action.status
                                    )
                                  }
                                  disabled={
                                    isStatusLoading
                                  }
                                >

                                  {statusLoading ===
                                  `${block.block_id}-${action.status}`
                                    ? "⏳"
                                    : action.label}

                                </button>

                              )
                            )

                          ) : block.status ===
                            "COMPLETED" ? (

                            <span className="badge status-completed">
                              ✅ Completed
                            </span>

                          ) : block.status ===
                            "CANCELLED" ? (

                            <span className="badge status-cancelled">
                              ❌ Cancelled
                            </span>

                          ) : (

                            <span>
                              —
                            </span>

                          )}

                        </td>

                      </tr>
                    );
                  }
                )}

              </tbody>

            </table>

          </div>

        )}

      </section>

    </div>
  );
}

export default Blocks;