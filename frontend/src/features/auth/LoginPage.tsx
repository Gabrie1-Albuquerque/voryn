import { CalendarCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { ApiError } from "../../lib/api";

export function LoginPage() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (user) return <Navigate to="/app/agenda" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail) : "Não foi possível entrar. Tente novamente.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <form onSubmit={handleSubmit} className="card auth-card">
        <div className="auth-brand">
          <span className="auth-brand-icon">
            <CalendarCheck size={19} />
          </span>
          Agendamentos
        </div>
        <h1>Entrar</h1>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Senha
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <p className="error-text">{error}</p>}
        <button type="submit" className="primary" disabled={isSubmitting}>
          {isSubmitting ? "Entrando..." : "Entrar"}
        </button>
        <Link to="/forgot-password" style={{ fontSize: 13, textAlign: "center" }}>
          Esqueceu a senha?
        </Link>
      </form>
    </div>
  );
}
