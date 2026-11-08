from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from downdetector.db.base import Base

_SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
_DOMAIN_PATTERN = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_services"),
        UniqueConstraint("slug", name="uq_services_slug"),
        UniqueConstraint("domain", name="uq_services_domain"),
        CheckConstraint(f"slug ~ '{_SLUG_PATTERN}'", name="ck_services_slug"),
        CheckConstraint("length(btrim(name)) > 0", name="ck_services_name"),
        CheckConstraint(f"domain ~ '{_DOMAIN_PATTERN}'", name="ck_services_domain"),
        CheckConstraint("homepage_url LIKE 'https://%'", name="ck_services_homepage_url"),
        ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_services_created_by_users",
            ondelete="SET NULL",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), default=uuid4)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    homepage_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
