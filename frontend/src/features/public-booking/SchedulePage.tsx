import { useQuery, useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { createPublicBooking, getPublicAvailability, listPublicEmployees, listPublicServices } from "../../api/publicBooking";
import { PublicApiError } from "../../lib/publicApi";

function todayLocalDate(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  return new Date(now.getTime() - offset * 60_000).toISOString().slice(0, 10);
}

function formatSlotTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export function SchedulePage() {
  const { slug = "", serviceId = "", employeeId = "" } = useParams();
  const navigate = useNavigate();

  const [date, setDate] = useState(todayLocalDate());
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [clientName, setClientName] = useState("");
  const [clientPhone, setClientPhone] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const servicesQuery = useQuery({ queryKey: ["public-services", slug], queryFn: () => listPublicServices(slug) });
  const employeesQuery = useQuery({ queryKey: ["public-employees", slug], queryFn: () => listPublicEmployees(slug) });
  const availabilityQuery = useQuery({
    queryKey: ["public-availability", slug, employeeId, serviceId, date],
    queryFn: () => getPublicAvailability(slug, employeeId, serviceId, date),
    enabled: Boolean(slug && employeeId && serviceId && date),
  });

  const service = servicesQuery.data?.find((s) => s.id === serviceId);
  const employee = employeesQuery.data?.find((e) => e.id === employeeId);

  const bookingMutation = useMutation({
    mutationFn: () =>
      createPublicBooking(slug, {
        service_id: serviceId,
        employee_id: employeeId,
        starts_at: selectedSlot as string,
        client_name: clientName,
        client_phone: clientPhone,
        client_email: clientEmail || undefined,
        notes: notes || undefined,
      }),
    onSuccess: (booking) => navigate(`/booking/${slug}/status/${booking.id}`),
    onError: (err) =>
      setError(err instanceof PublicApiError ? String(err.detail) : "Não foi possível concluir o agendamento."),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!selectedSlot) {
      setError("Escolha um horário.");
      return;
    }
    bookingMutation.mutate();
  }

  function handleDateChange(value: string) {
    setDate(value);
    setSelectedSlot(null);
  }

  return (
    <div>
      <Link to={`/booking/${slug}/service/${serviceId}`} className="public-booking-back">
        &larr; Voltar
      </Link>
      <h2>
        {service?.name} com {employee?.name}
      </h2>

      <label className="public-booking-field">
        Data
        <input
          type="date"
          value={date}
          min={todayLocalDate()}
          onChange={(e) => handleDateChange(e.target.value)}
        />
      </label>

      <div className="public-booking-slots">
        {availabilityQuery.isLoading && <p>Buscando horários...</p>}
        {availabilityQuery.isSuccess && availabilityQuery.data.slots.length === 0 && (
          <p>Nenhum horário livre nesse dia.</p>
        )}
        {availabilityQuery.data?.slots.map((slot) => (
          <button
            key={slot}
            type="button"
            className={selectedSlot === slot ? "primary" : ""}
            onClick={() => setSelectedSlot(slot)}
          >
            {formatSlotTime(slot)}
          </button>
        ))}
      </div>

      {selectedSlot && (
        <form onSubmit={handleSubmit} className="card public-booking-form">
          <label>
            Nome
            <input value={clientName} onChange={(e) => setClientName(e.target.value)} required />
          </label>
          <label>
            Telefone (WhatsApp)
            <input value={clientPhone} onChange={(e) => setClientPhone(e.target.value)} required />
          </label>
          <label>
            E-mail (opcional)
            <input type="email" value={clientEmail} onChange={(e) => setClientEmail(e.target.value)} />
          </label>
          <label>
            Observações (opcional)
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
          </label>
          {service?.deposit_required && (
            <p className="public-booking-badge">
              Este serviço exige um sinal de R$ {service.deposit_value} para confirmar o agendamento.
            </p>
          )}
          {error && <p className="error-text">{error}</p>}
          <button type="submit" className="primary" disabled={bookingMutation.isPending}>
            {bookingMutation.isPending ? "Agendando..." : "Confirmar agendamento"}
          </button>
        </form>
      )}
    </div>
  );
}
