import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from downdetector.auth.accounts import normalize_username

# Surrounding spaces make min_length/max_length disagree with a pattern that
# also allows those spaces, so the normalized value is checked instead.
_USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    username: str | None = None

    @field_validator("username")
    @classmethod
    def _check_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_username(value)
        if _USERNAME_RE.fullmatch(normalized) is None:
            raise ValueError("invalid username")
        return normalized


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str | None
    role: Literal["admin", "user"]
