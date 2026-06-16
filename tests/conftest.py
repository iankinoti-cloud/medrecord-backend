import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.audit_log import AuditLog
from app.models.lab_result import LabResult
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import User


NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


class FakeScalarResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeResult:
    def __init__(self, *, scalar=None, scalars=None, rows=None):
        self.scalar = scalar
        self.scalars_values = [] if scalars is None else scalars
        self.rows = [] if rows is None else rows

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return FakeScalarResult(self.scalars_values)

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.statements = []
        self.added = []
        self.commits = 0
        self.refreshed = []

    async def execute(self, statement):
        self.statements.append(statement)
        if not self.results:
            raise AssertionError("No fake result queued for execute()")
        return self.results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = NOW
        if isinstance(obj, Patient) and getattr(obj, "status", None) is None:
            obj.status = "Active"
        if isinstance(obj, LabResult) and getattr(obj, "status", None) is None:
            obj.status = "Pending"
        if isinstance(obj, MedicalRecord) and getattr(obj, "record_type", None) is None:
            obj.record_type = "General"


class FakeUploadFile:
    def __init__(self, contents=b"%PDF-1.7", filename="report.pdf", content_type="application/pdf"):
        self.contents = contents
        self.filename = filename
        self.content_type = content_type
        self.reads = 0

    async def read(self):
        self.reads += 1
        return self.contents


def make_request(ip="127.0.0.1", forwarded_for="", user_agent="pytest"):
    headers = {"User-Agent": user_agent}
    if forwarded_for:
        headers["X-Forwarded-For"] = forwarded_for
    return SimpleNamespace(headers=headers, client=SimpleNamespace(host=ip))


def make_user(**overrides):
    values = {
        "id": uuid.uuid4(),
        "email": "admin@example.com",
        "full_name": "Admin User",
        "role": "Admin",
        "password_hash": "hashed",
        "avatar_url": None,
        "is_active": True,
        "created_at": NOW,
    }
    values.update(overrides)
    return User(**values)


def make_patient(**overrides):
    values = {
        "id": uuid.uuid4(),
        "patient_id": "P-00001",
        "full_name": "Patient One",
        "date_of_birth": date(1990, 5, 10),
        "gender": "Female",
        "blood_type": "O+",
        "contact_phone": "555-0100",
        "contact_email": "patient@example.com",
        "address": "1 Clinic Road",
        "emergency_contact": "Relative",
        "status": "Active",
        "registered_by": uuid.uuid4(),
        "created_at": NOW,
        "medical_records": [],
        "lab_results": [],
    }
    values.update(overrides)
    return Patient(**values)


def make_medical_record(**overrides):
    values = {
        "id": uuid.uuid4(),
        "patient_id": uuid.uuid4(),
        "doctor_id": uuid.uuid4(),
        "diagnosis": "Flu",
        "prescription": "Rest",
        "notes": "Follow up",
        "record_type": "General",
        "created_at": NOW,
    }
    values.update(overrides)
    return MedicalRecord(**values)


def make_lab_result(**overrides):
    values = {
        "id": uuid.uuid4(),
        "patient_id": uuid.uuid4(),
        "uploader_id": uuid.uuid4(),
        "test_type": "CBC",
        "report_id": "LAB-20260102-ABC12345",
        "file_url": "/uploads/LAB-20260102-ABC12345.pdf",
        "status": "Pending",
        "created_at": NOW,
    }
    values.update(overrides)
    return LabResult(**values)


def make_audit_log(**overrides):
    values = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "action": "CREATE_USER",
        "entity_type": "User",
        "entity_id": uuid.uuid4(),
        "details": {"email": "doctor@example.com"},
        "ip_address": "127.0.0.1",
        "user_agent": "pytest",
        "created_at": NOW,
    }
    values.update(overrides)
    return AuditLog(**values)


@pytest.fixture
def fake_db():
    return FakeSession()
