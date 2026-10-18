from uuid import uuid4

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from downdetector.auth.passwords import hash_password, verify_password
from downdetector.db.user import User

# Checked once when the account row is missing so both login outcomes verify a hash.
_MISSING_USER_PASSWORD = "not-a-user-password"
_MISSING_USER_HASH = hash_password(_MISSING_USER_PASSWORD)


class EmailTaken(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def _require_admin_email(email: str) -> str:
    normalized = normalize_email(email)
    try:
        validate_email(normalized, check_deliverability=False)
    except EmailNotValidError:
        raise ValueError("ADMIN_EMAIL is invalid") from None
    return normalized


async def register_user(session: AsyncSession, email: str, password: str) -> User:
    user = User(
        id=uuid4(),
        email=normalize_email(email),
        password_hash=hash_password(password),
        role="user",
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise EmailTaken from None
    return user


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    normalized = normalize_email(email)
    result = await session.execute(select(User).where(User.email == normalized))
    user = result.scalar_one_or_none()
    password_hash = user.password_hash if user is not None else _MISSING_USER_HASH
    password_matches = verify_password(password, password_hash)
    if user is None or not password_matches:
        return None
    return user


async def ensure_admin(session: AsyncSession, email: str, password: str) -> None:
    if len(password) < 12 or len(password) > 128:
        raise ValueError("ADMIN_PASSWORD length is invalid")
    normalized = _require_admin_email(email)
    existing = await session.execute(select(User).where(User.email == normalized))
    if existing.scalar_one_or_none() is not None:
        return
    session.add(
        User(
            id=uuid4(),
            email=normalized,
            password_hash=hash_password(password),
            role="admin",
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
