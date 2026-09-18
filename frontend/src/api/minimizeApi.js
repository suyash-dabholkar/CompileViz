import apiClient from "./client";

export async function minimizeDfa(pattern, method = "indirect") {
  const { data } = await apiClient.post("/api/regex/minimize", { pattern, method });
  return data;
}
