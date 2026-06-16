from unittest.mock import patch

import pytest

from app.services import auth_service

from conftest import FakeResult, FakeSession, make_user


pytestmark = pytest.mark.asyncio


async def test_hash_password_creates_verifiable_non_plaintext_hash():
    hashed = auth_service.hash_password("secret")

    assert hashed != "secret"
    assert auth_service.verify_password("secret", hashed) is True
    assert auth_service.verify_password("wrong", hashed) is False


async def test_authenticate_user_returns_none_when_user_missing():
    db = FakeSession([FakeResult(scalar=None)])

    result = await auth_service.authenticate_user(db, "missing@example.com", "secret")

    assert result is None


async def test_authenticate_user_returns_none_without_password_hash():
    db = FakeSession([FakeResult(scalar=make_user(password_hash=None))])

    result = await auth_service.authenticate_user(db, "oauth@example.com", "secret")

    assert result is None


async def test_authenticate_user_returns_none_for_bad_password():
    user = make_user(password_hash="hashed")
    db = FakeSession([FakeResult(scalar=user)])

    with patch.object(auth_service, "verify_password", return_value=False):
        result = await auth_service.authenticate_user(db, user.email, "wrong")

    assert result is None


async def test_authenticate_user_returns_active_user_for_valid_password():
    user = make_user(password_hash="hashed")
    db = FakeSession([FakeResult(scalar=user)])

    with patch.object(auth_service, "verify_password", return_value=True):
        result = await auth_service.authenticate_user(db, user.email, "secret")

    assert result is user


async def test_get_or_create_oauth_user_updates_existing_google_user():
    user = make_user(google_id=None, github_id=None, avatar_url=None)
    db = FakeSession([FakeResult(scalar=user)])

    result = await auth_service.get_or_create_oauth_user(
        db,
        email=user.email,
        full_name="Updated Name",
        avatar_url="https://example.com/avatar.png",
        provider="google",
        provider_id="google-123",
    )

    assert result is user
    assert user.google_id == "google-123"
    assert user.github_id is None
    assert user.avatar_url == "https://example.com/avatar.png"
    assert db.commits == 1
    assert db.refreshed == [user]


async def test_get_or_create_oauth_user_creates_new_github_doctor():
    db = FakeSession([FakeResult(scalar=None)])

    result = await auth_service.get_or_create_oauth_user(
        db,
        email="new@example.com",
        full_name="New Doctor",
        avatar_url=None,
        provider="github",
        provider_id="42",
    )

    assert result.email == "new@example.com"
    assert result.full_name == "New Doctor"
    assert result.role == "Doctor"
    assert result.google_id is None
    assert result.github_id == "42"
    assert db.added == [result]
    assert db.commits == 1
    assert db.refreshed == [result]
