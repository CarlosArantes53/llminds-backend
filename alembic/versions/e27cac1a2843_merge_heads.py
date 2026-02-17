"""merge_heads

Revision ID: e27cac1a2843
Revises: 0002_add_indexes, 0002_add_timestamp_indexes
Create Date: 2026-02-09 22:33:30.299454
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e27cac1a2843'
down_revision: Union[str, None] = ('0002_add_indexes', '0002_add_timestamp_indexes')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
