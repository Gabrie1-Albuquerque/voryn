import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { cancelAppointment, completeAppointment, confirmAppointment } from "../../api/appointments";
import type { Appointment } from "../../api/types";
import { ApiError } from "../../lib/api";
import { Modal } from "../../components/Modal";

const STATUS_LABELS: Record<Appointment["status"], string> = {
  pending: "Pendente",
  confirmed: "Confirmado",
  completed: "Concluído",
  cancelled: "Cancelado",
  rescheduled: "Reagendado",
};

interface Props {
  appointment: Appointment | null;
  onClose: () => void;
  onChanged: () => void;
}

export function AppointmentDetailsModal({ appointment, onClose, onChanged }: Props) {
  const [error, setError] = useState<string | null>(null);

  const confirmMutation = useMutation({
    mutationFn: confirmAppointment,
    onSuccess: () => {
      onChanged();
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Ação falhou."),
  });
  const cancelMutation = useMutation({
    mutationFn: cancelAppointment,
    onSuccess: () => {
      onChanged();
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Ação falhou."),
  });
  const completeMutation = useMutation({
    mutationFn: completeAppointment,
    onSuccess: () => {
      onChanged();
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Ação falhou."),
  });

  if (!appointment) return null;

  const isPending = confirmMutation.isPending || cancelMutation.isPending || completeMutation.isPending;

  return (
    <Modal title="Detalhes do agendamento" onClose={onClose}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <p>
          <strong>Cliente:</strong> {appointment.client_name}
        </p>
        <p>
          <strong>Funcionário:</strong> {appointment.employee_name}
        </p>
        <p>
          <strong>Serviço:</strong> {appointment.service_name}
        </p>
        <p>
          <strong>Início:</strong> {new Date(appointment.starts_at).toLocaleString("pt-BR")}
        </p>
        <p>
          <strong>Status:</strong> {STATUS_LABELS[appointment.status]}
        </p>
        {error && <p className="error-text">{error}</p>}
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          {appointment.status === "pending" && (
            <button className="primary" disabled={isPending} onClick={() => confirmMutation.mutate(appointment.id)}>
              Confirmar
            </button>
          )}
          {appointment.status === "confirmed" && (
            <button disabled={isPending} onClick={() => completeMutation.mutate(appointment.id)}>
              Concluir
            </button>
          )}
          {(appointment.status === "pending" || appointment.status === "confirmed") && (
            <button disabled={isPending} onClick={() => cancelMutation.mutate(appointment.id)}>
              Cancelar
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}
