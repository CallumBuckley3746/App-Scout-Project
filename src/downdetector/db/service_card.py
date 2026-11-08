from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from downdetector.db.base import Base, sql_in

CARD_STATUSES = ("unknown", "up", "degraded", "down")


class ServiceCard(Base):
    __tablename__ = "service_cards"
    __table_args__ = (
        PrimaryKeyConstraint("service_id", name="pk_service_cards"),
        ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_service_cards_service_id_services",
            ondelete="CASCADE",
        ),
        CheckConstraint(sql_in("status", CARD_STATUSES), name="ck_service_cards_status"),
    )

    service_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default=text("'unknown'"),
    )
    status_since: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
