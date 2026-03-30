from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel


class UserModel(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    email: str = Field(index=True)
    is_active: bool
    token_version: int
    created_at: datetime


class CredentialModel(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="usermodel.id")
    password_hash: str


class UserTenantModel(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="usermodel.id")
    tenant_id: UUID = Field(index=True)