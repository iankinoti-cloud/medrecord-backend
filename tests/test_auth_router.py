from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.routers import auth
from app.schemas.auth import LoginRequest

from conftest import FakeSession, make_request, make_user


pytestmark = pytest.mark.asyncio


async def test_login_rejects_invalid_credentials():
    with patch.object(auth, "authenticate_user", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as error:
            await auth.login(
                body=LoginRequest(email="user@example.com", password="bad"),
                request=make_request(),
                db=FakeSession(),
            )

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid email or password"


async def test_login_returns_token_and_logs_action():
    user = make_user(role="Doctor")
    db = FakeSession()

    with (
        patch.object(auth, "authenticate_user", new=AsyncMock(return_value=user)),
        patch.object(auth, "create_access_token", return_value="token-123") as create_token,
        patch.object(auth, "log_action", new=AsyncMock()) as log_action,
    ):
        result = await auth.login(
            body=LoginRequest(email=user.email, password="secret"),
            request=make_request(),
            db=db,
        )

    assert result == {"access_token": "token-123", "token_type": "bearer", "user": user}
    create_token.assert_called_once_with(str(user.id), "Doctor")
    log_action.assert_awaited_once()
    assert log_action.await_args.args[:3] == (db, str(user.id), "LOGIN")


async def test_get_me_returns_current_user():
    user = make_user()

    result = await auth.get_me(current_user=user)

    assert result is user


async def test_logout_logs_action_and_returns_detail():
    user = make_user()
    db = FakeSession()

    with patch.object(auth, "log_action", new=AsyncMock()) as log_action:
        result = await auth.logout(request=make_request(), db=db, current_user=user)

    assert result == {"detail": "Logged out"}
    log_action.assert_awaited_once()
    assert log_action.await_args.args[:3] == (db, str(user.id), "LOGOUT")


async def test_google_login_redirects_to_google_authorization():
    response = await auth.google_login()

    assert response.status_code == 307
    assert response.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "response_type=code" in response.headers["location"]


async def test_github_login_redirects_to_github_authorization():
    response = await auth.github_login()

    assert response.status_code == 307
    assert response.headers["location"].startswith("https://github.com/login/oauth/authorize?")
    assert "scope=user:email" in response.headers["location"]


async def test_google_callback_exchanges_code_creates_user_and_redirects():
    user = make_user(role="Doctor")

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, data):
            return type("Response", (), {"json": lambda self: {"access_token": "google-token"}})()

        async def get(self, url, headers):
            return type(
                "Response",
                (),
                {"json": lambda self: {"email": "doc@example.com", "name": "Doc", "picture": "pic", "sub": "sub-1"}},
            )()

    with (
        patch.object(auth, "AsyncClient", return_value=FakeAsyncClient()),
        patch.object(auth, "get_or_create_oauth_user", new=AsyncMock(return_value=user)) as get_user,
        patch.object(auth, "create_access_token", return_value="jwt-token"),
        patch.object(auth, "log_action", new=AsyncMock()),
    ):
        response = await auth.google_callback(code="code-1", request=make_request(), db=FakeSession())

    assert response.status_code == 307
    assert response.headers["location"].endswith("/auth/callback?token=jwt-token")
    get_user.assert_awaited_once()


async def test_github_callback_uses_primary_email_and_redirects():
    user = make_user(role="Doctor")

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, data, headers):
            return type("Response", (), {"json": lambda self: {"access_token": "github-token"}})()

        async def get(self, url, headers):
            if url.endswith("/user"):
                return type("Response", (), {"json": lambda self: {"id": 42, "login": "octo", "name": None}})()
            return type(
                "Response",
                (),
                {"json": lambda self: [{"email": "secondary@example.com"}, {"email": "primary@example.com", "primary": True}]},
            )()

    with (
        patch.object(auth, "AsyncClient", return_value=FakeAsyncClient()),
        patch.object(auth, "get_or_create_oauth_user", new=AsyncMock(return_value=user)) as get_user,
        patch.object(auth, "create_access_token", return_value="jwt-token"),
        patch.object(auth, "log_action", new=AsyncMock()),
    ):
        response = await auth.github_callback(code="code-1", request=make_request(), db=FakeSession())

    assert response.status_code == 307
    assert response.headers["location"].endswith("/auth/callback?token=jwt-token")
    assert get_user.await_args.args[1] == "primary@example.com"
    assert get_user.await_args.args[2] == "octo"
