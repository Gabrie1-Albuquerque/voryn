import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { getMyCompany, updateMyCompany } from "../../api/company";
import { ApiError } from "../../lib/api";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const companyQuery = useQuery({ queryKey: ["company"], queryFn: getMyCompany });
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const updateMutation = useMutation({
    mutationFn: updateMyCompany,
    onSuccess: () => {
      setSaved(true);
      queryClient.invalidateQueries({ queryKey: ["company"] });
    },
    onError: (err) => {
      setSaved(false);
      setError(err instanceof ApiError ? String(err.detail) : "Não foi possível salvar.");
    },
  });

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSaved(false);
    const form = new FormData(e.currentTarget);
    updateMutation.mutate({
      reminder_first_hours: Number(form.get("reminder_first_hours")),
      reminder_second_hours: Number(form.get("reminder_second_hours")),
    });
  }

  const company = companyQuery.data;

  return (
    <div>
      <h1>Configurações</h1>

      <div className="card" style={{ maxWidth: 480 }}>
        <h2 style={{ marginTop: 0 }}>Lembretes de agendamento</h2>
        <p style={{ color: "var(--muted)", fontSize: 14 }}>
          Defina com quanta antecedência os clientes recebem o lembrete no WhatsApp antes do horário marcado.
          O primeiro lembrete precisa ser mais distante do horário do que o segundo.
        </p>

        {!company ? (
          <p>Carregando...</p>
        ) : (
          <form key={company.id} onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              Primeiro lembrete (horas antes)
              <input
                type="number"
                name="reminder_first_hours"
                min={1}
                max={168}
                defaultValue={company.reminder_first_hours}
                required
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              Segundo lembrete, mais próximo do horário (horas antes)
              <input
                type="number"
                name="reminder_second_hours"
                min={1}
                max={168}
                defaultValue={company.reminder_second_hours}
                required
              />
            </label>
            {error && <p className="error-text">{error}</p>}
            {saved && !error && <p style={{ color: "var(--success)", fontSize: 14 }}>Salvo!</p>}
            <div>
              <button type="submit" className="primary" disabled={updateMutation.isPending}>
                Salvar
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
