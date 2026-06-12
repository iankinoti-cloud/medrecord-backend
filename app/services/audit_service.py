"""
Shared audit logging service.

Person 2 and Person 3: call log_action() at the end of every route handler.

Example:
    await log_action(
        db=db,
        user_id=str(current_user.id),
        action="VIEW_PATIENT",
        entity_type="Patient",
        entity_id=str(patient.id),
        details={"patient_name": patient.full_name},
        request=request,
    )

Valid action values (mirror src/utils/constants.js):
    LOGIN, LOGOUT, VIEW_PATIENT, ADD_DIAGNOSIS,
    UPLOAD_LAB, CREATE_USER, DEACTIVATE_USER, REGISTER_PATIENT
"""

import uuid

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_action(
    db:          AsyncSession,
    user_id:     str,
    action:      str,
    request:     Request,
    entity_type: str | None  = None,
    entity_id:   str | None  = None,
    details:     dict        = {},
) -> None:
    ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.client.host
        if request.client else None
    )
    entry = AuditLog(
        user_id     = uuid.UUID(user_id),
        action      = action,
        entity_type = entity_type,
        entity_id   = uuid.UUID(entity_id) if entity_id else None,
        details     = details,
        ip_address  = ip,
        user_agent  = request.headers.get("User-Agent"),
    )
    db.add(entry)
    await db.commit()
