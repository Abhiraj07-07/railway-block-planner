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
  // BODY TYPE DETECTION
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

  // Add JSON content type automatically
  // when body is a normal JavaScript object/string.
  if (
    options.body &&
    !hasContentType &&
    !isFormData &&
    !isUrlSearchParams
  ) {
    headers["Content-Type"] = "application/json";
  }

  // ----------------------------------------------------------
  // AUTHORIZATION
  // ----------------------------------------------------------

  if (token) {
    headers.Authorization = `Bearer ${token}`;
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
    // RESPONSE PARSING
    // --------------------------------------------------------

    const contentType =
      response.headers.get("content-type") || "";

    let data = null;

    if (
      contentType.includes("application/json")
    ) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    // --------------------------------------------------------
    // ERROR HANDLING
    // --------------------------------------------------------

    if (!response.ok) {
      let message =
        `Request failed (${response.status})`;

      if (typeof data === "string") {
        if (data.trim()) {
          message = data;
        }
      } else if (data?.detail) {
        message =
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail);
      } else if (data?.message) {
        message =
          typeof data.message === "string"
            ? data.message
            : JSON.stringify(data.message);
      } else if (data) {
        message = JSON.stringify(data);
      }

      // ------------------------------------------------------
      // INVALID / EXPIRED TOKEN
      // ------------------------------------------------------

      if (
        response.status === 401 ||
        response.status === 403
      ) {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
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
      Date.now() - loaderStartTime;

    const remaining =
      Math.max(
        0,
        MIN_LOADER_TIME - elapsed
      );

    if (!skipGlobalLoader) {
      setTimeout(() => {
        window.dispatchEvent(
          new Event("railway-loading-end")
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
          localStorage.getItem(USER_KEY);

        if (!savedUser) {
          return null;
        }

        return JSON.parse(savedUser);
      } catch {
        localStorage.removeItem(USER_KEY);
        return null;
      }
    });

  // ==========================================================
  // AUTH MODE
  // login | register
  // ==========================================================

  const [authMode, setAuthMode] =
    useState("login");

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
  // REGISTER FORM STATE
  // ==========================================================

  const [registerUsername, setRegisterUsername] =
    useState("");

  const [registerPassword, setRegisterPassword] =
    useState("");

  const [confirmPassword, setConfirmPassword] =
    useState("");

  const [registerLoading, setRegisterLoading] =
    useState(false);

  const [registerError, setRegisterError] =
    useState("");

  const [registerSuccess, setRegisterSuccess] =
    useState("");

  // ==========================================================
  // SWITCH TO REGISTER
  // ==========================================================

  const showRegister = () => {
    setAuthMode("register");

    setLoginError("");
    setRegisterError("");
    setRegisterSuccess("");

    if (username.trim()) {
      setRegisterUsername(
        username.trim()
      );
    }

    setPassword("");
  };

  // ==========================================================
  // SWITCH TO LOGIN
  // ==========================================================

  const showLogin = () => {
    setAuthMode("login");

    setLoginError("");
    setRegisterError("");
    setRegisterSuccess("");

    setRegisterPassword("");
    setConfirmPassword("");

    // Automatically put registered username
    // into login field.
    if (registerUsername.trim()) {
      setUsername(
        registerUsername.trim()
      );
    }
  };

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
            typeof data.detail === "string"
              ? data.detail
              : JSON.stringify(
                  data.detail
                );
        } else if (
          data?.message
        ) {
          message =
            typeof data.message === "string"
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
      // ALWAYS START FROM HOME
      // ------------------------------------------------------

      window.history.replaceState(
        null,
        "",
        "/home"
      );

      // ------------------------------------------------------
      // UPDATE STATE
      // ------------------------------------------------------

      setCurrentUser(user);

      setUsername("");
      setPassword("");

      setLoginError("");

      setAuthMode("login");
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
  // REGISTER
  // ==========================================================

  const handleRegister = async (event) => {
    event.preventDefault();

    setRegisterError("");
    setRegisterSuccess("");

    const cleanUsername =
      registerUsername.trim();

    // --------------------------------------------------------
    // VALIDATE USERNAME
    // --------------------------------------------------------

    if (!cleanUsername) {
      setRegisterError(
        "Please enter a username."
      );

      return;
    }

    if (cleanUsername.length < 3) {
      setRegisterError(
        "Username must be at least 3 characters long."
      );

      return;
    }

    // --------------------------------------------------------
    // VALIDATE PASSWORD
    // --------------------------------------------------------

    if (!registerPassword) {
      setRegisterError(
        "Please enter a password."
      );

      return;
    }

    if (registerPassword.length < 4) {
      setRegisterError(
        "Password must be at least 4 characters long."
      );

      return;
    }

    // --------------------------------------------------------
    // CONFIRM PASSWORD
    // --------------------------------------------------------

    if (
      registerPassword !==
      confirmPassword
    ) {
      setRegisterError(
        "Passwords do not match."
      );

      return;
    }

    setRegisterLoading(true);

    try {
      // ------------------------------------------------------
      // POST /auth/register
      // ------------------------------------------------------

      const response =
        await fetch(
          `${API_BASE}/auth/register`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",

              Accept:
                "application/json",
            },

            body: JSON.stringify({
              username:
                cleanUsername,

              password:
                registerPassword,
            }),
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
      // REGISTRATION ERROR
      // ------------------------------------------------------

      if (!response.ok) {
        let message =
          "Registration failed.";

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
            typeof data.detail === "string"
              ? data.detail
              : JSON.stringify(
                  data.detail
                );
        } else if (
          data?.message
        ) {
          message =
            typeof data.message === "string"
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
      // SUCCESS
      // ------------------------------------------------------

      setRegisterSuccess(
        data?.message ||
        "Account created successfully."
      );

      // Put registered username
      // into login field.
      setUsername(
        cleanUsername
      );

      // Clear registration password fields.
      setRegisterPassword("");
      setConfirmPassword("");

      // ------------------------------------------------------
      // RETURN TO LOGIN
      // ------------------------------------------------------

      setTimeout(() => {
        setAuthMode("login");
        setRegisterSuccess("");
      }, 1200);
    } catch (error) {
      console.error(
        "Registration error:",
        error
      );

      setRegisterError(
        error?.message ||
        "Unable to register. Please try again."
      );
    } finally {
      setRegisterLoading(false);
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

    setRegisterUsername("");
    setRegisterPassword("");
    setConfirmPassword("");

    setRegisterError("");
    setRegisterSuccess("");

    setAuthMode("login");

    // --------------------------------------------------------
    // RESET ROUTE
    // --------------------------------------------------------

    window.history.replaceState(
      null,
      "",
      "/home"
    );
  };

  // ==========================================================
  // AUTH SCREEN
  // ==========================================================

  if (!currentUser) {
    return (
      <div className="login-page">

        <div className="login-card">

          {/* ==================================================
              BRAND
          ================================================== */}

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

          {/* ==================================================
              LOGIN SCREEN
          ================================================== */}

          {authMode === "login" && (
            <>
              <h1>
                RailYojana AI
              </h1>

              <p className="login-subtitle">
                Admin Control Panel
              </p>

              {loginError && (
                <div className="login-error">
                  {loginError}
                </div>
              )}

              <form
                onSubmit={
                  handleLogin
                }
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

              {/* REGISTER LINK */}

              <div className="auth-switch">

                <span>
                  Don't have an account?
                </span>

                <button
                  type="button"
                  className="auth-switch-button"
                  onClick={
                    showRegister
                  }
                  disabled={
                    loginLoading
                  }
                >
                  Create Account
                </button>

              </div>
            </>
          )}

          {/* ==================================================
              REGISTER SCREEN
          ================================================== */}

          {authMode === "register" && (
            <>
              <h1>
                Create Account
              </h1>

              <p className="login-subtitle">
                Register New Admin User
              </p>

              {registerError && (
                <div className="login-error">
                  {registerError}
                </div>
              )}

              {registerSuccess && (
                <div
                  className="login-success"
                  style={{
                    marginBottom:
                      "16px",
                    padding:
                      "12px 14px",
                    borderRadius:
                      "10px",
                    background:
                      "rgba(34, 197, 94, 0.12)",
                    border:
                      "1px solid rgba(34, 197, 94, 0.35)",
                    color:
                      "#86efac",
                  }}
                >
                  ✅{" "}
                  {registerSuccess}
                  <br />
                  <small>
                    Returning to login...
                  </small>
                </div>
              )}

              <form
                onSubmit={
                  handleRegister
                }
                className="login-form"
              >

                {/* USERNAME */}

                <div className="login-field">

                  <label htmlFor="register-username">
                    Username
                  </label>

                  <input
                    id="register-username"
                    type="text"
                    value={
                      registerUsername
                    }
                    onChange={(event) =>
                      setRegisterUsername(
                        event.target.value
                      )
                    }
                    placeholder="Enter username"
                    autoComplete="username"
                    disabled={
                      registerLoading
                    }
                  />

                </div>

                {/* PASSWORD */}

                <div className="login-field">

                  <label htmlFor="register-password">
                    Password
                  </label>

                  <input
                    id="register-password"
                    type="password"
                    value={
                      registerPassword
                    }
                    onChange={(event) =>
                      setRegisterPassword(
                        event.target.value
                      )
                    }
                    placeholder="Enter password"
                    autoComplete="new-password"
                    disabled={
                      registerLoading
                    }
                  />

                </div>

                {/* CONFIRM PASSWORD */}

                <div className="login-field">

                  <label htmlFor="confirm-password">
                    Confirm Password
                  </label>

                  <input
                    id="confirm-password"
                    type="password"
                    value={
                      confirmPassword
                    }
                    onChange={(event) =>
                      setConfirmPassword(
                        event.target.value
                      )
                    }
                    placeholder="Re-enter password"
                    autoComplete="new-password"
                    disabled={
                      registerLoading
                    }
                  />

                </div>

                {/* REGISTER BUTTON */}

                <button
                  type="submit"
                  className="login-button"
                  disabled={
                    registerLoading
                  }
                >
                  {registerLoading
                    ? "Creating Account..."
                    : "Create Account"}
                </button>

              </form>

              {/* BACK TO LOGIN */}

              <div className="auth-switch">

                <span>
                  Already have an account?
                </span>

                <button
                  type="button"
                  className="auth-switch-button"
                  onClick={
                    showLogin
                  }
                  disabled={
                    registerLoading
                  }
                >
                  Back to Login
                </button>

              </div>
            </>
          )}

          {/* ==================================================
              FOOTER
          ================================================== */}

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

              {/* COACH 1 */}

              <div className="train-coach">

                <div className="coach-window"></div>

                <div className="coach-name">
                  Abhishek Sharma
                </div>

                <div className="coach-wheel wheel-left"></div>

                <div className="coach-wheel wheel-right"></div>

              </div>

              <div className="train-connector"></div>

              {/* COACH 2 */}

              <div className="train-coach">

                <div className="coach-window"></div>

                <div className="coach-name">
                  Rupesh Kushwaha
                </div>

                <div className="coach-wheel wheel-left"></div>

                <div className="coach-wheel wheel-right"></div>

              </div>

              <div className="train-connector"></div>

              {/* COACH 3 */}

              <div className="train-coach">

                <div className="coach-window"></div>

                <div className="coach-name">
                  Adarsh Mishra
                </div>

                <div className="coach-wheel wheel-left"></div>

                <div className="coach-wheel wheel-right"></div>

              </div>

              <div className="train-connector"></div>

              {/* COACH 4 */}

              <div className="train-coach">

                <div className="coach-window"></div>

                <div className="coach-name">
                  Shreya Singh
                </div>

                <div className="coach-wheel wheel-left"></div>

                <div className="coach-wheel wheel-right"></div>

              </div>

              <div className="train-connector"></div>

              {/* COACH 5 */}

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