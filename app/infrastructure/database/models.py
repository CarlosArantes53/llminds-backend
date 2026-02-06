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
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
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
        Enum("admin", "agent", "user", name="user_role_enum", create_type=True),
        nullable=False,
        server_default="user",
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
        Enum("open", "in_progress", "done", name="ticket_status_enum", create_type=True),
        nullable=False,
        server_default="open",
        index=True,
    )
    milestones = Column(JSONB, default=list)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("UserModel", back_populates="tickets_created", foreign_keys=[created_by])
    assignee = relationship("UserModel", back_populates="tickets_assigned", foreign_keys=[assigned_to])


# ────────────────────────────────────────────────────────────────
# LLM DATASETS
# ────────────────────────────────────────────────────────────────
class LLMDatasetModel(Base):
    __tablename__ = "llm_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    target_model = Column(String(100), default="", index=True)
    status = Column(
        Enum("pending", "processing", "completed", "failed", name="finetuning_status_enum", create_type=True),
        nullable=False,
        server_default="pending",
        index=True,
    )
    metadata_ = Column("metadata", JSONB, default=dict)
    inserted_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("UserModel", back_populates="datasets")


# ────────────────────────────────────────────────────────────────
# AUDIT LOGS — Modificações de Usuário
# ────────────────────────────────────────────────────────────────
class UserAuditLogModel(Base):
    __tablename__ = "user_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)       # "created", "updated", "deleted", "role_changed"
    changed_fields = Column(JSONB, default=dict)       # {"field": {"old": ..., "new": ...}}
    performed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    performed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserModel", back_populates="audit_logs", foreign_keys=[user_id])


# ────────────────────────────────────────────────────────────────
# AUDIT LOGS — Modificações de Dataset LLM
# ────────────────────────────────────────────────────────────────
class DatasetAuditLogModel(Base):
    __tablename__ = "dataset_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("llm_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)        # "created", "updated", "deleted", "status_changed"
    changed_fields = Column(JSONB, default=dict)
    performed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    performed_at = Column(DateTime(timezone=True), server_default=func.now())
