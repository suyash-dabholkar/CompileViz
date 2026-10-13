import apiClient from "./client";

export async function minimizeDfa(pattern, method = "indirect") {
  const { data } = await apiClient.post("/api/regex/minimize", { pattern, method });
  return data;
}

// The teaching counterpart: the same refinement, but one group at a time,
// with the signature table that says why each group split or survived.
export async function fetchMinimizeSteps(pattern, method = "indirect") {
  const { data } = await apiClient.post("/api/regex/minimize/steps", {
    pattern,
    method,
  });
  return data;
}
