import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { resetPassword } from "../../api/auth";
import { ApiError } from "../../lib/api";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (newPassword !== confirmPassword) {
      setError("As senhas não coincidem.");
      return;
    }
    setIsSubmitting(true);
    try {
      await resetPassword(token, newPassword);
      setDone(true);
    } catch (err) {
      setError(
        err instanceof ApiError ? String(err.detail) : "Não foi possível redefinir a senha. O link pode ter expirado."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center" }}>
      <div className="card" style={{ width: 340, display: "flex", flexDirection: "column", gap: 12 }}>
        <h1>Redefinir senha</h1>
        {!token && <p className="error-text">Link inválido: token ausente.</p>}
        {done ? (
          <>
            <p>Senha redefinida. Você já pode entrar com a nova senha.</p>
            <Link to="/login" className="primary" style={{ textAlign: "center", padding: "8px 14px", borderRadius: 6 }}>
              Ir para o login
            </Link>
          </>
        ) : (
          token && (
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                Nova senha
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  autoFocus
                />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                Confirmar nova senha
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </label>
              {error && <p className="error-text">{error}</p>}
              <button type="submit" className="primary" disabled={isSubmitting}>
                {isSubmitting ? "Salvando..." : "Redefinir senha"}
              </button>
            </form>
          )
        )}
      </div>
    </div>
  );
}
