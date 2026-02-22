"""
Modelos SQLAlchemy — camada de Infraestrutura.

Tabelas:
  - users              (RBAC com roles)
  - tickets            (status + milestones JSONB)
  - llm_datasets       (pares prompt/response para fine-tuning)
  - user_audit_logs    (log de modificações em users)
  - dataset_audit_logs (log de modificações em llm_datasets)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    JSON,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.infrastructure.database.session import Base


# ────────────────────────────────────────────────────────────────
# USERS
# ────────────────────────────────────────────────────────────────
class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(Text, nullable=False)
    role = Column(
        String(100),
        nullable=False,
        server_default="user",
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relações
    tickets_created = relationship(
        "TicketModel", back_populates="creator", foreign_keys="TicketModel.created_by"
    )
    tickets_assigned = relationship(
        "TicketModel", back_populates="assignee", foreign_keys="TicketModel.assigned_to"
    )
    datasets = relationship("LLMDatasetModel", back_populates="owner")
    audit_logs = relationship(
        "UserAuditLogModel", 
        back_populates="user", 
        foreign_keys="UserAuditLogModel.user_id"
    )


# ────────────────────────────────────────────────────────────────
# TICKETS
# ────────────────────────────────────────────────────────────────
class TicketModel(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    status = Column(
        String(100),
        nullable=False,
        server_default="open",
        index=True,
    )
    milestones = Column(JSON().with_variant(JSONB, "postgresql"), default=list)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("UserModel", back_populates="tickets_created", foreign_keys=[created_by])
    assignee = relationship("UserModel", back_populates="tickets_assigned", foreign_keys=[assigned_to])

    replies = relationship(
        "TicketReplyModel",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketReplyModel.created_at",
    )
    attachments = relationship(
        "TicketAttachmentModel",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketAttachmentModel.created_at",
    )

# ────────────────────────────────────────────────────────────────
# LLM DATASETS
# ────────────────────────────────────────────────────────────────
class LLMDatasetModel(Base):
    __tablename__ = "llm_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    # REMOVIDOS: prompt_text, response_text
    target_model = Column(String(100), default="", index=True)
    status = Column(String(100), nullable=False, server_default="pending", index=True)
    metadata_ = Column("metadata", JSON().with_variant(JSONB, "postgresql"), default=dict)
    inserted_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("UserModel", back_populates="datasets")
    rows = relationship(
        "DatasetRowModel",
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DatasetRowModel.order",
    )


# ────────────────────────────────────────────────────────────────
# LLM DATASET ROWS (linhas de dados)
# ────────────────────────────────────────────────────────────────
class DatasetRowModel(Base):
    __tablename__ = "llm_dataset_rows"

    __table_args__ = (
        Index("ix_llm_dataset_rows_dataset_id_order", "dataset_id", "order"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(
        Integer,
        ForeignKey("llm_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    category = Column(String(255), nullable=False, server_default="")
    semantics = Column(String(255), nullable=False, server_default="")
    order = Column(Integer, nullable=False, server_default="0")
    inserted_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    dataset = relationship("LLMDatasetModel", back_populates="rows")

# ────────────────────────────────────────────────────────────────
# AUDIT LOGS — Modificações de Usuário
# ────────────────────────────────────────────────────────────────
class UserAuditLogModel(Base):
    __tablename__ = "user_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)       # "created", "updated", "deleted", "role_changed"
    changed_fields = Column(JSON().with_variant(JSONB, "postgresql"), default=dict)       # {"field": {"old": ..., "new": ...}}
    performed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("UserModel", back_populates="audit_logs", foreign_keys=[user_id])


# ────────────────────────────────────────────────────────────────
# AUDIT LOGS — Modificações de Dataset LLM
# ────────────────────────────────────────────────────────────────
class DatasetAuditLogModel(Base):
    __tablename__ = "dataset_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("llm_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)        # "created", "updated", "deleted", "status_changed"
    changed_fields = Column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    performed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

# ────────────────────────────────────────────────────────────────
# TICKET REPLIES
# ────────────────────────────────────────────────────────────────
class TicketReplyModel(Base):
    __tablename__ = "ticket_replies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(
        Integer,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    ticket = relationship("TicketModel", back_populates="replies")
    author = relationship("UserModel")
    attachments = relationship(
        "TicketAttachmentModel",
        back_populates="reply",
        cascade="all, delete-orphan",
    )


# ────────────────────────────────────────────────────────────────
# TICKET ATTACHMENTS
# ────────────────────────────────────────────────────────────────
class TicketAttachmentModel(Base):
    __tablename__ = "ticket_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(
        Integer,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reply_id = Column(
        Integer,
        ForeignKey("ticket_replies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    uploaded_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("TicketModel", back_populates="attachments")
    reply = relationship("TicketReplyModel", back_populates="attachments")
    uploader = relationship("UserModel")