"""Proves the DB-level exclusion constraints in migration 0001 actually
prevent double-booking under the exact scenario that makes application-only
checking unsafe: this is the backstop for races between concurrent requests
(e.g. a staff member and a public-booking customer hitting the same slot),
not just a nicety on top of an application-level pre-check.

appointment_service.py (task: engine de agendamento) will add its own tests
for the friendly-error translation and the application-level pre-check; this
file is scoped to what the migration itself is responsible for guaranteeing.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection

BASE_START = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)


async def _seed_catalog(conn: AsyncConnection, tenant_id: uuid.UUID) -> dict[str, uuid.UUID]:
    employee_id = uuid.uuid4()
    other_employee_id = uuid.uuid4()
    service_id = uuid.uuid4()
    client_id = uuid.uuid4()
    room_id = uuid.uuid4()

    await conn.execute(
        text("INSERT INTO employees (id, tenant_id, name) VALUES (:id, :t, 'Funcionaria A')"),
        {"id": employee_id, "t": tenant_id},
    )
    await conn.execute(
        text("INSERT INTO employees (id, tenant_id, name) VALUES (:id, :t, 'Funcionaria B')"),
        {"id": other_employee_id, "t": tenant_id},
    )
    await conn.execute(
        text(
            "INSERT INTO services (id, tenant_id, name, duration_minutes, price) "
            "VALUES (:id, :t, 'Corte', 60, 50.00)"
        ),
        {"id": service_id, "t": tenant_id},
    )
    await conn.execute(
        text("INSERT INTO clients (id, tenant_id, name, phone) VALUES (:id, :t, 'Cliente', '5511999990000')"),
        {"id": client_id, "t": tenant_id},
    )
    await conn.execute(
        text("INSERT INTO rooms (id, tenant_id, name) VALUES (:id, :t, 'Sala 1')"),
        {"id": room_id, "t": tenant_id},
    )
    return {
        "employee_id": employee_id,
        "other_employee_id": other_employee_id,
        "service_id": service_id,
        "client_id": client_id,
        "room_id": room_id,
    }


async def _insert_appointment(
    conn: AsyncConnection,
    tenant_id: uuid.UUID,
    *,
    employee_id: uuid.UUID,
    client_id: uuid.UUID,
    service_id: uuid.UUID,
    starts_at: datetime,
    ends_at: datetime,
    room_id: uuid.UUID | None = None,
    status: str = "confirmed",
) -> uuid.UUID:
    appointment_id = uuid.uuid4()
    await conn.execute(
        text(
            """
            INSERT INTO appointments
                (id, tenant_id, client_id, employee_id, service_id, room_id, starts_at, ends_at, status)
            VALUES
                (:id, :tenant_id, :client_id, :employee_id, :service_id, :room_id, :starts_at, :ends_at, :status)
            """
        ),
        {
            "id": appointment_id,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "employee_id": employee_id,
            "service_id": service_id,
            "room_id": room_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "status": status,
        },
    )
    return appointment_id


@pytest.mark.asyncio
async def test_overlapping_appointment_same_employee_is_rejected(db_connection: AsyncConnection, make_tenant):
    tenant_id = await make_tenant()
    catalog = await _seed_catalog(db_connection, tenant_id)

    await _insert_appointment(
        db_connection,
        tenant_id,
        employee_id=catalog["employee_id"],
        client_id=catalog["client_id"],
        service_id=catalog["service_id"],
        starts_at=BASE_START,
        ends_at=BASE_START + timedelta(hours=1),
    )

    with pytest.raises(IntegrityError, match="excl_appointments_employee_overlap"):
        await _insert_appointment(
            db_connection,
            tenant_id,
            employee_id=catalog["employee_id"],
            client_id=catalog["client_id"],
            service_id=catalog["service_id"],
            starts_at=BASE_START + timedelta(minutes=30),
            ends_at=BASE_START + timedelta(minutes=90),
            status="pending",
        )


@pytest.mark.asyncio
async def test_back_to_back_appointments_same_employee_are_allowed(
    db_connection: AsyncConnection, make_tenant
):
    tenant_id = await make_tenant()
    catalog = await _seed_catalog(db_connection, tenant_id)

    await _insert_appointment(
        db_connection,
        tenant_id,
        employee_id=catalog["employee_id"],
        client_id=catalog["client_id"],
        service_id=catalog["service_id"],
        starts_at=BASE_START,
        ends_at=BASE_START + timedelta(hours=1),
    )

    # Starts exactly when the previous one ends -- half-open range, no overlap.
    second_id = await _insert_appointment(
        db_connection,
        tenant_id,
        employee_id=catalog["employee_id"],
        client_id=catalog["client_id"],
        service_id=catalog["service_id"],
        starts_at=BASE_START + timedelta(hours=1),
        ends_at=BASE_START + timedelta(hours=2),
    )
    assert second_id is not None


@pytest.mark.asyncio
async def test_overlapping_appointments_different_employees_are_allowed(
    db_connection: AsyncConnection, make_tenant
):
    tenant_id = await make_tenant()
    catalog = await _seed_catalog(db_connection, tenant_id)

    await _insert_appointment(
        db_connection,
        tenant_id,
        employee_id=catalog["employee_id"],
        client_id=catalog["client_id"],
        service_id=catalog["service_id"],
        starts_at=BASE_START,
        ends_at=BASE_START + timedelta(hours=1),
    )

    second_id = await _insert_appointment(
        db_connection,
        tenant_id,
        employee_id=catalog["other_employee_id"],
        client_id=catalog["client_id"],
        service_id=catalog["service_id"],
        starts_at=BASE_START + timedelta(minutes=15),
        ends_at=BASE_START + timedelta(minutes=75),
    )
    assert second_id is not None


@pytest.mark.asyncio
async def test_cancelled_appointment_does_not_block_new_overlapping_appointment(
    db_connection: AsyncConnection, make_tenant
):
    tenant_id = await make_tenant()
    catalog = await _seed_catalog(db_connection, tenant_id)

    await _insert_appointment(
        db_connection,
        tenant_id,
        employee_id=catalog["employee_id"],
        client_id=catalog["client_id"],
        service_id=catalog["service_id"],
        starts_at=BASE_START,
        ends_at=BASE_START + timedelta(hours=1),
        status="cancelled",
    )

    second_id = await _insert_appointment(
        db_connection,
        tenant_id,
        employee_id=catalog["employee_id"],
        client_id=catalog["client_id"],
        service_id=catalog["service_id"],
        starts_at=BASE_START + timedelta(minutes=15),
        ends_at=BASE_START + timedelta(minutes=75),
    )
    assert second_id is not None


@pytest.mark.asyncio
async def test_overlapping_appointment_same_room_is_rejected_even_with_different_employees(
    db_connection: AsyncConnection, make_tenant
):
    tenant_id = await make_tenant()
    catalog = await _seed_catalog(db_connection, tenant_id)

    await _insert_appointment(
        db_connection,
        tenant_id,
        employee_id=catalog["employee_id"],
        client_id=catalog["client_id"],
        service_id=catalog["service_id"],
        starts_at=BASE_START,
        ends_at=BASE_START + timedelta(hours=1),
        room_id=catalog["room_id"],
    )

    with pytest.raises(IntegrityError, match="excl_appointments_room_overlap"):
        await _insert_appointment(
            db_connection,
            tenant_id,
            employee_id=catalog["other_employee_id"],
            client_id=catalog["client_id"],
            service_id=catalog["service_id"],
            starts_at=BASE_START + timedelta(minutes=30),
            ends_at=BASE_START + timedelta(minutes=90),
            room_id=catalog["room_id"],
            status="pending",
        )


@pytest.mark.asyncio
async def test_overlapping_appointments_without_room_are_never_blocked_by_room_constraint(
    db_connection: AsyncConnection, make_tenant
):
    tenant_id = await make_tenant()
    catalog = await _seed_catalog(db_connection, tenant_id)

    await _insert_appointment(
        db_connection,
        tenant_id,
        employee_id=catalog["employee_id"],
        client_id=catalog["client_id"],
        service_id=catalog["service_id"],
        starts_at=BASE_START,
        ends_at=BASE_START + timedelta(hours=1),
        room_id=None,
    )

    second_id = await _insert_appointment(
        db_connection,
        tenant_id,
        employee_id=catalog["other_employee_id"],
        client_id=catalog["client_id"],
        service_id=catalog["service_id"],
        starts_at=BASE_START + timedelta(minutes=30),
        ends_at=BASE_START + timedelta(minutes=90),
        room_id=None,
    )
    assert second_id is not None
