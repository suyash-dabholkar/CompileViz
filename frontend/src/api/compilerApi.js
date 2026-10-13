import apiClient from "./client";

export async function tokenizeSource(source) {
  const { data } = await apiClient.post("/api/compiler/tokenize", { source });
  return data;
}

export async function parseSource(source) {
  const { data } = await apiClient.post("/api/compiler/parse", { source });
  return data;
}

export async function analyzeSource(source) {
  const { data } = await apiClient.post("/api/compiler/analyze", { source });
  return data;
}

export async function generateTac(source) {
  const { data } = await apiClient.post("/api/compiler/tac", { source });
  return data;
}

export async function optimizeSource(source) {
  const { data } = await apiClient.post("/api/compiler/optimize", { source });
  return data;
}

export async function runProgram(source) {
  const { data } = await apiClient.post("/api/compiler/codegen", { source });
  return data;
}

// The teaching counterpart. `phases` picks which parts of the pipeline
// are instrumented ("lex", "run"); the rest still only report results.
export async function fetchCompilerSteps(source, phases) {
  const { data } = await apiClient.post("/api/compiler/steps", { source, phases });
  return data;
}
