from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from downdetector.db.base import Base, sql_in

CHECK_KINDS = ("http", "status_page", "rss", "breach")
CHECK_PURPOSES = ("primary", "extra", "breach")


class Check(Base):
    __tablename__ = "checks"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_checks"),
        ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_checks_service_id_services",
            ondelete="CASCADE",
        ),
        CheckConstraint(sql_in("kind", CHECK_KINDS), name="ck_checks_kind"),
        CheckConstraint(sql_in("purpose", CHECK_PURPOSES), name="ck_checks_purpose"),
        CheckConstraint("url IS NULL OR url LIKE 'https://%'", name="ck_checks_url"),
        CheckConstraint(
            "interval_seconds BETWEEN 30 AND 86400",
            name="ck_checks_interval_seconds",
        ),
        CheckConstraint("timeout_ms BETWEEN 100 AND 30000", name="ck_checks_timeout_ms"),
        CheckConstraint(
            "slow_threshold_ms > 0 AND slow_threshold_ms < timeout_ms",
            name="ck_checks_slow_threshold_ms",
        ),
        CheckConstraint(
            "failure_threshold BETWEEN 1 AND 20",
            name="ck_checks_failure_threshold",
        ),
        CheckConstraint(
            "recovery_threshold BETWEEN 1 AND 20",
            name="ck_checks_recovery_threshold",
        ),
        CheckConstraint(
            "(kind = 'breach') = (purpose = 'breach')",
            name="ck_checks_breach_purpose",
        ),
        CheckConstraint("(kind = 'breach') = (url IS NULL)", name="ck_checks_breach_url"),
        UniqueConstraint(
            "service_id",
            "kind",
            "url",
            name="uq_checks_target",
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "uq_checks_one_primary",
            "service_id",
            unique=True,
            postgresql_where=text("purpose = 'primary'"),
        ),
        Index(
            "ix_checks_due",
            "next_run_at",
            postgresql_where=text("enabled"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), default=uuid4)
    service_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048))
    interval_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("60"),
    )
    timeout_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("5000"),
    )
    slow_threshold_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("2000"),
    )
    failure_threshold: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default=text("3"),
    )
    recovery_threshold: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default=text("2"),
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
