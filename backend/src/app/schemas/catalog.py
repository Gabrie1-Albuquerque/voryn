import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import DepositType


class ServiceResponse(BaseModel):
    id: uuid.UUID
    name: str
    duration_minutes: int
    price: Decimal
    requires_room: bool
    is_active: bool
    deposit_required: bool
    deposit_type: DepositType | None
    deposit_value: Decimal | None


class ServiceCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    duration_minutes: int = Field(gt=0)
    price: Decimal = Field(ge=0)
    requires_room: bool = False
    deposit_required: bool = False
    deposit_type: DepositType | None = None
    deposit_value: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _deposit_fields_consistent(self) -> "ServiceCreateRequest":
        if self.deposit_required and (self.deposit_type is None or self.deposit_value is None):
            raise ValueError("deposit_type and deposit_value are required when deposit_required is true")
        return self


class ServiceUpdateRequest(BaseModel):
    name: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, ge=0)
    requires_room: bool | None = None
    is_active: bool | None = None
    deposit_required: bool | None = None
    deposit_type: DepositType | None = None
    deposit_value: Decimal | None = Field(default=None, gt=0)


class RoomResponse(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool


class RoomCreateRequest(BaseModel):
    name: str = Field(min_length=1)


class RoomUpdateRequest(BaseModel):
    name: str | None = None
    is_active: bool | None = None
