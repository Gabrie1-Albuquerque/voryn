import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { updateService } from "../../api/catalog";
import type { DepositType, Service } from "../../api/types";
import { ApiError } from "../../lib/api";
import { Modal } from "../../components/Modal";

interface Props {
  service: Service;
  onClose: () => void;
}

export function ServiceEditModal({ service, onClose }: Props) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(service.name);
  const [duration, setDuration] = useState(String(service.duration_minutes));
  const [price, setPrice] = useState(service.price);
  const [depositRequired, setDepositRequired] = useState(service.deposit_required);
  const [depositType, setDepositType] = useState<DepositType>(service.deposit_type ?? "fixed_amount");
  const [depositValue, setDepositValue] = useState(service.deposit_value ?? "");
  const [error, setError] = useState<string | null>(null);

  const updateMutation = useMutation({
    mutationFn: () =>
      updateService(service.id, {
        name,
        duration_minutes: Number(duration),
        price,
        deposit_required: depositRequired,
        deposit_type: depositRequired ? depositType : null,
        deposit_value: depositRequired ? depositValue : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível salvar."),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    updateMutation.mutate();
  }

  return (
    <Modal title="Editar serviço" onClose={onClose}>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Nome
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Duração (min)
          <input type="number" value={duration} onChange={(e) => setDuration(e.target.value)} required />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Preço
          <input type="number" step="0.01" value={price} onChange={(e) => setPrice(e.target.value)} required />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input type="checkbox" checked={depositRequired} onChange={(e) => setDepositRequired(e.target.checked)} />
          Exige sinal para confirmar
        </label>
        {depositRequired && (
          <>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              Tipo de sinal
              <select value={depositType} onChange={(e) => setDepositType(e.target.value as DepositType)}>
                <option value="fixed_amount">Valor fixo (R$)</option>
                <option value="percentage">Percentual (%)</option>
              </select>
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {depositType === "percentage" ? "Percentual do sinal" : "Valor do sinal (R$)"}
              <input
                type="number"
                step="0.01"
                value={depositValue}
                onChange={(e) => setDepositValue(e.target.value)}
                required
              />
            </label>
          </>
        )}
        {error && <p className="error-text">{error}</p>}
        <div>
          <button type="submit" className="primary" disabled={updateMutation.isPending}>
            Salvar
          </button>
        </div>
      </form>
    </Modal>
  );
}
