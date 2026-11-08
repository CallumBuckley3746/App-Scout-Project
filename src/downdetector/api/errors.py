from collections.abc import Mapping
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_HIDDEN_ERROR_KEYS = {"input", "ctx"}


def _submitted_password(body: object) -> str | None:
    if not isinstance(body, Mapping):
        return None
    password = body.get("password")
    if isinstance(password, str) and password:
        return password
    return None


def _redact(value: Any, password: str | None) -> Any:
    if not password:
        return value
    if isinstance(value, str):
        return value.replace(password, "[redacted]")
    if isinstance(value, list | tuple):
        return [_redact(item, password) for item in value]
    return value


async def request_validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    password = _submitted_password(exc.body)
    detail = [
        {
            key: _redact(value, password)
            for key, value in error.items()
            if key not in _HIDDEN_ERROR_KEYS
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content=jsonable_encoder({"detail": detail}))
