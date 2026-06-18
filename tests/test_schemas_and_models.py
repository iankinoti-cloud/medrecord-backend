import uuid
from datetime import date

import pytest
from pydantic import ValidationError
from app.models.audit_log import AuditLog
from app.models.lab_result import LabResult
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import User
from app.schemas.audit_log import AuditEntryOut
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.lab_result import LabResultOut
from app.schemas.patient import DiagnosisRequest, PatientDetailOut, PatientOut, PatientRegisterRequest
from app.schemas.user import CreateUserRequest, UpdateUserRequest, UserOut

from conftest import NOW, make_audit_log, make_lab_result, make_medical_record, make_patient, make_user


def test_user_request_validates_email_and_role():
    body = CreateUserRequest(
        email="doctor@example.com",
        full_name="Doctor User",
        role="Doctor",
        password="secret",
    )

    assert body.email == "doctor@example.com"

    with pytest.raises(ValidationError):
        CreateUserRequest(email="bad-email", full_name="Bad", role="Doctor", password="secret")

    with pytest.raises(ValidationError):
        CreateUserRequest(email="doctor@example.com", full_name="Bad", role="Nurse", password="secret")


def test_update_user_allows_partial_payload_and_validates_role():
    assert UpdateUserRequest().model_dump() == {"full_name": None, "role": None}
    assert UpdateUserRequest(role="Admin").role == "Admin"

    with pytest.raises(ValidationError):
        UpdateUserRequest(role="Owner")


def test_auth_schemas_validate_login_and_token_response():
    user = make_user()
    login = LoginRequest(email=user.email, password="secret")
    token = TokenResponse(access_token="token", user=UserOut.model_validate(user))

    assert login.email == user.email
    assert token.token_type == "bearer"
    assert token.user.id == user.id


def test_patient_schemas_validate_dates_and_default_record_type():
    body = PatientRegisterRequest(full_name="Patient", date_of_birth=date(1990, 1, 1))
    diagnosis = DiagnosisRequest(diagnosis="Flu")

    assert body.date_of_birth == date(1990, 1, 1)
    assert diagnosis.record_type == "General"

    with pytest.raises(ValidationError):
        PatientRegisterRequest(full_name="Patient", date_of_birth="not-a-date")


def test_output_schemas_validate_from_orm_models():
    patient = make_patient(medical_records=[make_medical_record()], lab_results=[make_lab_result()])
    audit_log = make_audit_log()

    assert UserOut.model_validate(make_user()).email == "admin@example.com"
    assert PatientOut.model_validate(patient).patient_id == "P-00001"
    assert PatientDetailOut.model_validate(patient).medical_records[0].diagnosis == "Flu"
    assert LabResultOut.model_validate(patient.lab_results[0]).report_id.startswith("LAB-")
    assert AuditEntryOut.model_validate(audit_log).details == {"email": "doctor@example.com"}


def test_patient_detail_defaults_are_not_shared_between_instances():
    first = PatientDetailOut(
        id=uuid.uuid4(),
        patient_id="P-1",
        full_name="First",
        date_of_birth=date(1990, 1, 1),
        gender=None,
        blood_type=None,
        contact_phone=None,
        contact_email=None,
        address=None,
        emergency_contact=None,
        status="Active",
        created_at=NOW,
    )
    second = PatientDetailOut(
        id=uuid.uuid4(),
        patient_id="P-2",
        full_name="Second",
        date_of_birth=date(1991, 1, 1),
        gender=None,
        blood_type=None,
        contact_phone=None,
        contact_email=None,
        address=None,
        emergency_contact=None,
        status="Active",
        created_at=NOW,
    )

    first.medical_records.append(make_medical_record())

    assert len(first.medical_records) == 1
    assert second.medical_records == []


def test_model_table_names_and_key_columns_are_configured():
    assert User.__tablename__ == "users"
    assert Patient.__tablename__ == "patients"
    assert MedicalRecord.__tablename__ == "medical_records"
    assert LabResult.__tablename__ == "lab_results"
    assert AuditLog.__tablename__ == "audit_log"
    assert User.__table__.c.email.unique is True
    assert Patient.__table__.c.patient_id.unique is True
    assert LabResult.__table__.c.report_id.unique is True


def test_model_relationship_foreign_keys_are_configured():
    assert next(iter(Patient.__table__.c.registered_by.foreign_keys)).column.table.name == "users"
    assert next(iter(MedicalRecord.__table__.c.patient_id.foreign_keys)).column.table.name == "patients"
    assert next(iter(MedicalRecord.__table__.c.doctor_id.foreign_keys)).column.table.name == "users"
    assert next(iter(LabResult.__table__.c.patient_id.foreign_keys)).column.table.name == "patients"
    assert next(iter(LabResult.__table__.c.uploader_id.foreign_keys)).column.table.name == "users"
    assert next(iter(AuditLog.__table__.c.user_id.foreign_keys)).column.table.name == "users"
    assert Patient.medical_records.property.back_populates == "patient"
    assert Patient.lab_results.property.back_populates == "patient"


def test_model_defaults_apply_on_python_object_construction():
    user = User(email="user@example.com", full_name="User", role="Doctor")
    patient = Patient(patient_id="P-1", full_name="Patient", date_of_birth=date(1990, 1, 1))
    record = MedicalRecord(patient_id=uuid.uuid4(), doctor_id=uuid.uuid4(), diagnosis="Flu")
    lab = LabResult(patient_id=uuid.uuid4(), uploader_id=uuid.uuid4(), test_type="CBC", report_id="LAB-1", file_url="/x.pdf")
    audit = AuditLog(user_id=uuid.uuid4(), action="LOGIN")

    assert user.is_active is None
    assert patient.status is None
    assert record.record_type is None
    assert lab.status is None
    assert audit.details is None
