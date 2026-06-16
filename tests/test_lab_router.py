import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.lab_result import LabResult
from app.routers import lab

from conftest import FakeResult, FakeSession, FakeUploadFile, make_lab_result, make_patient, make_request, make_user


pytestmark = pytest.mark.asyncio


async def test_generate_report_id_uses_expected_prefix_and_uuid_fragment():
    with patch.object(lab.uuid, "uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
        report_id = lab._generate_report_id()

    assert report_id.startswith("LAB-")
    assert report_id.endswith("-12345678")


async def test_safe_filename_uses_lowercase_original_extension_or_pdf_default():
    assert lab._safe_filename("scan.PDF", "LAB-1") == "LAB-1.pdf"
    assert lab._safe_filename("no-extension", "LAB-2") == "LAB-2.pdf"


async def test_upload_lab_result_rejects_non_pdf():
    with pytest.raises(HTTPException) as error:
        await lab.upload_lab_result(
            request=make_request(),
            db=FakeSession(),
            current_user=make_user(role="Lab Technician"),
            patient_id=str(uuid.uuid4()),
            test_type="CBC",
            file=FakeUploadFile(content_type="image/png"),
        )

    assert error.value.status_code == 422
    assert error.value.detail == "Only PDF files are accepted"


async def test_upload_lab_result_rejects_oversized_file():
    contents = b"x" * (lab.settings.MAX_UPLOAD_BYTES + 1)

    with pytest.raises(HTTPException) as error:
        await lab.upload_lab_result(
            request=make_request(),
            db=FakeSession(),
            current_user=make_user(role="Lab Technician"),
            patient_id=str(uuid.uuid4()),
            test_type="CBC",
            file=FakeUploadFile(contents=contents),
        )

    assert error.value.status_code == 413
    assert "File exceeds maximum size" in error.value.detail


async def test_upload_lab_result_returns_404_when_patient_missing():
    db = FakeSession([FakeResult(scalar=None)])

    with pytest.raises(HTTPException) as error:
        await lab.upload_lab_result(
            request=make_request(),
            db=db,
            current_user=make_user(role="Lab Technician"),
            patient_id=str(uuid.uuid4()),
            test_type="CBC",
            file=FakeUploadFile(),
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Patient not found"


async def test_upload_lab_result_saves_file_creates_record_and_logs_action(tmp_path, monkeypatch):
    patient = make_patient()
    uploader = make_user(role="Lab Technician", full_name="Lab Tech")
    db = FakeSession([FakeResult(scalar=patient)])
    monkeypatch.setattr(lab.settings, "UPLOAD_DIR", str(tmp_path))
    writes = []

    class FakeAsyncFile:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def write(self, contents):
            writes.append(contents)

    with (
        patch.object(lab, "_generate_report_id", return_value="LAB-20260102-ABC12345"),
        patch.object(lab.aiofiles, "open", return_value=FakeAsyncFile()) as aio_open,
        patch.object(lab, "log_action", new=AsyncMock()) as log_action,
    ):
        result = await lab.upload_lab_result(
            request=make_request(),
            db=db,
            current_user=uploader,
            patient_id=str(patient.id),
            test_type="CBC",
            file=FakeUploadFile(contents=b"%PDF-1.7 data", filename="result.PDF"),
        )

    aio_open.assert_called_once_with(str(tmp_path / "LAB-20260102-ABC12345.pdf"), "wb")
    assert writes == [b"%PDF-1.7 data"]
    record = db.added[0]
    assert isinstance(record, LabResult)
    assert record.patient_id == patient.id
    assert record.uploader_id == uploader.id
    assert record.file_url == "/uploads/LAB-20260102-ABC12345.pdf"
    assert result.uploader_name == "Lab Tech"
    assert db.commits == 1
    assert db.refreshed == [record]
    log_action.assert_awaited_once()
    assert log_action.await_args.kwargs["action"] == "UPLOAD_LAB"
    assert log_action.await_args.kwargs["details"]["report_id"] == "LAB-20260102-ABC12345"


async def test_get_lab_results_rejects_invalid_patient_id():
    with pytest.raises(HTTPException) as error:
        await lab.get_lab_results(patient_id="bad-id", db=FakeSession(), current_user=make_user(role="Lab Technician"))

    assert error.value.status_code == 422
    assert error.value.detail == "Invalid patient ID"


async def test_get_lab_results_returns_entries_with_uploader_names():
    lab_result = make_lab_result()
    db = FakeSession([FakeResult(rows=[(lab_result, "Lab Tech")])])

    result = await lab.get_lab_results(
        patient_id=str(lab_result.patient_id),
        db=db,
        current_user=make_user(role="Lab Technician"),
    )

    assert len(result) == 1
    assert result[0].id == lab_result.id
    assert result[0].uploader_name == "Lab Tech"
    assert "ORDER BY lab_results.created_at DESC" in str(db.statements[0])
