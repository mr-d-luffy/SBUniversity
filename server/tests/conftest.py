import asyncio
import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings
from app.core.redis import InMemoryRedisFallback
from app.db.base import Base
from app.db.models import Department, StudentProfile, TeacherProfile, User, UserRole, UserStatus
from app.db.session import get_db
from app.main import app

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Enable auth bypass for test dev tokens
settings.ALLOW_DEV_AUTH_BYPASS = True
settings.RATE_LIMIT_ENABLED = False
settings.CLERK_SECRET_KEY = None


@pytest.fixture(autouse=True)
def isolate_redis(monkeypatch):
    monkeypatch.setattr("app.core.redis.redis_client", InMemoryRedisFallback())


@pytest_asyncio.fixture(scope="session", autouse=True)
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    # Setup tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        # Seed test users — let SQLAlchemy auto-generate UUIDs
        admin = User(
            clerk_user_id="u_admin",
            email="admin@sbuniversity.edu",
            full_name="Admin User",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )

        teacher = User(
            clerk_user_id="u_teacher",
            email="teacher@sbuniversity.edu",
            full_name="Teacher User",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        teacher.teacher_profile = TeacherProfile(employee_code="T-TEST-01")

        student1 = User(
            clerk_user_id="u_student1",
            email="student1@sbuniversity.edu",
            full_name="Student One",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        student1.student_profile = StudentProfile(student_code="SBU-2026-0001", qr_token="qr-token-s1")

        student2 = User(
            clerk_user_id="u_student2",
            email="student2@sbuniversity.edu",
            full_name="Student Two",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        student2.student_profile = StudentProfile(student_code="SBU-2026-0002", qr_token="qr-token-s2")

        session.add_all([admin, teacher, student1, student2])
        await session.commit()

        # Expose seeded objects on the session for tests to reference
        session.test_admin = admin
        session.test_teacher = teacher
        session.test_student1 = student1
        session.test_student2 = student2

        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        yield ac
    app.dependency_overrides.clear()
