from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    id: UUID
    email: str
    is_active: bool
    token_version: int
    created_at: datetime


@dataclass
class Credential:
    user_id: UUID
    password_hash: str


@dataclass
class UserTenant:
    user_id: UUID
    tenant_id: UUID