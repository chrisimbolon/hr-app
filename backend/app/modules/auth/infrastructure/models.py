"""
auth/infrastructure/models.py
──────────────────────────────
Auth module has NO dedicated models.

The Employee, DeviceRegistration models in employee/infrastructure/models.py
ARE the auth data source. Auth is a behaviour (login/logout/token), not an
entity — so it doesn't own its own tables.

This file exists to keep the package structure consistent, and to document
this decision explicitly so no one creates a duplicate UserModel here.

Old SQLModel tables (usermodel, credentialmodel, usertenantmodel) that were
created by a previous version must be dropped manually:

    psql -U hr_user -d hr_db -c "DROP TABLE IF EXISTS usertenantmodel, credentialmodel, usermodel CASCADE;"
"""

# But initially, let's introduce this below
"""
auth/infrastructure/models.py

Production Auth Version (Stateful)

Auth introduces persistence for:
- Refresh tokens
- Sessions
- Token revocation

Core identity still comes from Employee model.
"""

from datetime import datetime

from app.database import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column


class RefreshTokenModel(Base):
    __tablename__ = "auth_refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        index=True
    )

    token_hash: Mapped[str] = mapped_column(String(255), unique=True)

    expires_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    revoked: Mapped[bool] = mapped_column(default=False)


class SessionModel(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        index=True
    )

    device_id: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(50))
    user_agent: Mapped[str] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    is_active: Mapped[bool] = mapped_column(default=True)