"""Baseline revision (no-op).

Revision ID: 0001_baseline
Revises: None
Create Date: 2025-01-01 00:00:00

"""

# revision identifiers, used by Alembic.
revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline marker, no schema changes
    pass


def downgrade() -> None:
    pass
