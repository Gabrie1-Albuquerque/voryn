import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { listServices } from "../../api/catalog";
import { replaceEmployeeAvailability, replaceEmployeeServices, updateEmployee } from "../../api/employees";
import type { AvailabilityWindow, Employee } from "../../api/types";
import { ApiError } from "../../lib/api";
import { Modal } from "../../components/Modal";

// Matches the backend's EmployeeAvailability.weekday: 0=segunda .. 6=domingo.
const WEEKDAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];

interface DayRow {
  enabled: boolean;
  start: string;
  end: string;
}

// One window per weekday: the backend allows several, but the UI keeps the
// common case simple -- a day with multiple windows shows only the first,
// and saving replaces them with the single edited one (PUT semantics).
function toDayRows(availability: AvailabilityWindow[]): DayRow[] {
  return WEEKDAYS.map((_, weekday) => {
    const window = availability.find((w) => w.weekday === weekday);
    return window
      ? { enabled: true, start: window.start_time.slice(0, 5), end: window.end_time.slice(0, 5) }
      : { enabled: false, start: "08:00", end: "18:00" };
  });
}

interface Props {
  employee: Employee;
  onClose: () => void;
}

export function EmployeeEditModal({ employee, onClose }: Props) {
  const queryClient = useQueryClient();
  const servicesQuery = useQuery({ queryKey: ["services"], queryFn: listServices });

  const [name, setName] = useState(employee.name);
  const [selectedServiceIds, setSelectedServiceIds] = useState<string[]>(employee.service_ids);
  const [dayRows, setDayRows] = useState<DayRow[]>(() => toDayRows(employee.availability));
  const [error, setError] = useState<string | null>(null);

  function toggleService(serviceId: string) {
    setSelectedServiceIds((current) =>
      current.includes(serviceId) ? current.filter((id) => id !== serviceId) : [...current, serviceId],
    );
  }

  function setDay(weekday: number, patch: Partial<DayRow>) {
    setDayRows((rows) => rows.map((row, i) => (i === weekday ? { ...row, ...patch } : row)));
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (name !== employee.name) {
        await updateEmployee(employee.id, { name });
      }
      await replaceEmployeeServices(employee.id, selectedServiceIds);
      const windows = dayRows.flatMap((row, weekday) =>
        row.enabled ? [{ weekday, start_time: row.start, end_time: row.end }] : [],
      );
      await replaceEmployeeAvailability(employee.id, windows);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível salvar."),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    for (const [weekday, row] of dayRows.entries()) {
      if (row.enabled && row.end <= row.start) {
        setError(`${WEEKDAYS[weekday]}: o horário final precisa ser depois do inicial.`);
        return;
      }
    }
    saveMutation.mutate();
  }

  const activeServices = servicesQuery.data?.filter(
    (s) => s.is_active || selectedServiceIds.includes(s.id),
  );

  return (
    <Modal title={`Configurar ${employee.name}`} onClose={onClose}>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Nome
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>

        <div>
          <strong>Serviços que atende</strong>
          <p style={{ color: "var(--muted)", fontSize: 13, margin: "4px 0 8px" }}>
            O profissional só aparece no link público para os serviços marcados aqui.
          </p>
          {!activeServices?.length && <p style={{ fontSize: 13 }}>Nenhum serviço cadastrado ainda.</p>}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {activeServices?.map((service) => (
              <label key={service.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14 }}>
                <input
                  type="checkbox"
                  checked={selectedServiceIds.includes(service.id)}
                  onChange={() => toggleService(service.id)}
                />
                {service.name}
              </label>
            ))}
          </div>
        </div>

        <div>
          <strong>Horários de atendimento</strong>
          <p style={{ color: "var(--muted)", fontSize: 13, margin: "4px 0 8px" }}>
            Sem horários cadastrados, o link público não mostra nenhum horário disponível.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {dayRows.map((row, weekday) => (
              <div key={weekday} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 8, width: 110 }}>
                  <input
                    type="checkbox"
                    checked={row.enabled}
                    onChange={(e) => setDay(weekday, { enabled: e.target.checked })}
                  />
                  {WEEKDAYS[weekday]}
                </label>
                {row.enabled && (
                  <>
                    <input
                      type="time"
                      value={row.start}
                      onChange={(e) => setDay(weekday, { start: e.target.value })}
                      required
                    />
                    às
                    <input
                      type="time"
                      value={row.end}
                      onChange={(e) => setDay(weekday, { end: e.target.value })}
                      required
                    />
                  </>
                )}
              </div>
            ))}
          </div>
        </div>

        {error && <p className="error-text">{error}</p>}
        <div>
          <button type="submit" className="primary" disabled={saveMutation.isPending}>
            Salvar
          </button>
        </div>
      </form>
    </Modal>
  );
}
