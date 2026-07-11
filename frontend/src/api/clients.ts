import { apiRequest } from "../lib/api";
import type { Client, ClientNote, ClientNoteType } from "./types";

export function listClients(): Promise<Client[]> {
  return apiRequest("/clients");
}

export function createClient(data: { name: string; phone: string; email?: string }): Promise<Client> {
  return apiRequest("/clients", { method: "POST", body: data });
}

export function updateClient(id: string, data: Partial<Pick<Client, "name" | "phone" | "email" | "is_active">>): Promise<Client> {
  return apiRequest(`/clients/${id}`, { method: "PATCH", body: data });
}

export function listClientNotes(clientId: string): Promise<ClientNote[]> {
  return apiRequest(`/clients/${clientId}/notes`);
}

export function addClientNote(
  clientId: string,
  data: { note_type: ClientNoteType; body: string },
): Promise<ClientNote> {
  return apiRequest(`/clients/${clientId}/notes`, { method: "POST", body: data });
}
