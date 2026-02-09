"""
Endpoints de Autenticação — /api/v1/auth

Register, Login, Refresh Token, Change Password, Me.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.systems.users.entity import User
from app.infrastructure.systems.users.repository import UserRepository
from app.application.shared.unit_of_work import UnitOfWork
from app.application.dtos.user_dtos import LoginCommand, RegisterUserCommand
from app.application.systems.users.use_cases import LoginUseCase, RegisterUserUseCase
from app.presentation.api.v1.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenOut,
    UserCreate,
    UserOut,
)
from app.presentation.api.v1.deps import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_active_user,
    get_uow,
    get_user_repo,
    hash_password,
    verify_password,
)
from app.infrastructure.config import get_settings
from app.presentation.api.v1.limiter import InMemoryRateLimiter

router = APIRouter()
settings = get_settings()
login_limiter = InMemoryRateLimiter(requests=10, window=60)
register_limiter = InMemoryRateLimiter(requests=5, window=60)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo usuário",
    description="Cria uma conta com username, email e senha. Role padrão: user.",
    dependencies=[Depends(register_limiter)],
)
async def register(
    payload: UserCreate,
    repo: UserRepository = Depends(get_user_repo),
    uow: UnitOfWork = Depends(get_uow),
):
    uc = RegisterUserUseCase(repo, uow, hash_password)
    result = await uc.execute(RegisterUserCommand(
        username=payload.username,
        email=payload.email,
        password=payload.password,
    ))
    return UserOut(id=result.id, username=result.username, email=result.email, role=result.role, is_active=result.is_active)


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Login — gera access + refresh token",
    dependencies=[Depends(login_limiter)],
)
async def login(
    payload: LoginRequest,
    repo: UserRepository = Depends(get_user_repo),
):
    uc = LoginUseCase(repo, verify_password, create_access_token)
    result = await uc.execute(LoginCommand(username=payload.username, password=payload.password))

    # Decodifica para pegar user info para refresh
    from jose import jwt as jose_jwt
    decoded = jose_jwt.decode(result.access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    refresh = create_refresh_token(data={"sub": decoded["sub"], "role": decoded["role"]})

    return TokenOut(
        access_token=result.access_token,
        refresh_token=refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenOut,
    summary="Renova access token usando refresh token",
)
async def refresh_token(payload: RefreshTokenRequest):
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token não é refresh")
        user_id = data.get("sub")
        role = data.get("role")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado")

    new_access = create_access_token(data={"sub": user_id, "role": role})
    new_refresh = create_refresh_token(data={"sub": user_id, "role": role})
    return TokenOut(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Alterar senha do usuário autenticado",
)
async def change_password(
    payload: ChangePasswordRequest,
    repo: UserRepository = Depends(get_user_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    current_user.hashed_password = hash_password(payload.new_password)
    await repo.update(current_user)
    await uow.commit()


@router.get(
    "/me",
    response_model=UserOut,
    summary="Perfil do usuário autenticado",
)
async def me(current_user: User = Depends(get_current_active_user)):
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.value,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )
