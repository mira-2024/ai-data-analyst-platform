/**
 * Central Axios instance.
 * All API calls flow through here — base URL, auth headers, error normalisation.
 */
import axios, { AxiosError, type AxiosRequestConfig } from "axios";

export const api = axios.create({
  baseURL: "/api/v1",
  timeout: 60_000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Request interceptor — add auth token when present ─────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("dataflow_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor — normalise errors ────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err: AxiosError<{ error: string; detail: string; meta?: Record<string, unknown> }>) => {
    if (err.response?.data) {
      const { detail, error } = err.response.data;
      const message = detail || error || "An unexpected error occurred.";
      return Promise.reject(new ApiError(message, err.response.status, err.response.data));
    }
    if (err.code === "ECONNABORTED") {
      return Promise.reject(new ApiError("Request timed out. Please try again.", 408));
    }
    return Promise.reject(new ApiError("Network error. Please check your connection.", 0));
  }
);

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const res = await api.get<T>(url, config);
  return res.data;
}

export async function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const res = await api.post<T>(url, data, config);
  return res.data;
}

export async function patch<T>(url: string, data?: unknown): Promise<T> {
  const res = await api.patch<T>(url, data);
  return res.data;
}

export async function del(url: string): Promise<void> {
  await api.delete(url);
}
