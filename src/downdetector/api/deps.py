from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from downdetector.auth.sessions import COOKIE_NAME, delete_session, get_session_user_id
from downdetector.config import Settings
from downdetector.db.user import User


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
        finally:
            if session.in_transaction():
                await session.rollback()


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]
AppSettings = Annotated[Settings, Depends(get_settings)]
SessionCookie = Annotated[str | None, Cookie(alias=COOKIE_NAME)]


async def get_current_user(
    session: DbSession,
    redis: RedisClient,
    session_id: SessionCookie = None,
) -> User:
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user_id = await get_session_user_id(redis, session_id)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        await delete_session(redis, session_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass(frozen=True)
class Viewer:
    id: UUID
    email: str
    role: str


async def get_viewer(
    session: DbSession,
    redis: RedisClient,
    session_id: SessionCookie = None,
) -> Viewer | None:
    if not session_id:
        return None
    user_id = await get_session_user_id(redis, session_id)
    if user_id is None:
        return None
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        await delete_session(redis, session_id)
        return None
    return Viewer(id=user.id, email=user.email, role=user.role)


CurrentViewer = Annotated[Viewer | None, Depends(get_viewer)]
