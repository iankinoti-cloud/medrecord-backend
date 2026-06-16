from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import settings
from app.utils.jwt import create_access_token, decode_token


def test_create_access_token_contains_subject_role_and_expiration():
    token = create_access_token("user-1", "Admin")

    payload = decode_token(token)

    assert payload["sub"] == "user-1"
    assert payload["role"] == "Admin"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_token_returns_none_for_invalid_token():
    assert decode_token("not-a-jwt") is None


def test_decode_token_returns_none_for_expired_token():
    expired = jwt.encode(
        {
            "sub": "user-1",
            "role": "Doctor",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    assert decode_token(expired) is None
