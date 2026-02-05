"""
Exception handlers globais — converte exceções de domínio/aplicação
em respostas HTTP padronizadas.
"""

from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.systems.users.authorization_service import AuthorizationError

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Recurso não encontrado."""
    def __init__(self, resource: str = "Recurso", resource_id: int | str = ""):
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} {resource_id} não encontrado")


class ConflictError(Exception):
    """Conflito de dados (duplicata, etc.)."""
    pass


class BadRequestError(Exception):
    """Requisição inválida de domínio."""
    pass


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos os handlers de exceção na app FastAPI."""

    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "forbidden",
                "detail": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "not_found",
                "detail": str(exc),
                "resource": exc.resource,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(ConflictError)
    async def conflict_error_handler(request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "conflict",
                "detail": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(BadRequestError)
    async def bad_request_error_handler(request: Request, exc: BadRequestError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "bad_request",
                "detail": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "validation_error",
                "detail": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception on %s %s: %s\n%s",
            request.method,
            request.url.path,
            exc,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "detail": "Erro interno do servidor",
                "request_id": getattr(request.state, "request_id", None),
            },
        )
