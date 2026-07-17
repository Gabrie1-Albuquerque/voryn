import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { createEmployee, deactivateEmployee, listEmployees, updateEmployee } from "../../api/employees";
import type { Employee } from "../../api/types";
import { ApiError } from "../../lib/api";
import { EmployeeEditModal } from "./EmployeeEditModal";

export function EmployeesPage() {
  const queryClient = useQueryClient();
  const employeesQuery = useQuery({ queryKey: ["employees"], queryFn: listEmployees });
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [showInactive, setShowInactive] = useState(false);

  const createMutation = useMutation({
    mutationFn: () => createEmployee({ name }),
    onSuccess: () => {
      setName("");
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível criar."),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: async (employee: Employee) => {
      if (employee.is_active) {
        await deactivateEmployee(employee.id);
      } else {
        await updateEmployee(employee.id, { is_active: true });
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["employees"] }),
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível atualizar."),
  });

  function handleToggleActive(employee: Employee) {
    if (employee.is_active && !window.confirm(`Desativar ${employee.name}? Ele deixará de aparecer para novos agendamentos.`)) {
      return;
    }
    toggleActiveMutation.mutate(employee);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    createMutation.mutate();
  }

  const visibleEmployees = employeesQuery.data?.filter((employee) => showInactive || employee.is_active);

  return (
    <div>
      <h1>Funcionários</h1>
      <p style={{ color: "var(--muted)", fontSize: 14, marginTop: 4, marginBottom: 16 }}>
        Um profissional só aparece no link público de agendamento depois de ter os serviços que atende e os
        horários de trabalho configurados — use o botão <strong>Configurar</strong>.
      </p>
      <form onSubmit={handleSubmit} className="card" style={{ display: "flex", gap: 8, marginBottom: 16, maxWidth: 400 }}>
        <input placeholder="Nome do funcionário" value={name} onChange={(e) => setName(e.target.value)} required />
        <button type="submit" className="primary" disabled={createMutation.isPending}>
          Adicionar
        </button>
      </form>
      {error && <p className="error-text">{error}</p>}
      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, marginBottom: 8 }}>
        <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />
        Mostrar desativados
      </label>
      <table className="card">
        <thead>
          <tr>
            <th>Nome</th>
            <th>Serviços</th>
            <th>Dias de atendimento</th>
            <th>Ativo</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {visibleEmployees?.map((employee) => (
            <tr key={employee.id}>
              <td>{employee.name}</td>
              <td>{employee.service_ids.length === 0 ? "⚠ nenhum" : employee.service_ids.length}</td>
              <td>{employee.availability.length === 0 ? "⚠ nenhum" : new Set(employee.availability.map((w) => w.weekday)).size}</td>
              <td>{employee.is_active ? "Sim" : "Não"}</td>
              <td style={{ display: "flex", gap: 8 }}>
                <button onClick={() => setEditingEmployee(employee)}>Configurar</button>
                <button
                  disabled={toggleActiveMutation.isPending}
                  onClick={() => handleToggleActive(employee)}
                >
                  {employee.is_active ? "Desativar" : "Reativar"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {editingEmployee && (
        <EmployeeEditModal employee={editingEmployee} onClose={() => setEditingEmployee(null)} />
      )}
    </div>
  );
}
