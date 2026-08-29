from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.features.auth import service
from app.features.auth.models import User
from app.features.auth.schemas import TokenResponse, UserLogin, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    return await service.register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    return await service.login_user(db, payload)


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)):
    return user
