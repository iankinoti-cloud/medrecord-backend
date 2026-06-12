import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditEntryOut(BaseModel):
    id:          uuid.UUID
    user_id:     uuid.UUID
    user_name:   str | None = None
    action:      str
    entity_type: str | None
    entity_id:   uuid.UUID | None
    details:     dict
    ip_address:  str | None
    created_at:  datetime

    model_config = {"from_attributes": True}
