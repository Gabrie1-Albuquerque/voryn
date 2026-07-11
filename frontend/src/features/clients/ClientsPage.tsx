import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { createClient, listClients } from "../../api/clients";
import { ApiError } from "../../lib/api";

export function ClientsPage() {
  const queryClient = useQueryClient();
  const clientsQuery = useQuery({ queryKey: ["clients"], queryFn: listClients });
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () => createClient({ name, phone }),
    onSuccess: () => {
      setName("");
      setPhone("");
      queryClient.invalidateQueries({ queryKey: ["clients"] });
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
      <h1>Clientes</h1>
      <form onSubmit={handleSubmit} className="card" style={{ display: "flex", gap: 8, marginBottom: 16, maxWidth: 500 }}>
        <input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} required />
        <input placeholder="Telefone (WhatsApp)" value={phone} onChange={(e) => setPhone(e.target.value)} required />
        <button type="submit" className="primary" disabled={createMutation.isPending}>
          Adicionar
        </button>
      </form>
      {error && <p className="error-text">{error}</p>}
      <table className="card">
        <thead>
          <tr>
            <th>Nome</th>
            <th>Telefone</th>
            <th>Ativo</th>
          </tr>
        </thead>
        <tbody>
          {clientsQuery.data?.map((client) => (
            <tr key={client.id}>
              <td>{client.name}</td>
              <td>{client.phone}</td>
              <td>{client.is_active ? "Sim" : "Não"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
