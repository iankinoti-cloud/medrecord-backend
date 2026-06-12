import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db, require_roles
from app.models.lab_result import LabResult
from app.models.patient import Patient
from app.models.user import User
from app.schemas.lab_result import LabResultOut
from app.services.audit_service import log_action
import aiofiles
import os

router = APIRouter()

LabTechOnly = Depends(require_roles("Lab Technician"))


def _generate_report_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    short = str(uuid.uuid4()).split("-")[0].upper()
    return f"LAB-{stamp}-{short}"


def _safe_filename(original: str, report_id: str) -> str:
    ext = os.path.splitext(original)[1].lower() or ".pdf"
    return f"{report_id}{ext}"


@router.post("/upload", response_model=LabResultOut, status_code=status.HTTP_201_CREATED)
async def upload_lab_result(
    request:     Request,
    db:          Annotated[AsyncSession, Depends(get_db)],
    current_user= LabTechOnly,
    patient_id:  str        = Form(...),
    test_type:   str        = Form(...),
    file:        UploadFile = File(...),
):
    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are accepted",
        )

    # Validate file size
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_BYTES // (1024*1024)} MB",
        )

    # Validate patient exists
    result = await db.execute(select(Patient).where(Patient.id == uuid.UUID(patient_id)))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Save file
    report_id = _generate_report_id()
    filename  = _safe_filename(file.filename or "report.pdf", report_id)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    dest_path = os.path.join(settings.UPLOAD_DIR, filename)

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(contents)

    file_url = f"/uploads/{filename}"

    lab_result = LabResult(
        patient_id  = patient.id,
        uploader_id = current_user.id,
        test_type   = test_type,
        report_id   = report_id,
        file_url    = file_url,
        status      = "Pending",
    )
    db.add(lab_result)
    await db.commit()
    await db.refresh(lab_result)

    await log_action(
        db=db, user_id=str(current_user.id), action="UPLOAD_LAB", request=request,
        entity_type="Patient", entity_id=str(patient.id),
        details={"test_type": test_type, "report_id": report_id, "patient_name": patient.full_name},
    )

    out = LabResultOut.model_validate(lab_result)
    out.uploader_name = current_user.full_name
    return out


@router.get("/{patient_id}", response_model=list[LabResultOut])
async def get_lab_results(
    patient_id:  str,
    db:          Annotated[AsyncSession, Depends(get_db)],
    current_user= LabTechOnly,
):
    try:
        pid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid patient ID")

    result = await db.execute(
        select(LabResult, User.full_name)
        .join(User, LabResult.uploader_id == User.id)
        .where(LabResult.patient_id == pid)
        .order_by(LabResult.created_at.desc())
    )
    rows = result.all()

    entries = []
    for lab, uploader_name in rows:
        entry = LabResultOut.model_validate(lab)
        entry.uploader_name = uploader_name
        entries.append(entry)
    return entries
