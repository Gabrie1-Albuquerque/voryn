import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../../api/auth";
import { ApiError } from "../../lib/api";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await forgotPassword(email);
      // Always show the same confirmation regardless of whether the email
      // matched an account -- the backend deliberately responds the same
      // way either way, so this shouldn't let a visitor probe which emails
      // have accounts.
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail) : "Não foi possível enviar o link. Tente novamente.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="card auth-card">
        <h1>Esqueci minha senha</h1>
        {sent ? (
          <p>Se esse email tiver uma conta, enviamos um link para redefinir a senha.</p>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              Email
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
            </label>
            {error && <p className="error-text">{error}</p>}
            <button type="submit" className="primary" disabled={isSubmitting}>
              {isSubmitting ? "Enviando..." : "Enviar link"}
            </button>
          </form>
        )}
        <Link to="/login" style={{ fontSize: 13 }}>
          Voltar para o login
        </Link>
      </div>
    </div>
  );
}
