import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock, Copy, XCircle } from "lucide-react";
import { useState } from "react";
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

function StatusIcon({ status }: { status: AppointmentStatus }) {
  if (status === "confirmed" || status === "completed") {
    return (
      <span className="public-booking-status-icon ok">
        <CheckCircle2 size={34} />
      </span>
    );
  }
  if (status === "cancelled") {
    return (
      <span className="public-booking-status-icon bad">
        <XCircle size={34} />
      </span>
    );
  }
  return (
    <span className="public-booking-status-icon waiting">
      <Clock size={34} />
    </span>
  );
}

function PixCopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Clipboard API unavailable (e.g. non-HTTPS on some browsers): the
      // code stays visible in the textarea below for manual selection.
    }
  }

  return (
    <button type="button" className="primary" onClick={copy} style={{ display: "inline-flex", gap: 8, alignItems: "center", justifyContent: "center" }}>
      <Copy size={16} />
      {copied ? "Copiado!" : "Copiar código PIX"}
    </button>
  );
}

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
      <StatusIcon status={booking.status} />
      <h2 style={{ margin: 0 }}>{STATUS_LABELS[booking.status] ?? booking.status}</h2>
      <p>
        <strong>{booking.service_name}</strong> com {booking.employee_name}
      </p>
      <p>{new Date(booking.starts_at).toLocaleString("pt-BR", { dateStyle: "long", timeStyle: "short" })}</p>

      {booking.deposit_required && (
        <div className="public-booking-deposit">
          <p>
            Sinal: <strong>R$ {booking.deposit_amount}</strong> ·{" "}
            {booking.payment_status === "approved" ? "pago ✓" : "pendente"}
          </p>
          {awaitingPayment && booking.pix_qr_code && (
            <>
              <p>Pague com PIX copia e cola para confirmar seu horário:</p>
              <PixCopyButton code={booking.pix_qr_code} />
              <textarea className="pix-code" readOnly value={booking.pix_qr_code} rows={3} />
              <p className="public-booking-reference">
                Assim que o pagamento for reconhecido, esta página atualiza sozinha.
              </p>
            </>
          )}
        </div>
      )}

      <p className="public-booking-reference">Guarde este link para consultar seu agendamento depois.</p>
    </div>
  );
}
