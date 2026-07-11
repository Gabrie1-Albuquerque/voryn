import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppShell } from "./components/AppShell";
import { LoginPage } from "./features/auth/LoginPage";
import { AgendaPage } from "./features/agenda/AgendaPage";
import { CatalogPage } from "./features/catalog/CatalogPage";
import { ClientsPage } from "./features/clients/ClientsPage";
import { EmployeesPage } from "./features/employees/EmployeesPage";

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/app" element={<AppShell />}>
              <Route index element={<Navigate to="agenda" replace />} />
              <Route path="agenda" element={<AgendaPage />} />
              <Route path="clientes" element={<ClientsPage />} />
              <Route path="funcionarios" element={<EmployeesPage />} />
              <Route path="catalogo" element={<CatalogPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}
