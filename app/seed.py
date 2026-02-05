"""
Seed script — cria usuário admin inicial.

Uso:
    python -m app.seed

Idempotente: não cria se admin já existir.
"""

import asyncio
import sys

from passlib.context import CryptContext

from app.infrastructure.config import get_settings
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.systems.users.repository import UserRepository
from app.domain.systems.users.entity import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()

ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@local.dev"
ADMIN_PASSWORD = "admin123"  # Trocar em produção!


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)

        existing = await repo.get_by_username(ADMIN_USERNAME)
        if existing:
            print(f"ℹ️  Admin '{ADMIN_USERNAME}' já existe (id={existing.id}). Seed ignorado.")
            return

        admin = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            hashed_password=pwd_context.hash(ADMIN_PASSWORD),
            role=UserRole.ADMIN,
        )
        created = await repo.create(admin)
        await session.commit()

        print(f"✅ Admin criado:")
        print(f"   Username: {ADMIN_USERNAME}")
        print(f"   Email:    {ADMIN_EMAIL}")
        print(f"   Senha:    {ADMIN_PASSWORD}")
        print(f"   ID:       {created.id}")
        print(f"\n⚠️  Troque a senha em produção!")


def main():
    asyncio.run(seed())


if __name__ == "__main__":
    main()
