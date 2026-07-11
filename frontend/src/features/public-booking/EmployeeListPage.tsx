import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { listPublicEmployees, listPublicServices } from "../../api/publicBooking";
import { BookingSteps } from "./BookingSteps";

export function EmployeeListPage() {
  const { slug = "", serviceId = "" } = useParams();
  const servicesQuery = useQuery({
    queryKey: ["public-services", slug],
    queryFn: () => listPublicServices(slug),
  });
  const employeesQuery = useQuery({
    queryKey: ["public-employees", slug],
    queryFn: () => listPublicEmployees(slug),
  });

  const service = servicesQuery.data?.find((s) => s.id === serviceId);
  // Filtered client-side against the one /employees list rather than a
  // dedicated per-service endpoint -- the catalog is small for a single
  // business, and the backend independently re-validates this pairing at
  // availability/booking time regardless of what this list shows.
  const qualifiedEmployees = employeesQuery.data?.filter((e) => e.service_ids.includes(serviceId)) ?? [];

  return (
    <div>
      <BookingSteps current={2} />
      <Link to={`/booking/${slug}`} className="public-booking-back">
        <ArrowLeft size={15} />
        Voltar
      </Link>
      <h2>{service ? `Profissional para ${service.name}` : "Escolha o profissional"}</h2>
      <div className="public-booking-list">
        {qualifiedEmployees.map((employee) => (
          <Link
            key={employee.id}
            to={`/booking/${slug}/service/${serviceId}/employee/${employee.id}`}
            className="card public-booking-option"
          >
            <span className="public-booking-option-icon">{employee.name.charAt(0).toUpperCase()}</span>
            <span className="public-booking-option-body">
              <strong>{employee.name}</strong>
            </span>
          </Link>
        ))}
        {employeesQuery.isSuccess && qualifiedEmployees.length === 0 && (
          <p>Nenhum profissional disponível para este serviço no momento.</p>
        )}
      </div>
    </div>
  );
}
