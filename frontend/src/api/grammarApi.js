import apiClient from "./client";

export async function analyzeGrammar(grammar) {
  const { data } = await apiClient.post("/api/grammar/analyze", { grammar });
  return data;
}

// The teaching counterpart: each fixed-point sweep and each row of the
// LL(1) table, rather than just the converged sets.
export async function fetchGrammarSteps(grammar) {
  const { data } = await apiClient.post("/api/grammar/steps", { grammar });
  return data;
}
