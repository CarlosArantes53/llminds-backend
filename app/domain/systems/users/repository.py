"""Interface (porta) do repositório de Users — camada de domínio."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from .entity import User


class IUserRepository(ABC):

    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        ...

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        ...

    @abstractmethod
    async def list_all(self) -> Sequence[User]:
        ...

    @abstractmethod
    async def create(self, user: User) -> User:
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        ...

    @abstractmethod
    async def delete(self, user_id: int) -> None:
        ...
