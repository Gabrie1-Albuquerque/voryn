"""refresh_tokens table + find_login_credentials lookup function

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-11

Login needs to find which tenant a user belongs to BEFORE tenant context can
be set (chicken-and-egg: RLS requires SET LOCAL app.current_tenant_id before
any query on `users` succeeds at all, but we don't know the tenant until
we've looked the user up by email). find_login_credentials() is a narrow,
SECURITY DEFINER function -- the one deliberate, minimal-surface-area RLS
bypass in the system, returning only the fields needed to authenticate and
discover the tenant. Everything else continues to go through normal
RLS-protected queries once set_tenant_context() runs post-authentication.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_refresh_tokens_tenant_id", "refresh_tokens", ["tenant_id"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.execute("ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE refresh_tokens FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON refresh_tokens
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
        """
    )
    # Belt-and-suspenders: migration 0001's ALTER DEFAULT PRIVILEGES already
    # covers tables created by this same (migrations) role, but grants are
    # cheap and explicit here removes any doubt.
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON refresh_tokens TO app_runtime")

    op.execute(
        """
        CREATE FUNCTION find_login_credentials(p_email text)
        RETURNS TABLE (
            user_id uuid,
            tenant_id uuid,
            password_hash text,
            role user_role,
            is_active boolean
        )
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public
        AS $$
            SELECT id, tenant_id, password_hash, role, is_active
            FROM users
            WHERE email = p_email;
        $$
        """
    )
    op.execute("REVOKE ALL ON FUNCTION find_login_credentials(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION find_login_credentials(text) TO app_runtime")


def downgrade() -> None:
    op.execute("REVOKE EXECUTE ON FUNCTION find_login_credentials(text) FROM app_runtime")
    op.execute("DROP FUNCTION IF EXISTS find_login_credentials(text)")

    op.execute("DROP POLICY IF EXISTS tenant_isolation ON refresh_tokens")
    op.drop_table("refresh_tokens")
