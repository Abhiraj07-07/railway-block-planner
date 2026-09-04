import {
  useEffect,
  useMemo,
  useState,
} from "react";

import "./Events.css";

const API_BASE =
  import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const TOKEN_KEY = "railway_admin_token";

/* =========================================================
   LOCAL AUTH FETCH
========================================================= */

const authFetch = (
  url,
  options = {}
) => {
  const token =
    localStorage.getItem(
      TOKEN_KEY
    );

  return fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Accept: "application/json",
      ...(token
        ? {
            Authorization:
              `Bearer ${token}`,
          }
        : {}),
    },
  });
};

/* =========================================================
   HELPERS
========================================================= */

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

const parseApiResponse = async (
  response
) => {
  const contentType =
    response.headers.get(
      "content-type"
    ) || "";

  if (
    contentType.includes(
      "application/json"
    )
  ) {
    return response.json();
  }

  const text =
    await response.text();

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
};

const formatDate = (
  value
) => {
  if (!value) {
    return "";
  }

  const direct = String(
    value
  ).match(
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

const todayKey = () => {
  const now = new Date();

  return `${now.getFullYear()}-${String(
    now.getMonth() + 1
  ).padStart(
    2,
    "0"
  )}-${String(
    now.getDate()
  ).padStart(
    2,
    "0"
  )}`;
};

/* =========================================================
   COMPONENT
========================================================= */

function Events() {

  /* =======================================================
     EVENTS
  ======================================================= */

  const [
    events,
    setEvents,
  ] = useState([]);

  /* =======================================================
     REPLAN RESULTS
  ======================================================= */

  const [
    replanResults,
    setReplanResults,
  ] = useState({});

  /* =======================================================
     UI STATE
  ======================================================= */

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    actionLoading,
    setActionLoading,
  ] = useState(null);

  const [
    error,
    setError,
  ] = useState("");

  const [
    message,
    setMessage,
  ] = useState("");

  /* =======================================================
     CREATE EVENT
  ======================================================= */

  const [
    showCreateForm,
    setShowCreateForm,
  ] = useState(false);

  const [
    createLoading,
    setCreateLoading,
  ] = useState(false);

  const [
    createError,
    setCreateError,
  ] = useState("");

  const [
    eventForm,
    setEventForm,
  ] = useState({
    event_type:
      "TRAIN_DELAY",

    severity:
      "HIGH",

    section_id:
      "1",

    train_id:
      "3",

    asset_id:
      "",

    delay_minutes:
      "40",

    event_date:
      todayKey(),

    description:
      "Operational train delay detected on Section 1.",
  });

  /* =======================================================
     LOAD EVENTS
  ======================================================= */

  const loadEvents = async () => {
    try {
      setLoading(true);
      setError("");

      const response =
        await authFetch(
          `${API_BASE}/events`,
          {
            method: "GET",
          }
        );

      const data =
        await parseApiResponse(
          response
        );

      if (!response.ok) {
        throw new Error(
          getErrorMessage(
            data,
            `Unable to load events. Status ${response.status}`
          )
        );
      }

      let loadedEvents = [];

      if (
        Array.isArray(data)
      ) {
        loadedEvents = data;
      } else if (
        Array.isArray(
          data?.events
        )
      ) {
        loadedEvents =
          data.events;
      } else if (
        Array.isArray(
          data?.data
        )
      ) {
        loadedEvents =
          data.data;
      }

      setEvents(
        loadedEvents
      );

    } catch (err) {
      console.error(
        "Events page error:",
        err
      );

      setEvents([]);

      setError(
        getErrorMessage(
          err,
          "Unable to load operational events."
        )
      );

    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  /* =======================================================
     CREATE EVENT
  ======================================================= */

  const handleCreateEvent =
    async (event) => {
      event.preventDefault();

      try {
        setCreateLoading(true);
        setCreateError("");
        setError("");
        setMessage("");

        const params =
          new URLSearchParams();

        params.append(
          "event_type",
          String(
            eventForm.event_type
          )
        );

        params.append(
          "event_date",
          String(
            eventForm.event_date
          )
        );

        params.append(
          "section_id",
          String(
            eventForm.section_id
          )
        );

        params.append(
          "severity",
          String(
            eventForm.severity
          )
        );

        if (
          eventForm.asset_id !==
            undefined &&
          eventForm.asset_id !==
            null &&
          String(
            eventForm.asset_id
          ).trim() !== ""
        ) {
          params.append(
            "asset_id",
            String(
              eventForm.asset_id
            ).trim()
          );
        }

        if (
          eventForm.train_id !==
            undefined &&
          eventForm.train_id !==
            null &&
          String(
            eventForm.train_id
          ).trim() !== ""
        ) {
          params.append(
            "train_id",
            String(
              eventForm.train_id
            ).trim()
          );
        }

        if (
          eventForm.delay_minutes !==
            undefined &&
          eventForm.delay_minutes !==
            null &&
          String(
            eventForm.delay_minutes
          ).trim() !== ""
        ) {
          params.append(
            "delay_minutes",
            String(
              eventForm.delay_minutes
            ).trim()
          );
        }

        if (
          eventForm.description &&
          eventForm.description
            .trim() !== ""
        ) {
          params.append(
            "description",
            eventForm.description
              .trim()
          );
        }

        const response =
          await authFetch(
            `${API_BASE}/events?${params.toString()}`,
            {
              method: "POST",
            }
          );

        const data =
          await parseApiResponse(
            response
          );

        if (!response.ok) {
          throw new Error(
            getErrorMessage(
              data,
              `Event creation failed with status ${response.status}`
            )
          );
        }

        setMessage(
          data?.message ||
            "✅ Operational event created successfully."
        );

        setShowCreateForm(
          false
        );

        setReplanResults(
          {}
        );

        setEventForm({
          event_type:
            "TRAIN_DELAY",

          severity:
            "HIGH",

          section_id:
            eventForm.section_id ||
            "1",

          train_id:
            eventForm.train_id ||
            "3",

          asset_id:
            "",

          delay_minutes:
            eventForm.delay_minutes ||
            "40",

          event_date:
            eventForm.event_date,

          description:
            "Operational train delay detected on Section 1.",
        });

        await loadEvents();

      } catch (err) {
        console.error(
          "Create event error:",
          err
        );

        setCreateError(
          getErrorMessage(
            err,
            "Unable to create operational event."
          )
        );

      } finally {
        setCreateLoading(false);
      }
    };

  /* =======================================================
     UPDATE FORM
  ======================================================= */

  const updateEventForm = (
    field,
    value
  ) => {
    setEventForm(
      (previous) => ({
        ...previous,
        [field]: value,
      })
    );
  };

  /* =======================================================
     AI REPLAN
  ======================================================= */

  const handleReplan = async (
    eventId
  ) => {
    try {
      setActionLoading(
        `replan-${eventId}`
      );

      setMessage("");
      setError("");

      const response =
        await authFetch(
          `${API_BASE}/events/${eventId}/replan`,
          {
            method: "POST",
          }
        );

      const data =
        await parseApiResponse(
          response
        );

      if (!response.ok) {
        throw new Error(
          getErrorMessage(
            data,
            `Re-plan failed with status ${response.status}`
          )
        );
      }

      const result =
        data?.replanning_result ??
        null;

      setReplanResults(
        (previous) => ({
          ...previous,
          [eventId]:
            result,
        })
      );

      setMessage(
        `✅ AI re-planning completed for Event #${eventId}.`
      );

    } catch (err) {
      console.error(
        "AI re-plan error:",
        err
      );

      setError(
        getErrorMessage(
          err,
          "Unable to run AI re-planning."
        )
      );

    } finally {
      setActionLoading(null);
    }
  };

  /* =======================================================
     APPLY WHOLE-BLOCK REPLAN
  ======================================================= */

  const handleApplyReplan =
    async (
      eventId
    ) => {
      try {
        setActionLoading(
          `apply-${eventId}`
        );

        setMessage("");
        setError("");

        const response =
          await authFetch(
            `${API_BASE}/events/${eventId}/apply-replan`,
            {
              method: "POST",
            }
          );

        const data =
          await parseApiResponse(
            response
          );

        if (!response.ok) {
          throw new Error(
            getErrorMessage(
              data,
              `Apply re-plan failed with status ${response.status}`
            )
          );
        }

        const appliedBlocks =
          Array.isArray(
            data?.applied_blocks
          )
            ? data.applied_blocks
            : [];

        const manualReviewBlocks =
          Array.isArray(
            data?.manual_review_blocks
          )
            ? data.manual_review_blocks
            : [];

        const taskLevelReplan =
          Array.isArray(
            data?.task_level_replan
          )
            ? data.task_level_replan
            : [];

        /*
          Important:
          We keep the result visible when the
          whole-block re-plan cannot be applied,
          because that is exactly when task-level
          re-planning should be offered.
        */

        if (
          appliedBlocks.length >
          0
        ) {
          setMessage(
            `✅ Whole-block re-planning applied to ${appliedBlocks.length} block(s).`
          );

          setReplanResults(
            (previous) => {
              const next = {
                ...previous,
              };

              delete next[eventId];

              return next;
            }
          );
        } else if (
          taskLevelReplan.length >
          0
        ) {
          setMessage(
            "⚠️ Whole-block re-planning was not possible. AI task-level safe windows are available below."
          );

          /*
            Keep detailed result so the user can
            directly apply task-level re-planning.
          */
          setReplanResults(
            (previous) => ({
              ...previous,
              [eventId]: {
                affected_blocks:
                  manualReviewBlocks,
                replanned_tasks:
                  taskLevelReplan,
                replanning_required:
                  true,
                event_action:
                  data?.event_action ||
                  "MANUAL_REVIEW",
              },
            })
          );
        } else {
          setMessage(
            "ℹ️ No safe block-level timing change could be applied."
          );
        }

        await loadEvents();

      } catch (err) {
        console.error(
          "Apply re-plan error:",
          err
        );

        setError(
          getErrorMessage(
            err,
            "Unable to apply re-planning."
          )
        );

      } finally {
        setActionLoading(null);
      }
    };

  /* =======================================================
     APPLY TASK-LEVEL REPLAN
  ======================================================= */

  const handleApplyTaskReplan =
    async (
      eventId
    ) => {
      try {
        setActionLoading(
          `apply-task-${eventId}`
        );

        setMessage("");
        setError("");

        const response =
          await authFetch(
            `${API_BASE}/events/${eventId}/apply-task-replan`,
            {
              method: "POST",
            }
          );

        const data =
          await parseApiResponse(
            response
          );

        if (!response.ok) {
          throw new Error(
            getErrorMessage(
              data,
              `Task-level re-plan failed with status ${response.status}`
            )
          );
        }

        const createdBlocks =
          Array.isArray(
            data?.created_blocks
          )
            ? data.created_blocks
            : [];

        const cancelledBlocks =
          Array.isArray(
            data?.cancelled_blocks
          )
            ? data.cancelled_blocks
            : [];

        const manualReviewTasks =
          Array.isArray(
            data?.manual_review_tasks
          )
            ? data.manual_review_tasks
            : [];

        if (
          data?.event_status ===
            "RESOLVED" &&
          createdBlocks.length > 0
        ) {
          setMessage(
            `✅ AI task-level re-planning applied successfully. ${cancelledBlocks.length} old block(s) cancelled and ${createdBlocks.length} new safe block(s) created.`
          );
        } else if (
          manualReviewTasks.length >
          0
        ) {
          setMessage(
            "⚠️ Task-level re-planning needs manual review."
          );
        } else {
          setMessage(
            data?.message ||
              "Task-level re-planning completed."
          );
        }

        /*
          Remove old result after apply.
          Events list will reload with latest
          event status.
        */
        setReplanResults(
          (previous) => {
            const next = {
              ...previous,
            };

            delete next[eventId];

            return next;
          }
        );

        await loadEvents();

      } catch (err) {
        console.error(
          "Apply task-level re-plan error:",
          err
        );

        setError(
          getErrorMessage(
            err,
            "Unable to apply task-level re-planning."
          )
        );

      } finally {
        setActionLoading(null);
      }
    };

  /* =======================================================
     SUMMARY
  ======================================================= */

  const openEvents =
    useMemo(
      () =>
        events.filter(
          (event) =>
            event.status ===
            "OPEN"
        ),
      [events]
    );

  const criticalEvents =
    useMemo(
      () =>
        openEvents.filter(
          (event) =>
            event.severity ===
            "CRITICAL"
        ),
      [openEvents]
    );

  const trainDelayEvents =
    useMemo(
      () =>
        events.filter(
          (event) =>
            event.event_type ===
            "TRAIN_DELAY"
        ),
      [events]
    );

  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="events-page">

      {/* =====================================================
          HERO
      ===================================================== */}

      <section className="events-hero">

        <div>

          <span className="events-eyebrow">
            REAL-TIME OPERATIONS
          </span>

          <h1>
            ⚠️ Dynamic Re-Planning
          </h1>

          <p>
            Detect operational
            disruptions, analyze their
            impact, and automatically
            re-plan maintenance blocks.
          </p>

        </div>

        <div className="events-live">

          <span className="status-dot"></span>

          LIVE MONITORING

        </div>

      </section>

      {/* =====================================================
          GLOBAL ERROR
      ===================================================== */}

      {error && (
        <div className="global-error">

          <strong>
            Events Error:
          </strong>{" "}

          {error}

        </div>
      )}

      {/* =====================================================
          SUCCESS MESSAGE
      ===================================================== */}

      {message && (
        <div className="events-message">
          {message}
        </div>
      )}

      {/* =====================================================
          SUMMARY
      ===================================================== */}

      <section className="events-summary">

        <div className="events-summary-card">

          <span>
            🚨 Open Events
          </span>

          <strong>
            {loading
              ? "..."
              : openEvents.length}
          </strong>

        </div>

        <div className="events-summary-card">

          <span>
            🔴 Critical Events
          </span>

          <strong>
            {loading
              ? "..."
              : criticalEvents.length}
          </strong>

        </div>

        <div className="events-summary-card">

          <span>
            🚆 Train Delays
          </span>

          <strong>
            {loading
              ? "..."
              : trainDelayEvents.length}
          </strong>

        </div>

        <div className="events-summary-card">

          <span>
            📊 Total Events
          </span>

          <strong>
            {loading
              ? "..."
              : events.length}
          </strong>

        </div>

      </section>

      {/* =====================================================
          CREATE EVENT
      ===================================================== */}

      <section className="events-card">

        <div className="events-card-header">

          <div>

            <h2>
              ➕ Create Operational Event
            </h2>

            <p>
              Simulate a new train delay
              or infrastructure defect to
              trigger dynamic re-planning.
            </p>

          </div>

          <button
            type="button"
            className="event-action-button"
            onClick={() => {

              setShowCreateForm(
                (previous) =>
                  !previous
              );

              setCreateError("");

              setError("");
            }}
          >
            {showCreateForm
              ? "✕ Close"
              : "＋ New Event"}
          </button>

        </div>

        {/* =================================================
            CREATE FORM
        ================================================= */}

        {showCreateForm && (

          <form
            className="event-create-form"
            onSubmit={
              handleCreateEvent
            }
          >

            <div className="event-form-grid">

              {/* EVENT TYPE */}

              <div className="event-form-field">

                <label>
                  Event Type
                </label>

                <select
                  value={
                    eventForm.event_type
                  }
                  onChange={(e) =>
                    updateEventForm(
                      "event_type",
                      e.target.value
                    )
                  }
                >

                  <option value="TRAIN_DELAY">
                    Train Delay
                  </option>

                  <option value="DEFECT">
                    Defect
                  </option>

                  <option value="BLOCK_CHANGE">
                    Block Change
                  </option>

                </select>

              </div>

              {/* SEVERITY */}

              <div className="event-form-field">

                <label>
                  Severity
                </label>

                <select
                  value={
                    eventForm.severity
                  }
                  onChange={(e) =>
                    updateEventForm(
                      "severity",
                      e.target.value
                    )
                  }
                >

                  <option value="LOW">
                    Low
                  </option>

                  <option value="MEDIUM">
                    Medium
                  </option>

                  <option value="HIGH">
                    High
                  </option>

                  <option value="CRITICAL">
                    Critical
                  </option>

                </select>

              </div>

              {/* SECTION */}

              <div className="event-form-field">

                <label>
                  Section ID
                </label>

                <input
                  type="number"
                  min="1"
                  value={
                    eventForm.section_id
                  }
                  onChange={(e) =>
                    updateEventForm(
                      "section_id",
                      e.target.value
                    )
                  }
                  required
                />

              </div>

              {/* TRAIN */}

              <div className="event-form-field">

                <label>
                  Train ID
                </label>

                <input
                  type="number"
                  min="1"
                  value={
                    eventForm.train_id
                  }
                  onChange={(e) =>
                    updateEventForm(
                      "train_id",
                      e.target.value
                    )
                  }
                />

              </div>

              {/* ASSET */}

              <div className="event-form-field">

                <label>
                  Asset ID
                </label>

                <input
                  type="number"
                  min="1"
                  value={
                    eventForm.asset_id
                  }
                  onChange={(e) =>
                    updateEventForm(
                      "asset_id",
                      e.target.value
                    )
                  }
                />

              </div>

              {/* DELAY */}

              <div className="event-form-field">

                <label>
                  Delay Minutes
                </label>

                <input
                  type="number"
                  min="0"
                  value={
                    eventForm.delay_minutes
                  }
                  onChange={(e) =>
                    updateEventForm(
                      "delay_minutes",
                      e.target.value
                    )
                  }
                />

              </div>

              {/* DATE */}

              <div className="event-form-field">

                <label>
                  Event Date
                </label>

                <input
                  type="date"
                  value={
                    eventForm.event_date
                  }
                  onChange={(e) =>
                    updateEventForm(
                      "event_date",
                      e.target.value
                    )
                  }
                  required
                />

              </div>

            </div>

            {/* DESCRIPTION */}

            <div className="event-form-field">

              <label>
                Description
              </label>

              <textarea
                rows="3"
                value={
                  eventForm.description
                }
                onChange={(e) =>
                  updateEventForm(
                    "description",
                    e.target.value
                  )
                }
              />

            </div>

            {createError && (

              <div className="global-error">

                <strong>
                  Create Event Error:
                </strong>{" "}

                {createError}

              </div>

            )}

            <div className="event-create-footer">

              <button
                type="submit"
                className="event-action-button"
                disabled={
                  createLoading
                }
              >

                {createLoading
                  ? "⏳ Creating..."
                  : "✅ Create Event"}

              </button>

            </div>

          </form>

        )}

      </section>

      {/* =====================================================
          EVENTS LIST
      ===================================================== */}

      <section className="events-card">

        <div className="events-card-header">

          <div>

            <h2>
              🚨 Operational Events
            </h2>

            <p>
              Events that may affect
              maintenance schedules and
              train operations.
            </p>

          </div>

          <span className="events-count">
            {events.length} Events
          </span>

        </div>

        {loading ? (

          <div className="events-loading">

            <div className="loader"></div>

            Loading operational events...

          </div>

        ) : events.length ===
          0 ? (

          <div className="events-empty">
            ✅ No operational events found.
          </div>

        ) : (

          <div className="event-list">

            {events.map(
              (event) => {

                const replanResult =
                  replanResults[
                    event.event_id
                  ];

                const isOpen =
                  event.status ===
                  "OPEN";

                const isReplanLoading =
                  actionLoading ===
                  `replan-${event.event_id}`;

                const isApplyLoading =
                  actionLoading ===
                  `apply-${event.event_id}`;

                const isTaskApplyLoading =
                  actionLoading ===
                  `apply-task-${event.event_id}`;

                const taskLevelPlans =
                  Array.isArray(
                    replanResult?.replanned_tasks
                  )
                    ? replanResult.replanned_tasks
                    : [];

                const hasTaskLevelPlan =
                  taskLevelPlans.length >
                  0;

                const hasAffectedBlocks =
                  Array.isArray(
                    replanResult?.affected_blocks
                  ) &&
                  replanResult
                    .affected_blocks
                    .length > 0;

                return (
                  <div
                    className={`event-card event-${(
                      event.severity ||
                      "MEDIUM"
                    ).toLowerCase()}`}
                    key={
                      event.event_id
                    }
                  >

                    {/* EVENT HEADER */}

                    <div className="event-header">

                      <div>

                        <span className="event-type-badge">

                          {event.event_type ===
                          "TRAIN_DELAY"
                            ? "🚆 TRAIN DELAY"
                            : event.event_type ===
                              "DEFECT"
                            ? "🔧 DEFECT"
                            : "⚠️ BLOCK CHANGE"}

                        </span>

                        <h3>
                          Event #
                          {
                            event.event_id
                          }
                        </h3>

                        <p>
                          Section{" "}
                          {
                            event.section_id
                          }
                        </p>

                      </div>

                      <div className="event-status-group">

                        <span
                          className={`badge ${(
                            event.severity ||
                            "MEDIUM"
                          ).toLowerCase()}`}
                        >
                          {
                            event.severity ||
                            "MEDIUM"
                          }
                        </span>

                        <span
                          className={`badge ${
                            event.status ===
                            "RESOLVED"
                              ? "status-resolved"
                              : "status-pending"
                          }`}
                        >
                          {
                            event.status
                          }
                        </span>

                      </div>

                    </div>

                    {/* EVENT DETAILS */}

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
                              {
                                event.train_id
                              }
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
                              Asset
                            </span>

                            <strong>
                              {
                                event.asset_id
                              }
                            </strong>

                          </div>

                        )}

                      <div>

                        <span>
                          Event Date
                        </span>

                        <strong>
                          {formatDate(
                            event.event_date
                          )}
                        </strong>

                      </div>

                    </div>

                    {/* DESCRIPTION */}

                    {event.description && (

                      <div className="event-description">

                        <strong>
                          Description
                        </strong>

                        <p>
                          {
                            event.description
                          }
                        </p>

                      </div>

                    )}

                    {/* ACTION */}

                    {isOpen && !replanResult && (

                      <div className="event-action-box">

                        <div>

                          <strong>
                            ⚠️ Dynamic
                            Re-Planning Required
                          </strong>

                          <p>
                            Run AI analysis to
                            identify affected
                            blocks and safer
                            maintenance windows.
                          </p>

                        </div>

                        <button
                          className="event-action-button"
                          onClick={() =>
                            handleReplan(
                              event.event_id
                            )
                          }
                          disabled={
                            isReplanLoading ||
                            isApplyLoading ||
                            isTaskApplyLoading
                          }
                        >

                          {isReplanLoading
                            ? "⏳ Analysing..."
                            : "🔄 AI Replan"}

                        </button>

                      </div>

                    )}

                    {/* =================================================
                        REPLAN RESULT
                    ================================================= */}

                    {replanResult && (

                      <div className="replan-result">

                        {/* RESULT HEADER */}

                        <div className="replan-result-header">

                          <div>

                            <strong>
                              🧠 AI Re-Planning Result
                            </strong>

                            <p>
                              Event action:{" "}
                              {
                                replanResult.event_action ??
                                "REVIEW"
                              }
                            </p>

                          </div>

                        </div>

                        {/* =================================================
                            WHOLE BLOCK ANALYSIS
                        ================================================= */}

                        {hasAffectedBlocks ? (

                          <div className="replan-block-list">

                            {replanResult.affected_blocks.map(
                              (
                                block
                              ) => (

                                <div
                                  className="replan-block-card"
                                  key={
                                    block.block_id
                                  }
                                >

                                  <div className="replan-block-header">

                                    <strong>
                                      {
                                        block.block_code
                                      }
                                    </strong>

                                    <span
                                      className={`badge impact-${(
                                        block.impact_level ||
                                        "NONE"
                                      ).toLowerCase()}`}
                                    >
                                      {
                                        block.impact_level ||
                                        "NONE"
                                      }
                                    </span>

                                  </div>

                                  <div className="replan-block-grid">

                                    <div>

                                      <span>
                                        Current Window
                                      </span>

                                      <strong>
                                        {
                                          block.current_start_time ??
                                          "N/A"
                                        }{" "}
                                        –{" "}
                                        {
                                          block.current_end_time ??
                                          "N/A"
                                        }
                                      </strong>

                                    </div>

                                    <div>

                                      <span>
                                        Conflicts
                                      </span>

                                      <strong>
                                        {
                                          block.conflict_count ??
                                          0
                                        }
                                      </strong>

                                    </div>

                                    <div>

                                      <span>
                                        Affected Trains
                                      </span>

                                      <strong>
                                        {Array.isArray(
                                          block.affected_train_ids
                                        ) &&
                                        block
                                          .affected_train_ids
                                          .length
                                          ? block
                                              .affected_train_ids
                                              .join(
                                                ", "
                                              )
                                          : "None"}
                                      </strong>

                                    </div>

                                    <div>

                                      <span>
                                        AI Action
                                      </span>

                                      <strong>
                                        {
                                          block.recommended_action ||
                                          "Review required"
                                        }
                                      </strong>

                                    </div>

                                  </div>

                                  {block.alternative_start_time &&
                                    block.alternative_end_time && (

                                      <div className="alternative-window">

                                        <span>
                                          ✅ Recommended Safe Window
                                        </span>

                                        <strong>
                                          {
                                            block.alternative_start_time
                                          }{" "}
                                          –{" "}
                                          {
                                            block.alternative_end_time
                                          }
                                        </strong>

                                      </div>

                                    )}

                                  {block.recommendation && (

                                    <p className="replan-recommendation">

                                      💡{" "}
                                      {
                                        block.recommendation
                                      }

                                    </p>

                                  )}

                                </div>
                              )
                            )}

                          </div>

                        ) : (

                          <p className="events-empty">
                            No affected maintenance
                            blocks detected.
                          </p>

                        )}

                        {/* =================================================
                            WHOLE BLOCK APPLY
                        ================================================= */}

                        {isOpen && hasAffectedBlocks && !hasTaskLevelPlan && (

                          <button
                            className="apply-replan-button"
                            onClick={() =>
                              handleApplyReplan(
                                event.event_id
                              )
                            }
                            disabled={
                              isApplyLoading ||
                              isTaskApplyLoading
                            }
                          >

                            {isApplyLoading
                              ? "⏳ Applying..."
                              : "✅ Apply Whole-Block Replan"}

                          </button>

                        )}

                        {/* =================================================
                            TASK-LEVEL REPLANNING
                        ================================================= */}

                        {hasTaskLevelPlan && (

                          <div className="task-level-replan-section">

                            <div className="task-level-replan-header">

                              <div>

                                <strong>
                                  🧠 AI Task-Level Re-Planning
                                </strong>

                                <p>
                                  Whole-block rescheduling
                                  is not fully safe. AI has
                                  generated conflict-free
                                  windows for individual
                                  maintenance tasks.
                                </p>

                              </div>

                              <span className="task-plan-badge">
                                {taskLevelPlans.length} AI
                                Window
                                {taskLevelPlans.length !== 1
                                  ? "s"
                                  : ""}
                              </span>

                            </div>

                            <div className="task-level-plan-list">

                              {taskLevelPlans.map(
                                (
                                  task
                                ) => (

                                  <div
                                    className="task-level-plan-card"
                                    key={
                                      task.task_id
                                    }
                                  >

                                    <div className="task-level-plan-main">

                                      <div>

                                        <span className="task-code-label">
                                          Task
                                        </span>

                                        <strong>
                                          {
                                            task.task_code ??
                                            `Task #${task.task_id}`
                                          }
                                        </strong>

                                      </div>

                                      <span
                                        className={`badge ${(
                                          task.priority ||
                                          "MEDIUM"
                                        ).toLowerCase()}`}
                                      >
                                        {
                                          task.priority ||
                                          "MEDIUM"
                                        }
                                      </span>

                                    </div>

                                    <div className="task-level-plan-grid">

                                      <div>

                                        <span>
                                          Safe Window
                                        </span>

                                        <strong>
                                          {
                                            task.start_time ??
                                            "N/A"
                                          }{" "}
                                          –{" "}
                                          {
                                            task.end_time ??
                                            "N/A"
                                          }
                                        </strong>

                                      </div>

                                      <div>

                                        <span>
                                          Duration
                                        </span>

                                        <strong>
                                          {
                                            task.duration_hours ??
                                            "N/A"
                                          }{" "}
                                          hr
                                        </strong>

                                      </div>

                                      <div>

                                        <span>
                                          ML Risk
                                        </span>

                                        <strong>
                                          {
                                            task.ml_risk_percentage ??
                                            "N/A"
                                          }
                                          %
                                        </strong>

                                      </div>

                                      <div>

                                        <span>
                                          Combined Risk
                                        </span>

                                        <strong>
                                          {
                                            task.combined_risk_score ??
                                            "N/A"
                                          }
                                        </strong>

                                      </div>

                                      <div>

                                        <span>
                                          Planning Score
                                        </span>

                                        <strong>
                                          {
                                            task.planning_score ??
                                            "N/A"
                                          }
                                        </strong>

                                      </div>

                                      <div>

                                        <span>
                                          Train Conflict
                                        </span>

                                        <strong>
                                          ✅ None
                                        </strong>

                                      </div>

                                    </div>

                                  </div>

                                )
                              )}

                            </div>

                            {/* TASK APPLY BUTTON */}

                            {isOpen && (

                              <div className="task-level-action-box">

                                <div>

                                  <strong>
                                    ✅ AI Safe Windows Ready
                                  </strong>

                                  <p>
                                    Applying this plan will
                                    cancel the affected
                                    block and create new
                                    task-level maintenance
                                    blocks after final
                                    train-safety validation.
                                  </p>

                                </div>

                                <button
                                  className="apply-task-replan-button"
                                  onClick={() =>
                                    handleApplyTaskReplan(
                                      event.event_id
                                    )
                                  }
                                  disabled={
                                    isTaskApplyLoading ||
                                    isApplyLoading
                                  }
                                >

                                  {isTaskApplyLoading
                                    ? "⏳ Applying Task Plan..."
                                    : "✅ Apply Task-Level Replan"}

                                </button>

                              </div>

                            )}

                          </div>

                        )}

                      </div>

                    )}

                    {/* =================================================
                        RESOLVED
                    ================================================= */}

                    {!isOpen && (

                      <div className="resolved-box">

                        ✅ This event has been
                        resolved.

                      </div>

                    )}

                  </div>
                );
              }
            )}

          </div>
        )}

      </section>

    </div>
  );
}

export default Events;