import { publicApiRequest } from "../lib/publicApi";
import type { AvailabilityResponse, PublicBooking, PublicCompany, PublicEmployee, PublicService } from "./types";

export function getPublicCompany(slug: string): Promise<PublicCompany> {
  return publicApiRequest(`/${slug}`);
}

export function listPublicServices(slug: string): Promise<PublicService[]> {
  return publicApiRequest(`/${slug}/services`);
}

export function listPublicEmployees(slug: string): Promise<PublicEmployee[]> {
  return publicApiRequest(`/${slug}/employees`);
}

export function getPublicAvailability(
  slug: string,
  employeeId: string,
  serviceId: string,
  date: string
): Promise<AvailabilityResponse> {
  const params = new URLSearchParams({ employee_id: employeeId, service_id: serviceId, date });
  return publicApiRequest(`/${slug}/availability?${params.toString()}`);
}

export function createPublicBooking(
  slug: string,
  data: {
    service_id: string;
    employee_id: string;
    starts_at: string;
    client_name: string;
    client_phone: string;
    client_email?: string;
    notes?: string;
  }
): Promise<PublicBooking> {
  return publicApiRequest(`/${slug}/bookings`, { method: "POST", body: data });
}

export function getPublicBookingStatus(slug: string, appointmentId: string): Promise<PublicBooking> {
  return publicApiRequest(`/${slug}/bookings/${appointmentId}`);
}
