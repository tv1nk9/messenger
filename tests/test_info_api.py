import pytest

from app.core.configs import settings, api_prefix
from app.db.repositories.chat_repos import ChatRepository
from app.web.schemas import FindUserRequest
from common import create_group_chat, create_private_chat, add_user_to_chat
from tests.conftest import db_session

app_url_prefix = settings.API_V1_STR

info_url_prefix = api_prefix.INFO_ROUTES
find_user_url = f"{app_url_prefix}{info_url_prefix}{api_prefix.FIND_USER}"
user_chats_url = f"{app_url_prefix}{info_url_prefix}{api_prefix.USER_CHATS}"


@pytest.mark.asyncio
async def test_find_user(
    client,
    user_factory,
    auth_headers_factory,
    db_session,
):
    user_1 = await user_factory()
    user_1_headers = auth_headers_factory(user_1)

    num_users_for_search = 10
    for i in range(num_users_for_search):
        await user_factory()

    offset = 0
    limit = 10
    resp = await client.post(
        find_user_url,
        headers=user_1_headers,
        json=FindUserRequest(name="Test User", offset=offset, limit=limit).model_dump(
            mode="json"
        ),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_user_chats(
    client,
    user_factory,
    auth_headers_factory,
):
    user_1 = await user_factory()
    user_1_headers = auth_headers_factory(user_1)
    user_2 = await user_factory()
    user_2_headers = auth_headers_factory(user_2)

    chat_group_1_id = await create_group_chat(client, user_1_headers)
    chat_group_2_id = await create_group_chat(client, user_1_headers)
    chat_private_1_id = await create_private_chat(client, user_2.id, user_1_headers)

    await add_user_to_chat(client, user_2.id, chat_group_1_id, user_1_headers)
    await add_user_to_chat(client, user_2.id, chat_group_2_id, user_1_headers)

    resp_user_1 = await client.get(
        user_chats_url,
        headers=user_1_headers,
    )
    assert resp_user_1.status_code == 200
    resp_user_2 = await client.get(
        user_chats_url,
        headers=user_2_headers,
    )
    assert resp_user_2.status_code == 200

    assert (
        len(resp_user_1.json()["chats"]) == 3 and len(resp_user_2.json()["chats"]) == 3
    )
    assert (
        resp_user_1.json()["chats"][0]["chat_id"] == str(chat_group_1_id)
        and resp_user_2.json()["chats"][0]["chat_id"] == str(chat_group_1_id)
        and resp_user_1.json()["chats"][1]["chat_id"] == str(chat_group_2_id)
        and resp_user_2.json()["chats"][1]["chat_id"] == str(chat_group_2_id)
        and resp_user_1.json()["chats"][2]["chat_id"] == str(chat_private_1_id)
        and resp_user_2.json()["chats"][2]["chat_id"] == str(chat_private_1_id)
    )


@pytest.mark.asyncio
async def test_user_chats_without_auth(
    client,
    user_factory,
):
    resp = await client.get(
        user_chats_url,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_user_chats_order(client, user_factory, auth_headers_factory, db_session):
    user_1 = await user_factory()
    user_1_headers = auth_headers_factory(user_1)
    user_2 = await user_factory()
    user_2_headers = auth_headers_factory(user_2)

    chat_group_1_id = await create_group_chat(client, user_1_headers)
    chat_private_1_id = await create_private_chat(client, user_2.id, user_1_headers)

    await add_user_to_chat(client, user_2.id, chat_group_1_id, user_1_headers)

    await ChatRepository(db_session).create_message(
        str(chat_private_1_id),
        str(user_1.id),
        str(user_2.id),
        content="Test Message",
    )

    resp_user_1 = await client.get(
        user_chats_url,
        headers=user_1_headers,
    )
    assert resp_user_1.status_code == 200
    resp_user_2 = await client.get(
        user_chats_url,
        headers=user_2_headers,
    )
    assert resp_user_2.status_code == 200
    assert (
        resp_user_1.json()["chats"][0]["chat_id"] == str(chat_private_1_id)
        and resp_user_2.json()["chats"][0]["chat_id"] == str(chat_private_1_id)
        and resp_user_1.json()["chats"][1]["chat_id"] == str(chat_group_1_id)
        and resp_user_2.json()["chats"][1]["chat_id"] == str(chat_group_1_id)
    )
