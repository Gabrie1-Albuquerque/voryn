import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const NAV_ITEMS = [
  { to: "/app/agenda", label: "Agenda" },
  { to: "/app/clientes", label: "Clientes" },
  { to: "/app/funcionarios", label: "Funcionários" },
  { to: "/app/catalogo", label: "Serviços & Salas" },
];

export function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside
        style={{
          width: 220,
          borderRight: "1px solid var(--border)",
          background: "var(--bg)",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        <h2 style={{ marginBottom: 20 }}>Agendamento</h2>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            style={({ isActive }) => ({
              padding: "8px 10px",
              borderRadius: 6,
              textDecoration: "none",
              color: isActive ? "var(--accent)" : "var(--text)",
              background: isActive ? "var(--accent-bg)" : "transparent",
              fontWeight: isActive ? 600 : 400,
            })}
          >
            {item.label}
          </NavLink>
        ))}
        <div style={{ marginTop: "auto", fontSize: 13 }}>
          <p style={{ marginBottom: 8 }}>{user?.email}</p>
          <button onClick={logout} style={{ width: "100%" }}>
            Sair
          </button>
        </div>
      </aside>
      <main style={{ flex: 1, padding: 24, overflow: "auto" }}>
        <Outlet />
      </main>
    </div>
  );
}
