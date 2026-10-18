import secrets
from uuid import UUID

from redis.asyncio import Redis

COOKIE_NAME = "session_id"
_SESSION_PREFIX = "session:"


def _session_key(session_id: str) -> str:
    return f"{_SESSION_PREFIX}{session_id}"


async def create_session(redis: Redis, user_id: UUID, ttl_seconds: int) -> str:
    token = secrets.token_urlsafe(32)
    await redis.set(_session_key(token), str(user_id), ex=ttl_seconds)
    return token


async def get_session_user_id(redis: Redis, session_id: str) -> UUID | None:
    raw = await redis.get(_session_key(session_id))
    if isinstance(raw, bytes):
        try:
            raw = raw.decode()
        except UnicodeDecodeError:
            return None
    if not isinstance(raw, str) or raw == "":
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None


async def delete_session(redis: Redis, session_id: str) -> None:
    await redis.delete(_session_key(session_id))
