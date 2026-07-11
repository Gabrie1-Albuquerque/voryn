import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { listPublicEmployees, listPublicServices } from "../../api/publicBooking";

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
      <Link to={`/booking/${slug}`} className="public-booking-back">
        &larr; Voltar
      </Link>
      <h2>{service ? `Profissional para ${service.name}` : "Escolha o profissional"}</h2>
      <div className="public-booking-list">
        {qualifiedEmployees.map((employee) => (
          <Link
            key={employee.id}
            to={`/booking/${slug}/service/${serviceId}/employee/${employee.id}`}
            className="card public-booking-option"
          >
            <strong>{employee.name}</strong>
          </Link>
        ))}
        {employeesQuery.isSuccess && qualifiedEmployees.length === 0 && (
          <p>Nenhum profissional disponível para este serviço no momento.</p>
        )}
      </div>
    </div>
  );
}
