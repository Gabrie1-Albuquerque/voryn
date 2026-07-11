import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.enums import AppointmentSource, AppointmentStatus, PaymentStatus
from app.schemas.catalog import ServiceCreateRequest
from app.schemas.client import ClientCreateRequest
from app.schemas.employee import EmployeeCreateRequest
from app.services import appointment_service, catalog_service, client_service, employee_service, payment_service

BASE_START = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)


async def _seed_with_deposit(db_session: AsyncSession, tenant_id: uuid.UUID, *, deposit_type="fixed_amount", deposit_value=Decimal("20.00")):
    service = await catalog_service.create_service(
        db_session,
        tenant_id,
        ServiceCreateRequest(
            name="Corte",
            duration_minutes=60,
            price=Decimal("100.00"),
            deposit_required=True,
            deposit_type=deposit_type,
            deposit_value=deposit_value,
        ),
    )
    employee = await employee_service.create_employee(db_session, tenant_id, EmployeeCreateRequest(name="Maria"))
    client = await client_service.create_client(
        db_session, tenant_id, ClientCreateRequest(name="Joana", phone="5511999998888")
    )
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=client.id,
        employee_id=employee.id,
        service_id=service.id,
        starts_at=BASE_START,
        source=AppointmentSource.PUBLIC_BOOKING,  # starts Pending, so deposit-gating is meaningful
    )
    return {"service": service, "employee": employee, "client": client, "appointment": appointment}


@pytest.mark.asyncio
async def test_deposit_charge_with_fixed_amount(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed_with_deposit(db_session, tenant_id, deposit_type="fixed_amount", deposit_value=Decimal("20.00"))

    result = await payment_service.create_deposit_charge(
        db_session, tenant_id, seed["appointment"].id, method="pix"
    )

    assert result.record.amount == Decimal("20.00")
    assert result.record.status == PaymentStatus.APPROVED  # mock provider auto-approves
    assert result.pix_qr_code is not None


@pytest.mark.asyncio
async def test_deposit_charge_with_percentage(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed_with_deposit(db_session, tenant_id, deposit_type="percentage", deposit_value=Decimal("30"))

    result = await payment_service.create_deposit_charge(
        db_session, tenant_id, seed["appointment"].id, method="pix"
    )

    # 30% of 100.00
    assert result.record.amount == Decimal("30.00")


@pytest.mark.asyncio
async def test_approved_deposit_confirms_pending_appointment(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed_with_deposit(db_session, tenant_id)
    assert seed["appointment"].status == AppointmentStatus.PENDING

    await payment_service.create_deposit_charge(db_session, tenant_id, seed["appointment"].id, method="pix")

    confirmed = await appointment_service.get_appointment(db_session, tenant_id, seed["appointment"].id)
    assert confirmed.status == AppointmentStatus.CONFIRMED


@pytest.mark.asyncio
async def test_deposit_charge_on_service_without_deposit_raises(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service = await catalog_service.create_service(
        db_session, tenant_id, ServiceCreateRequest(name="Escova", duration_minutes=30, price=Decimal("40"))
    )
    employee = await employee_service.create_employee(db_session, tenant_id, EmployeeCreateRequest(name="Maria"))
    client = await client_service.create_client(
        db_session, tenant_id, ClientCreateRequest(name="Joana", phone="5511999998888")
    )
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=client.id,
        employee_id=employee.id,
        service_id=service.id,
        starts_at=BASE_START,
    )

    with pytest.raises(ValidationError):
        await payment_service.create_deposit_charge(db_session, tenant_id, appointment.id, method="pix")
