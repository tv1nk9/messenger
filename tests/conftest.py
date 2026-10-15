import os
import uuid
import pytest_asyncio

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

import app.db.models
from app.db.models import Base, UserModel
from app.core.security import get_password_hash, issue_tokens
from app.db.session import get_session
from app.main import app


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """ Создаем отдельный движок бд для тестов """
    test_db_url = os.getenv("TEST_DATABASE_URL")

    test_engine = create_async_engine(test_db_url)

    async with test_engine.begin() as conn: # type: ignore
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield test_engine
    finally:
        async with test_engine.begin() as conn: # type: ignore
            await conn.run_sync(Base.metadata.drop_all)

            await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_connection(test_engine):
    """ Открываем транзакцию с новым движком """
    async with test_engine.connect() as conn:
        transaction = await conn.begin()

        try:
            yield conn
        finally:
            if transaction.is_active:
                await transaction.rollback()

@pytest_asyncio.fixture(scope="function")
async def db_session(db_connection):
    """ Раздаем сессии с тестовой бд """
    async with AsyncSession(
        bind=db_connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    ) as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    try:
        async with LifespanManager(app) as manager:
            transport = ASGITransport(app=manager.app)

            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as test_client:
                yield test_client

            app.dependency_overrides.clear()
    finally:
        app.dependency_overrides.pop(get_session, None)



@pytest_asyncio.fixture(scope="function")
async def test_user(db_session):
    """ Создает тестового пользователя в тестовой БД и возвращает его объект """
    async with db_session as session:
        user = UserModel(
            name="Test",
            surname="User",
            patronymic="TestUser",
            email="test@mail.com",
            password_hash= await get_password_hash("test")
        )
        session.add(user)

        await session.commit()
        await session.refresh(user)

        assert user.id is not None

        yield user

@pytest_asyncio.fixture(scope="function")
async def auth_client(client: AsyncClient, test_user: UserModel):
    ver = 1
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())

    tokens = issue_tokens(
        user_id=str(test_user.id), # type: ignore
        role=test_user.role,
        ver=ver,
        access_jti=access_jti,
        refresh_jti=refresh_jti
    )

    access_token = tokens["access_token"]

    client.headers.update({"Authorization": f"Bearer {access_token}"})

    yield client