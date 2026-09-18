import apiClient from "./client";

export async function analyzeGrammar(grammar) {
  const { data } = await apiClient.post("/api/grammar/analyze", { grammar });
  return data;
}
