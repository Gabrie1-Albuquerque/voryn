"""Exercises the company/employee/client/catalog services directly (not
through HTTP) against a real Postgres transaction. These use session.flush()
internally, not commit() -- see core/database.py:get_tenant_db's docstring
for why: an earlier version called commit() then queried again (a refresh,
a re-fetch-with-relations) and broke, because committing ends the
transaction the tenant's RLS SET LOCAL context lives in. flush() keeps the
transaction open, so create-then-immediately-read-back (exactly what these
tests do) is the right shape to catch a regression back to that pattern.
"""

import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.tenant import User
from app.schemas.catalog import (
    RoomCreateRequest,
    ServiceCreateRequest,
    ServiceUpdateRequest,
)
from app.schemas.client import ClientCreateRequest, ClientNoteCreateRequest
from app.schemas.company import CompanyUpdateRequest
from app.schemas.employee import AvailabilityWindow, EmployeeCreateRequest
from app.services import catalog_service, client_service, company_service, employee_service


async def _seed_user(session: AsyncSession, tenant_id: uuid.UUID) -> User:
    user = User(
        tenant_id=tenant_id,
        email=f"{uuid.uuid4()}@example.com",
        password_hash=hash_password("senha-forte-123"),
        role=UserRole.MANAGER,
    )
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_company_get_and_update(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant(name="Salao Original")

    company = await company_service.get_company(db_session, tenant_id)
    assert company.name == "Salao Original"

    updated = await company_service.update_company(
        db_session, tenant_id, CompanyUpdateRequest(name="Salao Renomeado")
    )
    assert updated.name == "Salao Renomeado"

    # Re-fetching in the same "request" must see the update without needing
    # a commit -- flush() already sent it to Postgres.
    refetched = await company_service.get_company(db_session, tenant_id)
    assert refetched.name == "Salao Renomeado"


@pytest.mark.asyncio
async def test_company_reminder_hours_default_and_update(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()

    # New tenants keep the hours the worker hardcoded before this became
    # configurable -- no silent behavior change for existing companies.
    company = await company_service.get_company(db_session, tenant_id)
    assert company.reminder_first_hours == 24
    assert company.reminder_second_hours == 2

    updated = await company_service.update_company(
        db_session, tenant_id, CompanyUpdateRequest(reminder_first_hours=48, reminder_second_hours=4)
    )
    assert updated.reminder_first_hours == 48
    assert updated.reminder_second_hours == 4


def test_company_reminder_hours_order_rejected_by_schema():
    with pytest.raises(PydanticValidationError):
        CompanyUpdateRequest(reminder_first_hours=2, reminder_second_hours=2)


@pytest.mark.asyncio
async def test_service_create_and_deposit_validation(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()

    service = await catalog_service.create_service(
        db_session,
        tenant_id,
        ServiceCreateRequest(
            name="Corte",
            duration_minutes=30,
            price=Decimal("50.00"),
            deposit_required=True,
            deposit_type="fixed_amount",
            deposit_value=Decimal("10.00"),
        ),
    )
    assert service.deposit_value == Decimal("10.00")

    # Turning deposit_required on via PATCH without also supplying the
    # deposit fields must be rejected -- a partial update can't be validated
    # at the Pydantic schema level alone (unlike create), since it depends
    # on merging with existing state.
    other_service = await catalog_service.create_service(
        db_session,
        tenant_id,
        ServiceCreateRequest(name="Escova", duration_minutes=20, price=Decimal("30.00")),
    )
    with pytest.raises(ValidationError):
        await catalog_service.update_service(
            db_session, tenant_id, other_service.id, ServiceUpdateRequest(deposit_required=True)
        )


@pytest.mark.asyncio
async def test_room_crud_and_soft_delete(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()

    room = await catalog_service.create_room(db_session, tenant_id, RoomCreateRequest(name="Sala 1"))
    assert room.is_active is True

    await catalog_service.deactivate_room(db_session, tenant_id, room.id)
    refetched = await catalog_service.get_room(db_session, tenant_id, room.id)
    assert refetched.is_active is False


@pytest.mark.asyncio
async def test_employee_create_with_services_and_availability(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service = await catalog_service.create_service(
        db_session, tenant_id, ServiceCreateRequest(name="Corte", duration_minutes=30, price=Decimal("50"))
    )

    employee = await employee_service.create_employee(
        db_session, tenant_id, EmployeeCreateRequest(name="Maria", service_ids=[service.id])
    )
    assert [s.id for s in employee.services] == [service.id]

    updated = await employee_service.replace_employee_availability(
        db_session,
        tenant_id,
        employee.id,
        [AvailabilityWindow(weekday=0, start_time="09:00", end_time="18:00")],
    )
    assert len(updated.availability) == 1
    assert updated.availability[0].weekday == 0

    cleared = await employee_service.replace_employee_services(db_session, tenant_id, employee.id, [])
    assert cleared.services == []


@pytest.mark.asyncio
async def test_employee_create_with_unknown_service_id_raises(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()

    with pytest.raises(NotFoundError):
        await employee_service.create_employee(
            db_session, tenant_id, EmployeeCreateRequest(name="Maria", service_ids=[uuid.uuid4()])
        )


@pytest.mark.asyncio
async def test_client_and_notes_lifecycle(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    author = await _seed_user(db_session, tenant_id)

    client = await client_service.create_client(
        db_session, tenant_id, ClientCreateRequest(name="Joana", phone="5511999998888")
    )

    note = await client_service.add_note(
        db_session,
        tenant_id,
        client.id,
        author.id,
        ClientNoteCreateRequest(note_type="alert", body="Alergia a amonia"),
    )
    assert note.note_type.value == "alert"

    notes = await client_service.list_notes(db_session, tenant_id, client.id)
    assert len(notes) == 1
    assert notes[0].body == "Alergia a amonia"

    await client_service.deactivate_client(db_session, tenant_id, client.id)
    refetched = await client_service.get_client(db_session, tenant_id, client.id)
    assert refetched.is_active is False


@pytest.mark.asyncio
async def test_client_from_other_tenant_is_not_found(db_session: AsyncSession, make_tenant):
    tenant_a = await make_tenant("tenant-a")
    client = await client_service.create_client(
        db_session, tenant_a, ClientCreateRequest(name="Joana", phone="5511999998888")
    )

    tenant_b = await make_tenant("tenant-b")
    with pytest.raises(NotFoundError):
        await client_service.get_client(db_session, tenant_b, client.id)
