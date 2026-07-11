import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    pass


def pg_enum(enum_cls: type[PyEnum], name: str) -> SAEnum:
    """Postgres-native enum, stored using the Python enum's string values."""
    return SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TenantMixin:
    """Every tenant-owned table gets a non-nullable, indexed FK to companies.id.

    Repositories must always filter on this column explicitly; Postgres RLS
    (set up in core/database.py) is the defense-in-depth backstop for the
    same rule, not a substitute for it.
    """

    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:  # noqa: N805
        return mapped_column(
            UUID(as_uuid=True),
            ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


# Re-exported for convenience so model modules only need `from app.models.base import *`-style
# imports for the common column type shorthands used everywhere.
UUIDType: Any = UUID(as_uuid=True)
