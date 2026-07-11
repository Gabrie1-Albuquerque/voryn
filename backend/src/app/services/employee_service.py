import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.catalog import Service
from app.models.tenant import Employee, EmployeeAvailability
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.employee import AvailabilityWindow, EmployeeCreateRequest, EmployeeUpdateRequest


async def _resolve_services(session: AsyncSession, tenant_id: uuid.UUID, service_ids: list[uuid.UUID]) -> list[Service]:
    if not service_ids:
        return []
    stmt = select(Service).where(Service.tenant_id == tenant_id, Service.id.in_(service_ids))
    result = await session.execute(stmt)
    services = list(result.scalars().all())
    if len(services) != len(set(service_ids)):
        raise NotFoundError("one or more service_ids not found")
    return services


async def list_employees(session: AsyncSession, tenant_id: uuid.UUID) -> list[Employee]:
    return await EmployeeRepository(session, tenant_id).list_with_relations()


async def get_employee(session: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID) -> Employee:
    employee = await EmployeeRepository(session, tenant_id).get_with_relations(employee_id)
    if employee is None:
        raise NotFoundError("employee not found")
    return employee


async def create_employee(session: AsyncSession, tenant_id: uuid.UUID, data: EmployeeCreateRequest) -> Employee:
    # services must be set in the constructor, not assigned after the fact:
    # SQLAlchemy's async mode can't do the implicit lazy-load of the OLD
    # collection state that a plain `employee.services = [...]` assignment
    # needs on an already-flushed object (there's no awaited context for it
    # to piggyback on, so it raises MissingGreenlet). A transient object's
    # collection is already known-empty, so setting it at construction time
    # needs no such load.
    services = await _resolve_services(session, tenant_id, data.service_ids)
    employee = EmployeeRepository(session, tenant_id).add(Employee(name=data.name, services=services))
    await session.flush()
    return await get_employee(session, tenant_id, employee.id)


async def update_employee(
    session: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID, data: EmployeeUpdateRequest
) -> Employee:
    employee = await get_employee(session, tenant_id, employee_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    await session.flush()
    return await get_employee(session, tenant_id, employee_id)


async def deactivate_employee(session: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID) -> None:
    # Soft delete: appointments reference employee_id with ON DELETE RESTRICT
    # (a real historical record shouldn't vanish), so "removing" a staff
    # member from the schedule means deactivating, not deleting the row.
    employee = await get_employee(session, tenant_id, employee_id)
    employee.is_active = False
    await session.flush()


async def replace_employee_services(
    session: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID, service_ids: list[uuid.UUID]
) -> Employee:
    employee = await get_employee(session, tenant_id, employee_id)
    employee.services = await _resolve_services(session, tenant_id, service_ids)
    await session.flush()
    return await get_employee(session, tenant_id, employee_id)


async def replace_employee_availability(
    session: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID, windows: list[AvailabilityWindow]
) -> Employee:
    await get_employee(session, tenant_id, employee_id)  # 404s if missing/other tenant
    await session.execute(
        delete(EmployeeAvailability).where(
            EmployeeAvailability.tenant_id == tenant_id, EmployeeAvailability.employee_id == employee_id
        )
    )
    for window in windows:
        session.add(
            EmployeeAvailability(
                tenant_id=tenant_id,
                employee_id=employee_id,
                weekday=window.weekday,
                start_time=window.start_time,
                end_time=window.end_time,
            )
        )
    await session.flush()
    return await get_employee(session, tenant_id, employee_id)
