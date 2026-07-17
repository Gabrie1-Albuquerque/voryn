import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { addClientNote, listClientNotes } from "../../api/clients";
import type { Client, ClientNoteType } from "../../api/types";
import { ApiError } from "../../lib/api";
import { Modal } from "../../components/Modal";

const NOTE_TYPE_LABELS: Record<ClientNoteType, string> = {
  alert: "Alerta",
  clinical: "Clínica",
  preference: "Preferência",
  general: "Geral",
};

interface Props {
  client: Client;
  onClose: () => void;
}

export function ClientNotesModal({ client, onClose }: Props) {
  const queryClient = useQueryClient();
  const notesQuery = useQuery({
    queryKey: ["client-notes", client.id],
    queryFn: () => listClientNotes(client.id),
  });

  const [noteType, setNoteType] = useState<ClientNoteType>("general");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  const addMutation = useMutation({
    mutationFn: () => addClientNote(client.id, { note_type: noteType, body }),
    onSuccess: () => {
      setBody("");
      queryClient.invalidateQueries({ queryKey: ["client-notes", client.id] });
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível salvar."),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    addMutation.mutate();
  }

  return (
    <Modal title={`Notas de ${client.name}`} onClose={onClose}>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Tipo
          <select value={noteType} onChange={(e) => setNoteType(e.target.value as ClientNoteType)}>
            <option value="general">Geral</option>
            <option value="alert">Alerta (alergias, restrições)</option>
            <option value="clinical">Clínica (evolução de atendimento)</option>
            <option value="preference">Preferência</option>
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Anotação
          <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={3} required />
        </label>
        {error && <p className="error-text">{error}</p>}
        <div>
          <button type="submit" className="primary" disabled={addMutation.isPending}>
            Adicionar nota
          </button>
        </div>
      </form>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {notesQuery.isLoading && <p>Carregando...</p>}
        {notesQuery.data?.length === 0 && (
          <p style={{ color: "var(--muted)", fontSize: 14 }}>Nenhuma nota ainda.</p>
        )}
        {notesQuery.data?.map((note) => (
          <div key={note.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--muted)" }}>
              <strong style={{ color: note.note_type === "alert" ? "var(--danger)" : "var(--text)" }}>
                {NOTE_TYPE_LABELS[note.note_type]}
              </strong>
              <span>{new Date(note.created_at).toLocaleString("pt-BR")}</span>
            </div>
            <p style={{ margin: "4px 0 0", fontSize: 14 }}>{note.body}</p>
          </div>
        ))}
      </div>
    </Modal>
  );
}
