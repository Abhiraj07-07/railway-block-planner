import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import "./Navbar.css";

function Navbar({ currentUser, onLogout }) {
  const [brandLanguage, setBrandLanguage] = useState(true);

  useEffect(() => {
  const interval = setInterval(() => {
    setBrandLanguage((prev) => !prev);
  }, 15000);

  return () => clearInterval(interval);
}, []);

  return (
    <nav className="navbar">

      {/* ======================================================
    BRAND
    ====================================================== */}

<div className="nav-brand">

  <div className="nav-brand-icon">
    🚆
  </div>

  <div className="nav-brand-content">

    <span className="nav-brand-title">

      <span
        className={`nav-brand-option ${
          brandLanguage ? "brand-active" : ""
        }`}
      >
        RailYojana AI
      </span>

      <span
        className={`nav-brand-option nav-brand-hindi ${
          !brandLanguage ? "brand-active" : ""
        }`}
      >
        रेलयोजना AI
      </span>

    </span>

    <span className="nav-brand-divider">
      |
    </span>

    <span className="nav-brand-ai">
      AI Operations Control
    </span>

  </div>

</div>


      {/* ======================================================
          NAVIGATION
          ====================================================== */}

      <div className="nav-links">

        <NavLink
          to="/home"
          className={({ isActive }) =>
            isActive ? "nav-link active" : "nav-link"
          }
        >
          <span>🏠</span>
          <span>Home</span>
        </NavLink>

        <NavLink
          to="/blocks"
          className={({ isActive }) =>
            isActive ? "nav-link active" : "nav-link"
          }
        >
          <span>🛠️</span>
          <span>Blocks</span>
        </NavLink>

        <NavLink
          to="/trains"
          className={({ isActive }) =>
            isActive ? "nav-link active" : "nav-link"
          }
        >
          <span>🚆</span>
          <span>Trains</span>
        </NavLink>

        <NavLink
          to="/ai"
          className={({ isActive }) =>
            isActive ? "nav-link active" : "nav-link"
          }
        >
          <span>🤖</span>
          <span>AI Center</span>
        </NavLink>

        <NavLink
          to="/events"
          className={({ isActive }) =>
            isActive ? "nav-link active" : "nav-link"
          }
        >
          <span>⚠️</span>
          <span>Events</span>
        </NavLink>

        <NavLink
          to="/timeline"
          className={({ isActive }) =>
            isActive ? "nav-link active" : "nav-link"
          }
        >
          <span>📅</span>
          <span>Timeline</span>
        </NavLink>

        <NavLink
          to="/analytics"
          className={({ isActive }) =>
            isActive ? "nav-link active" : "nav-link"
          }
        >
          <span>📊</span>
          <span>Analytics</span>
        </NavLink>

      </div>


      {/* ======================================================
          USER AREA
          ====================================================== */}

      <div className="nav-user">

        <div className="nav-online">
          <span className="nav-online-dot"></span>
          Online
        </div>

        <div className="nav-user-name">
          👤{" "}
          {currentUser?.username || "Admin"}
        </div>

        <button
          type="button"
          className="nav-logout"
          onClick={onLogout}
        >
          Logout
        </button>

      </div>

    </nav>
  );
}

export default Navbar;