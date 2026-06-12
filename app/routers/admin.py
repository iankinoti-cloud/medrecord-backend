import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_roles
from app.models.audit_log import AuditLog
from app.models.patient import Patient
from app.models.user import User
from app.schemas.audit_log import AuditEntryOut
from app.schemas.patient import PatientOut, PatientRegisterRequest
from app.schemas.user import CreateUserRequest, UpdateUserRequest, UserOut
from app.services.audit_service import log_action
from app.services.auth_service import hash_password

router = APIRouter()

AdminOnly = Depends(require_roles("Admin"))


# ── Staff management ──────────────────────────────────────────

@router.get("/users", response_model=list[UserOut])
async def list_users(
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user= AdminOnly,
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body:         CreateUserRequest,
    request:      Request,
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user= AdminOnly,
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email         = body.email,
        full_name     = body.full_name,
        role          = body.role,
        password_hash = hash_password(body.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    await log_action(
        db, str(current_user.id), "CREATE_USER", request,
        entity_type="User", entity_id=str(new_user.id),
        details={"email": new_user.email, "role": new_user.role},
    )
    return new_user


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id:      str,
    body:         UpdateUserRequest,
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user= AdminOnly,
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = body.role

    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(
    user_id:      str,
    request:      Request,
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user= AdminOnly,
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    user.is_active = False
    await db.commit()
    await db.refresh(user)

    await log_action(
        db, str(current_user.id), "DEACTIVATE_USER", request,
        entity_type="User", entity_id=str(user.id),
        details={"email": user.email},
    )
    return user


# ── Patient registration ──────────────────────────────────────

async def _next_patient_id(db: AsyncSession) -> str:
    result = await db.execute(select(Patient.patient_id))
    existing = result.scalars().all()
    max_num = 0
    for pid in existing:
        m = re.match(r"^P-(\d+)$", pid)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"P-{max_num + 1:05d}"


@router.post("/patients", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
async def register_patient(
    body:         PatientRegisterRequest,
    request:      Request,
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user= AdminOnly,
):
    patient_id = await _next_patient_id(db)

    patient = Patient(
        patient_id        = patient_id,
        full_name         = body.full_name,
        date_of_birth     = body.date_of_birth,
        gender            = body.gender,
        blood_type        = body.blood_type,
        contact_phone     = body.contact_phone,
        contact_email     = body.contact_email,
        address           = body.address,
        emergency_contact = body.emergency_contact,
        registered_by     = current_user.id,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)

    await log_action(
        db, str(current_user.id), "REGISTER_PATIENT", request,
        entity_type="Patient", entity_id=str(patient.id),
        details={"patient_id": patient_id, "full_name": body.full_name},
    )
    return PatientOut.model_validate(patient)


# ── Audit log ─────────────────────────────────────────────────

@router.get("/audit-log", response_model=list[AuditEntryOut])
async def get_audit_log(
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user= AdminOnly,
    date_from:    date | None = None,
    date_to:      date | None = None,
):
    query = select(AuditLog, User.full_name).join(User, AuditLog.user_id == User.id)

    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to:
        from datetime import timedelta
        query = query.where(AuditLog.created_at < date_to + timedelta(days=1))

    query = query.order_by(desc(AuditLog.created_at)).limit(500)
    result = await db.execute(query)
    rows = result.all()

    entries = []
    for log, user_name in rows:
        entry = AuditEntryOut.model_validate(log)
        entry.user_name = user_name
        entries.append(entry)
    return entries
