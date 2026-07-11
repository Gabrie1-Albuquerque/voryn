import uuid
from datetime import time

from pydantic import BaseModel, Field


class AvailabilityWindow(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0=segunda .. 6=domingo")
    start_time: time
    end_time: time


class EmployeeResponse(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    service_ids: list[uuid.UUID]
    availability: list[AvailabilityWindow]

    @classmethod
    def from_model(cls, employee) -> "EmployeeResponse":
        return cls(
            id=employee.id,
            name=employee.name,
            is_active=employee.is_active,
            service_ids=[s.id for s in employee.services],
            availability=[
                AvailabilityWindow(weekday=a.weekday, start_time=a.start_time, end_time=a.end_time)
                for a in employee.availability
            ],
        )


class EmployeeCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    service_ids: list[uuid.UUID] = []


class EmployeeUpdateRequest(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class ReplaceAvailabilityRequest(BaseModel):
    windows: list[AvailabilityWindow]


class ReplaceServicesRequest(BaseModel):
    service_ids: list[uuid.UUID]
