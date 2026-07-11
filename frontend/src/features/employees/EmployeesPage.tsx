import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { createEmployee, listEmployees } from "../../api/employees";
import { ApiError } from "../../lib/api";

export function EmployeesPage() {
  const queryClient = useQueryClient();
  const employeesQuery = useQuery({ queryKey: ["employees"], queryFn: listEmployees });
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () => createEmployee({ name }),
    onSuccess: () => {
      setName("");
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível criar."),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    createMutation.mutate();
  }

  return (
    <div>
      <h1>Funcionários</h1>
      <form onSubmit={handleSubmit} className="card" style={{ display: "flex", gap: 8, marginBottom: 16, maxWidth: 400 }}>
        <input placeholder="Nome do funcionário" value={name} onChange={(e) => setName(e.target.value)} required />
        <button type="submit" className="primary" disabled={createMutation.isPending}>
          Adicionar
        </button>
      </form>
      {error && <p className="error-text">{error}</p>}
      <table className="card">
        <thead>
          <tr>
            <th>Nome</th>
            <th>Serviços</th>
            <th>Ativo</th>
          </tr>
        </thead>
        <tbody>
          {employeesQuery.data?.map((employee) => (
            <tr key={employee.id}>
              <td>{employee.name}</td>
              <td>{employee.service_ids.length}</td>
              <td>{employee.is_active ? "Sim" : "Não"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
