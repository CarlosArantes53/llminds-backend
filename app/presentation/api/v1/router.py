"""Router API v1 — agrega todos os sub-routers."""

from fastapi import APIRouter

from app.presentation.api.v1.endpoints.auth import router as auth_router
from app.presentation.api.v1.endpoints.users import router as users_router
from app.presentation.api.v1.endpoints.tickets import router as tickets_router
from app.presentation.api.v1.endpoints.datasets import router as datasets_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router, prefix="/auth", tags=["🔐 Autenticação"])
api_v1_router.include_router(users_router, prefix="/users", tags=["👤 Usuários"])
api_v1_router.include_router(tickets_router, prefix="/tickets", tags=["🎫 Tickets"])
api_v1_router.include_router(datasets_router, prefix="/datasets", tags=["🧠 Datasets LLM"])
