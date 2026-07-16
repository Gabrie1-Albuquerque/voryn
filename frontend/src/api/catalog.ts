import { apiRequest } from "../lib/api";
import type { DepositType, Room, Service } from "./types";

export function listServices(): Promise<Service[]> {
  return apiRequest("/services");
}

export function createService(data: {
  name: string;
  duration_minutes: number;
  price: string;
  requires_room?: boolean;
  deposit_required?: boolean;
  deposit_type?: DepositType;
  deposit_value?: string;
}): Promise<Service> {
  return apiRequest("/services", { method: "POST", body: data });
}

export function updateService(
  id: string,
  data: {
    name?: string;
    duration_minutes?: number;
    price?: string;
    requires_room?: boolean;
    is_active?: boolean;
    deposit_required?: boolean;
    deposit_type?: DepositType | null;
    deposit_value?: string | null;
  },
): Promise<Service> {
  return apiRequest(`/services/${id}`, { method: "PATCH", body: data });
}

export function deactivateService(id: string): Promise<void> {
  return apiRequest(`/services/${id}`, { method: "DELETE" });
}

export function listRooms(): Promise<Room[]> {
  return apiRequest("/rooms");
}

export function createRoom(data: { name: string }): Promise<Room> {
  return apiRequest("/rooms", { method: "POST", body: data });
}

export function updateRoom(id: string, data: { name?: string; is_active?: boolean }): Promise<Room> {
  return apiRequest(`/rooms/${id}`, { method: "PATCH", body: data });
}

export function deactivateRoom(id: string): Promise<void> {
  return apiRequest(`/rooms/${id}`, { method: "DELETE" });
}
