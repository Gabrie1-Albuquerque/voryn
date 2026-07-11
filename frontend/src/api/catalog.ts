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

export function listRooms(): Promise<Room[]> {
  return apiRequest("/rooms");
}

export function createRoom(data: { name: string }): Promise<Room> {
  return apiRequest("/rooms", { method: "POST", body: data });
}
