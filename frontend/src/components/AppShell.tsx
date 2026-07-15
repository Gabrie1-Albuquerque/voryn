import { BarChart3, CalendarDays, LogOut, Scissors, UserCog, Users } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const NAV_ITEMS = [
  { to: "/app/agenda", label: "Agenda", icon: CalendarDays },
  { to: "/app/clientes", label: "Clientes", icon: Users },
  { to: "/app/funcionarios", label: "Funcionários", icon: UserCog },
  { to: "/app/catalogo", label: "Serviços & Salas", icon: Scissors },
  { to: "/app/dashboard", label: "Dashboard", icon: BarChart3 },
];

export function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-sidebar-brand">
          <img src="/logo-mark.svg" alt="" width={28} height={28} className="app-sidebar-brand-icon" />
          Voryn
        </div>
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `app-sidebar-link${isActive ? " active" : ""}`}>
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
        <div className="app-sidebar-footer">
          <p className="app-sidebar-user" title={user?.email}>
            {user?.email}
          </p>
          <button className="app-sidebar-logout" onClick={logout}>
            <LogOut size={15} />
            Sair
          </button>
        </div>
      </aside>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
