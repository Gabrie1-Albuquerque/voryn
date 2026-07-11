"""Import every model module so Base.metadata (and therefore Alembic
autogenerate / metadata.create_all) sees the full schema, and so
string-based relationship() references resolve regardless of import order.
"""

from app.models.base import Base
from app.models.appointment import Appointment, AppointmentStatusHistory, WaitlistEntry
from app.models.catalog import Room, Service, employee_service_association
from app.models.client import Client, ClientNote
from app.models.notification import NotificationLog
from app.models.payment import PaymentRecord
from app.models.tenant import Company, Employee, EmployeeAvailability, User

__all__ = [
    "Base",
    "Company",
    "User",
    "Employee",
    "EmployeeAvailability",
    "Client",
    "ClientNote",
    "Service",
    "Room",
    "employee_service_association",
    "Appointment",
    "AppointmentStatusHistory",
    "WaitlistEntry",
    "NotificationLog",
    "PaymentRecord",
]
