
import React, {
  useEffect,
  useMemo,
  useState,
} from "react";

import { authFetch } from "../App";
import "./Timeline.css";

/* =========================================================
   API CONFIG
========================================================= */

const API_BASE =
  import.meta.env.VITE_API_BASE ||
  "http://127.0.0.1:8000";

/* =========================================================
   API REQUEST
   App.jsx authFetch already returns parsed JSON.
========================================================= */

const apiRequest = async (
  url,
  options = {}
) => {
  try {
    return await authFetch(
      url,
      options
    );
  } catch (error) {
    console.error(
      "API request failed:",
      error
    );

    throw new Error(
      error?.message ||
        "Unable to connect to railway backend."
    );
  }
};

/* =========================================================
   BASIC HELPERS
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
    value?.items &&
    Array.isArray(value.items)
  ) {
    return value.items;
  }

  if (
    value?.results &&
    Array.isArray(value.results)
  ) {
    return value.results;
  }

  if (
    value?.blocks &&
    Array.isArray(value.blocks)
  ) {
    return value.blocks;
  }

  if (
    value?.schedules &&
    Array.isArray(value.schedules)
  ) {
    return value.schedules;
  }

  if (
    value?.train_schedule &&
    Array.isArray(
      value.train_schedule
    )
  ) {
    return value.train_schedule;
  }

  if (
    value?.recommendations &&
    Array.isArray(
      value.recommendations
    )
  ) {
    return value.recommendations;
  }

  if (
    value?.decisions &&
    Array.isArray(
      value.decisions
    )
  ) {
    return value.decisions;
  }

  if (
    value?.tasks &&
    Array.isArray(value.tasks)
  ) {
    return value.tasks;
  }

  return [];
};

const normalizeStatus = (value) => {
  return String(
    value ?? ""
  )
    .trim()
    .toUpperCase();
};

const formatTime = (value) => {
  if (!value) {
    return "—";
  }

  return String(value).slice(0, 5);
};

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

  return `${match[1].padStart(
    2,
    "0"
  )}:${match[2]}`;
};

const dateToKey = (value) => {
  if (!value) {
    return "";
  }

  const text = String(value);

  const match = text.match(
    /^(\d{4})-(\d{2})-(\d{2})/
  );

  if (match) {
    return match[0];
  }

  const date = new Date(value);

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return text.slice(0, 10);
  }

  return `${date.getFullYear()}-${String(
    date.getMonth() + 1
  ).padStart(
    2,
    "0"
  )}-${String(
    date.getDate()
  ).padStart(
    2,
    "0"
  )}`;
};

const formatDate = (value) => {
  if (!value) {
    return "—";
  }

  const direct =
    String(value).match(
      /^(\d{4})-(\d{2})-(\d{2})/
    );

  if (direct) {
    return `${direct[3]}-${direct[2]}-${direct[1]}`;
  }

  const date = new Date(value);

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return String(value);
  }

  return date.toLocaleDateString(
    "en-GB",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }
  );
};

const getDatePlusDays = (
  startDate,
  days
) => {
  const date = new Date(
    `${startDate}T00:00:00`
  );

  date.setDate(
    date.getDate() + days
  );

  return dateToKey(date);
};

const parseTime = (value) => {
  if (!value) {
    return 0;
  }

  const parts =
    String(value).split(":");

  const hours =
    Number(parts[0]) || 0;

  const minutes =
    Number(parts[1]) || 0;

  return (
    hours * 60 +
    minutes
  );
};

const getDurationHours = (
  startTime,
  endTime
) => {
  const start =
    parseTime(startTime);

  const end =
    parseTime(endTime);

  if (end <= start) {
    return 0;
  }

  return Number(
    ((end - start) / 60).toFixed(2)
  );
};

const getErrorMessage = (
  error,
  fallback
) => {
  if (!error) {
    return fallback;
  }

  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === "string") {
    return error;
  }

  if (error?.detail) {
    return typeof error.detail ===
      "string"
      ? error.detail
      : JSON.stringify(
          error.detail
        );
  }

  if (error?.message) {
    return typeof error.message ===
      "string"
      ? error.message
      : JSON.stringify(
          error.message
        );
  }

  try {
    return JSON.stringify(error);
  } catch {
    return fallback;
  }
};

/* =========================================================
   BLOCK STATUS HELPERS

   Active means only:
   PLANNED
   APPROVED
   IN_PROGRESS

   COMPLETED and CANCELLED are NOT active.
========================================================= */

const ACTIVE_BLOCK_STATUSES = [
  "PLANNED",
  "APPROVED",
  "IN_PROGRESS",
];

const isActiveBlock = (block) => {
  return ACTIVE_BLOCK_STATUSES.includes(
    normalizeStatus(block?.status)
  );
};

const isCancelledBlock = (block) => {
  return (
    normalizeStatus(block?.status) ===
    "CANCELLED"
  );
};

/* =========================================================
   HORIZON HELPERS
========================================================= */

const getHorizonDays = (
  plan
) => {
  if (!plan) {
    return [];
  }

  if (Array.isArray(plan.days)) {
    return plan.days;
  }

  if (Array.isArray(plan.plan)) {
    return plan.plan;
  }

  if (
    Array.isArray(
      plan.recommendations
    )
  ) {
    return plan.recommendations;
  }

  return [];
};

const getDayRecommendations = (
  day
) => {
  if (!day) {
    return [];
  }

  if (
    Array.isArray(
      day.recommendations
    )
  ) {
    return day.recommendations;
  }

  if (Array.isArray(day.blocks)) {
    return day.blocks;
  }

  if (
    Array.isArray(
      day.planned_blocks
    )
  ) {
    return day.planned_blocks;
  }

  return [];
};

const getRecommendationTaskIds = (
  recommendation
) => {
  if (!recommendation) {
    return [];
  }

  if (
    Array.isArray(
      recommendation.task_ids
    )
  ) {
    return recommendation.task_ids;
  }

  if (
    Array.isArray(
      recommendation.tasks
    )
  ) {
    return recommendation.tasks
      .map(
        (task) =>
          task?.task_id ??
          task?.id
      )
      .filter(
        (id) =>
          id !== undefined &&
          id !== null
      );
  }

  return [];
};

const getBlockTaskIds = (
  block
) => {
  if (!block) {
    return [];
  }

  if (
    Array.isArray(block.task_ids)
  ) {
    return block.task_ids.map(
      (id) => String(id)
    );
  }

  if (
    Array.isArray(block.tasks)
  ) {
    return block.tasks
      .map(
        (task) =>
          task?.task_id ??
          task?.id ??
          task
      )
      .map((id) => String(id));
  }

  if (
    Array.isArray(
      block.block_tasks
    )
  ) {
    return block.block_tasks
      .map(
        (task) =>
          task?.task_id ??
          task?.id ??
          task
      )
      .map((id) => String(id));
  }

  return [];
};

/* =========================================================
   COMPONENT
========================================================= */

function Timeline() {
  /* =======================================================
     DATA
  ======================================================= */

  const [
    blocks,
    setBlocks,
  ] = useState([]);

  const [
    trainSchedule,
    setTrainSchedule,
  ] = useState([]);

  const [
    maintenanceTasks,
    setMaintenanceTasks,
  ] = useState([]);

  const [
    aiDecisions,
    setAiDecisions,
  ] = useState([]);

  /* =======================================================
     PAGE STATE
  ======================================================= */

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");

  /* =======================================================
     ACTUAL TIMELINE
  ======================================================= */

  const [
    timelineDate,
    setTimelineDate,
  ] = useState(
    "2026-09-04"
  );

  const [
    timelineBlockFilter,
    setTimelineBlockFilter,
  ] = useState(
    "ACTIVE"
  );

  /* =======================================================
     PLANNING
  ======================================================= */

  const [
    planningMode,
    setPlanningMode,
  ] = useState(
    "WEEKLY"
  );

  const [
    planningStartDate,
    setPlanningStartDate,
  ] = useState(
    "2026-09-02"
  );

  const [
    planningEndDate,
    setPlanningEndDate,
  ] = useState(
    "2026-09-08"
  );

  const [
    horizonPlan,
    setHorizonPlan,
  ] = useState(null);

  const [
    planningLoading,
    setPlanningLoading,
  ] = useState(false);

  const [
    planningError,
    setPlanningError,
  ] = useState("");

  /* =======================================================
     REVIEW MODAL
  ======================================================= */

  const [
    selectedRecommendation,
    setSelectedRecommendation,
  ] = useState(null);

  const [
    approvalLoading,
    setApprovalLoading,
  ] = useState(false);

  const [
    approvalError,
    setApprovalError,
  ] = useState("");

  const [
    approvalSuccess,
    setApprovalSuccess,
  ] = useState("");

  /* =======================================================
     LOAD TIMELINE DATA
  ======================================================= */

  const loadTimelineData =
    async () => {
      try {
        setLoading(true);
        setError("");

        const [
          blocksData,
          trainsData,
          tasksData,
          decisionsData,
        ] =
          await Promise.all([
            apiRequest(
              `${API_BASE}/planner/blocks`
            ),

            apiRequest(
              `${API_BASE}/train-schedule`
            ),

            apiRequest(
              `${API_BASE}/maintenance-tasks`
            ),

            apiRequest(
              `${API_BASE}/ai/decisions`
            ),
          ]);

        setBlocks(
          normalizeArray(
            blocksData
          )
        );

        setTrainSchedule(
          normalizeArray(
            trainsData
          )
        );

        setMaintenanceTasks(
          normalizeArray(
            tasksData
          )
        );

        setAiDecisions(
          normalizeArray(
            decisionsData
          )
        );
      } catch (err) {
        console.error(
          "Timeline load error:",
          err
        );

        setError(
          getErrorMessage(
            err,
            "Unable to load timeline data."
          )
        );
      } finally {
        setLoading(false);
      }
    };

  useEffect(() => {
    loadTimelineData();
  }, []);

  /* =======================================================
     DATE RANGE
  ======================================================= */

  useEffect(() => {
    const dayCount =
      planningMode ===
      "MONTHLY"
        ? 29
        : 6;

    setPlanningEndDate(
      getDatePlusDays(
        planningStartDate,
        dayCount
      )
    );
  }, [
    planningMode,
    planningStartDate,
  ]);

  /* =======================================================
     TASK MAP
  ======================================================= */

  const taskMap =
    useMemo(() => {
      const map = {};

      maintenanceTasks.forEach(
        (task) => {
          map[
            String(
              task.task_id
            )
          ] = task;
        }
      );

      return map;
    }, [
      maintenanceTasks,
    ]);

  /* =======================================================
     AI DECISION MAP
  ======================================================= */

  const aiDecisionMap =
    useMemo(() => {
      const map = {};

      aiDecisions.forEach(
        (decision) => {
          if (
            decision?.task_id !==
              undefined &&
            decision?.task_id !== null
          ) {
            map[
              String(
                decision.task_id
              )
            ] = decision;
          }
        }
      );

      return map;
    }, [
      aiDecisions,
    ]);

  /* =======================================================
     HORIZON PLAN
  ======================================================= */

  const generateHorizonPlan =
    async () => {
      try {
        setPlanningLoading(true);
        setPlanningError("");
        setHorizonPlan(null);

        if (
          !planningStartDate ||
          !planningEndDate
        ) {
          throw new Error(
            "Please select start and end dates."
          );
        }

        if (
          planningEndDate <
          planningStartDate
        ) {
          throw new Error(
            "End date must be greater than or equal to start date."
          );
        }

        const data =
          await apiRequest(
            `${API_BASE}/planner/horizon-plan`,
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json",
              },
              body: JSON.stringify({
                start_date:
                  planningStartDate,

                end_date:
                  planningEndDate,

                horizon:
                  planningMode,
              }),
            }
          );

        if (
          !data ||
          typeof data !==
            "object"
        ) {
          throw new Error(
            "Invalid response received from horizon planner."
          );
        }

        setHorizonPlan(data);
      } catch (err) {
        console.error(
          "Horizon plan error:",
          err
        );

        setPlanningError(
          getErrorMessage(
            err,
            "Unable to generate maintenance plan."
          )
        );
      } finally {
        setPlanningLoading(false);
      }
    };

  /* =======================================================
     REVIEW
  ======================================================= */

  const openReview = (
    recommendation
  ) => {
    setSelectedRecommendation(
      recommendation
    );

    setApprovalError("");
    setApprovalSuccess("");
  };

  const closeReview = () => {
    if (approvalLoading) {
      return;
    }

    setSelectedRecommendation(
      null
    );

    setApprovalError("");
    setApprovalSuccess("");
  };

  /* =======================================================
     APPROVE + CREATE BLOCK
  ======================================================= */

  const approveAndCreateBlock =
    async () => {
      if (
        !selectedRecommendation
      ) {
        return;
      }

      const recommendation =
        selectedRecommendation;

      const taskIds =
        getRecommendationTaskIds(
          recommendation
        );

      const startTime =
        toHHMM(
          recommendation.start_time
        );

      const endTime =
        toHHMM(
          recommendation.end_time
        );

      const blockDate =
        dateToKey(
          recommendation.schedule_date ??
            recommendation.date
        );

      if (
        !recommendation.section_id ||
        !blockDate ||
        !startTime ||
        !endTime ||
        taskIds.length === 0
      ) {
        setApprovalError(
          "This recommendation does not contain enough information to create a block."
        );

        return;
      }

      try {
        setApprovalLoading(true);
        setApprovalError("");
        setApprovalSuccess("");

        const params =
          new URLSearchParams();

        params.set(
          "section_id",
          String(
            recommendation.section_id
          )
        );

        params.set(
          "block_date",
          blockDate
        );

        params.set(
          "start_time",
          startTime
        );

        params.set(
          "end_time",
          endTime
        );

        params.set(
          "admin",
          "Abhishek Pal"
        );

        const numericTaskIds =
          taskIds
            .map(
              (id) =>
                Number(id)
            )
            .filter(
              (id) =>
                !Number.isNaN(id)
            );

        const data =
          await apiRequest(
            `${API_BASE}/planner/create-block?${params.toString()}`,
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json",
              },
              body: JSON.stringify(
                numericTaskIds
              ),
            }
          );

        setApprovalSuccess(
          data?.message ||
            "Maintenance block created successfully."
        );

        await loadTimelineData();
      } catch (err) {
        console.error(
          "Approve block error:",
          err
        );

        setApprovalError(
          getErrorMessage(
            err,
            "Unable to create maintenance block."
          )
        );
      } finally {
        setApprovalLoading(false);
      }
    };

  /* =======================================================
     PLAN DATA
  ======================================================= */

  const planDays =
    useMemo(() => {
      return [
        ...getHorizonDays(
          horizonPlan
        ),
      ].sort(
        (a, b) =>
          dateToKey(
            a.schedule_date ??
              a.date
          ).localeCompare(
            dateToKey(
              b.schedule_date ??
                b.date
            )
          )
      );
    }, [
      horizonPlan,
    ]);

  const planSummary =
    horizonPlan?.summary ??
    {};

  const totalTasksConsidered =
    planSummary.total_tasks_considered ??
    planSummary.tasks_considered ??
    horizonPlan?.total_tasks_considered ??
    horizonPlan?.tasks_considered ??
    0;

  const totalTasksPlanned =
    planSummary.tasks_planned ??
    horizonPlan?.tasks_planned ??
    0;

  const totalPlannedBlocks =
    planSummary.total_blocks ??
    horizonPlan?.total_blocks ??
    planDays.reduce(
      (
        total,
        day
      ) =>
        total +
        getDayRecommendations(
          day
        ).length,
      0
    );

  const plannedHours =
    planSummary.total_planned_hours ??
    planSummary.planned_hours ??
    horizonPlan?.total_planned_hours ??
    horizonPlan?.planned_hours ??
    planDays
      .flatMap(
        (day) =>
          getDayRecommendations(
            day
          )
      )
      .reduce(
        (
          total,
          recommendation
        ) =>
          total +
          getDurationHours(
            recommendation.start_time,
            recommendation.end_time
          ),
        0
      );

  const unscheduledTasks =
    planSummary.unscheduled ??
    horizonPlan?.unscheduled ??
    (Array.isArray(
      horizonPlan?.unscheduled_tasks
    )
      ? horizonPlan
          .unscheduled_tasks
          .length
      : 0);

  const forecastAwareDays =
    useMemo(() => {
      return planDays.filter(
        (day) =>
          getDayRecommendations(
            day
          ).some(
            (recommendation) =>
              recommendation
                ?.goods_forecast_considered ===
              true
          )
      );
    }, [
      planDays,
    ]);

  /* =======================================================
     MONTHLY WEEKS
  ======================================================= */

  const monthlyWeeks =
    useMemo(() => {
      if (
        planningMode !==
        "MONTHLY"
      ) {
        return [];
      }

      const weeks = [];

      for (
        let index = 0;
        index < planDays.length;
        index += 7
      ) {
        weeks.push(
          planDays.slice(
            index,
            index + 7
          )
        );
      }

      return weeks;
    }, [
      planDays,
      planningMode,
    ]);

  /* =======================================================
     ACTUAL BLOCKS BY DATE
  ======================================================= */

  const allBlocksForDate =
    useMemo(() => {
      return blocks
        .filter(
          (block) =>
            dateToKey(
              block.block_date ??
                block.schedule_date ??
                block.date
            ) ===
            timelineDate
        )
        .sort(
          (a, b) =>
            parseTime(
              a.start_time ??
                a.start ??
                a.from_time
            ) -
            parseTime(
              b.start_time ??
                b.start ??
                b.from_time
            )
        );
    }, [
      blocks,
      timelineDate,
    ]);

  /*
    FIX:
    Only PLANNED / APPROVED / IN_PROGRESS
    are treated as active.

    COMPLETED is historical, therefore
    it must NOT appear in Active view.
  */
  const activeBlocksForDate =
    useMemo(
      () =>
        allBlocksForDate.filter(
          (block) =>
            isActiveBlock(block)
        ),
      [
        allBlocksForDate,
      ]
    );

  const cancelledBlocksForDate =
    useMemo(
      () =>
        allBlocksForDate.filter(
          (block) =>
            isCancelledBlock(block)
        ),
      [
        allBlocksForDate,
      ]
    );

  const timelineBlocksForDate =
    timelineBlockFilter ===
    "ACTIVE"
      ? activeBlocksForDate
      : timelineBlockFilter ===
        "CANCELLED"
      ? cancelledBlocksForDate
      : allBlocksForDate;

  /* =======================================================
     TRAINS BY DATE
  ======================================================= */

  const trainsForDate =
    useMemo(() => {
      return trainSchedule
        .filter(
          (train) =>
            dateToKey(
              train.schedule_date ??
                train.date ??
                train.run_date
            ) ===
            timelineDate
        )
        .sort(
          (a, b) =>
            parseTime(
              a.arrival_time ??
                a.arrival ??
                a.start_time ??
                a.time
            ) -
            parseTime(
              b.arrival_time ??
                b.arrival ??
                b.start_time ??
                b.time
            )
        );
    }, [
      trainSchedule,
      timelineDate,
    ]);

  /* =======================================================
     TIMELINE
  ======================================================= */

  const timelineStartHour = 8;
  const timelineEndHour = 20;

  const timelineDuration =
    (timelineEndHour -
      timelineStartHour) *
    60;

  const timelineHours =
    useMemo(() => {
      const hours = [];

      for (
        let hour =
          timelineStartHour;
        hour <=
        timelineEndHour;
        hour += 1
      ) {
        hours.push(hour);
      }

      return hours;
    }, []);

  const getTimelinePosition =
    (time) => {
      const minutes =
        parseTime(time);

      const position =
        ((minutes -
          timelineStartHour *
            60) /
          timelineDuration) *
        100;

      return Math.max(
        0,
        Math.min(
          100,
          position
        )
      );
    };

  /* =======================================================
     BLOCK AI DATA
  ======================================================= */

  const getBlockAiData = (
    block
  ) => {
    const taskIds =
      getBlockTaskIds(
        block
      );

    const decisions =
      taskIds
        .map(
          (taskId) =>
            aiDecisionMap[
              String(taskId)
            ]
        )
        .filter(Boolean);

    if (
      decisions.length ===
      0
    ) {
      return null;
    }

    return [
      ...decisions,
    ].sort(
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
     BLOCK TASK LABELS
  ======================================================= */

  const getBlockTaskLabels = (
    block
  ) => {
    return getBlockTaskIds(
      block
    ).map(
      (id) =>
        taskMap[id]
          ?.task_code ??
        `Task ${id}`
    );
  };

  /* =======================================================
     RECOMMENDED BLOCK
  ======================================================= */

  const renderRecommendedBlock = (
    recommendation,
    index
  ) => {
    const taskIds =
      getRecommendationTaskIds(
        recommendation
      );

    const startTime =
      formatTime(
        recommendation.start_time
      );

    const endTime =
      formatTime(
        recommendation.end_time
      );

    const duration =
      recommendation.duration_hours ??
      getDurationHours(
        startTime,
        endTime
      );

    const reason =
      recommendation.reason ||
      recommendation.planning_reason ||
      recommendation.explanation ||
      "AI-generated maintenance recommendation.";

    const goodsAware =
      recommendation
        .goods_forecast_considered ===
      true;

    const goodsCount =
      recommendation
        .expected_goods_trains ??
      0;

    return (
      <div
        className="planned-block"
        key={`${index}-${dateToKey(
          recommendation.schedule_date ??
            recommendation.date
        )}`}
      >
        <div className="planned-time">
          <strong>
            {startTime}
            {" – "}
            {endTime}
          </strong>

          <span>
            {duration}h
          </span>
        </div>

        <div className="planned-details">
          <div className="planned-section">
            Section{" "}
            {
              recommendation.section_id
            }
          </div>

          <div className="planned-task-list">
            {taskIds.map(
              (taskId) => (
                <span
                  className="planned-task-tag"
                  key={
                    taskId
                  }
                >
                  {
                    taskMap[
                      String(
                        taskId
                      )
                    ]
                      ?.task_code ??
                    `Task ${taskId}`
                  }
                </span>
              )
            )}
          </div>

          <p className="planned-block-reason">
            {reason}
          </p>

          <div className="timeline-ai-inline">
            <span>
              🧠 AI Planning
            </span>

            {recommendation
              .ml_risk_percentage !==
              undefined && (
              <strong>
                ML Risk{" "}
                {
                  recommendation
                    .ml_risk_percentage
                }%
              </strong>
            )}

            {recommendation
              .ml_risk_level && (
              <strong>
                {
                  recommendation
                    .ml_risk_level
                }
              </strong>
            )}

            {recommendation
              .planning_score !==
              undefined && (
              <strong>
                Plan Score{" "}
                {
                  recommendation
                    .planning_score
                }
              </strong>
            )}
          </div>

          {goodsAware && (
            <div className="planned-goods-forecast">
              <span className="planned-goods-icon">
                🚆
              </span>

              <div>
                <strong>
                  Goods Forecast
                  Considered
                </strong>

                <span>
                  {goodsCount}{" "}
                  expected goods
                  train
                  {Number(
                    goodsCount
                  ) === 1
                    ? ""
                    : "s"}

                  {recommendation
                    .goods_traffic_level &&
                    ` • ${recommendation.goods_traffic_level}`}
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="planned-actions">
          <span className="planned-recommended-badge">
            ✓ Recommended
          </span>

          <small>
            {taskIds.length}{" "}
            task
            {taskIds.length ===
            1
              ? ""
              : "s"}
          </small>

          <button
            type="button"
            className="timeline-review-button"
            onClick={() =>
              openReview(
                recommendation
              )
            }
          >
            Review
          </button>
        </div>
      </div>
    );
  };

  /* =======================================================
     DAY PLAN
  ======================================================= */

  const renderDayPlan = (
    day,
    index
  ) => {
    const dayDate =
      dateToKey(
        day.schedule_date ??
          day.date
      );

    const recommendations =
      getDayRecommendations(
        day
      );

    const totalDayHours =
      recommendations.reduce(
        (
          total,
          recommendation
        ) =>
          total +
          getDurationHours(
            recommendation.start_time,
            recommendation.end_time
          ),
        0
      );

    const dayTaskCount =
      recommendations.reduce(
        (
          total,
          recommendation
        ) =>
          total +
          getRecommendationTaskIds(
            recommendation
          ).length,
        0
      );

    const hasGoods =
      recommendations.some(
        (recommendation) =>
          recommendation
            ?.goods_forecast_considered ===
          true
      );

    const goodsCount =
      recommendations.reduce(
        (
          total,
          recommendation
        ) =>
          total +
          (Number(
            recommendation
              .expected_goods_trains
          ) || 0),
        0
      );

    return (
      <div
        className={`timeline-day-plan ${
          recommendations.length ===
          0
            ? "empty-day"
            : ""
        }`}
        key={`${dayDate}-${index}`}
      >
        <div className="timeline-day-header">
          <div>
            <strong>
              {
                formatDate(
                  dayDate
                )
              }
            </strong>

            <span>
              {
                recommendations.length
              }{" "}
              blocks •{" "}
              {dayTaskCount} tasks
              •{" "}
              {totalDayHours}h
              planned
            </span>
          </div>

          <div className="timeline-day-header-right">
            {hasGoods && (
              <span className="timeline-goods-badge">
                🚆 Goods{" "}
                {goodsCount}
              </span>
            )}

            <span className="timeline-day-label">
              DAY PLAN
            </span>
          </div>
        </div>

        {recommendations.length >
        0 ? (
          <div className="timeline-day-blocks">
            {recommendations.map(
              (
                recommendation,
                recommendationIndex
              ) =>
                renderRecommendedBlock(
                  recommendation,
                  `${index}-${recommendationIndex}`
                )
            )}
          </div>
        ) : (
          <div className="timeline-empty-day">
            No recommended
            maintenance block for
            this day.
          </div>
        )}
      </div>
    );
  };

  /* =======================================================
     RENDER
  ======================================================= */

  if (loading) {
    return (
      <div className="timeline-page">
        <div className="timeline-loading">
          <div className="timeline-loader" />
          Loading railway
          timeline...
        </div>
      </div>
    );
  }

  return (
    <div className="timeline-page">
      {/* =================================================
          HERO
      ================================================= */}

      <div className="timeline-hero">
        <div>
          <span className="timeline-eyebrow">
            RAILWAY OPERATIONS CONTROL
          </span>

          <h1>
            Maintenance Timeline
          </h1>

          <p>
            Monitor AI-generated
            maintenance plans,
            active blocks, ML risk,
            AI decisions, train
            movements and goods
            traffic constraints.
          </p>
        </div>

        <div className="timeline-live">
          <span className="timeline-live-dot" />
          Live Operations
        </div>
      </div>

      {/* ERROR */}

      {error && (
        <div className="timeline-error">
          ⚠ {error}
        </div>
      )}

      {/* =================================================
          PLANNING HORIZON
      ================================================= */}

      <section className="timeline-planner-card">
        <div className="timeline-planner-header">
          <div>
            <span className="timeline-eyebrow">
              AI MAINTENANCE
              PLANNING
            </span>

            <h2>
              📋 Planning Horizon
            </h2>

            <p>
              Generate weekly or
              monthly maintenance
              plans using maintenance
              priority, asset risk,
              train constraints and
              goods forecast data.
            </p>
          </div>

          <div className="timeline-mode-switch">
            <button
              type="button"
              className={
                planningMode ===
                "WEEKLY"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setPlanningMode(
                  "WEEKLY"
                )
              }
            >
              Weekly
            </button>

            <button
              type="button"
              className={
                planningMode ===
                "MONTHLY"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setPlanningMode(
                  "MONTHLY"
                )
              }
            >
              Monthly
            </button>
          </div>
        </div>

        <div className="timeline-planner-controls">
          <div className="timeline-field">
            <label>
              Start Date
            </label>

            <input
              type="date"
              value={
                planningStartDate
              }
              onChange={(event) =>
                setPlanningStartDate(
                  event.target.value
                )
              }
            />
          </div>

          <div className="timeline-field">
            <label>
              End Date
            </label>

            <input
              type="date"
              value={
                planningEndDate
              }
              onChange={(event) =>
                setPlanningEndDate(
                  event.target.value
                )
              }
            />
          </div>

          <button
            type="button"
            className="timeline-generate-button"
            onClick={
              generateHorizonPlan
            }
            disabled={
              planningLoading
            }
          >
            {planningLoading
              ? "⏳ Generating..."
              : `Generate ${
                  planningMode ===
                  "MONTHLY"
                    ? "Monthly"
                    : "Weekly"
                } Plan`}
          </button>
        </div>

        {planningError && (
          <div className="timeline-planning-error">
            ⚠{" "}
            {planningError}
          </div>
        )}
      </section>

      {/* =================================================
          GENERATED PLAN
      ================================================= */}

      {horizonPlan && (
        <>
          <section className="timeline-planning-summary">
            <div className="timeline-summary-heading">
              <div>
                <span className="timeline-eyebrow">
                  {planningMode ===
                  "MONTHLY"
                    ? "MONTHLY PLAN"
                    : "WEEKLY PLAN"}
                </span>

                <h2>
                  {
                    formatDate(
                      planningStartDate
                    )
                  }
                  {" → "}
                  {
                    formatDate(
                      planningEndDate
                    )
                  }
                </h2>
              </div>

              <span className="timeline-horizon-badge">
                {planningMode ===
                "MONTHLY"
                  ? "30 Days"
                  : "7 Days"}
              </span>
            </div>

            <div className="timeline-stats">
              <div className="timeline-stat-card">
                <span>
                  Tasks
                  Considered
                </span>

                <strong>
                  {
                    totalTasksConsidered
                  }
                </strong>
              </div>

              <div className="timeline-stat-card">
                <span>
                  Tasks
                  Planned
                </span>

                <strong>
                  {
                    totalTasksPlanned
                  }
                </strong>
              </div>

              <div className="timeline-stat-card">
                <span>
                  AI Blocks
                </span>

                <strong>
                  {
                    totalPlannedBlocks
                  }
                </strong>
              </div>

              <div className="timeline-stat-card">
                <span>
                  Planned Hours
                </span>

                <strong>
                  {
                    plannedHours
                  }h
                </strong>
              </div>

              <div className="timeline-stat-card">
                <span>
                  Unscheduled
                </span>

                <strong>
                  {
                    unscheduledTasks
                  }
                </strong>
              </div>

              <div className="timeline-stat-card timeline-forecast-stat">
                <span>
                  Forecast-aware
                  Days
                </span>

                <strong>
                  {
                    forecastAwareDays.length
                  }
                </strong>
              </div>
            </div>
          </section>

          {/* WEEKLY */}

          {planningMode ===
            "WEEKLY" && (
            <section className="timeline-section-card">
              <div className="timeline-section-heading">
                <div>
                  <h2>
                    🗓️ Weekly
                    Maintenance Plan
                  </h2>

                  <p>
                    AI-generated
                    maintenance windows
                    for the selected
                    horizon.
                  </p>
                </div>

                <span className="timeline-count-badge">
                  {
                    totalPlannedBlocks
                  }{" "}
                  Planned Blocks
                </span>
              </div>

              <div className="timeline-day-list">
                {planDays.length >
                0
                  ? planDays.map(
                      (
                        day,
                        index
                      ) =>
                        renderDayPlan(
                          day,
                          index
                        )
                    )
                  : (
                    <div className="timeline-empty">
                      No planning days
                      returned by the
                      AI planner.
                    </div>
                  )}
              </div>
            </section>
          )}

          {/* MONTHLY */}

          {planningMode ===
            "MONTHLY" && (
            <section className="timeline-section-card">
              <div className="timeline-section-heading">
                <div>
                  <h2>
                    🗓️ Monthly
                    Maintenance Plan
                  </h2>

                  <p>
                    AI-generated
                    maintenance plan
                    grouped by
                    operational weeks.
                  </p>
                </div>

                <span className="timeline-count-badge">
                  {
                    totalPlannedBlocks
                  }{" "}
                  Planned Blocks
                </span>
              </div>

              <div className="timeline-month-list">
                {monthlyWeeks.map(
                  (
                    week,
                    weekIndex
                  ) => (
                    <div
                      className="timeline-week-plan"
                      key={
                        `week-${weekIndex}`
                      }
                    >
                      <div className="timeline-week-header">
                        <div>
                          <strong>
                            Week{" "}
                            {
                              weekIndex +
                              1
                            }
                          </strong>

                          <span>
                            {
                              week.length
                            }{" "}
                            planning
                            days
                          </span>
                        </div>
                      </div>

                      <div className="timeline-week-days">
                        {week.map(
                          (
                            day,
                            dayIndex
                          ) => {
                            const dayDate =
                              dateToKey(
                                day.schedule_date ??
                                  day.date
                              );

                            const recommendations =
                              getDayRecommendations(
                                day
                              );

                            return (
                              <div
                                className="timeline-month-day"
                                key={`${dayDate}-${dayIndex}`}
                              >
                                <div className="timeline-month-day-header">
                                  <strong>
                                    {
                                      formatDate(
                                        dayDate
                                      )
                                    }
                                  </strong>

                                  <span>
                                    {
                                      recommendations.length
                                    }{" "}
                                    blocks
                                  </span>
                                </div>

                                <div className="timeline-month-day-content">
                                  {recommendations.length >
                                  0
                                    ? recommendations.map(
                                        (
                                          recommendation,
                                          recommendationIndex
                                        ) =>
                                          renderRecommendedBlock(
                                            recommendation,
                                            `${weekIndex}-${dayIndex}-${recommendationIndex}`
                                          )
                                      )
                                    : (
                                      <div className="timeline-month-empty">
                                        No maintenance
                                        block
                                        planned.
                                      </div>
                                    )}
                                </div>
                              </div>
                            );
                          }
                        )}
                      </div>
                    </div>
                  )
                )}
              </div>
            </section>
          )}

          {/* UNSCHEDULED */}

          {Array.isArray(
            horizonPlan.unscheduled_tasks
          ) &&
            horizonPlan
              .unscheduled_tasks
              .length >
              0 && (
              <section className="timeline-unscheduled">
                <div className="timeline-section-heading">
                  <div>
                    <h2>
                      ⚠ Unscheduled
                      Tasks
                    </h2>

                    <p>
                      Tasks that could
                      not be safely
                      placed inside the
                      selected horizon.
                    </p>
                  </div>
                </div>

                <div className="timeline-unscheduled-list">
                  {horizonPlan.unscheduled_tasks.map(
                    (
                      task,
                      index
                    ) => (
                      <div
                        className="timeline-unscheduled-item"
                        key={
                          task?.task_id ??
                          index
                        }
                      >
                        <strong>
                          {
                            task?.task_code ??
                            task?.code ??
                            `Task ${
                              task?.task_id ??
                              index + 1
                            }`
                          }
                        </strong>

                        <span>
                          {
                            task?.reason ??
                            "No feasible window found."
                          }
                        </span>
                      </div>
                    )
                  )}
                </div>
              </section>
            )}
        </>
      )}

      {/* =================================================
          ACTUAL OPERATIONS
      ================================================= */}

      <section className="timeline-existing-section">
        <div className="timeline-section-heading">
          <div>
            <span className="timeline-eyebrow">
              ACTUAL OPERATIONS
            </span>

            <h2>
              Existing Blocks &
              Train Movements
            </h2>

            <p>
              Compare maintenance
              blocks, ML risk and AI
              decisions against
              scheduled train
              movements.
            </p>
          </div>
        </div>

        {/* CONTROLS */}

        <div className="timeline-control-row">
          <div className="timeline-field timeline-date-field">
            <label>
              Timeline Date
            </label>

            <input
              type="date"
              value={
                timelineDate
              }
              onChange={(event) =>
                setTimelineDate(
                  event.target.value
                )
              }
            />
          </div>

          <div className="timeline-view-filter">
            <span>
              Block View
            </span>

            <button
              type="button"
              className={
                timelineBlockFilter ===
                "ACTIVE"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setTimelineBlockFilter(
                  "ACTIVE"
                )
              }
            >
              Active
            </button>

            <button
              type="button"
              className={
                timelineBlockFilter ===
                "ALL"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setTimelineBlockFilter(
                  "ALL"
                )
              }
            >
              All
            </button>

            <button
              type="button"
              className={
                timelineBlockFilter ===
                "CANCELLED"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setTimelineBlockFilter(
                  "CANCELLED"
                )
              }
            >
              Cancelled
            </button>
          </div>
        </div>

        {/* SUMMARY */}

        <div className="timeline-existing-summary">
          <div>
            <span>
              Active Blocks
            </span>

            <strong>
              {
                activeBlocksForDate.length
              }
            </strong>
          </div>

          <div>
            <span>
              All Blocks
            </span>

            <strong>
              {
                allBlocksForDate.length
              }
            </strong>
          </div>

          <div>
            <span>
              Cancelled
            </span>

            <strong>
              {
                cancelledBlocksForDate.length
              }
            </strong>
          </div>

          <div>
            <span>
              Train Movements
            </span>

            <strong>
              {
                trainsForDate.length
              }
            </strong>
          </div>
        </div>

        {/* LEGEND */}

        <div className="timeline-legend">
          <div>
            <span className="legend-dot maintenance" />
            Maintenance
          </div>

          <div>
            <span className="legend-dot train" />
            Train
          </div>

          <div>
            <span className="legend-dot cancelled" />
            Cancelled
          </div>

          <div>
            <span className="legend-ai">
              ML
            </span>
            ML Risk
          </div>

          <div>
            <span className="legend-ai">
              AI
            </span>
            AI Score
          </div>
        </div>

        {/* TIMELINE */}

        <div className="timeline-scroll">
          <div className="timeline-ruler">
            <div className="timeline-ruler-label">
              Operations
            </div>

            <div className="timeline-ruler-hours">
              {timelineHours.map(
                (hour) => (
                  <span
                    key={hour}
                  >
                    {String(
                      hour
                    ).padStart(
                      2,
                      "0"
                    )}
                    :00
                  </span>
                )
              )}
            </div>
          </div>

          <div className="timeline-track-area">
            {/* =================================================
                MAINTENANCE BLOCKS
            ================================================= */}

            {timelineBlocksForDate.map(
              (
                block,
                index
              ) => {
                const startTime =
                  block.start_time ??
                  block.start ??
                  block.from_time;

                const endTime =
                  block.end_time ??
                  block.end ??
                  block.to_time;

                const left =
                  getTimelinePosition(
                    startTime
                  );

                const right =
                  getTimelinePosition(
                    endTime
                  );

                const width =
                  Math.max(
                    1.5,
                    right - left
                  );

                const cancelled =
                  isCancelledBlock(
                    block
                  );

                const taskLabels =
                  getBlockTaskLabels(
                    block
                  );

                const aiData =
                  getBlockAiData(
                    block
                  );

                return (
                  <div
                    className={`timeline-operation-row ${
                      cancelled
                        ? "timeline-row-cancelled"
                        : ""
                    }`}
                    key={
                      block.block_id ??
                      index
                    }
                  >
                    <div className="timeline-operation-label">
                      <strong>
                        Section{" "}
                        {
                          block.section_id
                        }
                      </strong>

                      <span>
                        {
                          block.block_code
                        }
                      </span>
                    </div>

                    <div className="timeline-track">
                      <div
                        className={`timeline-block ${
                          cancelled
                            ? "timeline-block-cancelled"
                            : "timeline-block-active"
                        }`}
                        style={{
                          left: `${left}%`,
                          width: `${width}%`,
                        }}
                      >
                        <div className="timeline-block-top">
                          <strong>
                            {
                              block.block_code
                            }
                          </strong>

                          <span className="timeline-status-pill">
                            {
                              normalizeStatus(
                                block.status
                              )
                            }
                          </span>
                        </div>

                        <div className="timeline-block-time">
                          {
                            formatTime(
                              startTime
                            )
                          }
                          {" – "}
                          {
                            formatTime(
                              endTime
                            )
                          }
                        </div>

                        <div className="timeline-block-tasks">
                          {taskLabels
                            .slice(
                              0,
                              3
                            )
                            .map(
                              (
                                taskCode
                              ) => (
                                <span
                                  key={
                                    taskCode
                                  }
                                >
                                  {
                                    taskCode
                                  }
                                </span>
                              )
                            )}

                          {taskLabels.length >
                            3 && (
                            <span>
                              +
                              {
                                taskLabels.length -
                                3
                              }
                            </span>
                          )}
                        </div>

                        {!cancelled &&
                          aiData && (
                            <div className="timeline-block-ai">
                              <div className="timeline-ai-chip">
                                <span>
                                  ML
                                </span>

                                <strong>
                                  {
                                    aiData.ml_risk_percentage ??
                                    "—"
                                  }%
                                </strong>
                              </div>

                              <div className="timeline-ai-chip">
                                <span>
                                  AI
                                </span>

                                <strong>
                                  {
                                    aiData.ai_decision_score ??
                                    "—"
                                  }
                                </strong>
                              </div>

                              {aiData
                                .ml_risk_level && (
                                <div
                                  className={`timeline-risk-chip ${String(
                                    aiData.ml_risk_level
                                  ).toLowerCase()}`}
                                >
                                  {
                                    aiData.ml_risk_level
                                  }
                                </div>
                              )}
                            </div>
                          )}
                      </div>
                    </div>
                  </div>
                );
              }
            )}

            {/* =================================================
                TRAINS
            ================================================= */}

            {trainsForDate.map(
              (
                train,
                index
              ) => {
                const start =
                  train.arrival_time ??
                  train.arrival ??
                  train.start_time ??
                  train.time;

                const end =
                  train.departure_time ??
                  train.departure ??
                  train.end_time ??
                  start;

                const left =
                  getTimelinePosition(
                    start
                  );

                const right =
                  Math.max(
                    left + 0.8,
                    getTimelinePosition(
                      end
                    )
                  );

                const width =
                  Math.max(
                    0.8,
                    right - left
                  );

                return (
                  <div
                    className="timeline-operation-row timeline-train-operation"
                    key={
                      train.schedule_id ??
                      train.id ??
                      `train-${index}`
                    }
                  >
                    <div className="timeline-operation-label">
                      <strong>
                        Train{" "}
                        {
                          train.train_id ??
                          train.id
                        }
                      </strong>

                      <span>
                        Section{" "}
                        {
                          train.section_id
                        }
                      </span>
                    </div>

                    <div className="timeline-track">
                      <div
                        className="timeline-train"
                        style={{
                          left: `${left}%`,
                          width: `${width}%`,
                        }}
                      >
                        <strong>
                          🚆{" "}
                          {
                            train.train_no ??
                            train.train_number ??
                            train.train_name ??
                            `Train ${
                              train.train_id ??
                              train.id
                            }`
                          }
                        </strong>

                        <span>
                          {
                            formatTime(
                              start
                            )
                          }
                          {" – "}
                          {
                            formatTime(
                              end
                            )
                          }
                        </span>
                      </div>
                    </div>
                  </div>
                );
              }
            )}

            {timelineBlocksForDate
              .length ===
              0 &&
              trainsForDate
                .length ===
                0 && (
                <div className="timeline-empty">
                  No blocks or train
                  movements
                  available for
                  this date.
                </div>
              )}
          </div>
        </div>
      </section>

      {/* =================================================
          REVIEW MODAL
      ================================================= */}

      {selectedRecommendation && (
        <div
          className="timeline-modal-overlay"
          onClick={
            closeReview
          }
        >
          <div
            className="timeline-review-modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >
            <div className="timeline-modal-header">
              <div>
                <span className="timeline-modal-eyebrow">
                  BLOCK REVIEW
                </span>

                <h2>
                  🛠️ Maintenance
                  Block
                  Recommendation
                </h2>
              </div>

              <button
                type="button"
                className="timeline-modal-close"
                onClick={
                  closeReview
                }
                disabled={
                  approvalLoading
                }
              >
                ×
              </button>
            </div>

            <div className="timeline-modal-body">
              <div className="timeline-review-grid">
                <div className="timeline-review-item">
                  <span>
                    Date
                  </span>

                  <strong>
                    {
                      formatDate(
                        selectedRecommendation.schedule_date ??
                          selectedRecommendation.date
                      )
                    }
                  </strong>
                </div>

                <div className="timeline-review-item">
                  <span>
                    Section
                  </span>

                  <strong>
                    Section{" "}
                    {
                      selectedRecommendation.section_id
                    }
                  </strong>
                </div>

                <div className="timeline-review-item">
                  <span>
                    Recommended
                    Window
                  </span>

                  <strong className="timeline-review-time">
                    {
                      formatTime(
                        selectedRecommendation.start_time
                      )
                    }
                    {" – "}
                    {
                      formatTime(
                        selectedRecommendation.end_time
                      )
                    }
                  </strong>
                </div>

                <div className="timeline-review-item">
                  <span>
                    Duration
                  </span>

                  <strong>
                    {
                      selectedRecommendation.duration_hours ??
                      getDurationHours(
                        selectedRecommendation.start_time,
                        selectedRecommendation.end_time
                      )
                    }
                    h
                  </strong>
                </div>

                {selectedRecommendation
                  .ml_risk_percentage !==
                  undefined && (
                  <div className="timeline-review-item">
                    <span>
                      ML Risk
                    </span>

                    <strong>
                      {
                        selectedRecommendation
                          .ml_risk_percentage
                      }%
                    </strong>
                  </div>
                )}

                {selectedRecommendation
                  .planning_score !==
                  undefined && (
                  <div className="timeline-review-item">
                    <span>
                      Planning Score
                    </span>

                    <strong>
                      {
                        selectedRecommendation
                          .planning_score
                      }
                    </strong>
                  </div>
                )}
              </div>

              <div className="timeline-review-section">
                <h3>
                  Maintenance
                  Tasks
                </h3>

                <div className="timeline-review-task-list">
                  {getRecommendationTaskIds(
                    selectedRecommendation
                  ).map(
                    (taskId) => (
                      <span
                        className="planned-task-tag"
                        key={
                          taskId
                        }
                      >
                        {
                          taskMap[
                            String(
                              taskId
                            )
                          ]
                            ?.task_code ??
                          `Task ${taskId}`
                        }
                      </span>
                    )
                  )}
                </div>
              </div>

              <div className="timeline-review-reason">
                <strong>
                  Planning Reason
                </strong>

                <p>
                  {
                    selectedRecommendation.reason ||
                    selectedRecommendation.planning_reason ||
                    selectedRecommendation.explanation ||
                    "AI-generated maintenance recommendation based on current operational constraints."
                  }
                </p>
              </div>

              {selectedRecommendation
                .goods_forecast_considered ===
                true && (
                <div className="timeline-review-forecast">
                  🚆 Goods forecast was
                  considered during
                  this
                  recommendation.

                  <strong>
                    {
                      selectedRecommendation
                        .expected_goods_trains ??
                      0
                    }{" "}
                    expected goods
                    train
                    {
                      Number(
                        selectedRecommendation
                          .expected_goods_trains ??
                          0
                      ) === 1
                        ? ""
                        : "s"
                    }
                  </strong>
                </div>
              )}

              <div className="timeline-review-warning">
                ⚠ Approving this
                recommendation
                will create an
                actual planned
                maintenance block
                in the database.
              </div>

              {approvalError && (
                <div className="timeline-review-error">
                  ⚠{" "}
                  {
                    approvalError
                  }
                </div>
              )}

              {approvalSuccess && (
                <div className="timeline-review-success">
                  ✓{" "}
                  {
                    approvalSuccess
                  }
                </div>
              )}
            </div>

            <div className="timeline-modal-footer">
              <button
                type="button"
                className="timeline-modal-cancel"
                onClick={
                  closeReview
                }
                disabled={
                  approvalLoading
                }
              >
                Close
              </button>

              {approvalSuccess ? (
                <button
                  type="button"
                  className="timeline-modal-approve"
                  disabled
                >
                  ✓ Block
                  Created
                </button>
              ) : (
                <button
                  type="button"
                  className="timeline-modal-approve"
                  onClick={
                    approveAndCreateBlock
                  }
                  disabled={
                    approvalLoading
                  }
                >
                  {approvalLoading
                    ? "⏳ Creating..."
                    : "✓ Approve & Create Block"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Timeline;

