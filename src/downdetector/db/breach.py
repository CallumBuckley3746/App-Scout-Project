from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    desc,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from downdetector.db.base import Base, sql_in

BREACH_SOURCES = ("hibp",)
BREACH_SEVERITIES = ("low", "medium", "high", "critical")


class Breach(Base):
    __tablename__ = "breaches"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_breaches"),
        ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_breaches_service_id_services",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "service_id",
            "source",
            "external_name",
            name="uq_breaches_external",
        ),
        CheckConstraint(sql_in("source", BREACH_SOURCES), name="ck_breaches_source"),
        CheckConstraint(sql_in("severity", BREACH_SEVERITIES), name="ck_breaches_severity"),
        CheckConstraint("pwn_count >= 0", name="ck_breaches_pwn_count"),
        CheckConstraint(
            "jsonb_typeof(data_classes) = 'array'",
            name="ck_breaches_data_classes",
        ),
        Index("ix_breaches_service_published", "service_id", desc("published_at")),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), default=uuid4)
    service_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    external_name: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    breach_date: Mapped[date | None] = mapped_column(Date)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    pwn_count: Mapped[int | None] = mapped_column(BigInteger)
    data_classes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
