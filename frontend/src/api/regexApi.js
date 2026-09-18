import apiClient, { extractErrorMessage } from "./client";

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

// Re-exported so existing imports of extractErrorMessage from this file
// (from Milestone 4's RegexPlayground.jsx) keep working unchanged, now
// that the actual implementation lives in client.js and is shared with
// grammarApi.js and any future feature's API module.
export { extractErrorMessage };
