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
  mercadopago_access_token?: string;
  mercadopago_webhook_secret?: string;
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

export function testMercadoPagoToken(accessToken: string): Promise<{ success: boolean; message: string }> {
  return apiRequest("/companies/me/test-mercadopago", { method: "POST", body: { access_token: accessToken } });
}

export function connectWhatsApp(): Promise<{ state: string; qr_base64: string | null }> {
  return apiRequest("/companies/me/whatsapp/connect", { method: "POST" });
}

export function whatsAppStatus(): Promise<{ state: string }> {
  return apiRequest("/companies/me/whatsapp/status");
}
