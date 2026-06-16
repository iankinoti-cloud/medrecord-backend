import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.patient import Patient
from app.routers import admin
from app.schemas.patient import PatientRegisterRequest
from app.schemas.user import CreateUserRequest, UpdateUserRequest

from conftest import FakeResult, FakeSession, make_audit_log, make_request, make_user


pytestmark = pytest.mark.asyncio


async def test_list_users_returns_users_in_query_result():
    users = [make_user(email="new@example.com"), make_user(email="old@example.com")]
    db = FakeSession([FakeResult(scalars=users)])

    result = await admin.list_users(db=db, current_user=make_user())

    assert result == users
    assert len(db.statements) == 1
    assert "ORDER BY users.created_at DESC" in str(db.statements[0])


async def test_create_user_rejects_duplicate_email():
    db = FakeSession([FakeResult(scalar=make_user(email="taken@example.com"))])
    body = CreateUserRequest(
        email="taken@example.com",
        full_name="Taken User",
        role="Doctor",
        password="secret",
    )

    with pytest.raises(HTTPException) as error:
        await admin.create_user(body=body, request=make_request(), db=db, current_user=make_user())

    assert error.value.status_code == 400
    assert error.value.detail == "Email already registered"
    assert db.added == []
    assert db.commits == 0


async def test_create_user_hashes_password_persists_user_and_logs_action():
    db = FakeSession([FakeResult(scalar=None)])
    current_user = make_user()
    body = CreateUserRequest(
        email="doctor@example.com",
        full_name="Doctor User",
        role="Doctor",
        password="secret",
    )

    with (
        patch.object(admin, "hash_password", return_value="hashed-secret") as hash_password,
        patch.object(admin, "log_action", new=AsyncMock()) as log_action,
    ):
        result = await admin.create_user(body=body, request=make_request(), db=db, current_user=current_user)

    assert result.email == "doctor@example.com"
    assert result.full_name == "Doctor User"
    assert result.role == "Doctor"
    assert result.password_hash == "hashed-secret"
    assert db.added == [result]
    assert db.commits == 1
    assert db.refreshed == [result]
    hash_password.assert_called_once_with("secret")
    log_action.assert_awaited_once()
    assert log_action.await_args.kwargs["entity_type"] == "User"
    assert log_action.await_args.kwargs["details"] == {"email": result.email, "role": result.role}


async def test_update_user_returns_404_when_missing():
    db = FakeSession([FakeResult(scalar=None)])

    with pytest.raises(HTTPException) as error:
        await admin.update_user(
            user_id=str(uuid.uuid4()),
            body=UpdateUserRequest(full_name="Nobody"),
            db=db,
            current_user=make_user(),
        )

    assert error.value.status_code == 404
    assert error.value.detail == "User not found"


async def test_update_user_changes_supplied_fields_only():
    user = make_user(full_name="Old Name", role="Doctor")
    db = FakeSession([FakeResult(scalar=user)])

    result = await admin.update_user(
        user_id=str(user.id),
        body=UpdateUserRequest(full_name="New Name"),
        db=db,
        current_user=make_user(),
    )

    assert result is user
    assert user.full_name == "New Name"
    assert user.role == "Doctor"
    assert db.commits == 1
    assert db.refreshed == [user]


async def test_deactivate_user_returns_404_when_missing():
    db = FakeSession([FakeResult(scalar=None)])

    with pytest.raises(HTTPException) as error:
        await admin.deactivate_user(
            user_id=str(uuid.uuid4()),
            request=make_request(),
            db=db,
            current_user=make_user(),
        )

    assert error.value.status_code == 404
    assert error.value.detail == "User not found"


async def test_deactivate_user_rejects_current_user():
    current_user = make_user()
    db = FakeSession([FakeResult(scalar=current_user)])

    with pytest.raises(HTTPException) as error:
        await admin.deactivate_user(
            user_id=str(current_user.id),
            request=make_request(),
            db=db,
            current_user=current_user,
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Cannot deactivate your own account"
    assert current_user.is_active is True
    assert db.commits == 0


async def test_deactivate_user_disables_account_and_logs_action():
    current_user = make_user()
    target_user = make_user(email="doctor@example.com", role="Doctor")
    db = FakeSession([FakeResult(scalar=target_user)])

    with patch.object(admin, "log_action", new=AsyncMock()) as log_action:
        result = await admin.deactivate_user(
            user_id=str(target_user.id),
            request=make_request(),
            db=db,
            current_user=current_user,
        )

    assert result is target_user
    assert target_user.is_active is False
    assert db.commits == 1
    assert db.refreshed == [target_user]
    log_action.assert_awaited_once()
    assert log_action.await_args.kwargs["entity_type"] == "User"
    assert log_action.await_args.kwargs["details"] == {"email": "doctor@example.com"}


async def test_next_patient_id_increments_largest_well_formed_id():
    db = FakeSession([FakeResult(scalars=["P-00002", "bad-id", "P-00010", "P-abc"])])

    result = await admin._next_patient_id(db)

    assert result == "P-00011"


async def test_next_patient_id_starts_sequence_when_no_existing_ids():
    db = FakeSession([FakeResult(scalars=[])])

    result = await admin._next_patient_id(db)

    assert result == "P-00001"


async def test_register_patient_creates_patient_with_next_id_and_logs_action():
    db = FakeSession([FakeResult(scalars=["P-00001"])])
    current_user = make_user()
    body = PatientRegisterRequest(
        full_name="Patient One",
        date_of_birth=date(1990, 5, 10),
        gender="Female",
        blood_type="O+",
        contact_phone="555-0100",
        contact_email="patient@example.com",
        address="1 Clinic Road",
        emergency_contact="Relative",
    )

    with patch.object(admin, "log_action", new=AsyncMock()) as log_action:
        result = await admin.register_patient(body=body, request=make_request(), db=db, current_user=current_user)

    patient = db.added[0]
    assert isinstance(patient, Patient)
    assert patient.patient_id == "P-00002"
    assert patient.full_name == "Patient One"
    assert patient.registered_by == current_user.id
    assert result.patient_id == "P-00002"
    assert result.status == "Active"
    assert db.commits == 1
    assert db.refreshed == [patient]
    log_action.assert_awaited_once()
    assert log_action.await_args.kwargs["entity_type"] == "Patient"
    assert log_action.await_args.kwargs["details"] == {"patient_id": "P-00002", "full_name": "Patient One"}


async def test_get_audit_log_returns_entries_with_user_names_and_date_filters():
    log = make_audit_log()
    db = FakeSession([FakeResult(rows=[(log, "Admin User")])])

    result = await admin.get_audit_log(
        db=db,
        current_user=make_user(),
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )

    assert len(result) == 1
    assert result[0].id == log.id
    assert result[0].user_name == "Admin User"
    assert result[0].details == {"email": "doctor@example.com"}

    statement = str(db.statements[0])
    assert "audit_log.created_at >= :created_at_1" in statement
    assert "audit_log.created_at < :created_at_2" in statement
    assert "ORDER BY audit_log.created_at DESC" in statement
    assert "LIMIT :param_1" in statement
