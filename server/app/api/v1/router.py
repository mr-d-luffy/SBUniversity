from fastapi import APIRouter
from app.api.v1.admin import admin_router
from app.api.v1.activity import router as activity_router
from app.api.v1.security import router as security_router
from app.api.v1.assistant import router as assistant_router
from app.api.v1.auth_webhooks import router as webhooks_router
from app.api.v1.certificates import router as certificates_router
from app.api.v1.community_chat import router as community_chat_router
from app.api.v1.exams import router as exams_router
from app.api.v1.me import router as me_router
from app.api.v1.notices import router as notices_router
from app.api.v1.planner import router as planner_router
from app.api.v1.public import router as public_router
from app.api.v1.ranking import router as ranking_router
from app.api.v1.results import router as results_router
from app.api.v1.student import router as student_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.teacher import router as teacher_router
from app.api.v1.whiteboard import router as whiteboard_router

api_v1_router = APIRouter()

# Public & Webhooks
api_v1_router.include_router(public_router)
api_v1_router.include_router(webhooks_router)

# User / Self
api_v1_router.include_router(me_router)
api_v1_router.include_router(activity_router)
api_v1_router.include_router(security_router)

# Role Dashboards
api_v1_router.include_router(student_router)
api_v1_router.include_router(teacher_router)

# Core Domains
api_v1_router.include_router(exams_router)
api_v1_router.include_router(results_router)
api_v1_router.include_router(certificates_router)
api_v1_router.include_router(tasks_router)
api_v1_router.include_router(ranking_router)
api_v1_router.include_router(notices_router)
api_v1_router.include_router(community_chat_router)
api_v1_router.include_router(planner_router)
api_v1_router.include_router(whiteboard_router)
api_v1_router.include_router(assistant_router)

# Admin Panel
api_v1_router.include_router(admin_router)
