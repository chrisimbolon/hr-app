
# app/modules/auth/infrastructure/models.py
import uuid
from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel


class UserModel(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    is_active: bool = Field(default=True)
    token_version: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CredentialModel(SQLModel, table=True):
    user_id: uuid.UUID = Field(
        foreign_key="usermodel.id",
        primary_key=True
    )
    password_hash: str

class UserTenantModel(SQLModel, table=True):
    user_id: uuid.UUID = Field(
        foreign_key="usermodel.id",
        primary_key=True
    )
    tenant_id: uuid.UUID = Field(
        primary_key=True,
        index=True
    )
