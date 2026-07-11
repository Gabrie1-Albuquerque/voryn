import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { listPublicServices } from "../../api/publicBooking";

export function ServiceListPage() {
  const { slug = "" } = useParams();
  const servicesQuery = useQuery({
    queryKey: ["public-services", slug],
    queryFn: () => listPublicServices(slug),
  });

  return (
    <div>
      <h2>Escolha um serviço</h2>
      <div className="public-booking-list">
        {servicesQuery.data?.map((service) => (
          <Link key={service.id} to={`/booking/${slug}/service/${service.id}`} className="card public-booking-option">
            <strong>{service.name}</strong>
            <span>
              {service.duration_minutes} min &middot; R$ {service.price}
            </span>
            {service.deposit_required && <span className="public-booking-badge">Sinal necessário</span>}
          </Link>
        ))}
        {servicesQuery.isSuccess && servicesQuery.data.length === 0 && (
          <p>Nenhum serviço disponível para agendamento no momento.</p>
        )}
      </div>
    </div>
  );
}
