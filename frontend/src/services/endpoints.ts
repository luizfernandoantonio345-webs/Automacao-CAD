import { API_BASE_URL } from "./api";

export const LICENSING_BASE_URL =
  process.env.REACT_APP_LICENSING_URL ||
  process.env.REACT_APP_API_URL ||
  API_BASE_URL;
