from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from redis.asyncio import Redis

from downdetector.api.auth import router as auth_router
from downdetector.api.errors import request_validation_exception_handler
from downdetector.auth.accounts import ensure_admin
from downdetector.config import Settings
from downdetector.db.session import create_engine, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(resolved.database_url)
        session_factory = create_session_factory(engine)
        redis = Redis.from_url(resolved.redis_url, decode_responses=True)
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.redis = redis
        app.state.settings = resolved
        async with session_factory() as session:
            await ensure_admin(session, resolved.admin_email, resolved.admin_password)
        try:
            yield
        finally:
            await redis.aclose()
            await engine.dispose()

    app = FastAPI(debug=False, redirect_slashes=False, lifespan=lifespan)
    app.state.settings = resolved
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.include_router(auth_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
