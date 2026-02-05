"""
Dependências de autenticação JWT, RBAC e factories de DI.

Inclui: access token, refresh token, change password,
optional auth e active-user guard.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.config import get_settings
from app.infrastructure.database import get_db
from app.infrastructure.systems.users.repository import UserRepository
from app.infrastructure.systems.tickets.repository import TicketRepository
from app.infrastructure.systems.datasets.repository import DatasetRepository
from app.domain.systems.users.entity import User
from app.application.shared.unit_of_work import UnitOfWork

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ════════════════════════════════════════════════════════════════
# PASSWORD
# ════════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ════════════════════════════════════════════════════════════════
# JWT — Access + Refresh tokens
# ════════════════════════════════════════════════════════════════

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica e valida um token JWT. Raises JWTError."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ════════════════════════════════════════════════════════════════
# FASTAPI DEPENDENCIES
# ════════════════════════════════════════════════════════════════

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extrai e valida o usuário do access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id = int(payload.get("sub", 0))
        if not user_id:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Garante que o usuário está ativo."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )
    return current_user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Retorna o usuário se autenticado, ou None."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = int(payload.get("sub", 0))
        if not user_id:
            return None
        repo = UserRepository(db)
        return await repo.get_by_id(user_id)
    except (JWTError, ValueError):
        return None


def require_roles(*roles: str):
    """Dependency factory para RBAC baseado em roles."""
    async def _check(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requer role: {', '.join(roles)}",
            )
        return current_user
    return _check


# ════════════════════════════════════════════════════════════════
# DI FACTORIES — Repositórios e UoW
# ════════════════════════════════════════════════════════════════

def get_uow(db: AsyncSession = Depends(get_db)) -> UnitOfWork:
    return UnitOfWork(db)


def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_ticket_repo(db: AsyncSession = Depends(get_db)) -> TicketRepository:
    return TicketRepository(db)


def get_dataset_repo(db: AsyncSession = Depends(get_db)) -> DatasetRepository:
    return DatasetRepository(db)
