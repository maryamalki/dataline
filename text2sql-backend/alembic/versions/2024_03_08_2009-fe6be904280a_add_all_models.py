"""Add all models

Revision ID: fe6be904280a
Revises: 56925bfbf7db
Create Date: 2024-03-08 20:09:21.572802

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fe6be904280a"
down_revision: Union[str, None] = "56925bfbf7db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "connections",
        sa.Column("dsn", sa.String(), nullable=False),
        sa.Column("database", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("dialect", sa.String(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dsn"),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.Column("selected_tables", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["connections.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "message_results",
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
        ),
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["results.id"],
        ),
        sa.PrimaryKeyConstraint("message_id", "result_id"),
    )
    op.create_table(
        "saved_queries",
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["results.id"],
        ),
        sa.PrimaryKeyConstraint("result_id"),
    )
    op.create_table(
        "schema_tables",
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["connections.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "conversation_messages",
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
        ),
        sa.PrimaryKeyConstraint("message_id", "conversation_id"),
    )
    op.create_table(
        "schema_fields",
        sa.Column("table_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_primary_key", sa.Boolean(), nullable=False),
        sa.Column("is_foreign_key", sa.Boolean(), nullable=False),
        sa.Column("foreign_table", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["table_id"],
            ["schema_tables.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("schema_fields")
    op.drop_table("conversation_messages")
    op.drop_table("schema_tables")
    op.drop_table("saved_queries")
    op.drop_table("message_results")
    op.drop_table("conversations")
    op.drop_table("results")
    op.drop_table("messages")
    op.drop_table("connections")
    # ### end Alembic commands ###
