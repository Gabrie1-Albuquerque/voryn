import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import WaitlistStatus


class WaitlistEntryResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    service_id: uuid.UUID
    preferred_employee_id: uuid.UUID | None
    preferred_window_start: datetime
    preferred_window_end: datetime
    status: WaitlistStatus


class WaitlistEntryCreateRequest(BaseModel):
    client_id: uuid.UUID
    service_id: uuid.UUID
    preferred_window_start: datetime
    preferred_window_end: datetime
    preferred_employee_id: uuid.UUID | None = None
