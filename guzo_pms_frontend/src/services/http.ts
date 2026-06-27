import axios from "axios";
import { API_BASE_URL, DEV_AUTH_FALLBACK } from "../config/pms";
import { currentPmsUserEmail } from "../auth/permissions";
import { loadStoredSession } from "../auth/sessionStorage";

export const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

http.interceptors.request.use((config) => {
  const params = config.params as Record<string, unknown> | undefined;
  const body = config.data as Record<string, unknown> | undefined;
  const scopeValue = params?.property_code ?? params?.property ?? body?.property_code ?? body?.property;
  const declaresPropertyScope = Boolean(
    params && ("property_code" in params || "property" in params) ||
    body && typeof body === "object" && ("property_code" in body || "property" in body)
  );
  if (declaresPropertyScope && (typeof scopeValue !== "string" || !scopeValue.trim())) {
    return Promise.reject(new Error("Select a property before loading or changing PMS data."));
  }
  const session = loadStoredSession();
  if (session?.access_token) {
    config.headers.set("Authorization", `Bearer ${session.access_token}`);
  } else if (DEV_AUTH_FALLBACK) {
    config.headers.set("X-PMS-User-Email", currentPmsUserEmail());
  }
  return config;
});

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.code === "ERR_NETWORK" || error.message === "Network Error") {
      return "Network Error: PMS backend is unreachable or blocked by CORS. Confirm the backend is running and the frontend API base URL points to the same port.";
    }
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "message" in detail) {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === "string") return message;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg?: unknown }).msg);
          }
          return String(item);
        })
        .join("; ");
    }
    if (detail) return JSON.stringify(detail);
    const fallback = error.message;
    return fallback || "Request failed.";
  }
  if (error instanceof Error) return error.message;
  return "Unexpected error.";
}

export function isBackendUnreachable(error: unknown): boolean {
  return axios.isAxiosError(error) && (
    !error.response ||
    error.code === "ERR_NETWORK" ||
    error.code === "ECONNABORTED" ||
    error.message === "Network Error"
  );
}
