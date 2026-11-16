"""Add optional username to users."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_username"
down_revision: str | None = "0002_monitoring_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=32), nullable=True))
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_check_constraint(
        "ck_users_username",
        "users",
        "username IS NULL OR username ~ '^[a-z0-9_]{3,32}$'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_username", "users", type_="check")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "username")
