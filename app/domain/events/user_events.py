"""Eventos de domínio relacionados a Users."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.events.base import DomainEvent


@dataclass(frozen=True)
class UserCreated(DomainEvent):
    user_id: int = 0
    username: str = ""
    email: str = ""
    role: str = ""


@dataclass(frozen=True)
class UserUpdated(DomainEvent):
    user_id: int = 0
    changed_fields: dict = None  # {"field": {"old": ..., "new": ...}}
    performed_by: Optional[int] = None

    def __post_init__(self):
        if self.changed_fields is None:
            object.__setattr__(self, "changed_fields", {})


@dataclass(frozen=True)
class UserDeleted(DomainEvent):
    user_id: int = 0
    performed_by: Optional[int] = None


@dataclass(frozen=True)
class UserRoleChanged(DomainEvent):
    user_id: int = 0
    old_role: str = ""
    new_role: str = ""
    performed_by: Optional[int] = None
