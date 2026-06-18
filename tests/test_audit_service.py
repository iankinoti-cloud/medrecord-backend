import uuid

import pytest

from app.models.audit_log import AuditLog
from app.services.audit_service import log_action

from conftest import FakeSession, make_request


pytestmark = pytest.mark.asyncio


async def test_log_action_persists_audit_entry_with_forwarded_ip():
    db = FakeSession()
    user_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    request = make_request(ip="10.0.0.2", forwarded_for="203.0.113.5, 10.0.0.2", user_agent="pytest-agent")

    await log_action(
        db=db,
        user_id=str(user_id),
        action="VIEW_PATIENT",
        request=request,
        entity_type="Patient",
        entity_id=str(entity_id),
        details={"patient_name": "Patient One"},
    )

    assert db.commits == 1
    assert len(db.added) == 1
    entry = db.added[0]
    assert isinstance(entry, AuditLog)
    assert entry.user_id == user_id
    assert entry.entity_id == entity_id
    assert entry.ip_address == "203.0.113.5"
    assert entry.user_agent == "pytest-agent"
    assert entry.details == {"patient_name": "Patient One"}


async def test_log_action_defaults_details_and_uses_client_ip():
    db = FakeSession()
    user_id = uuid.uuid4()

    await log_action(db=db, user_id=str(user_id), action="LOGOUT", request=make_request(ip="127.0.0.1"))

    entry = db.added[0]
    assert entry.details == {}
    assert entry.entity_type is None
    assert entry.entity_id is None
    assert entry.ip_address == "127.0.0.1"
