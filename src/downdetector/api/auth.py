from fastapi import APIRouter, HTTPException, Response, status

from downdetector.api.cookies import apply_session_cookie, clear_session_cookie
from downdetector.api.deps import AppSettings, CurrentUser, DbSession, RedisClient, SessionCookie
from downdetector.api.schemas import LoginRequest, RegisterRequest, UserResponse
from downdetector.auth.accounts import AccountTaken, authenticate, register_user
from downdetector.auth.sessions import create_session, delete_session
from downdetector.db.user import User

router = APIRouter(prefix="/api/auth")


def _user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(
        {"id": user.id, "email": user.email, "username": user.username, "role": user.role},
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register(body: RegisterRequest, session: DbSession) -> UserResponse:
    try:
        user = await register_user(session, body.email, body.password, body.username)
    except AccountTaken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not complete registration",
        ) from None
    return _user_response(user)


@router.post("/login", status_code=status.HTTP_200_OK, response_model=UserResponse)
async def login(
    body: LoginRequest,
    response: Response,
    session: DbSession,
    redis: RedisClient,
    settings: AppSettings,
    session_id: SessionCookie = None,
) -> UserResponse:
    user = await authenticate(session, body.email, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if session_id:
        await delete_session(redis, session_id)
    token = await create_session(redis, user.id, settings.session_ttl_seconds)
    apply_session_cookie(response, token, settings)
    return _user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    redis: RedisClient,
    settings: AppSettings,
    session_id: SessionCookie = None,
) -> Response:
    if session_id:
        await delete_session(redis, session_id)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response, settings)
    return response


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return _user_response(user)
