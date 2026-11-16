from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from downdetector.catalog.errors import CatalogError
from downdetector.catalog.fields import CheckInput, ServiceInput
from downdetector.db.check import Check
from downdetector.db.service import Service


async def create_service(
    session: AsyncSession,
    actor_id: UUID,
    data: ServiceInput,
) -> Service:
    service = Service(
        id=uuid4(),
        name=data.name,
        slug=data.slug,
        domain=data.domain,
        homepage_url=data.homepage_url,
        company_name=data.company_name,
        description=data.description,
        created_by=actor_id,
        updated_at=datetime.now(UTC),
    )
    session.add(service)
    await _commit(session, "A service with this slug or domain already exists.")
    return service


async def update_service(
    session: AsyncSession,
    slug: str,
    data: ServiceInput,
) -> Service | None:
    service = await _service(session, slug)
    if service is None:
        return None
    service.name = data.name
    service.slug = data.slug
    service.domain = data.domain
    service.homepage_url = data.homepage_url
    service.company_name = data.company_name
    service.description = data.description
    service.updated_at = datetime.now(UTC)
    await _commit(session, "A service with this slug or domain already exists.")
    return service


async def delete_service(session: AsyncSession, slug: str) -> bool:
    service = await _service(session, slug)
    if service is None:
        return False
    await session.delete(service)
    await session.commit()
    return True


async def create_check(
    session: AsyncSession,
    slug: str,
    data: CheckInput,
) -> Service | None:
    service = await _service(session, slug)
    if service is None:
        return None
    await _ensure_unique_check(session, service.id, data, None)
    session.add(
        Check(
            id=uuid4(),
            service_id=service.id,
            kind=data.kind,
            purpose=data.purpose,
            url=data.url,
            interval_seconds=data.interval_seconds,
            timeout_ms=data.timeout_ms,
            slow_threshold_ms=data.slow_threshold_ms,
            failure_threshold=data.failure_threshold,
            recovery_threshold=data.recovery_threshold,
            enabled=data.enabled,
        )
    )
    await _commit(session, "This check already exists.")
    return service


async def update_check(
    session: AsyncSession,
    slug: str,
    check_id: UUID,
    data: CheckInput,
) -> Service | None:
    service = await _service(session, slug)
    if service is None:
        return None
    found = await session.execute(
        select(Check).where(Check.id == check_id, Check.service_id == service.id)
    )
    check = found.scalar_one_or_none()
    if check is None:
        return None
    await _ensure_unique_check(session, service.id, data, check.id)
    check.kind = data.kind
    check.purpose = data.purpose
    check.url = data.url
    check.interval_seconds = data.interval_seconds
    check.timeout_ms = data.timeout_ms
    check.slow_threshold_ms = data.slow_threshold_ms
    check.failure_threshold = data.failure_threshold
    check.recovery_threshold = data.recovery_threshold
    check.enabled = data.enabled
    await _commit(session, "This check already exists.")
    return service


async def delete_check(session: AsyncSession, slug: str, check_id: UUID) -> bool | None:
    service = await _service(session, slug)
    if service is None:
        return None
    found = await session.execute(
        select(Check).where(Check.id == check_id, Check.service_id == service.id)
    )
    check = found.scalar_one_or_none()
    if check is None:
        return False
    await session.delete(check)
    await session.commit()
    return True


async def _service(session: AsyncSession, slug: str) -> Service | None:
    found = await session.execute(select(Service).where(Service.slug == slug))
    return found.scalar_one_or_none()


async def _ensure_unique_check(
    session: AsyncSession,
    service_id: UUID,
    data: CheckInput,
    current_id: UUID | None,
) -> None:
    if data.purpose == "primary":
        primary_filter = [
            Check.service_id == service_id,
            Check.purpose == "primary",
        ]
        if current_id is not None:
            primary_filter.append(Check.id != current_id)
        primary = await session.execute(select(Check.id).where(*primary_filter))
        if primary.scalar_one_or_none() is not None:
            raise CatalogError("This service already has a primary check.")
    same_url = Check.url.is_(None) if data.url is None else Check.url == data.url
    duplicate_filter = [
        Check.service_id == service_id,
        Check.kind == data.kind,
        same_url,
    ]
    if current_id is not None:
        duplicate_filter.append(Check.id != current_id)
    duplicate = await session.execute(select(Check.id).where(*duplicate_filter))
    if duplicate.scalar_one_or_none() is not None:
        raise CatalogError("This check already exists.")


async def _commit(session: AsyncSession, duplicate_message: str) -> None:
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise CatalogError(duplicate_message) from None
