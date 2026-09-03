import { useEffect, useState } from "react";
import "./Trains.css";

const API_BASE = "http://127.0.0.1:8000";
const TOKEN_KEY = "railway_admin_token";

function Trains() {
  const [trains, setTrains] = useState([]);
  const [trainSchedule, setTrainSchedule] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // ============================================================
  // LOAD TRAIN DATA
  // ============================================================

  useEffect(() => {
    const loadTrainData = async () => {
      try {
        setLoading(true);
        setError("");

        const token = localStorage.getItem(TOKEN_KEY);

        const headers = {
          Accept: "application/json",
          ...(token
            ? {
                Authorization: `Bearer ${token}`,
              }
            : {}),
        };

        const [trainsResponse, scheduleResponse] =
          await Promise.all([
            fetch(`${API_BASE}/trains`, {
              headers,
            }),
            fetch(`${API_BASE}/train-schedule`, {
              headers,
            }),
          ]);

        if (!trainsResponse.ok) {
          throw new Error(
            `Trains API failed with status ${trainsResponse.status}`
          );
        }

        if (!scheduleResponse.ok) {
          throw new Error(
            `Train schedule API failed with status ${scheduleResponse.status}`
          );
        }

        const [trainsData, scheduleData] =
          await Promise.all([
            trainsResponse.json(),
            scheduleResponse.json(),
          ]);

        setTrains(trainsData || []);
        setTrainSchedule(scheduleData || []);

      } catch (err) {
        console.error(
          "Train page error:",
          err
        );

        setError(
          err.message ||
          "Unable to load train data."
        );
      } finally {
        setLoading(false);
      }
    };

    loadTrainData();
  }, []);

  // ============================================================
  // RENDER
  // ============================================================

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
            Monitor active trains, schedules,
            priorities and railway movement
            information.
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
          <span>🚆 Total Trains</span>

          <strong>
            {loading
              ? "..."
              : trains.length}
          </strong>
        </div>

        <div className="train-summary-card">
          <span>📅 Schedules</span>

          <strong>
            {loading
              ? "..."
              : trainSchedule.length}
          </strong>
        </div>

        <div className="train-summary-card">
          <span>⭐ High Priority</span>

          <strong>
            {loading
              ? "..."
              : trains.filter(
                  (train) =>
                    train.priority === "HIGH" ||
                    train.priority === "CRITICAL"
                ).length}
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

            {trains.map((train) => (

              <div
                className="train-operation-card"
                key={train.train_id}
              >

                <div className="train-operation-top">

                  <div className="train-number">
                    🚆 {train.train_no}
                  </div>

                  <span
                    className={`badge ${
                      (
                        train.priority ||
                        "MEDIUM"
                      ).toLowerCase()
                    }`}
                  >
                    {train.priority ||
                      "MEDIUM"}
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
                      {train.train_id}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Priority
                    </span>

                    <strong>
                      {train.priority}
                    </strong>
                  </div>

                </div>

              </div>

            ))}

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
                  (schedule) => (

                    <tr
                      key={
                        schedule.schedule_id
                      }
                    >

                      <td>
                        <strong>
                          #
                          {
                            schedule.schedule_id
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
                        ).padStart(2, "0")}
                      </td>

                      <td>
                        {
                          schedule.schedule_date
                        }
                      </td>

                      <td>
                        <span className="time-badge">
                          {
                            schedule.arrival_time
                          }
                        </span>
                      </td>

                      <td>
                        <span className="time-badge">
                          {
                            schedule.departure_time
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

    </div>
  );
}

export default Trains;