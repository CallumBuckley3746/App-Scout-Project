from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from downdetector.db.base import Base, sql_in

ATTEMPT_RESULTS = ("success", "slow", "failure", "unknown")
VENDOR_INDICATORS = ("none", "minor", "major", "critical", "maintenance")


class CheckAttempt(Base):
    __tablename__ = "check_attempts"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_check_attempts"),
        ForeignKeyConstraint(
            ["check_id"],
            ["checks.id"],
            name="fk_check_attempts_check_id_checks",
            ondelete="CASCADE",
        ),
        UniqueConstraint("check_id", "slot_at", name="uq_check_attempts_slot"),
        CheckConstraint(sql_in("result", ATTEMPT_RESULTS), name="ck_check_attempts_result"),
        CheckConstraint(
            "http_status BETWEEN 100 AND 599",
            name="ck_check_attempts_http_status",
        ),
        CheckConstraint("latency_ms >= 0", name="ck_check_attempts_latency_ms"),
        CheckConstraint(
            sql_in("vendor_indicator", VENDOR_INDICATORS),
            name="ck_check_attempts_vendor_indicator",
        ),
        CheckConstraint(
            "jsonb_typeof(detail) = 'object'",
            name="ck_check_attempts_detail",
        ),
        CheckConstraint(
            "finished_at >= started_at",
            name="ck_check_attempts_finished_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True))
    check_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    slot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[str] = mapped_column(String(8), nullable=False)
    http_status: Mapped[int | None] = mapped_column(SmallInteger)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    vendor_indicator: Mapped[str | None] = mapped_column(String(16))
    error: Mapped[str | None] = mapped_column(String(500))
    detail: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
