import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppShell } from "./components/AppShell";
import { LoginPage } from "./features/auth/LoginPage";
import { ForgotPasswordPage } from "./features/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "./features/auth/ResetPasswordPage";
import { AgendaPage } from "./features/agenda/AgendaPage";
import { CatalogPage } from "./features/catalog/CatalogPage";
import { ClientsPage } from "./features/clients/ClientsPage";
import { EmployeesPage } from "./features/employees/EmployeesPage";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { LandingPage } from "./features/landing/LandingPage";
import { PublicBookingLayout } from "./features/public-booking/PublicBookingLayout";
import { ServiceListPage } from "./features/public-booking/ServiceListPage";
import { EmployeeListPage } from "./features/public-booking/EmployeeListPage";
import { SchedulePage } from "./features/public-booking/SchedulePage";
import { BookingStatusPage } from "./features/public-booking/BookingStatusPage";

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public marketing landing -- the only page a cold visitor sees */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/app" element={<AppShell />}>
              <Route index element={<Navigate to="agenda" replace />} />
              <Route path="agenda" element={<AgendaPage />} />
              <Route path="clientes" element={<ClientsPage />} />
              <Route path="funcionarios" element={<EmployeesPage />} />
              <Route path="catalogo" element={<CatalogPage />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="configuracoes" element={<SettingsPage />} />
            </Route>
          </Route>
          {/* Unauthenticated, mobile-first client-facing flow -- deliberately
              its own route tree with no shared layout/menu with /app/*. */}
          <Route path="/booking/:slug" element={<PublicBookingLayout />}>
            <Route index element={<ServiceListPage />} />
            <Route path="service/:serviceId" element={<EmployeeListPage />} />
            <Route path="service/:serviceId/employee/:employeeId" element={<SchedulePage />} />
            <Route path="status/:appointmentId" element={<BookingStatusPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}
