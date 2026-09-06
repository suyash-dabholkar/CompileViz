import axios from "axios";

// In local dev this points at the FastAPI server started with `uvicorn`.
// Once the backend is deployed (Milestone 16), set VITE_API_BASE_URL in
// a .env file so the same code works against the live URL too.
const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const apiClient = axios.create({ baseURL });

export default apiClient;
