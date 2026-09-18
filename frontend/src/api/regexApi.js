import apiClient from "./client";

// Thin wrappers around the Milestone 4 backend routes (app/api/regex_routes.py).
// Each one returns response.data directly and lets errors (including the
// backend's 400 for an invalid regex) propagate to the caller, so the page
// component decides how to display them.

export async function buildDirectDfa(pattern) {
  const { data } = await apiClient.post("/api/regex/direct", { pattern });
  return data;
}

export async function buildIndirectDfa(pattern) {
  const { data } = await apiClient.post("/api/regex/indirect", { pattern });
  return data;
}

export async function buildThompsonNfa(pattern) {
  const { data } = await apiClient.post("/api/regex/thompson", { pattern });
  return data;
}

export async function matchPattern(pattern, text, method = "direct") {
  const { data } = await apiClient.post("/api/regex/match", {
    pattern,
    text,
    method,
  });
  return data;
}

export async function compareMethods(pattern, runs = 10) {
  const { data } = await apiClient.post("/api/regex/compare", {
    pattern,
    runs,
  });
  return data;
}

/**
 * The backend returns FastAPI/Pydantic validation errors as
 * { detail: [...] } for a 422, or { detail: "message" } for a 400
 * raised explicitly (e.g. RegexSyntaxError). This normalizes both into
 * a single readable string for the UI.
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
