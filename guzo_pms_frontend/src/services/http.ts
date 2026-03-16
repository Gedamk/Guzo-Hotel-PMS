import axios from "axios";
import { API_BASE_URL } from "../config/pms";

export const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail =
      (error.response?.data as { detail?: string } | undefined)?.detail ||
      error.message;
    return detail || "Request failed.";
  }
  if (error instanceof Error) return error.message;
  return "Unexpected error.";
}
