import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

UserRole = Literal["Doctor", "Lab Technician", "Admin"]


class UserOut(BaseModel):
    id:         uuid.UUID
    email:      str
    full_name:  str
    role:       str
    avatar_url: str | None
    is_active:  bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateUserRequest(BaseModel):
    email:     EmailStr
    full_name: str
    role:      UserRole
    password:  str


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    role:      UserRole | None = None
