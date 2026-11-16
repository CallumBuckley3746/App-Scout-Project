from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    String,
    desc,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from downdetector.db.base import Base, sql_in

INCIDENT_SOURCES = ("detector", "status_page")
INCIDENT_STATUSES = ("degraded", "down")


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_incidents"),
        ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_incidents_service_id_services",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["opened_by_attempt_id"],
            ["check_attempts.id"],
            name="fk_incidents_opened_by_attempt_id_check_attempts",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["resolved_by_attempt_id"],
            ["check_attempts.id"],
            name="fk_incidents_resolved_by_attempt_id_check_attempts",
            ondelete="SET NULL",
        ),
        CheckConstraint(sql_in("source", INCIDENT_SOURCES), name="ck_incidents_source"),
        CheckConstraint(sql_in("status", INCIDENT_STATUSES), name="ck_incidents_status"),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= opened_at",
            name="ck_incidents_resolved_after_opened",
        ),
        CheckConstraint(
            "(source = 'status_page') = (external_id IS NOT NULL)",
            name="ck_incidents_external_id",
        ),
        Index(
            "uq_incidents_one_open_detector",
            "service_id",
            unique=True,
            postgresql_where=text("source = 'detector' AND resolved_at IS NULL"),
        ),
        Index(
            "uq_incidents_external",
            "service_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        Index("ix_incidents_service_opened", "service_id", desc("opened_at")),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), default=uuid4)
    service_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128))
    vendor_status: Mapped[str | None] = mapped_column(String(32))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_by_attempt_id: Mapped[int | None] = mapped_column(BigInteger)
    resolved_by_attempt_id: Mapped[int | None] = mapped_column(BigInteger)
