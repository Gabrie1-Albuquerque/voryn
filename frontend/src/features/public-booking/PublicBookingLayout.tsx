import { useQuery } from "@tanstack/react-query";
import { Outlet, useParams } from "react-router-dom";
import { getPublicCompany } from "../../api/publicBooking";

export function PublicBookingLayout() {
  const { slug = "" } = useParams();
  const companyQuery = useQuery({
    queryKey: ["public-company", slug],
    queryFn: () => getPublicCompany(slug),
    retry: false,
  });

  if (companyQuery.isLoading) {
    return (
      <div className="public-booking-shell">
        <p style={{ padding: 24 }}>Carregando...</p>
      </div>
    );
  }

  if (companyQuery.isError || !companyQuery.data) {
    return (
      <div className="public-booking-shell">
        <p className="error-text" style={{ padding: 24 }}>
          Não encontramos essa página de agendamento.
        </p>
      </div>
    );
  }

  const company = companyQuery.data;

  return (
    <div className="public-booking-shell">
      <header className="public-booking-header">
        <span className="public-booking-avatar">{company.name.charAt(0).toUpperCase()}</span>
        <div>
          <h1>{company.name}</h1>
          <p>Agendamento online</p>
        </div>
      </header>
      <main className="public-booking-main">
        <Outlet />
      </main>
    </div>
  );
}
