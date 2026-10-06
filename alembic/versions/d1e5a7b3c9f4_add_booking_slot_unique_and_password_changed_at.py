"""add_booking_slot_unique_and_password_changed_at

Revision ID: d1e5a7b3c9f4
Revises: c8d4f2a6e9b1
Create Date: 2026-10-06 12:00:00.000000

- Adds user.password_changed_at (invalidates tokens issued before a password
  change, making reset tokens single-use).
- Drift-tolerant: also adds bookingitem.start_hour and priceslot.premium_price
  if a purely-migrated database is missing them (earlier revisions were
  hand-patched via run_migration.py).
- Adds bookingitem.booking_date (denormalized from Booking so the anti
  double-booking constraint lives in a single table) and backfills it.
- Adds the unique constraint (booking_date, lane_id, price_slot_id, start_hour)
  on bookingitem: the authoritative DB-level guard against concurrent
  double-booking.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e5a7b3c9f4'
down_revision: Union[str, Sequence[str], None] = 'c8d4f2a6e9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    inspector = sa.inspect(bind)
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    # --- user.password_changed_at ---
    if not _has_column(bind, "user", "password_changed_at"):
        op.add_column("user", sa.Column("password_changed_at", sa.DateTime(), nullable=True))

    # --- bookingitem.start_hour (drift repair from earlier hand-patches) ---
    if not _has_column(bind, "bookingitem", "start_hour"):
        op.add_column(
            "bookingitem",
            sa.Column("start_hour", sa.Integer(), nullable=False, server_default="0"),
        )

    # --- priceslot.premium_price (drift repair) ---
    if not _has_column(bind, "priceslot", "premium_price"):
        op.add_column(
            "priceslot",
            sa.Column("premium_price", sa.Float(), nullable=False, server_default="0.0"),
        )

    # --- bookingitem.booking_date + unique slot guard ---
    if not _has_column(bind, "bookingitem", "booking_date"):
        op.add_column("bookingitem", sa.Column("booking_date", sa.Date(), nullable=True))
        op.execute(
            """
            UPDATE bookingitem
            SET booking_date = (SELECT b.booking_date FROM booking b WHERE b.id = bookingitem.booking_id)
            WHERE bookingitem.booking_date IS NULL
            """
        )
        op.alter_column("bookingitem", "booking_date", existing_type=sa.Date(), nullable=False)
        op.create_index(op.f("ix_bookingitem_booking_date"), "bookingitem", ["booking_date"], unique=False)

    # Deduplicate rows that already occupy the same cell — leftovers of the
    # double-booking race this constraint exists to prevent. Keep the row with
    # the lowest id (the earliest reservation) and drop the later duplicates so
    # the unique index can be built.
    removed = op.get_bind().execute(
        sa.text(
            """
            DELETE FROM bookingitem
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM bookingitem
                GROUP BY booking_date, lane_id, price_slot_id, start_hour
            )
            """
        )
    )
    if removed.rowcount:
        print(
            f"cleaned {removed.rowcount} duplicate bookingitem row(s) "
            "(same booking_date/lane_id/price_slot_id/start_hour); "
            "kept the earliest reservation per cell"
        )

    op.create_unique_constraint(
        "uq_booking_item_slot",
        "bookingitem",
        ["booking_date", "lane_id", "price_slot_id", "start_hour"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_booking_item_slot", "bookingitem", type_="unique")
    op.drop_index(op.f("ix_bookingitem_booking_date"), table_name="bookingitem")
    op.drop_column("bookingitem", "booking_date")
    op.drop_column("user", "password_changed_at")