import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr


class PatientRegisterRequest(BaseModel):
    full_name:         str
    date_of_birth:     date
    gender:            str | None = None
    blood_type:        str | None = None
    contact_phone:     str | None = None
    contact_email:     str | None = None
    address:           str | None = None
    emergency_contact: str | None = None


class PatientOut(BaseModel):
    id:                uuid.UUID
    patient_id:        str
    full_name:         str
    date_of_birth:     date
    gender:            str | None
    blood_type:        str | None
    contact_phone:     str | None
    contact_email:     str | None
    address:           str | None
    emergency_contact: str | None
    status:            str
    created_at:        datetime

    model_config = {"from_attributes": True}


class DiagnosisRequest(BaseModel):
    diagnosis:    str
    prescription: str | None = None
    notes:        str | None = None
    record_type:  str = "General"


class MedicalRecordOut(BaseModel):
    id:           uuid.UUID
    patient_id:   uuid.UUID
    doctor_id:    uuid.UUID
    diagnosis:    str
    prescription: str | None
    notes:        str | None
    record_type:  str
    created_at:   datetime

    model_config = {"from_attributes": True}


class PatientDetailOut(PatientOut):
    medical_records: list[MedicalRecordOut] = []
    lab_results:     list["LabResultOut"]   = []


from app.schemas.lab_result import LabResultOut  # noqa: E402
PatientDetailOut.model_rebuild()
