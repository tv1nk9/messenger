import os
import uuid
import pytest_asyncio
import pytest

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

import app.db.models
from app.db.models import Base, UserModel
from app.core.security import get_password_hash, issue_tokens
from app.db.session import get_session
from app.main import app


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Создаем отдельный движок бд для тестов"""
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        raise RuntimeError("TEST_DATABASE_URL is not set")

    test_engine = create_async_engine(test_db_url)
    try:
        async with test_engine.begin() as conn:  # type: ignore
            await conn.run_sync(Base.metadata.create_all)
        yield test_engine
    finally:
        async with test_engine.begin() as conn:  # type: ignore
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    """Создает сессию в транзакции, которая откатывается после теста"""
    async with test_engine.connect() as conn:
        transaction = await conn.begin()

        try:
            async with AsyncSession(
                bind=conn,
                join_transaction_mode="create_savepoint",
                expire_on_commit=False,
            ) as session:
                yield session

        finally:
            if transaction.is_active:
                await transaction.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """Неавторизованный client"""

    async def override_get_session():
        yield db_session

    prev_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_session] = override_get_session

    try:
        async with LifespanManager(app) as manager:
            transport = ASGITransport(app=manager.app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as test_client:
                yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prev_overrides)


@pytest_asyncio.fixture(scope="function")
async def user_factory(db_session):
    """Фабрика для создания и сохранения в бд уникальных пользователей"""

    async def _create_user(
        name: str = "Test",
        surname: str = "User",
        patronymic: str = "TestUser",
        email: str | None = None,
        password: str = "test",
    ) -> UserModel:
        unique_email = email or f"test_{uuid.uuid4()}@mail.com"

        user = UserModel(
            name=name,
            surname=surname,
            patronymic=patronymic,
            email=unique_email,
            password_hash=await get_password_hash(password),
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        return user

    return _create_user


@pytest.fixture
def auth_headers_factory():
    """Фабрика заголовков авторизации"""

    def _get_headers(test_user: UserModel):
        tokens = issue_tokens(
            user_id=str(test_user.id),  # type: ignore
            role=test_user.role,
            ver=1,
            access_jti=str(uuid.uuid4()),
            refresh_jti=str(uuid.uuid4()),
        )
        return {"Authorization": f"Bearer {tokens['access_token']}"}

    return _get_headers
