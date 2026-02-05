"""
Event Handlers — gravam audit logs no banco a partir de eventos de domínio.

Registrados na inicialização da app (app/main.py).
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.events.user_events import UserCreated, UserUpdated, UserDeleted, UserRoleChanged
from app.domain.events.dataset_events import DatasetCreated, DatasetUpdated, DatasetDeleted, DatasetStatusChanged
from app.domain.events.ticket_events import TicketCreated, TicketStatusChanged, TicketDeleted
from app.infrastructure.database.models import UserAuditLogModel, DatasetAuditLogModel
from app.infrastructure.database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def _get_session() -> AsyncSession:
    """Cria sessão independente para handlers (fora do request)."""
    return AsyncSessionLocal()


# ════════════════════════════════════════════════════════════════
# USER AUDIT HANDLERS
# ════════════════════════════════════════════════════════════════

async def handle_user_created(event: UserCreated) -> None:
    async with AsyncSessionLocal() as session:
        log = UserAuditLogModel(
            user_id=event.user_id,
            action="created",
            changed_fields={"username": event.username, "email": event.email, "role": event.role},
            performed_by=event.user_id,
        )
        session.add(log)
        await session.commit()
        logger.info("Audit: User %d created", event.user_id)


async def handle_user_updated(event: UserUpdated) -> None:
    async with AsyncSessionLocal() as session:
        log = UserAuditLogModel(
            user_id=event.user_id,
            action="updated",
            changed_fields=event.changed_fields,
            performed_by=event.performed_by,
        )
        session.add(log)
        await session.commit()
        logger.info("Audit: User %d updated by %s", event.user_id, event.performed_by)


async def handle_user_deleted(event: UserDeleted) -> None:
    async with AsyncSessionLocal() as session:
        log = UserAuditLogModel(
            user_id=event.user_id,
            action="deleted",
            changed_fields={},
            performed_by=event.performed_by,
        )
        session.add(log)
        await session.commit()
        logger.info("Audit: User %d deleted by %s", event.user_id, event.performed_by)


async def handle_user_role_changed(event: UserRoleChanged) -> None:
    async with AsyncSessionLocal() as session:
        log = UserAuditLogModel(
            user_id=event.user_id,
            action="role_changed",
            changed_fields={"role": {"old": event.old_role, "new": event.new_role}},
            performed_by=event.performed_by,
        )
        session.add(log)
        await session.commit()
        logger.info("Audit: User %d role changed %s→%s", event.user_id, event.old_role, event.new_role)


# ════════════════════════════════════════════════════════════════
# DATASET AUDIT HANDLERS
# ════════════════════════════════════════════════════════════════

async def handle_dataset_created(event: DatasetCreated) -> None:
    async with AsyncSessionLocal() as session:
        log = DatasetAuditLogModel(
            dataset_id=event.dataset_id,
            action="created",
            changed_fields={"target_model": event.target_model},
            performed_by=event.user_id,
        )
        session.add(log)
        await session.commit()
        logger.info("Audit: Dataset %d created by user %d", event.dataset_id, event.user_id)


async def handle_dataset_updated(event: DatasetUpdated) -> None:
    async with AsyncSessionLocal() as session:
        log = DatasetAuditLogModel(
            dataset_id=event.dataset_id,
            action="updated",
            changed_fields=event.changed_fields,
            performed_by=event.performed_by,
        )
        session.add(log)
        await session.commit()
        logger.info("Audit: Dataset %d updated", event.dataset_id)


async def handle_dataset_deleted(event: DatasetDeleted) -> None:
    async with AsyncSessionLocal() as session:
        log = DatasetAuditLogModel(
            dataset_id=event.dataset_id,
            action="deleted",
            changed_fields={},
            performed_by=event.performed_by,
        )
        session.add(log)
        await session.commit()
        logger.info("Audit: Dataset %d deleted", event.dataset_id)


async def handle_dataset_status_changed(event: DatasetStatusChanged) -> None:
    async with AsyncSessionLocal() as session:
        log = DatasetAuditLogModel(
            dataset_id=event.dataset_id,
            action="status_changed",
            changed_fields={"status": {"old": event.old_status, "new": event.new_status}},
            performed_by=None,
        )
        session.add(log)
        await session.commit()
        logger.info("Audit: Dataset %d status %s→%s", event.dataset_id, event.old_status, event.new_status)


# ════════════════════════════════════════════════════════════════
# REGISTRATION
# ════════════════════════════════════════════════════════════════

def register_all_handlers() -> None:
    """Registra todos os handlers de audit log no dispatcher."""
    from app.application.shared.event_dispatcher import register_handler

    # Users
    register_handler(UserCreated, handle_user_created)
    register_handler(UserUpdated, handle_user_updated)
    register_handler(UserDeleted, handle_user_deleted)
    register_handler(UserRoleChanged, handle_user_role_changed)

    # Datasets
    register_handler(DatasetCreated, handle_dataset_created)
    register_handler(DatasetUpdated, handle_dataset_updated)
    register_handler(DatasetDeleted, handle_dataset_deleted)
    register_handler(DatasetStatusChanged, handle_dataset_status_changed)

    logger.info("Audit log event handlers registered")
