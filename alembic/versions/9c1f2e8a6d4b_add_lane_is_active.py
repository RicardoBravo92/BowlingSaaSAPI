"""add_lane_is_active

Revision ID: 9c1f2e8a6d4b
Revises: 677f882dc5c5
Create Date: 2026-09-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c1f2e8a6d4b'
down_revision: Union[str, Sequence[str], None] = '677f882dc5c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'lane',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )


def downgrade() -> None:
    op.drop_column('lane', 'is_active')