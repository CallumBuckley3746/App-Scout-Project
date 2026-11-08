from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    PrimaryKeyConstraint,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from downdetector.db.base import Base

_EVENT_TYPE_PATTERN = r"^[a-z_]+(\.[a-z_]+)+$"


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_outbox_events"),
        ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_outbox_events_service_id_services",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            f"event_type ~ '{_EVENT_TYPE_PATTERN}'",
            name="ck_outbox_events_event_type",
        ),
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="ck_outbox_events_payload"),
        Index(
            "ix_outbox_events_unpublished",
            "id",
            postgresql_where=text("published_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True))
    service_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
