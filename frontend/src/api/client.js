import axios from "axios";

// In local dev this points at the FastAPI server started with `uvicorn`.
// Once the backend is deployed (Milestone 16), set VITE_API_BASE_URL in
// a .env file so the same code works against the live URL too.
const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const apiClient = axios.create({ baseURL });

export default apiClient;

/**
 * The backend returns FastAPI/Pydantic validation errors as
 * { detail: [...] } for a 422, or { detail: "message" } for a 400
 * raised explicitly (RegexSyntaxError, GrammarSyntaxError, ...). This
 * normalizes both into a single readable string for the UI. Shared
 * across every page's API module rather than duplicated per feature.
 */
export function extractErrorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (!detail) return error?.message || "Something went wrong";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  return JSON.stringify(detail);
}
