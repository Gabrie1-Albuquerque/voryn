import { apiRequest } from "../lib/api";
import type { Company } from "./types";

export function getMyCompany(): Promise<Company> {
  return apiRequest("/companies/me");
}

export function updateMyCompany(data: {
  name?: string;
  document?: string;
  timezone?: string;
  auto_confirm_public_bookings?: boolean;
  reminder_first_hours?: number;
  reminder_second_hours?: number;
  smtp_host?: string;
  smtp_port?: number;
  smtp_username?: string;
  smtp_password?: string;
  smtp_from_email?: string;
}): Promise<Company> {
  return apiRequest("/companies/me", { method: "PATCH", body: data });
}

export interface SmtpTestData {
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password: string;
  smtp_from_email: string;
}

export function testSmtpConnection(data: SmtpTestData): Promise<{ success: boolean; message: string }> {
  return apiRequest("/companies/me/test-smtp", { method: "POST", body: data });
}
