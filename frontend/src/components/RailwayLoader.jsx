import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import "./RailwayLoader.css";

function RailwayLoader() {
  const [activeRequests, setActiveRequests] = useState(0);
  const [message, setMessage] = useState("Loading railway data...");

  const location = useLocation();

  // First render ko identify karne ke liye
  const firstRoute = useRef(true);

  // ============================================================
  // API LOADING EVENTS
  // ============================================================

  useEffect(() => {
    const handleStart = (event) => {
      setMessage(
        event.detail?.message || "Loading railway data..."
      );

      setActiveRequests((count) => count + 1);
    };

    const handleEnd = () => {
      setActiveRequests((count) =>
        Math.max(0, count - 1)
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


  // ============================================================
  // PAGE / ROUTE CHANGE LOADER
  // ============================================================

  useEffect(() => {

    // ----------------------------------------------------------
    // Initial render
    // ----------------------------------------------------------

    if (firstRoute.current) {
      firstRoute.current = false;
      return;
    }


    // ----------------------------------------------------------
    // HOME PAGE
    // Home par route-change loader nahi dikhana
    // ----------------------------------------------------------

    if (
      location.pathname === "/home" ||
      location.pathname === "/"
    ) {
      return;
    }


    // ----------------------------------------------------------
    // OTHER PAGES
    // ----------------------------------------------------------

    setMessage("Loading railway page...");

    // Loader start
    setActiveRequests((count) => count + 1);


    // ----------------------------------------------------------
    // Loader visibility
    // ----------------------------------------------------------

    const timer = setTimeout(() => {

      setActiveRequests((count) =>
        Math.max(0, count - 1)
      );

    }, 900);


    // ----------------------------------------------------------
    // Cleanup
    // ----------------------------------------------------------

    return () => {
      clearTimeout(timer);
    };

  }, [location.pathname]);


  // ============================================================
  // NOTHING TO SHOW
  // ============================================================

  if (activeRequests === 0) {
    return null;
  }


  // ============================================================
  // LOADER UI
  // ============================================================

  return (
    <div className="railway-loader-overlay">

      <div className="railway-loader-card">


        {/* ======================================================
            TITLE
        ====================================================== */}

        <div className="railway-loader-title">
          {message}
        </div>


        {/* ======================================================
            RAILWAY TRACK
        ====================================================== */}

        <div className="railway-loader-track">


          {/* ====================================================
              STATIONARY SLEEPERS
          ==================================================== */}

          <div className="railway-loader-sleepers">

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


          {/* ====================================================
              MOVING TRAIN

              Direction:

              COACH → COACH → COACH → ENGINE 🚆
                                              →→→
          ==================================================== */}

          <div className="railway-loader-train">


            {/* ==================================================
                COACH 1
            ================================================== */}

            <div className="railway-loader-coach">

              <div className="railway-loader-windows">

                <span />
                <span />
                <span />
                <span />

              </div>

            </div>


            {/* ==================================================
                COACH 2
            ================================================== */}

            <div className="railway-loader-coach">

              <div className="railway-loader-windows">

                <span />
                <span />
                <span />
                <span />

              </div>

            </div>


            {/* ==================================================
                COACH 3
            ================================================== */}

            <div className="railway-loader-coach">

              <div className="railway-loader-windows">

                <span />
                <span />
                <span />
                <span />

              </div>

            </div>


            {/* ==================================================
                ENGINE - FRONT / RIGHT
            ================================================== */}

            <div className="railway-loader-engine">

              <div className="railway-loader-window" />

              <div className="railway-loader-light" />

              <div className="railway-loader-front" />

            </div>

          </div>

        </div>


        {/* ======================================================
            SUBTITLE
        ====================================================== */}

        <div className="railway-loader-subtitle">
          AI Railway Operations Control
        </div>

      </div>

    </div>
  );
}

export default RailwayLoader;