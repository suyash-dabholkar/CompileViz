import apiClient from "./client";

export async function tokenizeSource(source) {
  const { data } = await apiClient.post("/api/compiler/tokenize", { source });
  return data;
}
