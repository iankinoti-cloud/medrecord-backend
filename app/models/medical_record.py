import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from app.types import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id:   Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id:    Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"),    nullable=False)
    diagnosis:    Mapped[str]             = mapped_column(Text,        nullable=False)
    prescription: Mapped[str | None]      = mapped_column(Text,        nullable=True)
    notes:        Mapped[str | None]      = mapped_column(Text,        nullable=True)
    record_type:  Mapped[str]             = mapped_column(String(50),  default="General", nullable=False)
    created_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient", back_populates="medical_records")
    doctor:  Mapped["User"]    = relationship("User", foreign_keys=[doctor_id])


from app.models.patient import Patient  # noqa: E402
from app.models.user import User        # noqa: E402
