from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from downdetector.db.breach import Breach
from downdetector.db.check import Check
from downdetector.db.incident import Incident
from downdetector.db.service import Service


@dataclass(frozen=True)
class OverviewRow:
    slug: str
    name: str
    company_name: str | None
    domain: str
    status: str
    status_since: datetime | None
    last_checked_at: datetime | None
    breach_count: int
    major_breach_count: int
    open_incident: str | None


@dataclass(frozen=True)
class IncidentRow:
    title: str
    status: str
    source: str
    opened_at: datetime
    resolved_at: datetime | None


@dataclass(frozen=True)
class BreachRow:
    title: str
    severity: str
    published_at: datetime
    breach_date: date | None


@dataclass(frozen=True)
class CheckRow:
    id: str
    kind: str
    purpose: str
    url: str | None
    interval_seconds: int
    timeout_ms: int
    slow_threshold_ms: int
    failure_threshold: int
    recovery_threshold: int
    enabled: bool


@dataclass(frozen=True)
class ServicePage:
    id: UUID
    slug: str
    name: str
    company_name: str | None
    description: str | None
    domain: str
    homepage_url: str
    status: str
    status_since: datetime | None
    last_checked_at: datetime | None
    breach_count: int
    major_breach_count: int
    incidents: tuple[IncidentRow, ...]
    breaches: tuple[BreachRow, ...]


_STATUS_RANK = {"down": 0, "degraded": 1, "unknown": 2, "up": 3}

_LIST = """
SELECT o.slug, o.name, o.company_name, o.domain, o.status,
       o.status_since, o.last_checked_at, o.breach_count, o.major_breach_count,
       incident.title AS open_incident
FROM service_overview AS o
LEFT JOIN LATERAL (
    SELECT title
    FROM incidents
    WHERE incidents.service_id = o.service_id
      AND incidents.resolved_at IS NULL
    ORDER BY incidents.opened_at DESC
    LIMIT 1
) AS incident ON true
"""


async def list_services(session: AsyncSession, query: str) -> list[OverviewRow]:
    sql = _LIST
    params: dict[str, str] = {}
    if query:
        sql += """
        WHERE o.name ILIKE :pattern ESCAPE '\\'
           OR o.domain ILIKE :pattern ESCAPE '\\'
        """
        params["pattern"] = _like(query)
    found = (await session.execute(text(sql), params)).mappings()
    rows = [
        OverviewRow(
            slug=row["slug"],
            name=row["name"],
            company_name=row["company_name"],
            domain=row["domain"],
            status=row["status"],
            status_since=row["status_since"],
            last_checked_at=row["last_checked_at"],
            breach_count=int(row["breach_count"]),
            major_breach_count=int(row["major_breach_count"]),
            open_incident=row["open_incident"],
        )
        for row in found
    ]
    rows.sort(key=lambda row: (_STATUS_RANK.get(row.status, 9), row.name.casefold()))
    return rows


async def service_page(session: AsyncSession, slug: str) -> ServicePage | None:
    found = await session.execute(select(Service).where(Service.slug == slug))
    service = found.scalar_one_or_none()
    if service is None:
        return None
    overview = (
        (
            await session.execute(
                text(
                    """
                SELECT status, status_since, last_checked_at,
                       breach_count, major_breach_count
                FROM service_overview
                WHERE slug = :slug
                """
                ),
                {"slug": slug},
            )
        )
        .mappings()
        .one()
    )
    incidents = await session.execute(
        select(Incident)
        .where(Incident.service_id == service.id)
        .order_by(Incident.opened_at.desc())
    )
    breaches = await session.execute(
        select(Breach).where(Breach.service_id == service.id).order_by(Breach.published_at.desc())
    )
    return ServicePage(
        id=service.id,
        slug=service.slug,
        name=service.name,
        company_name=service.company_name,
        description=service.description,
        domain=service.domain,
        homepage_url=service.homepage_url,
        status=overview["status"],
        status_since=overview["status_since"],
        last_checked_at=overview["last_checked_at"],
        breach_count=int(overview["breach_count"]),
        major_breach_count=int(overview["major_breach_count"]),
        incidents=tuple(
            IncidentRow(
                title=item.title,
                status=item.status,
                source=item.source,
                opened_at=item.opened_at,
                resolved_at=item.resolved_at,
            )
            for item in incidents.scalars()
        ),
        breaches=tuple(
            BreachRow(
                title=item.title,
                severity=item.severity,
                published_at=item.published_at,
                breach_date=item.breach_date,
            )
            for item in breaches.scalars()
        ),
    )


async def list_checks(session: AsyncSession, service_id: UUID) -> list[CheckRow]:
    rows = await session.execute(
        select(Check).where(Check.service_id == service_id).order_by(Check.created_at)
    )
    return [
        CheckRow(
            id=str(item.id),
            kind=item.kind,
            purpose=item.purpose,
            url=item.url,
            interval_seconds=item.interval_seconds,
            timeout_ms=item.timeout_ms,
            slow_threshold_ms=item.slow_threshold_ms,
            failure_threshold=item.failure_threshold,
            recovery_threshold=item.recovery_threshold,
            enabled=item.enabled,
        )
        for item in rows.scalars()
    ]


def _like(query: str) -> str:
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
