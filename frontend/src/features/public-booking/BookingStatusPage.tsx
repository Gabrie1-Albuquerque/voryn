import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { getPublicBookingStatus } from "../../api/publicBooking";
import type { AppointmentStatus, PublicBooking } from "../../api/types";

const STATUS_LABELS: Record<AppointmentStatus, string> = {
  pending: "Aguardando confirmação",
  confirmed: "Confirmado",
  completed: "Concluído",
  cancelled: "Cancelado",
  rescheduled: "Reagendado",
};

export function BookingStatusPage() {
  const { slug = "", appointmentId = "" } = useParams();

  const statusQuery = useQuery({
    queryKey: ["public-booking-status", slug, appointmentId],
    queryFn: () => getPublicBookingStatus(slug, appointmentId),
    // Polling this endpoint IS the payment-status refresh mechanism (no
    // public webhook target without a tunnel) -- keeps polling only while
    // there's an actual pending deposit to resolve.
    refetchInterval: (query) => {
      const data = query.state.data as PublicBooking | undefined;
      return data?.payment_status === "pending" ? 4000 : false;
    },
  });

  if (statusQuery.isLoading) {
    return <p>Carregando...</p>;
  }
  if (statusQuery.isError || !statusQuery.data) {
    return <p className="error-text">Não encontramos esse agendamento.</p>;
  }

  const booking = statusQuery.data;
  const awaitingPayment = booking.deposit_required && booking.payment_status === "pending";

  return (
    <div className="card public-booking-status">
      <h2>{STATUS_LABELS[booking.status] ?? booking.status}</h2>
      <p>
        {booking.service_name} com {booking.employee_name}
      </p>
      <p>{new Date(booking.starts_at).toLocaleString("pt-BR", { dateStyle: "long", timeStyle: "short" })}</p>

      {booking.deposit_required && (
        <div className="public-booking-deposit">
          <p>
            Sinal: R$ {booking.deposit_amount} &middot;{" "}
            {booking.payment_status === "approved" ? "pago" : "pendente"}
          </p>
          {awaitingPayment && booking.pix_qr_code && (
            <div>
              <p>Pague com PIX copia e cola:</p>
              <textarea readOnly value={booking.pix_qr_code} rows={3} />
              <p>Assim que o pagamento for reconhecido, esta página atualiza sozinha.</p>
            </div>
          )}
        </div>
      )}

      <p className="public-booking-reference">Guarde este link para consultar seu agendamento depois.</p>
    </div>
  );
}
