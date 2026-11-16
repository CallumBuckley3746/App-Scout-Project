from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from downdetector.api.deps import CurrentViewer, DbSession, Viewer
from downdetector.api.render import KINDS, PURPOSES, page
from downdetector.catalog.errors import CatalogError
from downdetector.catalog.fields import parse_check_form, parse_service_form
from downdetector.catalog.read import list_checks, list_services, service_page
from downdetector.catalog.write import (
    create_check,
    create_service,
    delete_check,
    delete_service,
    update_check,
    update_service,
)

router = APIRouter(include_in_schema=False)


def _guard(request: Request, viewer: Viewer | None):
    if viewer is None:
        target = "/login?next=" + quote(request.url.path, safe="/")
        return RedirectResponse(target, status_code=303)
    if viewer.role != "admin":
        return page(request, "forbidden.html", status_code=403, viewer=viewer)
    return None


def _service_values(
    *,
    name: str,
    slug: str,
    domain: str,
    homepage_url: str,
    company_name: str,
    description: str,
) -> dict[str, str]:
    return {
        "name": name,
        "slug": slug,
        "domain": domain,
        "homepage_url": homepage_url,
        "company_name": company_name,
        "description": description,
    }


@router.get("/admin")
async def admin_home(request: Request, session: DbSession, viewer: CurrentViewer):
    blocked = _guard(request, viewer)
    if blocked is not None:
        return blocked
    services = await list_services(session, "")
    return page(request, "admin_list.html", viewer=viewer, services=services)


@router.get("/admin/services/new")
async def new_service_form(request: Request, viewer: CurrentViewer):
    blocked = _guard(request, viewer)
    if blocked is not None:
        return blocked
    return page(
        request,
        "admin_new.html",
        viewer=viewer,
        error="",
        form=_service_values(
            name="",
            slug="",
            domain="",
            homepage_url="",
            company_name="",
            description="",
        ),
    )


@router.post("/admin/services/new")
async def new_service_submit(
    request: Request,
    session: DbSession,
    viewer: CurrentViewer,
    name: Annotated[str, Form()] = "",
    slug: Annotated[str, Form()] = "",
    domain: Annotated[str, Form()] = "",
    homepage_url: Annotated[str, Form()] = "",
    company_name: Annotated[str, Form()] = "",
    description: Annotated[str, Form()] = "",
):
    blocked = _guard(request, viewer)
    if blocked is not None:
        return blocked
    assert viewer is not None
    form = _service_values(
        name=name,
        slug=slug,
        domain=domain,
        homepage_url=homepage_url,
        company_name=company_name,
        description=description,
    )
    try:
        data = parse_service_form(**form)
        service = await create_service(session, viewer.id, data)
    except CatalogError as error:
        return page(
            request,
            "admin_new.html",
            status_code=400,
            viewer=viewer,
            error=error.message,
            form=form,
        )
    return RedirectResponse(f"/admin/services/{service.slug}", status_code=303)


@router.get("/admin/services/{slug}")
async def edit_service_form(
    request: Request,
    slug: str,
    session: DbSession,
    viewer: CurrentViewer,
):
    blocked = _guard(request, viewer)
    if blocked is not None:
        return blocked
    found = await service_page(session, slug.strip().casefold())
    if found is None:
        return page(request, "missing.html", status_code=404, viewer=viewer)
    checks = await list_checks(session, found.id)
    return page(
        request,
        "admin_service.html",
        viewer=viewer,
        service=found,
        checks=checks,
        kinds=KINDS,
        purposes=PURPOSES,
        error="",
        form=_service_values(
            name=found.name,
            slug=found.slug,
            domain=found.domain,
            homepage_url=found.homepage_url,
            company_name=found.company_name or "",
            description=found.description or "",
        ),
    )


@router.post("/admin/services/{slug}")
async def edit_service_submit(
    request: Request,
    slug: str,
    session: DbSession,
    viewer: CurrentViewer,
    name: Annotated[str, Form()] = "",
    slug_field: Annotated[str, Form(alias="slug")] = "",
    domain: Annotated[str, Form()] = "",
    homepage_url: Annotated[str, Form()] = "",
    company_name: Annotated[str, Form()] = "",
    description: Annotated[str, Form()] = "",
):
    blocked = _guard(request, viewer)
    if blocked is not None:
        return blocked
    form = _service_values(
        name=name,
        slug=slug_field,
        domain=domain,
        homepage_url=homepage_url,
        company_name=company_name,
        description=description,
    )
    try:
        data = parse_service_form(**form)
        updated = await update_service(session, slug.strip().casefold(), data)
    except CatalogError as error:
        return await _edit_page(request, session, viewer, slug, error.message, form)
    if updated is None:
        return page(request, "missing.html", status_code=404, viewer=viewer)
    return RedirectResponse(f"/admin/services/{updated.slug}", status_code=303)


@router.post("/admin/services/{slug}/delete")
async def delete_service_submit(
    request: Request,
    slug: str,
    session: DbSession,
    viewer: CurrentViewer,
):
    blocked = _guard(request, viewer)
    if blocked is not None:
        return blocked
    removed = await delete_service(session, slug.strip().casefold())
    if not removed:
        return page(request, "missing.html", status_code=404, viewer=viewer)
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/services/{slug}/checks")
async def add_check_submit(
    request: Request,
    slug: str,
    session: DbSession,
    viewer: CurrentViewer,
    kind: Annotated[str, Form()] = "",
    purpose: Annotated[str, Form()] = "",
    url: Annotated[str, Form()] = "",
    interval_seconds: Annotated[str, Form()] = "",
    timeout_ms: Annotated[str, Form()] = "",
    slow_threshold_ms: Annotated[str, Form()] = "",
    failure_threshold: Annotated[str, Form()] = "",
    recovery_threshold: Annotated[str, Form()] = "",
    enabled: Annotated[str | None, Form()] = None,
):
    blocked = _guard(request, viewer)
    if blocked is not None:
        return blocked
    clean_slug = slug.strip().casefold()
    try:
        data = parse_check_form(
            kind=kind,
            purpose=purpose,
            url=url,
            interval_seconds=interval_seconds,
            timeout_ms=timeout_ms,
            slow_threshold_ms=slow_threshold_ms,
            failure_threshold=failure_threshold,
            recovery_threshold=recovery_threshold,
            enabled=enabled is not None,
        )
        updated = await create_check(session, clean_slug, data)
    except CatalogError as error:
        return await _edit_page(request, session, viewer, clean_slug, error.message, None)
    if updated is None:
        return page(request, "missing.html", status_code=404, viewer=viewer)
    return RedirectResponse(f"/admin/services/{updated.slug}", status_code=303)


@router.post("/admin/services/{slug}/checks/{check_id}")
async def edit_check_submit(
    request: Request,
    slug: str,
    check_id: UUID,
    session: DbSession,
    viewer: CurrentViewer,
    kind: Annotated[str, Form()] = "",
    purpose: Annotated[str, Form()] = "",
    url: Annotated[str, Form()] = "",
    interval_seconds: Annotated[str, Form()] = "",
    timeout_ms: Annotated[str, Form()] = "",
    slow_threshold_ms: Annotated[str, Form()] = "",
    failure_threshold: Annotated[str, Form()] = "",
    recovery_threshold: Annotated[str, Form()] = "",
    enabled: Annotated[str | None, Form()] = None,
):
    blocked = _guard(request, viewer)
    if blocked is not None:
        return blocked
    clean_slug = slug.strip().casefold()
    try:
        data = parse_check_form(
            kind=kind,
            purpose=purpose,
            url=url,
            interval_seconds=interval_seconds,
            timeout_ms=timeout_ms,
            slow_threshold_ms=slow_threshold_ms,
            failure_threshold=failure_threshold,
            recovery_threshold=recovery_threshold,
            enabled=enabled is not None,
        )
        updated = await update_check(session, clean_slug, check_id, data)
    except CatalogError as error:
        return await _edit_page(request, session, viewer, clean_slug, error.message, None)
    if updated is None:
        return page(request, "missing.html", status_code=404, viewer=viewer)
    return RedirectResponse(f"/admin/services/{updated.slug}", status_code=303)


@router.post("/admin/services/{slug}/checks/{check_id}/delete")
async def delete_check_submit(
    request: Request,
    slug: str,
    check_id: UUID,
    session: DbSession,
    viewer: CurrentViewer,
):
    blocked = _guard(request, viewer)
    if blocked is not None:
        return blocked
    clean_slug = slug.strip().casefold()
    removed = await delete_check(session, clean_slug, check_id)
    if removed is None:
        return page(request, "missing.html", status_code=404, viewer=viewer)
    if not removed:
        return page(request, "missing.html", status_code=404, viewer=viewer)
    return RedirectResponse(f"/admin/services/{clean_slug}", status_code=303)


async def _edit_page(request, session, viewer, slug: str, error: str, form):
    found = await service_page(session, slug.strip().casefold())
    if found is None:
        return page(request, "missing.html", status_code=404, viewer=viewer)
    checks = await list_checks(session, found.id)
    shown = form or _service_values(
        name=found.name,
        slug=found.slug,
        domain=found.domain,
        homepage_url=found.homepage_url,
        company_name=found.company_name or "",
        description=found.description or "",
    )
    return page(
        request,
        "admin_service.html",
        status_code=400,
        viewer=viewer,
        service=found,
        checks=checks,
        kinds=KINDS,
        purposes=PURPOSES,
        error=error,
        form=shown,
    )
