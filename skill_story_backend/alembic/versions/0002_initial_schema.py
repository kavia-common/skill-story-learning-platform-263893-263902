"""Initial schema for core entities.

Revision ID: 0002_initial_schema
Revises: 0001_baseline
Create Date: 2025-01-01 00:10:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_initial_schema"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # user table
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.String(length=64), nullable=True),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_story_id", sa.Integer(), nullable=True),
        sa.Column("current_episode_index", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["current_story_id"], ["story.id"], name="fk_user_current_story", initially=None, use_alter=True),
    )
    op.create_index("ix_user_username", "user", ["username"], unique=True)
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    # story table
    op.create_table(
        "story",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )

    # episode table
    op.create_table(
        "episode",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("story_id", sa.Integer(), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["story_id"], ["story.id"], ondelete=None),
    )
    op.create_index("ix_episode_story_id", "episode", ["story_id"], unique=False)
    op.create_index("ix_episode_index", "episode", ["index"], unique=False)

    # choice table
    op.create_table(
        "choice",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("episode_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("next_episode_index", sa.Integer(), nullable=True),
        sa.Column("xp_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["episode_id"], ["episode.id"], ondelete=None),
    )
    op.create_index("ix_choice_episode_id", "choice", ["episode_id"], unique=False)

    # journal_entry table
    op.create_table(
        "journal_entry",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete=None),
    )
    op.create_index("ix_journal_user_id", "journal_entry", ["user_id"], unique=False)

    # Add the FK from user.current_story_id to story.id now that story exists
    # (already declared with use_alter=True above, but make sure it's created)
    # Alembic handles via the FK declaration with use_alter.


def downgrade() -> None:
    op.drop_index("ix_journal_user_id", table_name="journal_entry")
    op.drop_table("journal_entry")
    op.drop_index("ix_choice_episode_id", table_name="choice")
    op.drop_table("choice")
    op.drop_index("ix_episode_index", table_name="episode")
    op.drop_index("ix_episode_story_id", table_name="episode")
    op.drop_table("episode")
    op.drop_table("story")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_index("ix_user_username", table_name="user")
    op.drop_table("user")
