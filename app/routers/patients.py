import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_roles
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.schemas.patient import DiagnosisRequest, MedicalRecordOut, PatientDetailOut, PatientOut
from app.services.audit_service import log_action

router = APIRouter()

DoctorOrAdmin = Depends(require_roles("Doctor", "Admin"))
DoctorOnly    = Depends(require_roles("Doctor"))


@router.get("", response_model=dict)
async def list_patients(
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user= DoctorOrAdmin,
    search:  str  = Query("", description="Search by name or patient_id"),
    page:    int  = Query(1,  ge=1),
    limit:   int  = Query(20, ge=1, le=100),
):
    query = select(Patient)

    if search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Patient.full_name.ilike(term),
                Patient.patient_id.ilike(term),
            )
        )

    count_result = await db.execute(query)
    total = len(count_result.scalars().all())

    query = query.order_by(Patient.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    patients = result.scalars().all()

    return {
        "patients": [PatientOut.model_validate(p) for p in patients],
        "total":    total,
        "page":     page,
        "limit":    limit,
        "pages":    max(1, -(-total // limit)),  # ceiling division
    }


@router.get("/{patient_id}", response_model=PatientDetailOut)
async def get_patient(
    patient_id:  str,
    request:     Request,
    db:          Annotated[AsyncSession, Depends(get_db)],
    current_user= DoctorOrAdmin,
):
    try:
        pid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid patient ID")

    result = await db.execute(
        select(Patient).where(Patient.id == pid)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    await log_action(
        db=db, user_id=str(current_user.id), action="VIEW_PATIENT", request=request,
        entity_type="Patient", entity_id=str(patient.id),
        details={"patient_name": patient.full_name},
    )
    return PatientDetailOut.model_validate(patient)


@router.post("/{patient_id}/diagnosis", response_model=MedicalRecordOut, status_code=status.HTTP_201_CREATED)
async def add_diagnosis(
    patient_id:  str,
    body:        DiagnosisRequest,
    request:     Request,
    db:          Annotated[AsyncSession, Depends(get_db)],
    current_user= DoctorOnly,
):
    try:
        pid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid patient ID")

    result = await db.execute(
        select(Patient).where(Patient.id == pid)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    record = MedicalRecord(
        patient_id   = patient.id,
        doctor_id    = current_user.id,
        diagnosis    = body.diagnosis,
        prescription = body.prescription,
        notes        = body.notes,
        record_type  = body.record_type,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    await log_action(
        db=db, user_id=str(current_user.id), action="ADD_DIAGNOSIS", request=request,
        entity_type="Patient", entity_id=str(patient.id),
        details={"diagnosis": body.diagnosis, "patient_name": patient.full_name},
    )
    return MedicalRecordOut.model_validate(record)
