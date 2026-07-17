import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import {
  createRoom,
  createService,
  deactivateRoom,
  deactivateService,
  listRooms,
  listServices,
  updateRoom,
  updateService,
} from "../../api/catalog";
import type { Service } from "../../api/types";
import { ApiError } from "../../lib/api";
import { ServiceEditModal } from "./ServiceEditModal";

export function CatalogPage() {
  const queryClient = useQueryClient();
  const servicesQuery = useQuery({ queryKey: ["services"], queryFn: listServices });
  const roomsQuery = useQuery({ queryKey: ["rooms"], queryFn: listRooms });

  const [serviceName, setServiceName] = useState("");
  const [duration, setDuration] = useState("30");
  const [price, setPrice] = useState("0");
  const [roomName, setRoomName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editingService, setEditingService] = useState<Service | null>(null);
  const [showInactiveServices, setShowInactiveServices] = useState(false);
  const [showInactiveRooms, setShowInactiveRooms] = useState(false);

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

  const toggleServiceMutation = useMutation({
    mutationFn: async (service: Service) => {
      if (service.is_active) {
        await deactivateService(service.id);
      } else {
        await updateService(service.id, { is_active: true });
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["services"] }),
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível atualizar."),
  });

  function handleToggleService(service: Service) {
    if (service.is_active && !window.confirm(`Desativar ${service.name}? Ele deixará de aparecer no link público.`)) {
      return;
    }
    toggleServiceMutation.mutate(service);
  }

  const toggleRoomMutation = useMutation({
    mutationFn: async (room: { id: string; is_active: boolean }) => {
      if (room.is_active) {
        await deactivateRoom(room.id);
      } else {
        await updateRoom(room.id, { is_active: true });
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rooms"] }),
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível atualizar."),
  });

  function handleToggleRoom(room: { id: string; name: string; is_active: boolean }) {
    if (room.is_active && !window.confirm(`Desativar ${room.name}?`)) {
      return;
    }
    toggleRoomMutation.mutate(room);
  }

  const renameRoomMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => updateRoom(id, { name }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rooms"] }),
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Não foi possível renomear."),
  });

  function handleRenameRoom(room: { id: string; name: string }) {
    const name = window.prompt("Novo nome da sala:", room.name);
    if (name && name.trim() && name !== room.name) {
      renameRoomMutation.mutate({ id: room.id, name: name.trim() });
    }
  }

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
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={showInactiveServices}
            onChange={(e) => setShowInactiveServices(e.target.checked)}
          />
          Mostrar desativados
        </label>
        <table className="card">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Duração</th>
              <th>Preço</th>
              <th>Sinal</th>
              <th>Ativo</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {servicesQuery.data?.filter((service) => showInactiveServices || service.is_active).map((service) => (
              <tr key={service.id}>
                <td>{service.name}</td>
                <td>{service.duration_minutes}min</td>
                <td>R$ {service.price}</td>
                <td>{service.deposit_required ? `R$ ${service.deposit_value}` : "—"}</td>
                <td>{service.is_active ? "Sim" : "Não"}</td>
                <td style={{ display: "flex", gap: 8 }}>
                  <button onClick={() => setEditingService(service)}>Editar</button>
                  <button disabled={toggleServiceMutation.isPending} onClick={() => handleToggleService(service)}>
                    {service.is_active ? "Desativar" : "Reativar"}
                  </button>
                </td>
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
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={showInactiveRooms}
            onChange={(e) => setShowInactiveRooms(e.target.checked)}
          />
          Mostrar desativadas
        </label>
        <table className="card">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Ativo</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {roomsQuery.data?.filter((room) => showInactiveRooms || room.is_active).map((room) => (
              <tr key={room.id}>
                <td>{room.name}</td>
                <td>{room.is_active ? "Sim" : "Não"}</td>
                <td style={{ display: "flex", gap: 8 }}>
                  <button onClick={() => handleRenameRoom(room)}>Renomear</button>
                  <button disabled={toggleRoomMutation.isPending} onClick={() => handleToggleRoom(room)}>
                    {room.is_active ? "Desativar" : "Reativar"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {error && <p className="error-text">{error}</p>}

      {editingService && <ServiceEditModal service={editingService} onClose={() => setEditingService(null)} />}
    </div>
  );
}
