"""add indexes to timestamp columns

Revision ID: 0002_add_indexes
Revises: 0001_initial
Create Date: 2026-02-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "0002_add_indexes"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # tickets
    op.create_index(op.f("ix_tickets_created_at"), "tickets", ["created_at"], unique=False)

    # llm_datasets
    op.create_index(op.f("ix_llm_datasets_inserted_at"), "llm_datasets", ["inserted_at"], unique=False)

    # user_audit_logs
    op.create_index(op.f("ix_user_audit_logs_performed_at"), "user_audit_logs", ["performed_at"], unique=False)

    # dataset_audit_logs
    op.create_index(op.f("ix_dataset_audit_logs_performed_at"), "dataset_audit_logs", ["performed_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dataset_audit_logs_performed_at"), table_name="dataset_audit_logs")
    op.drop_index(op.f("ix_user_audit_logs_performed_at"), table_name="user_audit_logs")
    op.drop_index(op.f("ix_llm_datasets_inserted_at"), table_name="llm_datasets")
    op.drop_index(op.f("ix_tickets_created_at"), table_name="tickets")
