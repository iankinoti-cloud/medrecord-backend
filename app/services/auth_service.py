from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email, User.is_active == True))
    user = result.scalar_one_or_none()
    if user is None or user.password_hash is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_or_create_oauth_user(
    db:        AsyncSession,
    email:     str,
    full_name: str,
    avatar_url: str | None,
    provider:  str,
    provider_id: str,
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        if provider == "google" and not user.google_id:
            user.google_id = provider_id
        if provider == "github" and not user.github_id:
            user.github_id = provider_id
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        await db.commit()
        await db.refresh(user)
        return user

    new_user = User(
        email      = email,
        full_name  = full_name,
        role       = "Doctor",
        avatar_url = avatar_url,
        google_id  = provider_id if provider == "google" else None,
        github_id  = provider_id if provider == "github" else None,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
