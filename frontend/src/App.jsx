import { useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import Navbar from "./components/Navbar";

import Home from "./pages/Home";
import Blocks from "./pages/Blocks";
import Trains from "./pages/Trains";
import AICenter from "./pages/AICenter";
import Events from "./pages/Events";
import Timeline from "./pages/Timeline";
import Analytics from "./pages/Analytics";

import "./App.css";

// ============================================================
// API CONFIG
// ============================================================

const API_BASE = "http://127.0.0.1:8000";

const TOKEN_KEY = "railway_admin_token";
const USER_KEY = "railway_admin_user";

// ============================================================
// AUTH FETCH
// ============================================================

export async function authFetch(url, options = {}) {
  const token = localStorage.getItem(TOKEN_KEY);

  const headers = {
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";

  let data = null;

  if (contentType.includes("application/json")) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;

    if (typeof data === "string") {
      message = data;
    } else if (data?.detail) {
      if (typeof data.detail === "string") {
        message = data.detail;
      } else {
        message = JSON.stringify(data.detail);
      }
    } else if (data?.message) {
      if (typeof data.message === "string") {
        message = data.message;
      } else {
        message = JSON.stringify(data.message);
      }
    } else if (data) {
      message = JSON.stringify(data);
    }

    throw new Error(message);
  }

  return data;
}

// ============================================================
// APP
// ============================================================

function App() {

  // ==========================================================
  // AUTHENTICATION STATE
  // ==========================================================

  const [token, setToken] = useState(
    () =>
      localStorage.getItem(
        TOKEN_KEY
      )
  );

  const [currentUser, setCurrentUser] =
    useState(() => {

      const savedUser =
        localStorage.getItem(
          USER_KEY
        );

      if (!savedUser) {
        return null;
      }

      try {
        return JSON.parse(
          savedUser
        );
      } catch {
        return null;
      }
    });

  const [loginUsername, setLoginUsername] =
    useState("");

  const [loginPassword, setLoginPassword] =
    useState("");

  const [loginLoading, setLoginLoading] =
    useState(false);

  const [loginError, setLoginError] =
    useState("");


  // ==========================================================
  // LOGIN
  // ==========================================================

  const handleLogin = async (event) => {

    event.preventDefault();

    const username =
      loginUsername.trim();

    if (!username || !loginPassword) {

      setLoginError(
        "Please enter username and password."
      );

      return;
    }

    try {

      setLoginLoading(true);
      setLoginError("");

      const formData =
        new URLSearchParams();

      formData.append(
        "username",
        username
      );

      formData.append(
        "password",
        loginPassword
      );

      const response =
        await fetch(
          `${API_BASE}/auth/login`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/x-www-form-urlencoded",

              Accept:
                "application/json",
            },

            body:
              formData.toString(),
          }
        );

      const data =
        await response
          .json()
          .catch(() => null);

      if (!response.ok) {

        throw new Error(
          data?.detail ||
          `Login failed with status ${response.status}`
        );
      }

      if (!data?.access_token) {

        throw new Error(
          "Login succeeded but no access token was returned."
        );
      }

      // Save token
      localStorage.setItem(
        TOKEN_KEY,
        data.access_token
      );

      // Save user
      localStorage.setItem(
        USER_KEY,
        JSON.stringify(
          data.user || {
            username,
          }
        )
      );

      setToken(
        data.access_token
      );

      setCurrentUser(
        data.user || {
          username,
        }
      );

      setLoginPassword("");

    } catch (error) {

      console.error(
        "Login error:",
        error
      );

      setLoginError(
        error.message ||
        "Unable to login."
      );

    } finally {

      setLoginLoading(false);

    }
  };


  // ==========================================================
  // LOGOUT
  // ==========================================================

  const handleLogout = () => {

    localStorage.removeItem(
      TOKEN_KEY
    );

    localStorage.removeItem(
      USER_KEY
    );

    setToken(null);
    setCurrentUser(null);

    setLoginUsername("");
    setLoginPassword("");
    setLoginError("");
  };


  // ==========================================================
  // LOGIN SCREEN
  // ==========================================================

  if (!token) {

    return (
      <div className="login-page">

        <div className="login-card">

          <div className="login-icon">
            🚆
          </div>

          <h1>
            AI Automatic Railway
            Block Planner
          </h1>

          <p className="login-subtitle">
            Admin Control Panel
          </p>


          <form onSubmit={handleLogin}>

            {/* USERNAME */}

            <div className="login-field">

              <label>
                Username
              </label>

              <input
                type="text"
                value={
                  loginUsername
                }
                onChange={(event) =>
                  setLoginUsername(
                    event.target.value
                  )
                }
                placeholder="Enter admin username"
                autoComplete="username"
                disabled={
                  loginLoading
                }
              />

            </div>


            {/* PASSWORD */}

            <div className="login-field">

              <label>
                Password
              </label>

              <input
                type="password"
                value={
                  loginPassword
                }
                onChange={(event) =>
                  setLoginPassword(
                    event.target.value
                  )
                }
                placeholder="Enter password"
                autoComplete="current-password"
                disabled={
                  loginLoading
                }
              />

            </div>


            {/* ERROR */}

            {loginError && (
              <div className="login-error">
                ❌ {loginError}
              </div>
            )}


            {/* LOGIN BUTTON */}

            <button
              type="submit"
              className="login-button"
              disabled={
                loginLoading
              }
            >
              {loginLoading
                ? "⏳ Signing in..."
                : "🔐 Admin Login"}
            </button>

          </form>


          {/* FOOTER */}

          <div className="login-footer">

            <div>
              🔒 Authorized personnel only
            </div>

            <div className="project-leader">
              Project Leader:{" "}
              <strong>
                Abhishek Kumar
              </strong>
            </div>

          </div>

        </div>

      </div>
    );
  }


  // ==========================================================
  // AUTHENTICATED LAYOUT
  // ==========================================================

  return (
    <BrowserRouter>

      <div className="app">

        {/* ====================================================
            NAVBAR
            ==================================================== */}

        <Navbar
          currentUser={
            currentUser
          }
          onLogout={
            handleLogout
          }
        />


        {/* ====================================================
            MAIN CONTENT
            ==================================================== */}

        <main className="container">

          <Routes>

            {/* DEFAULT */}

            <Route
              path="/"
              element={
                <Navigate
                  to="/home"
                  replace
                />
              }
            />


            {/* HOME */}

            <Route
              path="/home"
              element={
                <Home />
              }
            />


            {/* BLOCKS */}

            <Route
              path="/blocks"
              element={
                <Blocks />
              }
            />


            {/* TRAINS */}

            <Route
              path="/trains"
              element={
                <Trains />
              }
            />


            {/* AI */}

            <Route
              path="/ai"
              element={
                <AICenter />
              }
            />


            {/* EVENTS */}

            <Route
              path="/events"
              element={
                <Events />
              }
            />


            {/* TIMELINE */}

            <Route
              path="/timeline"
              element={
                <Timeline />
              }
            />


            {/* ANALYTICS */}

            <Route
              path="/analytics"
              element={
                <Analytics />
              }
            />


            {/* INVALID URL */}

            <Route
              path="*"
              element={
                <Navigate
                  to="/home"
                  replace
                />
              }
            />

          </Routes>

        </main>


        {/* ====================================================
            PROJECT FOOTER
            ==================================================== */}

        <footer className="project-footer">

          <span>
            Project Leader:
          </span>

          <strong>
            Abhishek Kumar
          </strong>

        </footer>

      </div>

    </BrowserRouter>
  );
}

export default App;