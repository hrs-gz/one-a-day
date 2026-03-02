import axios from "axios";

/**
 * Shared axios instance. All API calls go through this client so that
 * base URL and headers are configured in one place.
 *
 * The Vite dev server proxies /api → http://localhost:8000, so in development
 * the base URL is just "/" (relative). In production the app is served from
 * the same origin as the API.
 */
export const client = axios.create({
  baseURL: "/",
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor — surface the backend { detail: "..." } message
// as the error message so components can display it directly.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message: string =
      error.response?.data?.detail ?? error.message ?? "Unknown error";
    return Promise.reject(new Error(message));
  }
);
