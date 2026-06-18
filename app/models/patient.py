import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from app.types import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id:                Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id:        Mapped[str]        = mapped_column(String(20),  unique=True, nullable=False, index=True)
    full_name:         Mapped[str]        = mapped_column(String(255), nullable=False, index=True)
    date_of_birth:     Mapped[date]       = mapped_column(Date, nullable=False)
    gender:            Mapped[str | None] = mapped_column(String(50),  nullable=True)
    blood_type:        Mapped[str | None] = mapped_column(String(10),  nullable=True)
    contact_phone:     Mapped[str | None] = mapped_column(String(50),  nullable=True)
    contact_email:     Mapped[str | None] = mapped_column(String(255), nullable=True)
    address:           Mapped[str | None] = mapped_column(Text,        nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status:            Mapped[str]        = mapped_column(String(50),  default="Active", nullable=False, index=True)
    registered_by:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at:        Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:        Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    medical_records: Mapped[list["MedicalRecord"]] = relationship("MedicalRecord", back_populates="patient", lazy="selectin")
    lab_results:     Mapped[list["LabResult"]]     = relationship("LabResult",     back_populates="patient", lazy="selectin")


from app.models.medical_record import MedicalRecord  # noqa: E402
from app.models.lab_result import LabResult          # noqa: E402
