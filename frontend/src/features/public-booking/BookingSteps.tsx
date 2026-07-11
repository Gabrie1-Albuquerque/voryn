import { Check } from "lucide-react";

const STEPS = ["Serviço", "Profissional", "Horário"];

// current is 1-based (1 = Serviço). Steps below it render as done, above as
// upcoming. The status/confirmation page simply doesn't render this.
export function BookingSteps({ current }: { current: number }) {
  return (
    <div className="booking-steps" aria-label={`Etapa ${current} de ${STEPS.length}`}>
      {STEPS.map((label, i) => {
        const step = i + 1;
        const state = step < current ? "done" : step === current ? "current" : "";
        return (
          <span key={label} style={{ display: "contents" }}>
            {i > 0 && <span className="booking-step-line" />}
            <span className={`booking-step ${state}`}>
              <span className="booking-step-dot">{step < current ? <Check size={13} /> : step}</span>
              {label}
            </span>
          </span>
        );
      })}
    </div>
  );
}
