"""Implementação concreta do repositório de Users — SQLAlchemy."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.systems.users.entity import User, UserRole
from app.domain.systems.users.repository import IUserRepository
from app.infrastructure.database.models import UserModel


class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Helpers de mapeamento ──
    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            username=model.username,
            email=model.email,
            hashed_password=model.hashed_password,
            role=UserRole(model.role),
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_model(entity: User) -> UserModel:
        return UserModel(
            id=entity.id,
            username=entity.username,
            email=entity.email,
            hashed_password=entity.hashed_password,
            role=entity.role.value,
            is_active=entity.is_active,
        )

    # ── Interface ──
    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self._session.get(UserModel, user_id)
        return self._to_entity(result) if result else None

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self) -> Sequence[User]:
        stmt = select(UserModel).order_by(UserModel.id)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, user: User) -> User:
        model = self._to_model(user)
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, user: User) -> User:
        model = await self._session.get(UserModel, user.id)
        if not model:
            raise ValueError(f"User {user.id} não encontrado")
        model.username = user.username
        model.email = user.email
        model.hashed_password = user.hashed_password
        model.role = user.role.value
        model.is_active = user.is_active
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, user_id: int) -> None:
        model = await self._session.get(UserModel, user_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()
