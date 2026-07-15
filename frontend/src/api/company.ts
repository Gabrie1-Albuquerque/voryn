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
}): Promise<Company> {
  return apiRequest("/companies/me", { method: "PATCH", body: data });
}
