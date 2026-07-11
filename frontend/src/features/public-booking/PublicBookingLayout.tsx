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
        <p>Carregando...</p>
      </div>
    );
  }

  if (companyQuery.isError || !companyQuery.data) {
    return (
      <div className="public-booking-shell">
        <p className="error-text">Não encontramos essa página de agendamento.</p>
      </div>
    );
  }

  return (
    <div className="public-booking-shell">
      <header className="public-booking-header">
        <h1>{companyQuery.data.name}</h1>
      </header>
      <main className="public-booking-main">
        <Outlet />
      </main>
    </div>
  );
}
