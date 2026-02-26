"""add_manager_and_maintenance_roles

Revision ID: 677f882dc5c5
Revises: a4b514858609
Create Date: 2026-02-26 11:58:43.060366

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '677f882dc5c5'
down_revision: Union[str, Sequence[str], None] = 'a4b514858609'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use execute to add values to the ENUM
    # Note: ALTER TYPE ADD VALUE cannot run inside a transaction block in some PG versions
    # but Alembic context can handle this if we use op.execute with autocommit
    op.execute("ALTER TYPE userrole ADD VALUE 'MANAGER'")
    op.execute("ALTER TYPE userrole ADD VALUE 'MAINTENANCE'")


def downgrade() -> None:
    # Downgrading enums in Postgres is not straightforward.
    # We would need to create a new type, migrate the columns, and drop the old one.
    # For now, we leave it as is or do nothing to avoid data loss risk.
    pass
