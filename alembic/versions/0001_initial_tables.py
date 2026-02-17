"""initial_tables — users, tickets, llm_datasets, audit_logs

Revision ID: 0001_initial
Revises: None
Create Date: 2026-02-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    user_role_enum = ENUM('admin', 'agent', 'user', name='user_role_enum', create_type=False)
    ticket_status_enum = sa.Enum("open", "in_progress", "done", name="ticket_status_enum")
    finetuning_status_enum = sa.Enum("pending", "processing", "completed", "failed", name="finetuning_status_enum")

    user_role_enum.create(op.get_bind(), checkfirst=True)
    ticket_status_enum.create(op.get_bind(), checkfirst=True)
    finetuning_status_enum.create(op.get_bind(), checkfirst=True)

    # ── USERS ──
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(150), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("role", sa.Enum('admin', 'agent', 'user', name='user_role_enum', create_type=False), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── TICKETS ──
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("status", ticket_status_enum, nullable=False, server_default="open"),
        sa.Column("milestones", JSONB(), nullable=True),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── LLM DATASETS ──
    op.create_table(
        "llm_datasets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("target_model", sa.String(100), server_default=""),
        sa.Column("status", finetuning_status_enum, nullable=False, server_default="pending"),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("inserted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── USER AUDIT LOGS ──
    op.create_table(
        "user_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("changed_fields", JSONB(), nullable=True),
        sa.Column("performed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── DATASET AUDIT LOGS ──
    op.create_table(
        "dataset_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.Integer(), sa.ForeignKey("llm_datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("changed_fields", JSONB(), nullable=True),
        sa.Column("performed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("dataset_audit_logs")
    op.drop_table("user_audit_logs")
    op.drop_table("llm_datasets")
    op.drop_table("tickets")
    op.drop_table("users")

    # Drop enums
    sa.Enum(name="finetuning_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ticket_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role_enum").drop(op.get_bind(), checkfirst=True)
