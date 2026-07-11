import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { createRoom, createService, listRooms, listServices } from "../../api/catalog";
import { ApiError } from "../../lib/api";

export function CatalogPage() {
  const queryClient = useQueryClient();
  const servicesQuery = useQuery({ queryKey: ["services"], queryFn: listServices });
  const roomsQuery = useQuery({ queryKey: ["rooms"], queryFn: listRooms });

  const [serviceName, setServiceName] = useState("");
  const [duration, setDuration] = useState("30");
  const [price, setPrice] = useState("0");
  const [roomName, setRoomName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const createServiceMutation = useMutation({
    mutationFn: () => createService({ name: serviceName, duration_minutes: Number(duration), price }),
    onSuccess: () => {
      setServiceName("");
      queryClient.invalidateQueries({ queryKey: ["services"] });
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível criar o serviço."),
  });

  const createRoomMutation = useMutation({
    mutationFn: () => createRoom({ name: roomName }),
    onSuccess: () => {
      setRoomName("");
      queryClient.invalidateQueries({ queryKey: ["rooms"] });
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível criar a sala."),
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
      <div>
        <h1>Serviços</h1>
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setError(null);
            createServiceMutation.mutate();
          }}
          className="card"
          style={{ display: "flex", gap: 8, marginBottom: 16, maxWidth: 500 }}
        >
          <input placeholder="Nome do serviço" value={serviceName} onChange={(e) => setServiceName(e.target.value)} required />
          <input
            type="number"
            placeholder="Duração (min)"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            style={{ width: 130 }}
            required
          />
          <input
            type="number"
            step="0.01"
            placeholder="Preço"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            style={{ width: 100 }}
            required
          />
          <button type="submit" className="primary" disabled={createServiceMutation.isPending}>
            Adicionar
          </button>
        </form>
        <table className="card">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Duração</th>
              <th>Preço</th>
              <th>Sinal</th>
            </tr>
          </thead>
          <tbody>
            {servicesQuery.data?.map((service) => (
              <tr key={service.id}>
                <td>{service.name}</td>
                <td>{service.duration_minutes}min</td>
                <td>R$ {service.price}</td>
                <td>{service.deposit_required ? `R$ ${service.deposit_value}` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div>
        <h1>Salas / Recursos</h1>
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setError(null);
            createRoomMutation.mutate();
          }}
          className="card"
          style={{ display: "flex", gap: 8, marginBottom: 16, maxWidth: 400 }}
        >
          <input placeholder="Nome da sala" value={roomName} onChange={(e) => setRoomName(e.target.value)} required />
          <button type="submit" className="primary" disabled={createRoomMutation.isPending}>
            Adicionar
          </button>
        </form>
        <table className="card">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Ativo</th>
            </tr>
          </thead>
          <tbody>
            {roomsQuery.data?.map((room) => (
              <tr key={room.id}>
                <td>{room.name}</td>
                <td>{room.is_active ? "Sim" : "Não"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {error && <p className="error-text">{error}</p>}
    </div>
  );
}
