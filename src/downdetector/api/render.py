from datetime import date, datetime
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

PACKAGE = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(PACKAGE / "templates"))

KINDS = (
    ("http", "HTTP"),
    ("status_page", "Status page"),
    ("rss", "RSS"),
    ("breach", "Breach"),
)
PURPOSES = (
    ("primary", "Primary"),
    ("extra", "Extra"),
    ("breach", "Breach"),
)
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _status_label(value: str) -> str:
    return {
        "up": "Up",
        "degraded": "Degraded",
        "down": "Down",
        "unknown": "Unknown",
    }.get(value, value)


def _when(value: datetime | date | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        local = value.astimezone()
        return f"{local.day} {_MONTHS[local.month - 1]} {local.year}, {local:%H:%M}"
    return f"{value.day} {_MONTHS[value.month - 1]} {value.year}"


def _severity_label(value: str) -> str:
    return {
        "low": "low",
        "medium": "medium",
        "high": "high",
        "critical": "critical",
    }.get(value, value)


def _source_label(value: str) -> str:
    return {"detector": "our check", "status_page": "status page"}.get(value, value)


def _labeled(options: tuple[tuple[str, str], ...], value: str) -> str:
    for key, label in options:
        if key == value:
            return label
    return value


templates.env.filters["status_label"] = _status_label
templates.env.filters["when"] = _when
templates.env.filters["severity_label"] = _severity_label
templates.env.filters["source_label"] = _source_label
templates.env.filters["kind_label"] = lambda value: _labeled(KINDS, value)
templates.env.filters["purpose_label"] = lambda value: _labeled(PURPOSES, value)


def page(request: Request, name: str, *, status_code: int = 200, **context: object) -> Response:
    return templates.TemplateResponse(request, name, context, status_code=status_code)
