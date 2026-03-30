from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str