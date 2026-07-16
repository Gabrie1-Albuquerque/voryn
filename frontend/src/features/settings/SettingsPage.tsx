import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { getMyCompany, testSmtpConnection, updateMyCompany } from "../../api/company";
import { ApiError } from "../../lib/api";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const companyQuery = useQuery({ queryKey: ["company"], queryFn: getMyCompany });
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [linkCopied, setLinkCopied] = useState(false);

  const [infoError, setInfoError] = useState<string | null>(null);
  const [infoSaved, setInfoSaved] = useState(false);

  const infoMutation = useMutation({
    mutationFn: updateMyCompany,
    onSuccess: () => {
      setInfoSaved(true);
      queryClient.invalidateQueries({ queryKey: ["company"] });
    },
    onError: (err) => {
      setInfoSaved(false);
      setInfoError(err instanceof ApiError ? String(err.detail) : "Não foi possível salvar.");
    },
  });

  function handleSaveInfo(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setInfoError(null);
    setInfoSaved(false);
    const form = new FormData(e.currentTarget);
    infoMutation.mutate({
      name: String(form.get("name") ?? ""),
      document: String(form.get("document") ?? ""),
      timezone: String(form.get("timezone") ?? ""),
      auto_confirm_public_bookings: form.get("auto_confirm_public_bookings") === "on",
    });
  }

  async function handleCopyLink(link: string) {
    await navigator.clipboard.writeText(link);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2000);
  }

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

  const [smtpError, setSmtpError] = useState<string | null>(null);
  const [smtpSaved, setSmtpSaved] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const smtpUpdateMutation = useMutation({
    mutationFn: updateMyCompany,
    onSuccess: () => {
      setSmtpSaved(true);
      queryClient.invalidateQueries({ queryKey: ["company"] });
    },
    onError: (err) => {
      setSmtpSaved(false);
      setSmtpError(err instanceof ApiError ? String(err.detail) : "Não foi possível salvar.");
    },
  });

  const smtpTestMutation = useMutation({
    mutationFn: testSmtpConnection,
    onSuccess: (result) => setTestResult(result),
    onError: (err) =>
      setTestResult({
        success: false,
        message: err instanceof ApiError ? String(err.detail) : "Não foi possível testar a conexão.",
      }),
  });

  function readSmtpForm(form: HTMLFormElement) {
    const data = new FormData(form);
    return {
      smtp_host: String(data.get("smtp_host") ?? ""),
      smtp_port: Number(data.get("smtp_port")),
      smtp_username: String(data.get("smtp_username") ?? ""),
      smtp_password: String(data.get("smtp_password") ?? ""),
      smtp_from_email: String(data.get("smtp_from_email") ?? ""),
    };
  }

  function handleTestSmtp(form: HTMLFormElement) {
    setTestResult(null);
    smtpTestMutation.mutate(readSmtpForm(form));
  }

  function handleSaveSmtp(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSmtpError(null);
    setSmtpSaved(false);
    const values = readSmtpForm(e.currentTarget);
    smtpUpdateMutation.mutate({
      smtp_host: values.smtp_host,
      smtp_port: values.smtp_port,
      smtp_username: values.smtp_username,
      smtp_from_email: values.smtp_from_email,
      // Left blank on purpose to keep the already-saved password -- only
      // sent when the field actually has something new typed into it.
      ...(values.smtp_password ? { smtp_password: values.smtp_password } : {}),
    });
  }

  const company = companyQuery.data;

  const bookingLink = company ? `${window.location.origin}/booking/${company.slug}` : "";

  return (
    <div>
      <h1>Configurações</h1>

      <div className="card" style={{ maxWidth: 480 }}>
        <h2 style={{ marginTop: 0 }}>Seu link de agendamento</h2>
        <p style={{ color: "var(--muted)", fontSize: 14 }}>
          Compartilhe esse link com seus clientes (Instagram, WhatsApp, Google) para que eles marquem um
          horário sozinhos, vendo sua agenda real em tempo real.
        </p>
        {!company ? (
          <p>Carregando...</p>
        ) : (
          <div style={{ display: "flex", gap: 8 }}>
            <input type="text" value={bookingLink} readOnly style={{ flex: 1 }} />
            <button type="button" onClick={() => handleCopyLink(bookingLink)}>
              {linkCopied ? "Copiado!" : "Copiar link"}
            </button>
          </div>
        )}
      </div>

      <div className="card" style={{ maxWidth: 480, marginTop: 16 }}>
        <h2 style={{ marginTop: 0 }}>Informações da empresa</h2>

        {!company ? (
          <p>Carregando...</p>
        ) : (
          <form
            key={company.id}
            onSubmit={handleSaveInfo}
            style={{ display: "flex", flexDirection: "column", gap: 12 }}
          >
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              Nome da empresa
              <input type="text" name="name" defaultValue={company.name} required />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              CNPJ/documento (opcional)
              <input type="text" name="document" defaultValue={company.document ?? ""} />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              Fuso horário
              <input type="text" name="timezone" defaultValue={company.timezone} required />
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                name="auto_confirm_public_bookings"
                defaultChecked={company.auto_confirm_public_bookings}
              />
              Confirmar automaticamente agendamentos feitos pelo link público
            </label>
            {infoError && <p className="error-text">{infoError}</p>}
            {infoSaved && !infoError && <p style={{ color: "var(--success)", fontSize: 14 }}>Salvo!</p>}
            <div>
              <button type="submit" className="primary" disabled={infoMutation.isPending}>
                Salvar
              </button>
            </div>
          </form>
        )}
      </div>

      <div className="card" style={{ maxWidth: 480, marginTop: 16 }}>
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

      <div className="card" style={{ maxWidth: 480, marginTop: 16 }}>
        <h2 style={{ marginTop: 0 }}>Email (SMTP)</h2>
        <p style={{ color: "var(--muted)", fontSize: 14 }}>
          Conecte sua própria conta de email para que os clientes recebam confirmações e lembretes também por
          email, vindos do seu endereço. A maioria dos provedores exige uma "senha de app" em vez da sua senha
          normal.
        </p>
        {company?.smtp_configured && (
          <p style={{ fontSize: 14 }}>
            Conectado como: <strong>{company.smtp_username}</strong>
          </p>
        )}

        {!company ? (
          <p>Carregando...</p>
        ) : (
          <form
            key={company.id}
            onSubmit={handleSaveSmtp}
            style={{ display: "flex", flexDirection: "column", gap: 12 }}
          >
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              Servidor (host)
              <input type="text" name="smtp_host" placeholder="smtp.gmail.com" defaultValue={company.smtp_host ?? ""} required />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              Porta
              <input type="number" name="smtp_port" placeholder="587" defaultValue={company.smtp_port ?? 587} required />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              Usuário
              <input
                type="text"
                name="smtp_username"
                placeholder="contato@suaempresa.com"
                defaultValue={company.smtp_username ?? ""}
                required
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              Senha {company.smtp_configured ? "(deixe em branco para manter a atual)" : ""}
              <input type="password" name="smtp_password" autoComplete="new-password" />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              Email de remetente
              <input
                type="email"
                name="smtp_from_email"
                placeholder="contato@suaempresa.com"
                defaultValue={company.smtp_from_email ?? ""}
                required
              />
            </label>
            {testResult && (
              <p style={{ color: testResult.success ? "var(--success)" : "var(--danger)", fontSize: 14 }}>
                {testResult.message}
              </p>
            )}
            {smtpError && <p className="error-text">{smtpError}</p>}
            {smtpSaved && !smtpError && <p style={{ color: "var(--success)", fontSize: 14 }}>Salvo!</p>}
            <div style={{ display: "flex", gap: 8 }}>
              <button
                type="button"
                disabled={smtpTestMutation.isPending}
                onClick={(e) => handleTestSmtp(e.currentTarget.form!)}
              >
                {smtpTestMutation.isPending ? "Testando..." : "Testar conexão"}
              </button>
              <button type="submit" className="primary" disabled={smtpUpdateMutation.isPending}>
                Salvar
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
