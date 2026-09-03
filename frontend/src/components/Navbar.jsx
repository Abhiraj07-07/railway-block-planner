import { NavLink } from "react-router-dom";
import "./Navbar.css";

function Navbar({ currentUser, onLogout }) {
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
            Railway Block Planner
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
            isActive
              ? "nav-link active"
              : "nav-link"
          }
        >
          <span>🏠</span>
          <span>Home</span>
        </NavLink>


        <NavLink
          to="/blocks"
          className={({ isActive }) =>
            isActive
              ? "nav-link active"
              : "nav-link"
          }
        >
          <span>🛠️</span>
          <span>Blocks</span>
        </NavLink>


        <NavLink
          to="/trains"
          className={({ isActive }) =>
            isActive
              ? "nav-link active"
              : "nav-link"
          }
        >
          <span>🚆</span>
          <span>Trains</span>
        </NavLink>


        <NavLink
          to="/ai"
          className={({ isActive }) =>
            isActive
              ? "nav-link active"
              : "nav-link"
          }
        >
          <span>🤖</span>
          <span>AI Center</span>
        </NavLink>


        <NavLink
          to="/events"
          className={({ isActive }) =>
            isActive
              ? "nav-link active"
              : "nav-link"
          }
        >
          <span>⚠️</span>
          <span>Events</span>
        </NavLink>


        <NavLink
          to="/timeline"
          className={({ isActive }) =>
            isActive
              ? "nav-link active"
              : "nav-link"
          }
        >
          <span>📅</span>
          <span>Timeline</span>
        </NavLink>


        <NavLink
          to="/analytics"
          className={({ isActive }) =>
            isActive
              ? "nav-link active"
              : "nav-link"
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
          {currentUser?.username || "Abhishek Kumar"}
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