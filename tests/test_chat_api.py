import pytest

from httpx import AsyncClient
from sqlalchemy import select

from app.core.configs import settings, api_prefix
from app.db.models import GroupChatModel, GroupChatMemberModel, PrivateChatModel
from app.web.schemas import AddUserGroupChatRequest, PrivateChatCreateRequest
from common import create_private_chat, create_group_chat, create_group_chat_request

app_url_prefix = settings.API_V1_STR

chat_url_prefix = api_prefix.CHAT_ROUTES
create_group_chat_url = (
    f"{app_url_prefix}{chat_url_prefix}{api_prefix.CREATE_GROUP_CHAT}"
)
add_user_to_chat_url = f"{app_url_prefix}{chat_url_prefix}{api_prefix.ADD_USER_TO_CHAT}"
create_private_chat_url = (
    f"{app_url_prefix}{chat_url_prefix}{api_prefix.CREATE_PRIVATE_CHAT}"
)


@pytest.mark.asyncio
async def test_create_group_chat(
    client, user_factory, auth_headers_factory, db_session
):
    user = await user_factory()

    chat_id = await create_group_chat(
        client_u=client, headers=auth_headers_factory(user)
    )
    chat = await db_session.scalar(
        select(GroupChatModel).where(GroupChatModel.chat_id == chat_id)
    )
    assert chat is not None
    assert chat.chat_name == create_group_chat_request.chat_name
    assert chat.chat_desc == create_group_chat_request.chat_description

    member = await db_session.scalar(
        select(GroupChatMemberModel).where(
            GroupChatMemberModel.chat_id == chat_id,
            GroupChatMemberModel.user_id == user.id,
        )
    )
    assert member is not None
    assert member.user_id == user.id
    assert member.role.value == "owner"


@pytest.mark.asyncio
async def test_create_group_chat_without_auth(client: AsyncClient):
    resp = await client.post(
        create_group_chat_url, json=create_group_chat_request.model_dump(mode="json")
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_add_user_to_group_chat(
    client, user_factory, auth_headers_factory, db_session
):
    owner_user = await user_factory(name="owner")
    owner_user_headers = auth_headers_factory(owner_user)
    member_user = await user_factory(name="member")

    chat_id = await create_group_chat(client, headers=owner_user_headers)
    resp = await client.post(
        add_user_to_chat_url,
        headers=owner_user_headers,
        json=AddUserGroupChatRequest(
            user_id=str(member_user.id), chat_id=str(chat_id)
        ).model_dump(mode="json"),
    )
    assert resp.status_code == 200

    members = await db_session.scalars(
        select(GroupChatMemberModel).where(GroupChatMemberModel.chat_id == chat_id)
    )
    member_ids = {item.user_id for item in members}
    assert member_ids == {owner_user.id, member_user.id}


@pytest.mark.asyncio
async def test_add_user_to_group_chat_twice(
    client, user_factory, auth_headers_factory, db_session
):
    owner = await user_factory()
    owner_headers = auth_headers_factory(owner)
    member = await user_factory()

    chat_id = await create_group_chat(client_u=client, headers=owner_headers)
    resp = await client.post(
        add_user_to_chat_url,
        headers=owner_headers,
        json=AddUserGroupChatRequest(
            user_id=str(member.id), chat_id=str(chat_id)
        ).model_dump(mode="json"),
    )
    assert resp.status_code == 200

    resp = await client.post(
        add_user_to_chat_url,
        headers=owner_headers,
        json=AddUserGroupChatRequest(
            user_id=str(member.id), chat_id=str(chat_id)
        ).model_dump(mode="json"),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_private_chat(
    client, user_factory, auth_headers_factory, db_session
):
    user_1 = await user_factory()
    user_1_headers = auth_headers_factory(user_1)
    user_2 = await user_factory()

    chat_id = await create_private_chat(
        client_u=client, user_2_id=user_2.id, headers=user_1_headers
    )
    chat = await db_session.scalar(
        select(PrivateChatModel).where(PrivateChatModel.chat_id == chat_id)
    )
    assert chat is not None
    assert chat.user_1_id is not None
    assert chat.user_2_id is not None
    assert chat.user_1_id == user_1.id or chat.user_2_id == user_1.id
    assert chat.user_1_id == user_2.id or chat.user_2_id == user_2.id


@pytest.mark.asyncio
async def test_create_private_chat_without_auth(
    client,
    user_factory,
):
    user_2 = await user_factory()

    resp = await client.post(
        create_private_chat_url,
        json=PrivateChatCreateRequest(user_2_id=str(user_2.id)).model_dump(mode="json"),
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_private_chat_twice(
    client, user_factory, auth_headers_factory, db_session
):
    user_1 = await user_factory()
    user_1_headers = auth_headers_factory(user_1)
    user_2 = await user_factory()
    user_2_headers = auth_headers_factory(user_2)

    await create_private_chat(
        client_u=client, user_2_id=user_2.id, headers=user_1_headers
    )

    resp = await client.post(
        create_private_chat_url,
        headers=user_2_headers,
        json=PrivateChatCreateRequest(user_2_id=str(user_1.id)).model_dump(mode="json"),
    )
    assert resp.status_code == 409
