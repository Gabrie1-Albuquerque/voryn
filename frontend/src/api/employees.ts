import { apiRequest } from "../lib/api";
import type { AvailabilityWindow, Employee } from "./types";

export function listEmployees(): Promise<Employee[]> {
  return apiRequest("/employees");
}

export function createEmployee(data: { name: string; service_ids?: string[] }): Promise<Employee> {
  return apiRequest("/employees", { method: "POST", body: data });
}

export function updateEmployee(id: string, data: { name?: string; is_active?: boolean }): Promise<Employee> {
  return apiRequest(`/employees/${id}`, { method: "PATCH", body: data });
}

export function deactivateEmployee(id: string): Promise<void> {
  return apiRequest(`/employees/${id}`, { method: "DELETE" });
}

export function replaceEmployeeServices(id: string, serviceIds: string[]): Promise<Employee> {
  return apiRequest(`/employees/${id}/services`, { method: "PUT", body: { service_ids: serviceIds } });
}

export function replaceEmployeeAvailability(id: string, windows: AvailabilityWindow[]): Promise<Employee> {
  return apiRequest(`/employees/${id}/availability`, { method: "PUT", body: { windows } });
}
