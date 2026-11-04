import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import require_role
from app.db.models.user import UserRole
from app.db.session import get_db
from app.repositories.audit_repository import AuditRepository

router = APIRouter(prefix="/audit-logs", tags=["Admin Audit Logs"], dependencies=[Depends(require_role(UserRole.ADMIN))])


@router.get("")
async def list_audit_logs(
    actor_id: Optional[uuid.UUID] = None,
    action: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    repo = AuditRepository(db)
    logs, total = await repo.list_logs(actor_id=actor_id, action=action, page=page, page_size=page_size)
    return {
        "items": [
            {
                "id": audit_log.id,
                "actor_id": str(audit_log.actor_id) if audit_log.actor_id else None,
                "actor_name": audit_log.actor.full_name if audit_log.actor else None,
                "action": audit_log.action,
                "entity_type": audit_log.entity_type,
                "entity_id": audit_log.entity_id,
                "metadata": audit_log.metadata_,
                "ip_address": audit_log.ip_address,
                "created_at": audit_log.created_at.isoformat(),
            }
            for audit_log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
