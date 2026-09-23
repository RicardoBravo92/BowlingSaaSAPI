"""add_business_settings

Revision ID: c8d4f2a6e9b1
Revises: f6a3d1c9b2e8
Create Date: 2026-09-23 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c8d4f2a6e9b1'
down_revision: Union[str, Sequence[str], None] = 'f6a3d1c9b2e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'businesssettings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('address', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('phone', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    # Seed the single settings row
    op.bulk_insert(
        sa.table(
            'businesssettings',
            sa.column('id', sa.Integer),
            sa.column('name', sa.String),
            sa.column('address', sa.String),
            sa.column('phone', sa.String),
        ),
        [
            {
                "id": 1,
                "name": "Bowling SaaS",
                "address": "Calle 123, Centro Ciudad",
                "phone": "+1 (555) 123-4567",
            }
        ],
    )


def downgrade() -> None:
    op.drop_table('businesssettings')