from fastapi import APIRouter
from app.api.v1.admin.users import router as users_router
from app.api.v1.admin.progress import router as progress_router
from app.api.v1.admin.analytics import router as analytics_router
from app.api.v1.admin.notices import router as notices_router
from app.api.v1.admin.audit_logs import router as audit_logs_router
from app.api.v1.admin.courses import router as courses_router
from app.api.v1.admin.security import router as security_router

admin_router = APIRouter(prefix="/admin")
admin_router.include_router(users_router)
admin_router.include_router(progress_router)
admin_router.include_router(analytics_router)
admin_router.include_router(notices_router)
admin_router.include_router(audit_logs_router)
admin_router.include_router(courses_router)
admin_router.include_router(security_router)

__all__ = ["admin_router"]
