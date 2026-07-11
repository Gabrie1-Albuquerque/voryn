import uuid
from datetime import date as date_

from fastapi import APIRouter, Depends, Query

from app.core.database import SlugTenantContext, get_tenant_db_by_slug
from app.schemas.public_booking import (
    AvailabilityResponse,
    PublicBookingCreateRequest,
    PublicBookingResponse,
    PublicCompanyResponse,
    PublicEmployeeResponse,
    PublicServiceResponse,
)
from app.services import booking_service

router = APIRouter()


@router.get("/{company_slug}", response_model=PublicCompanyResponse)
async def get_public_company(ctx: SlugTenantContext = Depends(get_tenant_db_by_slug)) -> PublicCompanyResponse:
    company = await booking_service.get_company(ctx.session, ctx.tenant_id)
    return PublicCompanyResponse(name=company.name, slug=company.slug, timezone=company.timezone)


@router.get("/{company_slug}/services", response_model=list[PublicServiceResponse])
async def list_public_services(
    ctx: SlugTenantContext = Depends(get_tenant_db_by_slug),
) -> list[PublicServiceResponse]:
    services = await booking_service.list_bookable_services(ctx.session, ctx.tenant_id)
    return [
        PublicServiceResponse(
            id=s.id,
            name=s.name,
            duration_minutes=s.duration_minutes,
            price=s.price,
            deposit_required=s.deposit_required,
            deposit_type=s.deposit_type,
            deposit_value=s.deposit_value,
        )
        for s in services
    ]


@router.get("/{company_slug}/employees", response_model=list[PublicEmployeeResponse])
async def list_public_employees(
    ctx: SlugTenantContext = Depends(get_tenant_db_by_slug),
) -> list[PublicEmployeeResponse]:
    employees = await booking_service.list_active_employees(ctx.session, ctx.tenant_id)
    return [PublicEmployeeResponse(id=e.id, name=e.name, service_ids=[s.id for s in e.services]) for e in employees]


@router.get("/{company_slug}/availability", response_model=AvailabilityResponse)
async def get_public_availability(
    employee_id: uuid.UUID,
    service_id: uuid.UUID,
    date: date_ = Query(...),
    ctx: SlugTenantContext = Depends(get_tenant_db_by_slug),
) -> AvailabilityResponse:
    slots = await booking_service.compute_availability(
        ctx.session, ctx.tenant_id, employee_id=employee_id, service_id=service_id, on_date=date
    )
    return AvailabilityResponse(slots=slots)


@router.post("/{company_slug}/bookings", response_model=PublicBookingResponse, status_code=201)
async def create_public_booking(
    body: PublicBookingCreateRequest, ctx: SlugTenantContext = Depends(get_tenant_db_by_slug)
) -> PublicBookingResponse:
    return await booking_service.create_booking(
        ctx.session,
        ctx.tenant_id,
        service_id=body.service_id,
        employee_id=body.employee_id,
        starts_at=body.starts_at,
        client_name=body.client_name,
        client_phone=body.client_phone,
        client_email=body.client_email,
        notes=body.notes,
        payment_method=body.payment_method,
    )


@router.get("/{company_slug}/bookings/{appointment_id}", response_model=PublicBookingResponse)
async def get_public_booking(
    appointment_id: uuid.UUID, ctx: SlugTenantContext = Depends(get_tenant_db_by_slug)
) -> PublicBookingResponse:
    return await booking_service.get_booking_status(ctx.session, ctx.tenant_id, appointment_id)
