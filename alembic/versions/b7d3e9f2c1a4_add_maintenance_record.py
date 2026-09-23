"""add_maintenance_record

Revision ID: b7d3e9f2c1a4
Revises: 9c1f2e8a6d4b
Create Date: 2026-09-22 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d3e9f2c1a4'
down_revision: Union[str, Sequence[str], None] = '9c1f2e8a6d4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'maintenancerecord',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lane_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['lane_id'], ['lane.id'], ),
        sa.ForeignKeyConstraint(['changed_by'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_maintenancerecord_lane_id'), 'maintenancerecord', ['lane_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_maintenancerecord_lane_id'), table_name='maintenancerecord')
    op.drop_table('maintenancerecord')
