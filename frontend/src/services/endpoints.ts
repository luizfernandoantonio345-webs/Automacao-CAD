const runtimeOrigin =
  typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:3000";

export const LICENSING_BASE_URL =
  process.env.REACT_APP_LICENSING_URL ||
  process.env.REACT_APP_API_URL ||
  runtimeOrigin.replace(/:3000$/, ":8000");
