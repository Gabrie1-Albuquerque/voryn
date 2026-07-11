"""Admin-provisioning CLI: the spec's commercial strategy is sales-led (free
demo + paid setup), so the MVP deliberately has no public self-signup --
new tenants are created through this instead of a website form.

Usage (inside the backend container):
    python -m app.cli create-tenant --company-name "Salao Exemplo" \\
        --company-slug salao-exemplo --admin-email dono@exemplo.com --admin-password "senha-forte"
"""

import argparse
import asyncio
import sys

from app.core.database import async_session_factory, set_tenant_context
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.tenant import Company, User


async def create_tenant(*, company_name: str, company_slug: str, admin_email: str, admin_password: str) -> None:
    async with async_session_factory() as session:
        company = Company(slug=company_slug, name=company_name)
        session.add(company)
        await session.flush()  # assigns company.id without committing yet

        await set_tenant_context(session, company.id)
        session.add(
            User(
                tenant_id=company.id,
                email=admin_email,
                password_hash=hash_password(admin_password),
                role=UserRole.ADMIN,
            )
        )
        await session.commit()
        print(f"Criado: empresa {company_slug!r} (id={company.id}) com admin {admin_email!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-tenant", help="Cria uma nova empresa (tenant) e seu usuário admin")
    create.add_argument("--company-name", required=True)
    create.add_argument("--company-slug", required=True)
    create.add_argument("--admin-email", required=True)
    create.add_argument("--admin-password", required=True)

    args = parser.parse_args()

    if args.command == "create-tenant":
        asyncio.run(
            create_tenant(
                company_name=args.company_name,
                company_slug=args.company_slug,
                admin_email=args.admin_email,
                admin_password=args.admin_password,
            )
        )


if __name__ == "__main__":
    sys.exit(main())
