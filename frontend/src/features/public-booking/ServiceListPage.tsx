import { useQuery } from "@tanstack/react-query";
import { Clock, Sparkles } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { listPublicServices } from "../../api/publicBooking";
import { BookingSteps } from "./BookingSteps";

export function ServiceListPage() {
  const { slug = "" } = useParams();
  const servicesQuery = useQuery({
    queryKey: ["public-services", slug],
    queryFn: () => listPublicServices(slug),
  });

  return (
    <div>
      <BookingSteps current={1} />
      <h2>Escolha um serviço</h2>
      <div className="public-booking-list">
        {servicesQuery.data?.map((service) => (
          <Link key={service.id} to={`/booking/${slug}/service/${service.id}`} className="card public-booking-option">
            <span className="public-booking-option-icon">
              <Sparkles size={20} />
            </span>
            <span className="public-booking-option-body">
              <strong>{service.name}</strong>
              <span className="public-booking-option-meta">
                <span className="chip">
                  <Clock size={13} />
                  {service.duration_minutes} min
                </span>
                <span className="chip price">R$ {service.price}</span>
                {service.deposit_required && <span className="public-booking-badge">Sinal para confirmar</span>}
              </span>
            </span>
          </Link>
        ))}
        {servicesQuery.isSuccess && servicesQuery.data.length === 0 && (
          <p>Nenhum serviço disponível para agendamento no momento.</p>
        )}
      </div>
    </div>
  );
}
