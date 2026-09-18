import apiClient from "./client";

export async function tokenizeSource(source) {
  const { data } = await apiClient.post("/api/compiler/tokenize", { source });
  return data;
}

export async function parseSource(source) {
  const { data } = await apiClient.post("/api/compiler/parse", { source });
  return data;
}
