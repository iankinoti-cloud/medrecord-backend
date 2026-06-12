from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         "UserOut"


from app.schemas.user import UserOut  # noqa: E402
TokenResponse.model_rebuild()
