from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class AppointmentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class AppointmentSource(str, Enum):
    STAFF = "staff"
    PUBLIC_BOOKING = "public_booking"


class WaitlistStatus(str, Enum):
    WAITING = "waiting"
    PROMOTED = "promoted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ClientNoteType(str, Enum):
    CLINICAL = "clinical"
    PREFERENCE = "preference"
    ALERT = "alert"
    GENERAL = "general"


class DepositType(str, Enum):
    FIXED_AMOUNT = "fixed_amount"
    PERCENTAGE = "percentage"


class NotificationChannel(str, Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"


class NotificationType(str, Enum):
    REMINDER_24H = "reminder_24h"
    REMINDER_2H = "reminder_2h"
    CONFIRMATION = "confirmation"
    CANCELLATION = "cancellation"
    RESCHEDULE = "reschedule"
    WAITLIST_PROMOTION = "waitlist_promotion"


class NotificationStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class PaymentProviderName(str, Enum):
    MOCK = "mock"
    MERCADOPAGO = "mercadopago"


class PaymentType(str, Enum):
    DEPOSIT_PARTIAL = "deposit_partial"
    DEPOSIT_FULL = "deposit_full"


class PaymentMethod(str, Enum):
    PIX = "pix"
    CREDIT_CARD = "credit_card"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDED = "refunded"
