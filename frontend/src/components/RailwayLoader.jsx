import { useEffect, useState } from "react";
import "./RailwayLoader.css";

function RailwayLoader() {
  const [activeRequests, setActiveRequests] = useState(0);
  const [message, setMessage] = useState(
    "Loading railway data..."
  );

  useEffect(() => {
    const handleStart = (event) => {
      setMessage(
        event.detail?.message ||
          "Loading railway data..."
      );

      setActiveRequests(
        (count) => count + 1
      );
    };

    const handleEnd = () => {
      setActiveRequests(
        (count) => Math.max(0, count - 1)
      );
    };

    window.addEventListener(
      "railway-loading-start",
      handleStart
    );

    window.addEventListener(
      "railway-loading-end",
      handleEnd
    );

    return () => {
      window.removeEventListener(
        "railway-loading-start",
        handleStart
      );

      window.removeEventListener(
        "railway-loading-end",
        handleEnd
      );
    };
  }, []);

  if (activeRequests === 0) {
    return null;
  }

  return (
    <div className="railway-loader-overlay">
      <div className="railway-loader-card">

        {/* LOADING TITLE */}
        <div className="railway-loader-title">
          {message}
        </div>

        {/* RAILWAY SCENE */}
        <div className="railway-track">

          {/* RAILWAY SLEEPERS */}
          <div className="railway-sleepers">
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>

          {/* TRAIN */}
          <div className="train">

            {/* ENGINE */}
            <div className="train-engine">
              <div className="train-window" />
              <div className="train-light" />
              <div className="train-front" />
            </div>

            {/* COACH 1 */}
            <div className="train-coach">
              <div className="coach-windows">
                <span />
                <span />
                <span />
                <span />
              </div>
            </div>

            {/* COACH 2 */}
            <div className="train-coach">
              <div className="coach-windows">
                <span />
                <span />
                <span />
                <span />
              </div>
            </div>

          </div>
        </div>

        {/* SUBTITLE */}
        <div className="railway-loader-subtitle">
          AI Railway Operations Control
        </div>

      </div>
    </div>
  );
}

export default RailwayLoader;