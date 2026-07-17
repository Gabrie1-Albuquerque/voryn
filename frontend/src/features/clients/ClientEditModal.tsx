import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { updateClient } from "../../api/clients";
import type { Client } from "../../api/types";
import { ApiError } from "../../lib/api";
import { Modal } from "../../components/Modal";

interface Props {
  client: Client;
  onClose: () => void;
}

export function ClientEditModal({ client, onClose }: Props) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(client.name);
  const [phone, setPhone] = useState(client.phone);
  const [email, setEmail] = useState(client.email ?? "");
  const [document, setDocument] = useState(client.document ?? "");
  const [error, setError] = useState<string | null>(null);

  const updateMutation = useMutation({
    mutationFn: () =>
      updateClient(client.id, {
        name,
        phone,
        email: email || undefined,
        document: document || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível salvar."),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    updateMutation.mutate();
  }

  return (
    <Modal title="Editar cliente" onClose={onClose}>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Nome
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Telefone (WhatsApp)
          <input value={phone} onChange={(e) => setPhone(e.target.value)} required />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Email (opcional)
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Documento (opcional)
          <input value={document} onChange={(e) => setDocument(e.target.value)} />
        </label>
        {error && <p className="error-text">{error}</p>}
        <div>
          <button type="submit" className="primary" disabled={updateMutation.isPending}>
            Salvar
          </button>
        </div>
      </form>
    </Modal>
  );
}
