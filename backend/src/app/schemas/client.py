import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ClientNoteType


class ClientResponse(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    email: str | None
    document: str | None
    is_active: bool


class ClientCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    email: str | None = None
    document: str | None = None


class ClientUpdateRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    document: str | None = None
    is_active: bool | None = None


class ClientNoteResponse(BaseModel):
    id: uuid.UUID
    note_type: ClientNoteType
    body: str
    author_user_id: uuid.UUID | None
    appointment_id: uuid.UUID | None
    created_at: datetime


class ClientNoteCreateRequest(BaseModel):
    note_type: ClientNoteType = ClientNoteType.GENERAL
    body: str = Field(min_length=1)
    appointment_id: uuid.UUID | None = None
