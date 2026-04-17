/**
 * k6/stress.js — EngCAD Stress Test
 * Run: k6 run k6/stress.js
 *
 * Stages:
 *   0→1 min:  ramp to 100 VUs (warm-up)
 *   1→3 min:  ramp to 500 VUs (stress)
 *   3→5 min:  hold 500 VUs (steady load)
 *   5→6 min:  ramp down to 0
 *
 * Thresholds: p95 < 500ms, error rate < 1%
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ─── Config ───────────────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || "https://api.engcad.com.br";
const TEST_TOKEN = __ENV.TEST_TOKEN || ""; // Bearer token for authenticated routes

// ─── Custom metrics ───────────────────────────────────────────
const errorRate = new Rate("error_rate");
const loginTrend = new Trend("login_duration_ms");
const projectsTrend = new Trend("projects_duration_ms");
const bridgeTrend = new Trend("bridge_pending_duration_ms");

// ─── Options ──────────────────────────────────────────────────
export const options = {
  stages: [
    { duration: "1m", target: 100 },
    { duration: "2m", target: 500 },
    { duration: "2m", target: 500 },
    { duration: "1m", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<500"],
    error_rate: ["rate<0.01"],
    login_duration_ms: ["p(95)<600"],
    projects_duration_ms: ["p(95)<400"],
    bridge_pending_duration_ms: ["p(95)<400"],
  },
};

// ─── Helpers ──────────────────────────────────────────────────
const authHeaders = {
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${TEST_TOKEN}`,
  },
};

function randomItem(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

// ─── Scenarios ────────────────────────────────────────────────

/** Scenario 1: POST /api/auth/login */
function scenarioLogin() {
  const payload = JSON.stringify({
    username: `user_${Math.floor(Math.random() * 1000)}@test.com`,
    password: "TestPassword123!",
  });
  const res = http.post(`${BASE_URL}/api/auth/login`, payload, {
    headers: { "Content-Type": "application/json" },
    timeout: "10s",
  });
  loginTrend.add(res.timings.duration);
  const ok = check(res, {
    "login status 200 or 401": (r) => r.status === 200 || r.status === 401,
    "login responded in <600ms": (r) => r.timings.duration < 600,
  });
  errorRate.add(!ok);
}

/** Scenario 2: GET /api/projects */
function scenarioProjects() {
  if (!TEST_TOKEN) return;
  const res = http.get(`${BASE_URL}/api/projects`, authHeaders);
  projectsTrend.add(res.timings.duration);
  const ok = check(res, {
    "projects status 200": (r) => r.status === 200,
    "projects responded in <400ms": (r) => r.timings.duration < 400,
  });
  errorRate.add(!ok);
}

/** Scenario 3: GET /api/bridge/pending */
function scenarioBridgePending() {
  if (!TEST_TOKEN) return;
  const res = http.get(`${BASE_URL}/api/bridge/pending`, authHeaders);
  bridgeTrend.add(res.timings.duration);
  const ok = check(res, {
    "bridge status 200": (r) => r.status === 200,
    "bridge responded in <400ms": (r) => r.timings.duration < 400,
  });
  errorRate.add(!ok);
}

/** Scenario 4: GET /health */
function scenarioHealth() {
  const res = http.get(`${BASE_URL}/health`, { timeout: "5s" });
  const ok = check(res, {
    "health status 200": (r) => r.status === 200,
  });
  errorRate.add(!ok);
}

// ─── Default function (VU loop) ───────────────────────────────
export default function () {
  const scenario = randomItem([
    scenarioLogin,
    scenarioProjects,
    scenarioBridgePending,
    scenarioHealth,
  ]);
  scenario();
  sleep(randomItem([0.5, 1, 1.5, 2]));
}
