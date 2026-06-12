import uuid
from datetime import datetime

from pydantic import BaseModel


class LabResultOut(BaseModel):
    id:            uuid.UUID
    patient_id:    uuid.UUID
    uploader_id:   uuid.UUID
    uploader_name: str | None = None
    test_type:     str
    report_id:     str
    file_url:      str
    status:        str
    created_at:    datetime

    model_config = {"from_attributes": True}
