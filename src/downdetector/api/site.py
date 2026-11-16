from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from downdetector.api.cookies import apply_session_cookie, clear_session_cookie
from downdetector.api.deps import (
    AppSettings,
    CurrentViewer,
    DbSession,
    RedisClient,
    SessionCookie,
)
from downdetector.api.render import page
from downdetector.api.schemas import LoginRequest, RegisterRequest
from downdetector.auth.accounts import AccountTaken, authenticate, register_user
from downdetector.auth.sessions import create_session, delete_session
from downdetector.catalog.read import OverviewRow, list_services, service_page

router = APIRouter(include_in_schema=False)


def _groups(services: list[OverviewRow]) -> dict[str, list[OverviewRow]]:
    return {
        "problems": [row for row in services if row.status in {"down", "degraded"}],
        "up": [row for row in services if row.status == "up"],
        "unknown": [row for row in services if row.status not in {"down", "degraded", "up"}],
    }


def _counts(services: list[OverviewRow]) -> dict[str, int]:
    return {
        "down": sum(row.status == "down" for row in services),
        "degraded": sum(row.status == "degraded" for row in services),
        "up": sum(row.status == "up" for row in services),
        "unknown": sum(row.status == "unknown" for row in services),
    }


def _safe_next(value: str | None) -> str:
    if value is None:
        return "/"
    target = value.strip()
    if not target.startswith("/") or target.startswith("//") or "\\" in target:
        return "/"
    return target


@router.get("/")
async def home(
    request: Request,
    session: DbSession,
    viewer: CurrentViewer,
    q: str = "",
):
    query = q.strip()[:100]
    services = await list_services(session, query)
    return page(
        request,
        "home.html",
        viewer=viewer,
        services=services,
        groups=_groups(services),
        counts=_counts(services),
        query=query,
    )


@router.get("/services/{slug}")
async def service_detail(
    request: Request,
    slug: str,
    session: DbSession,
    viewer: CurrentViewer,
):
    found = await service_page(session, slug.strip().casefold())
    if found is None:
        return page(request, "missing.html", status_code=404, viewer=viewer)
    return page(request, "service.html", viewer=viewer, service=found)


@router.get("/login")
async def login_form(
    request: Request,
    viewer: CurrentViewer,
    next: str = "",
    created: str = "",
):
    return page(
        request,
        "login.html",
        viewer=viewer,
        next=_safe_next(next),
        created=created == "1",
        error="",
        email="",
    )


@router.post("/login")
async def login_submit(
    request: Request,
    session: DbSession,
    redis: RedisClient,
    settings: AppSettings,
    viewer: CurrentViewer,
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    next: Annotated[str, Form()] = "",
):
    target = _safe_next(next)
    try:
        LoginRequest(email=email, password=password)
    except ValidationError:
        return page(
            request,
            "login.html",
            status_code=400,
            viewer=viewer,
            next=target,
            created=False,
            error="Check the email and password.",
            email=email,
        )
    user = await authenticate(session, email, password)
    if user is None:
        return page(
            request,
            "login.html",
            status_code=401,
            viewer=viewer,
            next=target,
            created=False,
            error="Invalid email or password.",
            email=email,
        )
    token = await create_session(redis, user.id, settings.session_ttl_seconds)
    response = RedirectResponse(target, status_code=303)
    apply_session_cookie(response, token, settings)
    return response


@router.get("/register")
async def register_form(request: Request, viewer: CurrentViewer):
    return page(request, "register.html", viewer=viewer, error="", email="", username="")


@router.post("/register")
async def register_submit(
    request: Request,
    session: DbSession,
    viewer: CurrentViewer,
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    username: Annotated[str, Form()] = "",
):
    clean_username = username.strip() or None
    try:
        body = RegisterRequest(email=email, password=password, username=clean_username)
    except ValidationError:
        return page(
            request,
            "register.html",
            status_code=400,
            viewer=viewer,
            error="Check the email, a password of at least 12 characters, and the username.",
            email=email,
            username=username,
        )
    try:
        await register_user(session, body.email, body.password, body.username)
    except AccountTaken:
        return page(
            request,
            "register.html",
            status_code=409,
            viewer=viewer,
            error="Could not complete registration.",
            email=email,
            username=username,
        )
    return RedirectResponse("/login?created=1", status_code=303)


@router.post("/logout")
async def logout(
    redis: RedisClient,
    settings: AppSettings,
    session_id: SessionCookie = None,
):
    if session_id:
        await delete_session(redis, session_id)
    response = RedirectResponse("/", status_code=303)
    clear_session_cookie(response, settings)
    return response
