"""add_assigned_booking_status

Revision ID: f6a3d1c9b2e8
Revises: b7d3e9f2c1a4
Create Date: 2026-09-23 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f6a3d1c9b2e8'
down_revision: Union[str, Sequence[str], None] = 'b7d3e9f2c1a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use execute to add the value to the ENUM
    # Note: ALTER TYPE ADD VALUE cannot run inside a transaction block in some PG versions
    op.execute("ALTER TYPE bookingstatus ADD VALUE 'ASSIGNED'")


def downgrade() -> None:
    # Downgrading enums in Postgres is not straightforward.
    # We would need to create a new type, migrate the columns, and drop the old one.
    pass