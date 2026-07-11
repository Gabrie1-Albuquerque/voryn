import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AppointmentSource, AppointmentStatus


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    client_name: str
    employee_id: uuid.UUID
    employee_name: str
    service_id: uuid.UUID
    service_name: str
    room_id: uuid.UUID | None
    room_name: str | None
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    source: AppointmentSource
    notes: str | None

    @classmethod
    def from_model(cls, appointment) -> "AppointmentResponse":
        return cls(
            id=appointment.id,
            client_id=appointment.client_id,
            client_name=appointment.client.name,
            employee_id=appointment.employee_id,
            employee_name=appointment.employee.name,
            service_id=appointment.service_id,
            service_name=appointment.service.name,
            room_id=appointment.room_id,
            room_name=appointment.room.name if appointment.room else None,
            starts_at=appointment.starts_at,
            ends_at=appointment.ends_at,
            status=appointment.status,
            source=appointment.source,
            notes=appointment.notes,
        )


class AppointmentCreateRequest(BaseModel):
    client_id: uuid.UUID
    employee_id: uuid.UUID
    service_id: uuid.UUID
    room_id: uuid.UUID | None = None
    starts_at: datetime
    notes: str | None = None


class AppointmentRescheduleRequest(BaseModel):
    new_starts_at: datetime
