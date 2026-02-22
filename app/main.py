"""
Ponto de entrada principal da aplicação FastAPI.

    uvicorn app.main:app --reload --port 8000

Inclui: middleware (CORS, Request ID, logging), exception handlers globais,
health check com ping ao banco, e documentação Swagger completa.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.infrastructure.config import get_settings
from app.infrastructure.database.session import AsyncSessionLocal
from app.presentation.api.v1.router import api_v1_router
from app.presentation.middleware.exception_handlers import register_exception_handlers
from app.presentation.middleware.request_id import RequestIdMiddleware
from app.presentation.middleware.security_headers import SecurityHeadersMiddleware

settings = get_settings()

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# LIFESPAN — startup / shutdown
# ════════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.application.shared.event_handlers import register_all_handlers
    register_all_handlers()
    logger.info("✅ App started — event handlers registered")
    yield
    # Shutdown
    logger.info("🛑 App shutting down")


# ════════════════════════════════════════════════════════════════
# APP
# ════════════════════════════════════════════════════════════════
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API REST com Clean Architecture, autenticação JWT, RBAC, "
        "tickets com state machine e milestones, e datasets para fine-tuning LLM."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
    responses={
        401: {"description": "Token inválido ou ausente"},
        403: {"description": "Permissão insuficiente"},
        404: {"description": "Recurso não encontrado"},
        422: {"description": "Erro de validação"},
        500: {"description": "Erro interno do servidor"},
    },
)

# ── Middleware ──
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(SecurityHeadersMiddleware)

# ── Exception handlers globais ──
register_exception_handlers(app)

# ── Rotas versionadas ──
app.include_router(api_v1_router, prefix="/api/v1")


# ════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ════════════════════════════════════════════════════════════════
@app.get(
    "/health",
    tags=["❤️ Health"],
    summary="Verificação de saúde da API",
    description="Retorna status da API e conectividade com o banco de dados.",
)
async def health_check():
    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "version": settings.APP_VERSION,
        "database": "connected" if db_ok else "disconnected",
    }
