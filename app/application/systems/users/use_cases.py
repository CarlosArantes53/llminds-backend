"""
Use Cases de Users — camada de Aplicação.

Orquestram entidades de domínio, repositórios e eventos.
Toda lógica de negócio vive no domínio; aqui apenas coordenamos.
"""

from __future__ import annotations

from typing import Optional, Sequence

from app.application.dtos.ticket_dtos import AddReplyCommand, AssignTicketCommand, AttachmentResult, GetTicketByIdQuery, ReplyResult, TicketResult
from app.domain.systems.tickets.entity import TicketReply
from app.domain.systems.tickets.repository import ITicketRepository
from app.domain.systems.users.entity import User, UserRole
from app.domain.systems.users.repository import IUserRepository
from app.domain.systems.users.authorization_service import (
    AuthorizationError,
    AuthorizationService,
)
from app.application.dtos.user_dtos import (
    DeleteUserCommand,
    GetUserByIdQuery,
    ListUsersQuery,
    LoginCommand,
    RegisterUserCommand,
    TokenResult,
    UpdateUserCommand,
    UserResult,
)
from app.application.shared.unit_of_work import UnitOfWork

def _to_result(user: User) -> UserResult:
    return UserResult(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


class RegisterUserUseCase:
    """Registra um novo usuário."""

    def __init__(self, repo: IUserRepository, uow: UnitOfWork, hash_fn) -> None:
        self._repo = repo
        self._uow = uow
        self._hash_fn = hash_fn

    async def execute(self, cmd: RegisterUserCommand) -> UserResult:
        # Unicidade
        if await self._repo.get_by_email(cmd.email):
            raise ValueError("Email já cadastrado")
        if await self._repo.get_by_username(cmd.username):
            raise ValueError("Username já cadastrado")

        # Cria entidade de domínio
        role = UserRole(cmd.role) if cmd.role in [r.value for r in UserRole] else UserRole.USER
        user = User(
            username=cmd.username,
            email=cmd.email,
            hashed_password=self._hash_fn(cmd.password),
            role=role,
        )

        created = await self._repo.create(user)
        created.record_creation()
        self._uow.collect_events_from(created)
        await self._uow.commit()
        return _to_result(created)


class LoginUseCase:
    """Autentica usuário e gera token JWT."""

    def __init__(self, repo: IUserRepository, verify_fn, token_fn) -> None:
        self._repo = repo
        self._verify_fn = verify_fn
        self._token_fn = token_fn

    async def execute(self, cmd: LoginCommand) -> TokenResult:
        user = await self._repo.get_by_username(cmd.username)
        if not user or not self._verify_fn(cmd.password, user.hashed_password):
            raise ValueError("Credenciais inválidas")
        if not user.is_active:
            raise ValueError("Usuário inativo")

        token = self._token_fn(data={"sub": str(user.id), "role": user.role.value})
        return TokenResult(access_token=token)


class GetUserUseCase:
    """Busca usuário por ID."""

    def __init__(self, repo: IUserRepository) -> None:
        self._repo = repo

    async def execute(self, query: GetUserByIdQuery) -> Optional[UserResult]:
        user = await self._repo.get_by_id(query.user_id)
        return _to_result(user) if user else None


class ListUsersUseCase:
    """Lista todos os usuários (apenas admin)."""

    def __init__(self, repo: IUserRepository) -> None:
        self._repo = repo

    async def execute(self, query: ListUsersQuery, actor: User) -> list[UserResult]:
        AuthorizationService.ensure_can_manage_users(actor)
        users = await self._repo.list_all()
        return [_to_result(u) for u in users]


class UpdateUserUseCase:
    """Atualiza dados de um usuário."""

    def __init__(self, repo: IUserRepository, uow: UnitOfWork, hash_fn) -> None:
        self._repo = repo
        self._uow = uow
        self._hash_fn = hash_fn

    async def execute(self, cmd: UpdateUserCommand, actor: User) -> UserResult:
        user = await self._repo.get_by_id(cmd.user_id)
        if not user:
            raise ValueError("Usuário não encontrado")

        # Permissão: próprio usuário ou admin
        AuthorizationService.ensure_owner_or_admin(actor, cmd.user_id)

        changed: dict = {}

        if cmd.username is not None and cmd.username != user.username:
            changed["username"] = {"old": user.username, "new": cmd.username}
            user.username = cmd.username

        if cmd.email is not None and cmd.email != user.email:
            changed["email"] = {"old": user.email, "new": cmd.email}
            user.email = cmd.email

        if cmd.password is not None:
            user.hashed_password = self._hash_fn(cmd.password)
            changed["password"] = {"old": "***", "new": "***"}

        if cmd.role is not None:
            new_role = UserRole(cmd.role)
            AuthorizationService.ensure_can_change_role(actor, user, new_role)
            user.change_role(new_role, performed_by=actor.id)
            changed["role"] = {"old": user.role.value, "new": cmd.role}

        if cmd.is_active is not None and cmd.is_active != user.is_active:
            AuthorizationService.ensure_can_manage_users(actor)
            changed["is_active"] = {"old": user.is_active, "new": cmd.is_active}
            if cmd.is_active:
                user.activate()
            else:
                user.deactivate()

        if changed:
            user.record_update(changed, performed_by=cmd.performed_by)

        updated = await self._repo.update(user)
        self._uow.collect_events_from(updated)
        await self._uow.commit()
        return _to_result(updated)


class DeleteUserUseCase:
    """Deleta um usuário (apenas admin)."""

    def __init__(self, repo: IUserRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: DeleteUserCommand, actor: User) -> None:
        AuthorizationService.ensure_can_delete_user(actor, cmd.user_id)

        user = await self._repo.get_by_id(cmd.user_id)
        if not user:
            raise ValueError("Usuário não encontrado")

        user.record_deletion(performed_by=cmd.performed_by)
        self._uow.collect_events_from(user)
        await self._repo.delete(cmd.user_id)
        await self._uow.commit()

# ════════════════════════════════════════════════════════════════
# ASSIGN TICKET (admin → agent)
# ════════════════════════════════════════════════════════════════

class AssignTicketUseCase:
    def __init__(
        self,
        ticket_repo: ITicketRepository,
        user_repo: IUserRepository,
        uow: UnitOfWork,
    ) -> None:
        self._ticket_repo = ticket_repo
        self._user_repo = user_repo
        self._uow = uow

    async def execute(self, cmd: AssignTicketCommand, actor: User) -> TicketResult:
        # 1) Verificar se actor é admin
        AuthorizationService.ensure_can_assign_ticket(actor)

        # 2) Buscar ticket
        ticket = await self._ticket_repo.get_by_id(cmd.ticket_id)
        if not ticket:
            raise ValueError("Ticket não encontrado")

        # 3) Verificar se target é agente ativo
        agent = await self._user_repo.get_by_id(cmd.agent_id)
        if not agent:
            raise ValueError("Agente não encontrado")
        AuthorizationService.ensure_is_agent(agent)
        if not agent.is_active:
            raise ValueError("Agente está inativo")

        # 4) Atribuir
        ticket.assign_to(cmd.agent_id, assigned_by=cmd.performed_by)

        updated = await self._ticket_repo.update(ticket)
        self._uow.collect_events_from(updated)
        await self._uow.commit()
        return _to_result(updated)


# ════════════════════════════════════════════════════════════════
# ADD REPLY
# ════════════════════════════════════════════════════════════════

class AddReplyUseCase:
    def __init__(self, repo: ITicketRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: AddReplyCommand, actor: User) -> ReplyResult:
        ticket = await self._repo.get_by_id(cmd.ticket_id)
        if not ticket:
            raise ValueError("Ticket não encontrado")

        # Verificar permissão de resposta
        AuthorizationService.ensure_can_reply_ticket(
            actor, ticket.created_by, ticket.assigned_to
        )

        reply = TicketReply(
            ticket_id=cmd.ticket_id,
            author_id=cmd.author_id,
            body=cmd.body,
        )
        reply.validate()

        created = await self._repo.add_reply(reply)
        await self._uow.commit()

        return ReplyResult(
            id=created.id,
            ticket_id=created.ticket_id,
            author_id=created.author_id,
            body=created.body,
            created_at=created.created_at.isoformat() if created.created_at else None,
        )


# ════════════════════════════════════════════════════════════════
# GET TICKET WITH REPLIES (detail view)
# ════════════════════════════════════════════════════════════════

class GetTicketWithRepliesUseCase:
    def __init__(self, repo: ITicketRepository) -> None:
        self._repo = repo

    async def execute(self, query: GetTicketByIdQuery, actor: User) -> Optional[TicketResult]:
        ticket = await self._repo.get_by_id_with_replies(query.ticket_id)
        if not ticket:
            return None

        AuthorizationService.ensure_can_access_ticket(actor, ticket.created_by, ticket.assigned_to)

        def _att(a):
            return AttachmentResult(
                id=a.id, ticket_id=a.ticket_id, reply_id=a.reply_id,
                uploaded_by=a.uploaded_by,
                original_filename=a.original_filename,
                stored_filename=a.stored_filename,
                content_type=a.content_type,
                file_size=a.file_size,
                created_at=a.created_at.isoformat() if a.created_at else None,
            )

        replies = [
            ReplyResult(
                id=r.id, ticket_id=r.ticket_id, author_id=r.author_id,
                body=r.body,
                attachments=[_att(a) for a in r.attachments],
                created_at=r.created_at.isoformat() if r.created_at else None,
                updated_at=r.updated_at.isoformat() if r.updated_at else None,
            )
            for r in ticket.replies
        ]

        result = TicketResult(
            id=ticket.id,
            title=ticket.title,
            description=ticket.description,
            status=ticket.status.value,
            milestones=ticket.milestones_as_dicts(),
            assigned_to=ticket.assigned_to,
            created_by=ticket.created_by,
            created_at=ticket.created_at.isoformat() if ticket.created_at else None,
            updated_at=ticket.updated_at.isoformat() if ticket.updated_at else None,
        )
        
        result.replies = replies
        result.attachments = [_att(a) for a in ticket.attachments]
        return result