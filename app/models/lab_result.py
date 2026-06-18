import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LabResult(Base):
    __tablename__ = "lab_results"

    id:          Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id:  Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    uploader_id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    test_type:   Mapped[str]        = mapped_column(String(100), nullable=False)
    report_id:   Mapped[str]        = mapped_column(String(50),  unique=True, nullable=False)
    file_url:    Mapped[str]        = mapped_column(String(500), nullable=False)
    status:      Mapped[str]        = mapped_column(String(50),  default="Pending", nullable=False)
    created_at:  Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient:  Mapped["Patient"] = relationship("Patient", back_populates="lab_results")
    uploader: Mapped["User"]    = relationship("User", foreign_keys=[uploader_id])


from app.models.patient import Patient  # noqa: E402
from app.models.user import User        # noqa: E402
