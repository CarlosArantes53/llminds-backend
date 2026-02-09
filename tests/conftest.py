"""
Fixtures de teste — client HTTP + banco SQLite em memória.

Usa SQLite async para testes rápidos sem Docker.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from passlib.context import CryptContext

from app.infrastructure.database.session import Base, get_db
from app.main import app
from app.infrastructure.systems.users.repository import UserRepository
from app.domain.systems.users.entity import User, UserRole

# ── SQLite async para testes ──
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Override dependency
app.dependency_overrides[get_db] = override_get_db

# Disable rate limiting for tests
from app.presentation.api.v1.endpoints.auth import login_limiter, register_limiter
async def no_op_limiter(): pass
app.dependency_overrides[login_limiter] = no_op_limiter
app.dependency_overrides[register_limiter] = no_op_limiter


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Cria/destrói tabelas antes/depois de cada teste."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    """Registra admin e retorna token."""
    # Create admin directly in DB to bypass API restrictions
    async with TestSessionLocal() as session:
        repo = UserRepository(session)
        admin = User(
            username="admin_test",
            email="admin@test.com",
            hashed_password=pwd_context.hash("admin123"),
            role=UserRole.ADMIN,
        )
        await repo.create(admin)
        await session.commit()

    resp = await client.post("/api/v1/auth/login", json={
        "username": "admin_test",
        "password": "admin123",
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def user_token(client: AsyncClient) -> str:
    """Registra user comum e retorna token."""
    await client.post("/api/v1/auth/register", json={
        "username": "user_test",
        "email": "user@test.com",
        "password": "user123",
        "role": "user",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "username": "user_test",
        "password": "user123",
    })
    return resp.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
