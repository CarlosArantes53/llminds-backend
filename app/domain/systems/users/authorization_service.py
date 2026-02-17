"""
Serviço de domínio para autorização (RBAC).

Centraliza regras de permissão — lógica pura de domínio, sem dependências externas.
"""

from __future__ import annotations
from typing import Optional

from app.domain.systems.users.entity import User, UserRole


class AuthorizationError(Exception):
    """Exceção de domínio para acesso negado."""
    pass


class AuthorizationService:
    """Regras RBAC centralizadas no domínio."""

    @staticmethod
    def ensure_can_manage_users(actor: User) -> None:
        if not actor.can_manage_users():
            raise AuthorizationError(
                f"Usuário {actor.username} (role={actor.role.value}) não pode gerenciar usuários"
            )

    @staticmethod
    def ensure_can_manage_tickets(actor: User) -> None:
        if not actor.can_manage_tickets():
            raise AuthorizationError(
                f"Usuário {actor.username} (role={actor.role.value}) não pode gerenciar tickets"
            )

    @staticmethod
    def ensure_owner_or_admin(actor: User, resource_owner_id: int) -> None:
        if actor.id != resource_owner_id and not actor.is_admin():
            raise AuthorizationError("Acesso negado: não é dono do recurso nem admin")

    @staticmethod
    def ensure_can_change_role(actor: User, target: User, new_role: UserRole) -> None:
        if not actor.is_admin():
            raise AuthorizationError("Apenas admins podem alterar roles")
        if target.id == actor.id and new_role != UserRole.ADMIN:
            raise AuthorizationError("Admin não pode rebaixar a si mesmo")

    @staticmethod
    def ensure_can_delete_user(actor: User, target_id: int) -> None:
        if not actor.is_admin():
            raise AuthorizationError("Apenas admins podem deletar usuários")
        if actor.id == target_id:
            raise AuthorizationError("Admin não pode deletar a si mesmo")

    @staticmethod
    def ensure_can_access_dataset(actor: User, dataset_owner_id: int) -> None:
        if actor.id != dataset_owner_id and not actor.is_admin():
            raise AuthorizationError("Acesso negado ao dataset")
    @staticmethod
    def ensure_can_assign_ticket(actor: User) -> None:
        """Apenas admin pode atribuir tickets."""
        if not actor.is_admin():
            raise AuthorizationError("Apenas administradores podem atribuir tickets")

    @staticmethod
    def ensure_is_agent(target: User) -> None:
        """Verifica se o target é agente."""
        if target.role != UserRole.AGENT:
            raise AuthorizationError(
                f"Usuário {target.username} não é agente (role={target.role.value})"
            )

    @staticmethod
    def ensure_can_reply_ticket(actor: User, ticket_created_by: int, ticket_assigned_to: Optional[int]) -> None:
        """Criador, agente atribuído ou admin podem responder."""
        if actor.is_admin():
            return
        if actor.id == ticket_created_by:
            return
        if ticket_assigned_to and actor.id == ticket_assigned_to:
            return
        raise AuthorizationError(
            "Apenas o criador, agente atribuído ou admin podem responder a este ticket"
        )