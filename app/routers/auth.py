from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserOut
from app.services.audit_service import log_action
from app.services.auth_service import authenticate_user, get_or_create_oauth_user
from app.utils.jwt import create_access_token

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    body:    LoginRequest,
    request: Request,
    db:      Annotated[AsyncSession, Depends(get_db)],
):
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(str(user.id), user.role)
    await log_action(db, str(user.id), "LOGIN", request, entity_type="User", entity_id=str(user.id))
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=UserOut)
async def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(
    request:      Request,
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user= Depends(get_current_user),
):
    await log_action(db, str(current_user.id), "LOGOUT", request, entity_type="User", entity_id=str(current_user.id))
    return {"detail": "Logged out"}


# ── Google OAuth ──────────────────────────────────────────────

@router.get("/google")
async def google_login():
    params = (
        f"client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&access_type=offline"
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/google/callback")
async def google_callback(
    code:    str,
    request: Request,
    db:      Annotated[AsyncSession, Depends(get_db)],
):
    async with AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code":          code,
                "client_id":     settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
                "grant_type":    "authorization_code",
            },
        )
        token_data = token_res.json()
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        info = user_res.json()

    user = await get_or_create_oauth_user(
        db, info["email"], info.get("name", info["email"]),
        info.get("picture"), "google", info["sub"],
    )
    token = create_access_token(str(user.id), user.role)
    await log_action(db, str(user.id), "LOGIN", request, entity_type="User", entity_id=str(user.id))
    return RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback?token={token}")


# ── GitHub OAuth ──────────────────────────────────────────────

@router.get("/github")
async def github_login():
    params = (
        f"client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=user:email"
    )
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")


@router.get("/github/callback")
async def github_callback(
    code:    str,
    request: Request,
    db:      Annotated[AsyncSession, Depends(get_db)],
):
    async with AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id":     settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code":          code,
                "redirect_uri":  settings.GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )
        gh_token = token_res.json()["access_token"]

        user_res  = await client.get("https://api.github.com/user",  headers={"Authorization": f"Bearer {gh_token}"})
        email_res = await client.get("https://api.github.com/user/emails", headers={"Authorization": f"Bearer {gh_token}"})
        info   = user_res.json()
        emails = email_res.json()

    primary_email = next((e["email"] for e in emails if e.get("primary")), info.get("email"))
    user = await get_or_create_oauth_user(
        db, primary_email, info.get("name") or info["login"],
        info.get("avatar_url"), "github", str(info["id"]),
    )
    token = create_access_token(str(user.id), user.role)
    await log_action(db, str(user.id), "LOGIN", request, entity_type="User", entity_id=str(user.id))
    return RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback?token={token}")
