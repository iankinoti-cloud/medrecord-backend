import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.medical_record import MedicalRecord
from app.routers import patients
from app.schemas.patient import DiagnosisRequest

from conftest import FakeResult, FakeSession, make_medical_record, make_patient, make_request, make_user


pytestmark = pytest.mark.asyncio


async def test_list_patients_returns_paginated_patients_without_search():
    patient = make_patient()
    db = FakeSession([FakeResult(scalars=[patient]), FakeResult(scalars=[patient])])

    result = await patients.list_patients(db=db, current_user=make_user(role="Doctor"), search="", page=1, limit=20)

    assert result["patients"][0].patient_id == "P-00001"
    assert result["total"] == 1
    assert result["page"] == 1
    assert result["limit"] == 20
    assert result["pages"] == 1
    assert len(db.statements) == 2


async def test_list_patients_applies_search_and_calculates_pages():
    db = FakeSession([FakeResult(scalars=[make_patient(), make_patient(patient_id="P-00002")]), FakeResult(scalars=[])])

    result = await patients.list_patients(
        db=db,
        current_user=make_user(role="Admin"),
        search=" P-000 ",
        page=2,
        limit=1,
    )

    assert result["total"] == 2
    assert result["page"] == 2
    assert result["pages"] == 2
    statement = str(db.statements[0])
    assert "lower(patients.full_name) LIKE lower(:full_name_1)" in statement
    assert "lower(patients.patient_id) LIKE lower(:patient_id_1)" in statement


async def test_get_patient_rejects_invalid_uuid():
    with pytest.raises(HTTPException) as error:
        await patients.get_patient(
            patient_id="not-a-uuid",
            request=make_request(),
            db=FakeSession(),
            current_user=make_user(role="Doctor"),
        )

    assert error.value.status_code == 422
    assert error.value.detail == "Invalid patient ID"


async def test_get_patient_returns_404_when_missing():
    db = FakeSession([FakeResult(scalar=None)])

    with pytest.raises(HTTPException) as error:
        await patients.get_patient(
            patient_id=str(uuid.uuid4()),
            request=make_request(),
            db=db,
            current_user=make_user(role="Doctor"),
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Patient not found"


async def test_get_patient_logs_view_and_returns_detail():
    patient = make_patient(medical_records=[make_medical_record()], lab_results=[])
    db = FakeSession([FakeResult(scalar=patient)])
    current_user = make_user(role="Doctor")

    with patch.object(patients, "log_action", new=AsyncMock()) as log_action:
        result = await patients.get_patient(
            patient_id=str(patient.id),
            request=make_request(),
            db=db,
            current_user=current_user,
        )

    assert result.id == patient.id
    assert result.medical_records[0].diagnosis == "Flu"
    log_action.assert_awaited_once()
    assert log_action.await_args.kwargs["action"] == "VIEW_PATIENT"
    assert log_action.await_args.kwargs["details"] == {"patient_name": patient.full_name}


async def test_add_diagnosis_rejects_invalid_uuid():
    with pytest.raises(HTTPException) as error:
        await patients.add_diagnosis(
            patient_id="bad-id",
            body=DiagnosisRequest(diagnosis="Flu"),
            request=make_request(),
            db=FakeSession(),
            current_user=make_user(role="Doctor"),
        )

    assert error.value.status_code == 422


async def test_add_diagnosis_returns_404_when_patient_missing():
    db = FakeSession([FakeResult(scalar=None)])

    with pytest.raises(HTTPException) as error:
        await patients.add_diagnosis(
            patient_id=str(uuid.uuid4()),
            body=DiagnosisRequest(diagnosis="Flu"),
            request=make_request(),
            db=db,
            current_user=make_user(role="Doctor"),
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Patient not found"


async def test_add_diagnosis_creates_record_and_logs_action():
    patient = make_patient()
    doctor = make_user(role="Doctor")
    db = FakeSession([FakeResult(scalar=patient)])
    body = DiagnosisRequest(diagnosis="Migraine", prescription="Ibuprofen", notes="Hydrate", record_type="Follow-up")

    with patch.object(patients, "log_action", new=AsyncMock()) as log_action:
        result = await patients.add_diagnosis(
            patient_id=str(patient.id),
            body=body,
            request=make_request(),
            db=db,
            current_user=doctor,
        )

    record = db.added[0]
    assert isinstance(record, MedicalRecord)
    assert record.patient_id == patient.id
    assert record.doctor_id == doctor.id
    assert record.diagnosis == "Migraine"
    assert result.record_type == "Follow-up"
    assert db.commits == 1
    assert db.refreshed == [record]
    log_action.assert_awaited_once()
    assert log_action.await_args.kwargs["action"] == "ADD_DIAGNOSIS"
    assert log_action.await_args.kwargs["details"] == {"diagnosis": "Migraine", "patient_name": patient.full_name}
