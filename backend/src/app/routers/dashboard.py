from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_tenant_db
from app.core.deps import CurrentUser, require_role
from app.models.enums import UserRole
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard_service

router = APIRouter()

# Business-wide revenue/occupancy is management information, not something
# an individual Funcionário needs -- same bucket as catalog/employee CRUD
# (Admin/Gestor only), unlike appointments/clients (all three roles).
_MANAGEMENT_ROLE = require_role(UserRole.ADMIN, UserRole.MANAGER)


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    current_user: CurrentUser = Depends(_MANAGEMENT_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> DashboardSummary:
    # Defaults to the trailing 30 days (inclusive of today) when no range is
    # given, so the page has something to show without the user picking
    # dates first.
    resolved_end = end if end is not None else date.today() + timedelta(days=1)
    resolved_start = start if start is not None else resolved_end - timedelta(days=30)
    return await dashboard_service.get_summary(db, current_user.tenant_id, start=resolved_start, end=resolved_end)
