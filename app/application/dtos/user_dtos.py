"""DTOs da camada de aplicação para Users — commands e queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ════════════════════════════════════════════════════════════════
# COMMANDS (escrita)
# ════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RegisterUserCommand:
    username: str
    email: str
    password: str
    role: str = "user"


@dataclass(frozen=True)
class UpdateUserCommand:
    user_id: int
    performed_by: int
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


@dataclass(frozen=True)
class DeleteUserCommand:
    user_id: int
    performed_by: int


@dataclass(frozen=True)
class LoginCommand:
    username: str
    password: str


# ════════════════════════════════════════════════════════════════
# QUERIES (leitura)
# ════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GetUserByIdQuery:
    user_id: int


@dataclass(frozen=True)
class ListUsersQuery:
    pass


# ════════════════════════════════════════════════════════════════
# RESULT DTOs
# ════════════════════════════════════════════════════════════════

@dataclass
class UserResult:
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str = ""
    updated_at: Optional[str] = None


@dataclass
class TokenResult:
    access_token: str
    token_type: str = "bearer"
