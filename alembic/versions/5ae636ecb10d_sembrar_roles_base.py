"""sembrar roles base

Revision ID: 5ae636ecb10d
Revises: 45b5e0ccffab
Create Date: 2026-10-24 19:41:22.102952

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision: str = '5ae636ecb10d'
down_revision: Union[str, Sequence[str], None] = '45b5e0ccffab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
roles_table = sa.table(
    "roles",
    sa.column("id", sa.Uuid()),
    sa.column("name", sa.String()),
)


def upgrade() -> None:
    op.bulk_insert(
        roles_table,
        [
            {"id": uuid.uuid4(), "name": "admin"},
            {"id": uuid.uuid4(), "name": "user"},
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.delete(roles_table).where(roles_table.c.name.in_(["admin", "user"]))
    )