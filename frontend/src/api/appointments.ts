import { apiRequest } from "../lib/api";
import type { Appointment } from "./types";

export function listAppointments(start: string, end: string, employeeId?: string): Promise<Appointment[]> {
  const params = new URLSearchParams({ start, end });
  if (employeeId) params.set("employee_id", employeeId);
  return apiRequest(`/appointments?${params.toString()}`);
}

export function createAppointment(data: {
  client_id: string;
  employee_id: string;
  service_id: string;
  room_id?: string;
  starts_at: string;
  notes?: string;
}): Promise<Appointment> {
  return apiRequest("/appointments", { method: "POST", body: data });
}

export function rescheduleAppointment(id: string, newStartsAt: string): Promise<Appointment> {
  return apiRequest(`/appointments/${id}/reschedule`, { method: "POST", body: { new_starts_at: newStartsAt } });
}

export function confirmAppointment(id: string): Promise<Appointment> {
  return apiRequest(`/appointments/${id}/confirm`, { method: "POST" });
}

export function cancelAppointment(id: string): Promise<Appointment> {
  return apiRequest(`/appointments/${id}/cancel`, { method: "POST" });
}

export function completeAppointment(id: string): Promise<Appointment> {
  return apiRequest(`/appointments/${id}/complete`, { method: "POST" });
}
