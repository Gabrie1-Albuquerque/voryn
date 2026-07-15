import type { EventDropArg } from "@fullcalendar/core";
import ptBrLocale from "@fullcalendar/core/locales/pt-br";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { listAppointments, rescheduleAppointment } from "../../api/appointments";
import { listEmployees } from "../../api/employees";
import type { Appointment } from "../../api/types";
import { ApiError } from "../../lib/api";
import { AppointmentDetailsModal } from "./AppointmentDetailsModal";
import { AppointmentFormModal } from "./AppointmentFormModal";

const STATUS_COLORS: Record<Appointment["status"], string> = {
  pending: "#d97706",
  confirmed: "#16a34a",
  completed: "#6b7280",
  cancelled: "#dc2626",
  rescheduled: "#7c3aed",
};

interface VisibleRange {
  start: string;
  end: string;
}

export function AgendaPage() {
  const queryClient = useQueryClient();
  const [range, setRange] = useState<VisibleRange | null>(null);
  const [employeeFilter, setEmployeeFilter] = useState("");
  const [selectedSlot, setSelectedSlot] = useState<{ start: string } | null>(null);
  const [selectedAppointmentId, setSelectedAppointmentId] = useState<string | null>(null);

  const employeesQuery = useQuery({ queryKey: ["employees"], queryFn: listEmployees });

  const appointmentsQuery = useQuery({
    queryKey: ["appointments", range, employeeFilter],
    queryFn: () => listAppointments(range!.start, range!.end, employeeFilter || undefined),
    enabled: range !== null,
  });

  const rescheduleMutation = useMutation({
    mutationFn: ({ id, newStartsAt }: { id: string; newStartsAt: string }) => rescheduleAppointment(id, newStartsAt),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["appointments"] }),
  });

  function handleEventDrop(info: EventDropArg) {
    rescheduleMutation.mutate(
      { id: info.event.id, newStartsAt: info.event.start!.toISOString() },
      {
        onError: (err) => {
          info.revert();
          const message = err instanceof ApiError ? String(err.detail) : "Não foi possível reagendar.";
          window.alert(message);
        },
      },
    );
  }

  const events =
    appointmentsQuery.data?.map((appointment) => ({
      id: appointment.id,
      title: `${appointment.service_name} — ${appointment.client_name}`,
      start: appointment.starts_at,
      end: appointment.ends_at,
      color: STATUS_COLORS[appointment.status],
    })) ?? [];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h1>Agenda</h1>
        <select value={employeeFilter} onChange={(e) => setEmployeeFilter(e.target.value)}>
          <option value="">Todos os funcionários</option>
          {employeesQuery.data?.map((employee) => (
            <option key={employee.id} value={employee.id}>
              {employee.name}
            </option>
          ))}
        </select>
      </div>

      <div className="card">
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          headerToolbar={{ left: "prev,next today", center: "title", right: "dayGridMonth,timeGridWeek,timeGridDay" }}
          locales={[ptBrLocale]}
          locale="pt-br"
          firstDay={0}
          height="auto"
          slotMinTime="07:00:00"
          slotMaxTime="21:00:00"
          dayMaxEvents={3}
          editable
          selectable
          events={events}
          datesSet={(arg) => setRange({ start: arg.start.toISOString(), end: arg.end.toISOString() })}
          eventDrop={handleEventDrop}
          select={(info) => setSelectedSlot({ start: info.start.toISOString() })}
          eventClick={(info) => setSelectedAppointmentId(info.event.id)}
        />
      </div>

      {selectedSlot && (
        <AppointmentFormModal
          initialStart={selectedSlot.start}
          onClose={() => setSelectedSlot(null)}
          onCreated={() => {
            setSelectedSlot(null);
            queryClient.invalidateQueries({ queryKey: ["appointments"] });
          }}
        />
      )}

      {selectedAppointmentId && (
        <AppointmentDetailsModal
          appointment={appointmentsQuery.data?.find((a) => a.id === selectedAppointmentId) ?? null}
          onClose={() => setSelectedAppointmentId(null)}
          onChanged={() => queryClient.invalidateQueries({ queryKey: ["appointments"] })}
        />
      )}
    </div>
  );
}
