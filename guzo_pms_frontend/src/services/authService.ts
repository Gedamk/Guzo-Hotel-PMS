import { http } from "./http";
import type { UserSession } from "../types/pms";

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  user: UserSession;
};

export async function loginPmsUser(payload: {
  email: string;
  password: string;
  property_code: string;
}): Promise<UserSession> {
  const { data } = await http.post<LoginResponse>("/auth/login", payload);
  return {
    ...data.user,
    access_token: data.access_token,
    expires_at: data.expires_at,
  };
}

export async function fetchCurrentUser(): Promise<UserSession> {
  const { data } = await http.get<UserSession>("/auth/me");
  return data;
}

export async function logoutPmsUser(): Promise<void> {
  await http.post("/auth/logout");
}
