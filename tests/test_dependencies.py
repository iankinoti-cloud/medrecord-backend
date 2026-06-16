import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app import dependencies

from conftest import FakeResult, FakeSession, make_user


pytestmark = pytest.mark.asyncio


async def test_get_current_user_rejects_invalid_token():
    credentials = SimpleNamespace(credentials="bad-token")

    with patch.object(dependencies, "decode_token", return_value=None):
        with pytest.raises(HTTPException) as error:
            await dependencies.get_current_user(credentials=credentials, db=FakeSession())

    assert error.value.status_code == 401
    assert error.value.headers == {"WWW-Authenticate": "Bearer"}


async def test_get_current_user_rejects_payload_without_subject():
    credentials = SimpleNamespace(credentials="token")

    with patch.object(dependencies, "decode_token", return_value={"role": "Doctor"}):
        with pytest.raises(HTTPException) as error:
            await dependencies.get_current_user(credentials=credentials, db=FakeSession())

    assert error.value.status_code == 401


async def test_get_current_user_rejects_missing_or_inactive_user():
    credentials = SimpleNamespace(credentials="token")
    user_id = uuid.uuid4()
    db = FakeSession([FakeResult(scalar=make_user(id=user_id, is_active=False))])

    with patch.object(dependencies, "decode_token", return_value={"sub": str(user_id)}):
        with pytest.raises(HTTPException) as error:
            await dependencies.get_current_user(credentials=credentials, db=db)

    assert error.value.status_code == 401


async def test_get_current_user_returns_active_user():
    credentials = SimpleNamespace(credentials="token")
    user = make_user()
    db = FakeSession([FakeResult(scalar=user)])

    with patch.object(dependencies, "decode_token", return_value={"sub": str(user.id)}):
        result = await dependencies.get_current_user(credentials=credentials, db=db)

    assert result is user


async def test_require_roles_allows_authorized_role():
    checker = dependencies.require_roles("Admin", "Doctor")
    user = make_user(role="Doctor")

    result = await checker(current_user=user)

    assert result is user


async def test_require_roles_rejects_unauthorized_role():
    checker = dependencies.require_roles("Admin")

    with pytest.raises(HTTPException) as error:
        await checker(current_user=make_user(role="Lab Technician"))

    assert error.value.status_code == 403
    assert error.value.detail == "You do not have permission to perform this action"
