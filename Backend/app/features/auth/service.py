from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.features.auth.models import User, UserRole
from app.features.auth.schemas import TokenResponse, UserLogin, UserRegister


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, payload: UserRegister) -> TokenResponse:
    existing = await get_user_by_email(db, payload.email)
    if existing is not None:
        raise ConflictError("A user with this email already exists")

    is_first_user = (await db.execute(select(User.id).limit(1))).first() is None

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.ADMIN if is_first_user else UserRole.USER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return _issue_token(user)


async def login_user(db: AsyncSession, payload: UserLogin) -> TokenResponse:
    user = await get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    return _issue_token(user)


def _issue_token(user: User) -> TokenResponse:
    token = create_access_token(user_id=user.id, role=user.role.value)
    return TokenResponse(access_token=token, user=user)
