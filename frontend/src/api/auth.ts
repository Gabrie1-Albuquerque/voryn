import { apiRequest } from "../lib/api";
import type { CurrentUser } from "./types";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export function login(email: string, password: string): Promise<TokenPair> {
  return apiRequest<TokenPair>("/auth/login", {
    method: "POST",
    body: { email, password },
    authenticated: false,
  });
}

export function logout(refreshToken: string): Promise<void> {
  return apiRequest<void>("/auth/logout", {
    method: "POST",
    body: { refresh_token: refreshToken },
  });
}

export function fetchCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/auth/me");
}

export function forgotPassword(email: string): Promise<{ message: string }> {
  return apiRequest("/auth/forgot-password", { method: "POST", body: { email }, authenticated: false });
}

export function resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  return apiRequest("/auth/reset-password", {
    method: "POST",
    body: { token, new_password: newPassword },
    authenticated: false,
  });
}
