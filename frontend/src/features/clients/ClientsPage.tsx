import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { createClient, deactivateClient, listClients, updateClient } from "../../api/clients";
import type { Client } from "../../api/types";
import { ApiError } from "../../lib/api";
import { ClientEditModal } from "./ClientEditModal";

export function ClientsPage() {
  const queryClient = useQueryClient();
  const clientsQuery = useQuery({ queryKey: ["clients"], queryFn: listClients });
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editingClient, setEditingClient] = useState<Client | null>(null);
  const [showInactive, setShowInactive] = useState(false);

  const createMutation = useMutation({
    mutationFn: () => createClient({ name, phone, email: email || undefined }),
    onSuccess: () => {
      setName("");
      setPhone("");
      setEmail("");
      queryClient.invalidateQueries({ queryKey: ["clients"] });
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível criar."),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    createMutation.mutate();
  }

  const toggleActiveMutation = useMutation({
    mutationFn: async (client: Client) => {
      if (client.is_active) {
        await deactivateClient(client.id);
      } else {
        await updateClient(client.id, { is_active: true });
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clients"] }),
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível atualizar."),
  });

  function handleToggleActive(client: Client) {
    if (client.is_active && !window.confirm(`Desativar ${client.name}?`)) {
      return;
    }
    toggleActiveMutation.mutate(client);
  }

  return (
    <div>
      <h1>Clientes</h1>
      <form onSubmit={handleSubmit} className="card" style={{ display: "flex", gap: 8, marginBottom: 16, maxWidth: 640 }}>
        <input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} required />
        <input placeholder="Telefone (WhatsApp)" value={phone} onChange={(e) => setPhone(e.target.value)} required />
        <input
          type="email"
          placeholder="Email (opcional)"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
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
            <th>Telefone</th>
            <th>Email</th>
            <th>Ativo</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {clientsQuery.data?.filter((client) => showInactive || client.is_active).map((client) => (
            <tr key={client.id}>
              <td>{client.name}</td>
              <td>{client.phone}</td>
              <td>{client.email ?? "—"}</td>
              <td>{client.is_active ? "Sim" : "Não"}</td>
              <td style={{ display: "flex", gap: 8 }}>
                <button onClick={() => setEditingClient(client)}>Editar</button>
                <button disabled={toggleActiveMutation.isPending} onClick={() => handleToggleActive(client)}>
                  {client.is_active ? "Desativar" : "Reativar"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {editingClient && <ClientEditModal client={editingClient} onClose={() => setEditingClient(null)} />}
    </div>
  );
}
