from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.features.auth import service
from app.features.auth.models import User
from app.features.auth.schemas import RefreshTokenRequest, TokenResponse, UserLogin, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    return await service.register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    return await service.login_user(db, payload)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Exchanges a refresh token for a new access token, rotating it."""
    return await service.refresh_tokens(db, payload.refresh_token)


@router.post("/logout", status_code=204)
async def logout(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Revokes a refresh token (e.g. on client sign-out). Its access token
    keeps working until it naturally expires — access tokens are short-lived
    and not tracked server-side, by design."""
    await service.logout_user(db, payload.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)):
    return user


@router.get("/me/quota")
async def my_quota(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """The caller's dollar quota: the three windows with used / limit / reset time (for the chat banner)."""
    from app.features.usage import quota

    return await quota.user_quota(db, user)


@router.get("/me/usage")
async def my_usage(days: int = Query(30, ge=1, le=90), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """The caller's own consumption (this Jalali month by purpose, daily cost) for the profile page."""
    from app.features.usage import quota

    return await quota.my_usage(db, user, days)
