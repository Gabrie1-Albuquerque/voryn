"""Proves Row-Level Security actually isolates tenants when the app connects
as the restricted `app_runtime` role (see migration 0001 and
core/database.py:set_tenant_context). This regression-guards a real bug
found while building this migration: the official postgres image's default
user is a superuser, and superusers silently bypass RLS regardless of
ENABLE/FORCE -- so this must run through the same role/connection the app
actually uses, not the migrations superuser role.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.database import set_tenant_context


async def _seed_employee(conn: AsyncConnection, tenant_id: uuid.UUID, name: str = "Funcionaria") -> uuid.UUID:
    employee_id = uuid.uuid4()
    await conn.execute(
        text("INSERT INTO employees (id, tenant_id, name) VALUES (:id, :tenant_id, :name)"),
        {"id": employee_id, "tenant_id": tenant_id, "name": name},
    )
    return employee_id


@pytest.mark.asyncio
async def test_tenant_cannot_see_other_tenants_rows(db_connection: AsyncConnection, make_tenant):
    tenant_a = await make_tenant("tenant-a")
    await _seed_employee(db_connection, tenant_a, "Funcionaria A")

    tenant_b = await make_tenant("tenant-b")
    await _seed_employee(db_connection, tenant_b, "Funcionaria B")

    await set_tenant_context(db_connection, tenant_a)
    result = await db_connection.execute(text("SELECT name FROM employees"))
    names = {row[0] for row in result.fetchall()}
    assert names == {"Funcionaria A"}

    await set_tenant_context(db_connection, tenant_b)
    result = await db_connection.execute(text("SELECT name FROM employees"))
    names = {row[0] for row in result.fetchall()}
    assert names == {"Funcionaria B"}


@pytest.mark.asyncio
async def test_tenant_cannot_insert_row_claiming_another_tenant_id(
    db_connection: AsyncConnection, make_tenant
):
    tenant_a = await make_tenant("tenant-a")
    tenant_b = await make_tenant("tenant-b")

    await set_tenant_context(db_connection, tenant_b)
    with pytest.raises(DBAPIError, match="row-level security"):
        await db_connection.execute(
            text("INSERT INTO employees (id, tenant_id, name) VALUES (:id, :tenant_id, :name)"),
            {"id": uuid.uuid4(), "tenant_id": tenant_a, "name": "Injetado"},
        )


@pytest.mark.asyncio
async def test_query_without_any_tenant_context_set_raises(db_connection: AsyncConnection, make_tenant):
    """A forgotten set_tenant_context call must fail loudly, not silently
    return another tenant's rows or an empty set indistinguishable from
    legitimate "no data". Needs a real row to filter (RLS quals are only
    evaluated per fetched row, so a query against a genuinely empty table
    wouldn't exercise this at all) and then explicitly resets the setting to
    simulate a forgotten call -- for a custom (namespaced) GUC like this
    one, RESET sets it to an empty string rather than a fully-undefined
    parameter, so the RLS policy fails casting '' to uuid instead of
    failing on current_setting() itself. Different error message, same
    fail-loud property: no code path here silently proceeds with the query.
    """
    tenant_a = await make_tenant("tenant-a")
    await _seed_employee(db_connection, tenant_a)

    await db_connection.execute(text("RESET app.current_tenant_id"))

    with pytest.raises(
        DBAPIError, match="unrecognized configuration parameter|invalid input syntax for type uuid"
    ):
        await db_connection.execute(text("SELECT name FROM employees"))
