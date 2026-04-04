"""audit/presentation/api/v1/routes.py"""
from uuid import UUID

from app.core.dependencies import get_db, require_roles
from app.modules.audit.infrastructure.models import AuditLogModel
from app.shared.schemas.base import ApiResponse
from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/", response_model=ApiResponse[list[dict]])
async def get_audit_logs(
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    page: int = 1,
    page_size: int = 50,
    hr=Depends(require_roles("hr_admin", "company_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Audit log for HR admin. Filter by entity type and ID."""
    conditions = []
    if entity_type:
        conditions.append(AuditLogModel.entity_type == entity_type)
    if entity_id:
        conditions.append(AuditLogModel.entity_id == entity_id)

    offset = (page - 1) * page_size
    rows = await db.execute(
        select(AuditLogModel)
        .where(and_(*conditions) if conditions else True)
        .order_by(AuditLogModel.created_at.desc())
        .limit(page_size).offset(offset)
    )
    logs = rows.scalars().all()
    return ApiResponse(data=[
        {
            "id": str(log.id),
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id) if log.entity_id else None,
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ])
