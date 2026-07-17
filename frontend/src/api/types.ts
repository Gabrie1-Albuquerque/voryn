export type UserRole = "admin" | "manager" | "employee";

export interface CurrentUser {
  id: string;
  tenant_id: string;
  email: string;
  role: UserRole;
}

export interface Company {
  id: string;
  slug: string;
  name: string;
  document: string | null;
  timezone: string;
  plan_tier: string;
  auto_confirm_public_bookings: boolean;
  reminder_first_hours: number;
  reminder_second_hours: number;
  // Password/ciphertext never included -- smtp_configured is the only
  // signal the UI gets for "is something connected".
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_username: string | null;
  smtp_from_email: string | null;
  smtp_configured: boolean;
  mercadopago_configured: boolean;
}

export interface AvailabilityWindow {
  weekday: number;
  start_time: string;
  end_time: string;
}

export interface Employee {
  id: string;
  name: string;
  is_active: boolean;
  service_ids: string[];
  availability: AvailabilityWindow[];
}

export interface Client {
  id: string;
  name: string;
  phone: string;
  email: string | null;
  document: string | null;
  is_active: boolean;
}

export type ClientNoteType = "clinical" | "preference" | "alert" | "general";

export interface ClientNote {
  id: string;
  note_type: ClientNoteType;
  body: string;
  author_user_id: string | null;
  appointment_id: string | null;
  created_at: string;
}

export type DepositType = "fixed_amount" | "percentage";

export interface Service {
  id: string;
  name: string;
  duration_minutes: number;
  price: string;
  requires_room: boolean;
  is_active: boolean;
  deposit_required: boolean;
  deposit_type: DepositType | null;
  deposit_value: string | null;
}

export interface Room {
  id: string;
  name: string;
  is_active: boolean;
}

export type AppointmentStatus = "pending" | "confirmed" | "completed" | "cancelled" | "rescheduled";
export type AppointmentSource = "staff" | "public_booking";

export interface Appointment {
  id: string;
  client_id: string;
  client_name: string;
  employee_id: string;
  employee_name: string;
  service_id: string;
  service_name: string;
  room_id: string | null;
  room_name: string | null;
  starts_at: string;
  ends_at: string;
  status: AppointmentStatus;
  source: AppointmentSource;
  notes: string | null;
  is_no_show: boolean;
}

export type PaymentStatus = "pending" | "approved" | "rejected" | "refunded";

export interface PublicCompany {
  name: string;
  slug: string;
  timezone: string;
}

export interface PublicService {
  id: string;
  name: string;
  duration_minutes: number;
  price: string;
  deposit_required: boolean;
  deposit_type: DepositType | null;
  deposit_value: string | null;
}

export interface PublicEmployee {
  id: string;
  name: string;
  service_ids: string[];
}

export interface AvailabilityResponse {
  slots: string[];
}

export interface PublicBooking {
  id: string;
  status: AppointmentStatus;
  starts_at: string;
  ends_at: string;
  service_name: string;
  employee_name: string;
  deposit_required: boolean;
  deposit_amount: string | null;
  payment_status: PaymentStatus | null;
  pix_qr_code: string | null;
  checkout_url: string | null;
}

export interface TopServiceEntry {
  name: string;
  completed_count: number;
  revenue: string;
}

export interface DashboardSummary {
  period_start: string;
  period_end: string;
  projected_revenue: string;
  realized_revenue: string;
  no_show_rate: number | null;
  occupancy_rate: number | null;
  top_services: TopServiceEntry[];
}
