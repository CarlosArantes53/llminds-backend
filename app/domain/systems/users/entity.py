"""Entidade de domínio User — com eventos de domínio e regras de negócio."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domain.events.base import AggregateRoot
from app.domain.events.user_events import (
    UserCreated,
    UserDeleted,
    UserRoleChanged,
    UserUpdated,
)


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    AGENT = "agent"
    USER = "user"


@dataclass
class User(AggregateRoot):
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    hashed_password: str = ""
    role: UserRole = UserRole.USER
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        AggregateRoot.__init__(self)

    # ── Regras de negócio ──

    def change_role(self, new_role: UserRole, performed_by: int) -> None:
        old_role = self.role
        if old_role == new_role:
            return
        self.role = new_role
        self.updated_at = datetime.utcnow()
        self._record_event(UserRoleChanged(
            user_id=self.id,
            old_role=old_role.value,
            new_role=new_role.value,
            performed_by=performed_by,
        ))

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def record_creation(self) -> None:
        self._record_event(UserCreated(
            user_id=self.id,
            username=self.username,
            email=self.email,
            role=self.role.value,
        ))

    def record_update(self, changed_fields: dict, performed_by: Optional[int] = None) -> None:
        self._record_event(UserUpdated(
            user_id=self.id,
            changed_fields=changed_fields,
            performed_by=performed_by,
        ))

    def record_deletion(self, performed_by: Optional[int] = None) -> None:
        self._record_event(UserDeleted(
            user_id=self.id,
            performed_by=performed_by,
        ))

    # ── RBAC helpers ──

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def is_agent_or_above(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.AGENT)

    def can_manage_users(self) -> bool:
        return self.is_admin()

    def can_manage_tickets(self) -> bool:
        return self.is_agent_or_above()
