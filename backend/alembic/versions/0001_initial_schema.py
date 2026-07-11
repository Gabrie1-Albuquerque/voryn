"""initial schema: companies, users, catalog, appointments, RLS, conflict constraints

Revision ID: 0001
Revises:
Create Date: 2026-07-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.config import get_settings

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# Tenant-owned tables get RLS + FORCE RLS. `companies` is the tenant root (no
# tenant_id of its own) and `employee_service_association` is a pure join
# table whose rows are only ever reached via employees/services, which are
# themselves already RLS-protected -- so both are intentionally excluded.
TENANT_TABLES = [
    "employees",
    "employee_availabilities",
    "users",
    "clients",
    "services",
    "rooms",
    "appointments",
    "appointment_status_history",
    "waitlist_entries",
    "client_notes",
    "notification_logs",
    "payment_records",
]

ENUMS = {
    "user_role": ["admin", "manager", "employee"],
    "appointment_status": ["pending", "confirmed", "completed", "cancelled", "rescheduled"],
    "appointment_source": ["staff", "public_booking"],
    "waitlist_status": ["waiting", "promoted", "expired", "cancelled"],
    "client_note_type": ["clinical", "preference", "alert", "general"],
    "deposit_type": ["fixed_amount", "percentage"],
    "notification_channel": ["whatsapp", "email", "sms"],
    "notification_type": [
        "reminder_24h",
        "reminder_2h",
        "confirmation",
        "cancellation",
        "reschedule",
        "waitlist_promotion",
    ],
    "notification_status": ["queued", "sent", "delivered", "failed"],
    "payment_provider_name": ["mock", "mercadopago"],
    "payment_type": ["deposit_partial", "deposit_full"],
    "payment_method": ["pix", "credit_card"],
    "payment_status": ["pending", "approved", "rejected", "refunded"],
}


def _enum(name: str) -> postgresql.ENUM:
    # create_type=False: the type is created explicitly (once) in upgrade()
    # below; letting individual columns auto-create it would try to CREATE
    # TYPE once per column/table that uses it.
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    for name, values in ENUMS.items():
        postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("document", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("plan_tier", sa.String(20), nullable=False, server_default="starter"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="America/Sao_Paulo"),
        sa.Column(
            "auto_confirm_public_bookings", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_companies_slug", "companies", ["slug"])

    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_employees_tenant_id", "employees", ["tenant_id"])

    op.create_table(
        "employee_availabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.SmallInteger, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_employee_availability_weekday"),
        sa.CheckConstraint("end_time > start_time", name="ck_employee_availability_time_order"),
    )
    op.create_index("ix_employee_availabilities_tenant_id", "employee_availabilities", ["tenant_id"])
    op.create_index("ix_employee_availabilities_employee_id", "employee_availabilities", ["employee_id"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", _enum("user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "employee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("employees.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("document", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_clients_tenant_id", "clients", ["tenant_id"])
    op.create_index("ix_clients_tenant_phone", "clients", ["tenant_id", "phone"])

    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("requires_room", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deposit_required", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("deposit_type", _enum("deposit_type"), nullable=True),
        sa.Column("deposit_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_services_tenant_id", "services", ["tenant_id"])

    op.create_table(
        "employee_service_association",
        sa.Column(
            "employee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "service_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_rooms_tenant_id", "rooms", ["tenant_id"])

    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("employees.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "service_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "room_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rooms.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", _enum("appointment_status"), nullable=False, server_default="pending"),
        sa.Column("source", _enum("appointment_source"), nullable=False, server_default="staff"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        # The actual source of truth for "no double booking", correct even
        # under concurrent requests (two staff, or staff + public booking,
        # racing for the same slot) -- application-level pre-checks in
        # appointment_service.py are a UX nicety on top of this, not a
        # substitute for it.
        postgresql.ExcludeConstraint(
            ("tenant_id", "="),
            ("employee_id", "="),
            (sa.text("tstzrange(starts_at, ends_at)"), "&&"),
            where=sa.text("status <> 'cancelled'"),
            using="gist",
            name="excl_appointments_employee_overlap",
        ),
        postgresql.ExcludeConstraint(
            ("tenant_id", "="),
            ("room_id", "="),
            (sa.text("tstzrange(starts_at, ends_at)"), "&&"),
            where=sa.text("status <> 'cancelled' AND room_id IS NOT NULL"),
            using="gist",
            name="excl_appointments_room_overlap",
        ),
    )
    op.create_index("ix_appointments_tenant_id", "appointments", ["tenant_id"])
    op.create_index(
        "ix_appointments_tenant_employee_starts", "appointments", ["tenant_id", "employee_id", "starts_at"]
    )
    op.create_index(
        "ix_appointments_tenant_room_starts", "appointments", ["tenant_id", "room_id", "starts_at"]
    )
    op.create_index("ix_appointments_tenant_status", "appointments", ["tenant_id", "status"])

    op.create_table(
        "appointment_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", _enum("appointment_status"), nullable=True),
        sa.Column("to_status", _enum("appointment_status"), nullable=False),
        sa.Column("changed_by", sa.Text, nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_appointment_status_history_tenant_id", "appointment_status_history", ["tenant_id"])
    op.create_index(
        "ix_appointment_status_history_appointment_id", "appointment_status_history", ["appointment_id"]
    )

    op.create_table(
        "waitlist_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "service_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "preferred_employee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("employees.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("preferred_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("preferred_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", _enum("waitlist_status"), nullable=False, server_default="waiting"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_waitlist_entries_tenant_id", "waitlist_entries", ["tenant_id"])
    op.create_index("ix_waitlist_entries_status", "waitlist_entries", ["tenant_id", "status"])

    op.create_table(
        "client_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("note_type", _enum("client_note_type"), nullable=False, server_default="general"),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_client_notes_tenant_id", "client_notes", ["tenant_id"])
    op.create_index("ix_client_notes_client_id", "client_notes", ["client_id"])

    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", _enum("notification_channel"), nullable=False),
        sa.Column("notification_type", _enum("notification_type"), nullable=False),
        sa.Column("status", _enum("notification_status"), nullable=False, server_default="queued"),
        sa.Column("provider_message_id", sa.Text, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_notification_logs_tenant_id", "notification_logs", ["tenant_id"])
    op.create_index(
        "ix_notification_logs_idempotency",
        "notification_logs",
        ["tenant_id", "appointment_id", "notification_type"],
    )

    op.create_table(
        "payment_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", _enum("payment_provider_name"), nullable=False),
        sa.Column("provider_reference_id", sa.Text, nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("type", _enum("payment_type"), nullable=False),
        sa.Column("method", _enum("payment_method"), nullable=False),
        sa.Column("status", _enum("payment_status"), nullable=False, server_default="pending"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_payment_records_tenant_id", "payment_records", ["tenant_id"])
    op.create_index("ix_payment_records_appointment_id", "payment_records", ["appointment_id"])

    # Row-Level Security: defense-in-depth behind repository-level tenant_id
    # filtering. FORCE is required alongside ENABLE, otherwise the table
    # owner bypasses RLS entirely and this whole section becomes a silent
    # no-op for any connection using that role.
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
            """
        )

    # RLS is only a real control -- not just documentation -- against a role
    # that cannot bypass it. Postgres superusers (and BYPASSRLS roles) always
    # ignore RLS regardless of FORCE, and the official postgres image's
    # POSTGRES_USER is a superuser. So the running app/worker must connect as
    # a separate, deliberately unprivileged role, never as the migrations
    # role this file itself runs as.
    # CREATE ROLE's PASSWORD clause is a string literal in Postgres's grammar,
    # not a place bind parameters can go (asyncpg/SQLAlchemy bind params
    # produce a `$1` placeholder here, which Postgres rejects with a syntax
    # error) -- so this is a manually-escaped literal rather than op.execute
    # with bindparams. Standard-conforming-strings (the default since PG 9.1)
    # means doubling embedded single quotes is the correct, sufficient
    # escape, and this value comes from our own settings/.env, not end-user
    # input.
    settings = get_settings()
    escaped_password = settings.app_runtime_db_password.replace("'", "''")
    op.execute(f"CREATE ROLE app_runtime WITH LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{escaped_password}'")
    op.execute("GRANT USAGE ON SCHEMA public TO app_runtime")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_runtime")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_runtime")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_runtime"
    )


def downgrade() -> None:
    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM app_runtime")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM app_runtime")
    op.execute("DROP OWNED BY app_runtime")
    op.execute("DROP ROLE IF EXISTS app_runtime")

    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

    op.drop_table("payment_records")
    op.drop_table("notification_logs")
    op.drop_table("client_notes")
    op.drop_table("waitlist_entries")
    op.drop_table("appointment_status_history")
    op.drop_table("appointments")
    op.drop_table("rooms")
    op.drop_table("employee_service_association")
    op.drop_table("services")
    op.drop_table("clients")
    op.drop_table("users")
    op.drop_table("employee_availabilities")
    op.drop_table("employees")
    op.drop_table("companies")

    bind = op.get_bind()
    for name in ENUMS:
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)

    op.execute("DROP EXTENSION IF EXISTS btree_gist")
