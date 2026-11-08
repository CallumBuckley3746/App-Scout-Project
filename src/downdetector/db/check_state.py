from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from downdetector.db.base import Base, sql_in

LAST_RESULTS = ("success", "slow", "failure", "unknown")


class CheckState(Base):
    __tablename__ = "check_states"
    __table_args__ = (
        PrimaryKeyConstraint("check_id", name="pk_check_states"),
        ForeignKeyConstraint(
            ["check_id"],
            ["checks.id"],
            name="fk_check_states_check_id_checks",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_check_states_consecutive_failures",
        ),
        CheckConstraint(
            "consecutive_successes >= 0",
            name="ck_check_states_consecutive_successes",
        ),
        CheckConstraint(sql_in("last_result", LAST_RESULTS), name="ck_check_states_last_result"),
        CheckConstraint(
            "consecutive_failures = 0 OR consecutive_successes = 0",
            name="ck_check_states_one_streak",
        ),
    )

    check_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    consecutive_successes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    last_result: Mapped[str | None] = mapped_column(String(8))
    last_slot_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
