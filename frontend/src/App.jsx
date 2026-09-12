import { useState } from "react";

import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import RailwayLoader from "./components/RailwayLoader";
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
// API CONFIGURATION
// ============================================================

const API_BASE =
  import.meta.env.VITE_API_BASE?.trim().replace(/\/+$/, "") ||
  "https://serene-perfection-production-261b.up.railway.app";

// ============================================================
// AUTH STORAGE KEYS
// ============================================================

const TOKEN_KEY = "railway_token";
const USER_KEY = "railway_user";

// ============================================================
// COMMON AUTH FETCH
// ============================================================

export async function authFetch(url, options = {}) {
  const token = localStorage.getItem(TOKEN_KEY);

  const loaderMessage =
    options.loaderMessage ||
    "Loading railway data...";

  const skipGlobalLoader =
    options.skipGlobalLoader === true;

  const loaderStartTime = Date.now();

  // ----------------------------------------------------------
  // START GLOBAL LOADER
  // ----------------------------------------------------------

  if (!skipGlobalLoader) {
    window.dispatchEvent(
      new CustomEvent("railway-loading-start", {
        detail: {
          message: loaderMessage,
        },
      })
    );
  }

  // ----------------------------------------------------------
  // PREPARE HEADERS
  // ----------------------------------------------------------

  const headers = {
    ...(options.headers || {}),
  };

  // ----------------------------------------------------------
  // JSON BODY HANDLING
  // ----------------------------------------------------------

  const hasContentType =
    headers["Content-Type"] ||
    headers["content-type"];

  const isFormData =
    typeof FormData !== "undefined" &&
    options.body instanceof FormData;

  const isUrlSearchParams =
    typeof URLSearchParams !== "undefined" &&
    options.body instanceof URLSearchParams;

  if (
    options.body &&
    !hasContentType &&
    !isFormData &&
    !isUrlSearchParams
  ) {
    headers["Content-Type"] =
      "application/json";
  }

  // ----------------------------------------------------------
  // AUTHORIZATION
  // ----------------------------------------------------------

  if (token) {
    headers.Authorization =
      `Bearer ${token}`;
  }

  try {
    // --------------------------------------------------------
    // REQUEST
    // --------------------------------------------------------

    const response = await fetch(url, {
      ...options,
      headers,
    });

    // --------------------------------------------------------
    // RESPONSE TYPE
    // --------------------------------------------------------

    const contentType =
      response.headers.get(
        "content-type"
      ) || "";

    let data = null;

    if (
      contentType.includes(
        "application/json"
      )
    ) {
      data =
        await response.json();
    } else {
      data =
        await response.text();
    }

    // --------------------------------------------------------
    // ERROR HANDLING
    // --------------------------------------------------------

    if (!response.ok) {
      let message =
        `Request failed (${response.status})`;

      if (
        typeof data === "string"
      ) {
        if (data.trim()) {
          message = data;
        }
      } else if (
        data?.detail
      ) {
        message =
          typeof data.detail ===
          "string"
            ? data.detail
            : JSON.stringify(
                data.detail
              );
      } else if (
        data?.message
      ) {
        message =
          typeof data.message ===
          "string"
            ? data.message
            : JSON.stringify(
                data.message
              );
      } else if (data) {
        message =
          JSON.stringify(data);
      }

      // ------------------------------------------------------
      // INVALID / EXPIRED TOKEN
      // ------------------------------------------------------

      if (
        response.status === 401 ||
        response.status === 403
      ) {
        localStorage.removeItem(
          TOKEN_KEY
        );

        localStorage.removeItem(
          USER_KEY
        );
      }

      throw new Error(message);
    }

    // --------------------------------------------------------
    // SUCCESS
    // --------------------------------------------------------

    return data;

  } finally {

    // --------------------------------------------------------
    // MINIMUM LOADER TIME
    // --------------------------------------------------------

    const MIN_LOADER_TIME = 800;

    const elapsed =
      Date.now() -
      loaderStartTime;

    const remaining =
      Math.max(
        0,
        MIN_LOADER_TIME -
          elapsed
      );

    if (!skipGlobalLoader) {
      setTimeout(() => {
        window.dispatchEvent(
          new Event(
            "railway-loading-end"
          )
        );
      }, remaining);
    }
  }
}

// ============================================================
// APP
// ============================================================

function App() {

  // ==========================================================
  // CURRENT USER
  // ==========================================================

  const [currentUser, setCurrentUser] =
    useState(() => {
      try {
        const savedUser =
          localStorage.getItem(
            USER_KEY
          );

        if (!savedUser) {
          return null;
        }

        return JSON.parse(
          savedUser
        );

      } catch {
        localStorage.removeItem(
          USER_KEY
        );

        return null;
      }
    });

  // ==========================================================
  // LOGIN FORM STATE
  // ==========================================================

  const [username, setUsername] =
    useState("");

  const [password, setPassword] =
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

    setLoginError("");

    const cleanUsername =
      username.trim();

    // --------------------------------------------------------
    // VALIDATION
    // --------------------------------------------------------

    if (
      !cleanUsername ||
      !password
    ) {
      setLoginError(
        "Please enter username and password."
      );

      return;
    }

    setLoginLoading(true);

    try {

      // ------------------------------------------------------
      // BACKEND LOGIN
      // POST /auth/login
      // ------------------------------------------------------

      const loginBody =
        new URLSearchParams();

      loginBody.append(
        "username",
        cleanUsername
      );

      loginBody.append(
        "password",
        password
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
              loginBody.toString(),
          }
        );

      // ------------------------------------------------------
      // PARSE RESPONSE
      // ------------------------------------------------------

      const contentType =
        response.headers.get(
          "content-type"
        ) || "";

      let data = null;

      if (
        contentType.includes(
          "application/json"
        )
      ) {
        data =
          await response.json();
      } else {
        data =
          await response.text();
      }

      // ------------------------------------------------------
      // LOGIN ERROR
      // ------------------------------------------------------

      if (!response.ok) {

        let message =
          "Login failed.";

        if (
          typeof data === "string"
        ) {

          if (data.trim()) {
            message = data;
          }

        } else if (
          data?.detail
        ) {

          message =
            typeof data.detail ===
            "string"
              ? data.detail
              : JSON.stringify(
                  data.detail
                );

        } else if (
          data?.message
        ) {

          message =
            typeof data.message ===
            "string"
              ? data.message
              : JSON.stringify(
                  data.message
                );

        } else if (data) {

          message =
            JSON.stringify(data);
        }

        throw new Error(message);
      }

      // ------------------------------------------------------
      // GET ACCESS TOKEN
      // ------------------------------------------------------

      const token =
        data?.access_token;

      if (!token) {
        throw new Error(
          "Login successful, but access token was not received from the server."
        );
      }

      // ------------------------------------------------------
      // GET USER
      // ------------------------------------------------------

      const user = {
        user_id:
          data?.user?.user_id,

        username:
          data?.user?.username ||
          cleanUsername,

        role:
          data?.user?.role ||
          "ADMIN",
      };

      // ------------------------------------------------------
      // SAVE TOKEN
      // ------------------------------------------------------

      localStorage.setItem(
        TOKEN_KEY,
        token
      );

      // ------------------------------------------------------
      // SAVE USER
      // ------------------------------------------------------

      localStorage.setItem(
        USER_KEY,
        JSON.stringify(user)
      );

      // ------------------------------------------------------
      // IMPORTANT:
      // ALWAYS START FROM HOME AFTER LOGIN
      // ------------------------------------------------------

      window.history.replaceState(
        null,
        "",
        "/home"
      );

      // ------------------------------------------------------
      // UPDATE APP STATE
      // ------------------------------------------------------

      setCurrentUser(user);

      setUsername("");

      setPassword("");

      setLoginError("");

    } catch (error) {

      console.error(
        "Login error:",
        error
      );

      setLoginError(
        error?.message ||
        "Unable to login. Please try again."
      );

    } finally {

      setLoginLoading(false);
    }
  };

  // ==========================================================
  // LOGOUT
  // ==========================================================

  const handleLogout = () => {

    // --------------------------------------------------------
    // REMOVE AUTH DATA
    // --------------------------------------------------------

    localStorage.removeItem(
      TOKEN_KEY
    );

    localStorage.removeItem(
      USER_KEY
    );

    // --------------------------------------------------------
    // CLEAR APP STATE
    // --------------------------------------------------------

    setCurrentUser(null);

    setUsername("");

    setPassword("");

    setLoginError("");

    // --------------------------------------------------------
    // IMPORTANT:
    // RESET ROUTE TO HOME
    //
    // So after logout/login cycle,
    // user never remains on old page.
    // --------------------------------------------------------

    window.history.replaceState(
      null,
      "",
      "/home"
    );
  };

  // ==========================================================
  // LOGIN SCREEN
  // ==========================================================

  if (!currentUser) {

    return (

      <div className="login-page">

        <div className="login-card">

          {/* LOGIN BRAND */}

          <div className="login-brand">

            <div className="login-brand-icon">
              🚄
            </div>

            <div className="login-brand-name">
              RailYojana AI
            </div>

            <div className="login-brand-subtitle">
              AI Operations Control
            </div>

          </div>

          {/* TITLE */}

          <h1>
            RailYojana AI
          </h1>

          <p className="login-subtitle">
            Admin Control Panel
          </p>

          {/* LOGIN ERROR */}

          {loginError && (
            <div className="login-error">
              {loginError}
            </div>
          )}

          {/* LOGIN FORM */}

          <form
            onSubmit={handleLogin}
            className="login-form"
          >

            {/* USERNAME */}

            <div className="login-field">

              <label htmlFor="username">
                Username
              </label>

              <input
                id="username"
                type="text"
                value={username}

                onChange={(event) =>
                  setUsername(
                    event.target.value
                  )
                }

                placeholder="Enter username"

                autoComplete="username"

                disabled={
                  loginLoading
                }
              />

            </div>

            {/* PASSWORD */}

            <div className="login-field">

              <label htmlFor="password">
                Password
              </label>

              <input
                id="password"
                type="password"
                value={password}

                onChange={(event) =>
                  setPassword(
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

            {/* LOGIN BUTTON */}

            <button
              type="submit"
              className="login-button"
              disabled={
                loginLoading
              }
            >
              {loginLoading
                ? "Signing in..."
                : "Login"}
            </button>

          </form>

          {/* LOGIN FOOTER */}

          <div className="login-footer">
            Railway Infrastructure
            Intelligence Platform
          </div>

        </div>

      </div>
    );
  }

  // ==========================================================
  // MAIN APPLICATION
  // ==========================================================

  return (

    <BrowserRouter>

      {/* GLOBAL RAILWAY LOADER */}

      <RailwayLoader />

      <div className="app">

        {/* NAVBAR */}

        <Navbar
          currentUser={
            currentUser
          }
          onLogout={
            handleLogout
          }
        />

        {/* MAIN CONTENT */}

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

            {/* AI CENTER */}

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

            {/* UNKNOWN ROUTE */}

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

          <div className="railway-track">

            <div className="moving-train">

              {/* Coach 1 */}

              <div className="train-coach">

                <div className="coach-window"></div>

                <div className="coach-name">
                  Abhishek Sharma
                </div>

                <div className="coach-wheel wheel-left"></div>

                <div className="coach-wheel wheel-right"></div>

              </div>

              <div className="train-connector"></div>

              {/* Coach 2 */}

              <div className="train-coach">

                <div className="coach-window"></div>

                <div className="coach-name">
                  Rupesh Kushwaha
                </div>

                <div className="coach-wheel wheel-left"></div>

                <div className="coach-wheel wheel-right"></div>

              </div>

              <div className="train-connector"></div>

              {/* Coach 3 */}

              <div className="train-coach">

                <div className="coach-window"></div>

                <div className="coach-name">
                  Adarsh Mishra
                </div>

                <div className="coach-wheel wheel-left"></div>

                <div className="coach-wheel wheel-right"></div>

              </div>

              <div className="train-connector"></div>

              {/* Coach 4 */}

              <div className="train-coach">

                <div className="coach-window"></div>

                <div className="coach-name">
                  Shreya Singh
                </div>

                <div className="coach-wheel wheel-left"></div>

                <div className="coach-wheel wheel-right"></div>

              </div>

              <div className="train-connector"></div>

              {/* Coach 5 */}

              <div className="train-coach">

                <div className="coach-window"></div>

                <div className="coach-name">
                  Atul Shakya
                </div>

                <div className="coach-wheel wheel-left"></div>

                <div className="coach-wheel wheel-right"></div>

              </div>

              <div className="train-connector"></div>

              {/* ENGINE / TEAM LEADER */}

              <div className="train-engine">

                <div className="engine-top"></div>

                <div className="engine-body">

                  <div className="engine-front">
                    🚆
                  </div>

                  <div className="engine-name">
                    <strong>
                      Abhishek Kumar
                    </strong>
                  </div>

                </div>

                <div className="train-wheel wheel-1"></div>

                <div className="train-wheel wheel-2"></div>

              </div>

            </div>

          </div>

        </footer>

      </div>

    </BrowserRouter>
  );
}

export default App;