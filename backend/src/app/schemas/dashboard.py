from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class TopServiceEntry(BaseModel):
    name: str
    completed_count: int
    revenue: Decimal


class DashboardSummary(BaseModel):
    period_start: date
    period_end: date
    projected_revenue: Decimal
    realized_revenue: Decimal
    # None when there's no data to compute a rate from (e.g. no completed
    # or no-show appointments yet in the period) -- 0% would misleadingly
    # imply "measured and good", not "nothing to measure".
    no_show_rate: float | None
    occupancy_rate: float | None
    top_services: list[TopServiceEntry]
