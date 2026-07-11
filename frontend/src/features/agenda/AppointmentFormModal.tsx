import { useMutation, useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { createAppointment } from "../../api/appointments";
import { listClients } from "../../api/clients";
import { listEmployees } from "../../api/employees";
import { listServices } from "../../api/catalog";
import { ApiError } from "../../lib/api";
import { Modal } from "../../components/Modal";

interface Props {
  initialStart: string;
  onClose: () => void;
  onCreated: () => void;
}

function toLocalInputValue(iso: string): string {
  const date = new Date(iso);
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 16);
}

export function AppointmentFormModal({ initialStart, onClose, onCreated }: Props) {
  const employeesQuery = useQuery({ queryKey: ["employees"], queryFn: listEmployees });
  const clientsQuery = useQuery({ queryKey: ["clients"], queryFn: listClients });
  const servicesQuery = useQuery({ queryKey: ["services"], queryFn: listServices });

  const [clientId, setClientId] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [serviceId, setServiceId] = useState("");
  const [startsAt, setStartsAt] = useState(toLocalInputValue(initialStart));
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: createAppointment,
    onSuccess: onCreated,
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível criar o agendamento."),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    createMutation.mutate({
      client_id: clientId,
      employee_id: employeeId,
      service_id: serviceId,
      starts_at: new Date(startsAt).toISOString(),
    });
  }

  return (
    <Modal title="Novo agendamento" onClose={onClose}>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Cliente
          <select value={clientId} onChange={(e) => setClientId(e.target.value)} required>
            <option value="" disabled>
              Selecione
            </option>
            {clientsQuery.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Funcionário
          <select value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} required>
            <option value="" disabled>
              Selecione
            </option>
            {employeesQuery.data?.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Serviço
          <select value={serviceId} onChange={(e) => setServiceId(e.target.value)} required>
            <option value="" disabled>
              Selecione
            </option>
            {servicesQuery.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.duration_minutes}min)
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Data e hora
          <input type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} required />
        </label>
        {error && <p className="error-text">{error}</p>}
        <button type="submit" className="primary" disabled={createMutation.isPending}>
          {createMutation.isPending ? "Salvando..." : "Criar agendamento"}
        </button>
      </form>
    </Modal>
  );
}
