
import { useEffect, useMemo, useState } from "react";
import { authFetch } from "../App";
import "./Trains.css";

const API_BASE =
  import.meta.env.VITE_API_BASE ||
  "http://127.0.0.1:8000";

/* ============================================================
   HELPERS
============================================================ */

const normalizeArray = (value) => {
  if (Array.isArray(value)) {
    return value;
  }

  if (Array.isArray(value?.data)) {
    return value.data;
  }

  if (Array.isArray(value?.trains)) {
    return value.trains;
  }

  if (Array.isArray(value?.schedules)) {
    return value.schedules;
  }

  if (Array.isArray(value?.train_schedule)) {
    return value.train_schedule;
  }

  if (Array.isArray(value?.results)) {
    return value.results;
  }

  if (Array.isArray(value?.items)) {
    return value.items;
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

const formatTime = (value) => {
  if (!value) {
    return "—";
  }

  return String(value).slice(0, 5);
};

const normalizePriority = (value) => {
  return String(value || "MEDIUM")
    .trim()
    .toUpperCase();
};

/* ============================================================
   COMPONENT
============================================================ */

function Trains() {
  const [trains, setTrains] = useState([]);
  const [trainSchedule, setTrainSchedule] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  /* ==========================================================
     LOAD TRAIN DATA
  ========================================================== */

  const loadTrainData = async () => {
    try {
      setLoading(true);
      setError("");

      const [
        trainsData,
        scheduleData,
      ] = await Promise.all([
        authFetch(
          `${API_BASE}/trains`
        ),

        authFetch(
          `${API_BASE}/train-schedule`
        ),
      ]);

      setTrains(
        normalizeArray(trainsData)
      );

      setTrainSchedule(
        normalizeArray(scheduleData)
      );
    } catch (err) {
      console.error(
        "Train page error:",
        err
      );

      setError(
        err?.message ||
          "Unable to load train data."
      );

      setTrains([]);
      setTrainSchedule([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrainData();
  }, []);

  /* ==========================================================
     DERIVED DATA
  ========================================================== */

  const highPriorityTrains =
    useMemo(() => {
      return trains.filter((train) => {
        const priority =
          normalizePriority(
            train.priority
          );

        return (
          priority === "HIGH" ||
          priority === "CRITICAL"
        );
      });
    }, [trains]);

  const trainScheduleCount = useMemo(() => {
    const counts = {};

    trainSchedule.forEach(
      (schedule) => {
        const id = String(
          schedule.train_id
        );

        counts[id] =
          (counts[id] || 0) + 1;
      }
    );

    return counts;
  }, [trainSchedule]);

  /* ==========================================================
     RENDER
  ========================================================== */

  return (
    <div className="trains-page">

      {/* ======================================================
          PAGE HEADER
      ====================================================== */}

      <section className="trains-hero">

        <div>
          <span className="trains-eyebrow">
            RAILWAY OPERATIONS
          </span>

          <h1>
            🚆 Train Operations
          </h1>

          <p>
            Monitor active trains,
            schedules, priorities and
            railway movement information.
          </p>
        </div>

        <div className="trains-live-badge">
          <span className="status-dot"></span>
          LIVE OPERATIONS
        </div>

      </section>

      {/* ======================================================
          ERROR
      ====================================================== */}

      {error && (
        <div className="global-error">
          <strong>
            Train data error:
          </strong>{" "}
          {error}
        </div>
      )}

      {/* ======================================================
          TRAIN SUMMARY
      ====================================================== */}

      <section className="trains-summary">

        <div className="train-summary-card">
          <span>
            🚆 Total Trains
          </span>

          <strong>
            {loading
              ? "..."
              : trains.length}
          </strong>
        </div>

        <div className="train-summary-card">
          <span>
            📅 Schedules
          </span>

          <strong>
            {loading
              ? "..."
              : trainSchedule.length}
          </strong>
        </div>

        <div className="train-summary-card">
          <span>
            ⭐ High Priority
          </span>

          <strong>
            {loading
              ? "..."
              : highPriorityTrains.length}
          </strong>
        </div>

      </section>

      {/* ======================================================
          TRAIN LIST
      ====================================================== */}

      <section className="trains-card">

        <div className="trains-card-header">

          <div>
            <h2>
              🚆 Train Fleet
            </h2>

            <p>
              Registered trains and their
              operating priority.
            </p>
          </div>

          <span className="trains-count">
            {trains.length} Trains
          </span>

        </div>

        {loading ? (

          <div className="trains-loading">

            <div className="loader"></div>

            Loading train data...

          </div>

        ) : trains.length === 0 ? (

          <p className="empty-state">
            No train data available.
          </p>

        ) : (

          <div className="train-list-grid">

            {trains.map((train) => {

              const trainId =
                train.train_id;

              const priority =
                normalizePriority(
                  train.priority
                );

              const scheduleCount =
                trainScheduleCount[
                  String(trainId)
                ] || 0;

              return (
                <div
                  className="train-operation-card"
                  key={trainId}
                >

                  <div className="train-operation-top">

                    <div className="train-number">
                      🚆{" "}
                      {train.train_no}
                    </div>

                    <span
                      className={`badge ${priority.toLowerCase()}`}
                    >
                      {priority}
                    </span>

                  </div>

                  <h3>
                    {train.train_name}
                  </h3>

                  <p>
                    {train.train_type}
                  </p>

                  <div className="train-operation-info">

                    <div>
                      <span>
                        Train ID
                      </span>

                      <strong>
                        {trainId}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Schedule Entries
                      </span>

                      <strong>
                        {scheduleCount}
                      </strong>
                    </div>

                  </div>

                </div>
              );
            })}

          </div>

        )}

      </section>

      {/* ======================================================
          TRAIN SCHEDULE
      ====================================================== */}

      <section className="trains-card">

        <div className="trains-card-header">

          <div>
            <h2>
              📅 Train Schedule
            </h2>

            <p>
              Scheduled arrival and departure
              across railway sections.
            </p>
          </div>

          <span className="trains-count">
            {trainSchedule.length} Entries
          </span>

        </div>

        {loading ? (

          <div className="trains-loading">

            <div className="loader"></div>

            Loading schedules...

          </div>

        ) : trainSchedule.length === 0 ? (

          <p className="empty-state">
            No train schedules available.
          </p>

        ) : (

          <div className="table-container">

            <table>

              <thead>

                <tr>
                  <th>Schedule</th>
                  <th>Train</th>
                  <th>Section</th>
                  <th>Date</th>
                  <th>Arrival</th>
                  <th>Departure</th>
                </tr>

              </thead>

              <tbody>

                {trainSchedule.map(
                  (schedule, index) => (

                    <tr
                      key={
                        schedule.schedule_id ??
                        `${schedule.train_id}-${schedule.schedule_date}-${schedule.section_id}-${index}`
                      }
                    >

                      <td>
                        <strong>
                          #
                          {
                            schedule.schedule_id ??
                            "—"
                          }
                        </strong>
                      </td>

                      <td>
                        🚆 Train{" "}
                        {
                          schedule.train_id
                        }
                      </td>

                      <td>
                        SEC
                        {String(
                          schedule.section_id
                        ).padStart(
                          2,
                          "0"
                        )}
                      </td>

                      <td>
                        {formatDate(
                          schedule.schedule_date
                        )}
                      </td>

                      <td>
                        <span className="time-badge">
                          {formatTime(
                            schedule.arrival_time
                          )}
                        </span>
                      </td>

                      <td>
                        <span className="time-badge">
                          {formatTime(
                            schedule.departure_time
                          )}
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

      {/* ======================================================
          FOOTER
      ====================================================== */}

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

export default Trains;