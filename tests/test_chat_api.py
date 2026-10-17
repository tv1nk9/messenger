import uuid
import pytest

from httpx import AsyncClient
from sqlalchemy import select

from app.core.configs import settings, api_prefix
from app.db.models import GroupChatModel, GroupChatMemberModel
from app.web.schemas import GroupChatCreateRequest, AddUserGroupChatRequest

app_url_prefix = settings.API_V1_STR

chat_url_prefix = api_prefix.CHAT_ROUTES
create_group_chat_url = f"{app_url_prefix}{chat_url_prefix}{api_prefix.CREATE_GROUP_CHAT}"
add_user_to_chat_url = f"{app_url_prefix}{chat_url_prefix}{api_prefix.ADD_USER_TO_CHAT}"

create_group_chat_request = GroupChatCreateRequest(
    chat_name="test_chat",
    chat_description="test_chat_desc"
)


async def _create_group_chat(
        client_u: AsyncClient,
        headers: dict | None = None
) -> uuid.UUID:
    resp = await client_u.post(
        create_group_chat_url,
        headers=headers,
        json=create_group_chat_request.model_dump(mode="json")
    )

    assert resp.status_code == 200
    return uuid.UUID(resp.json()["chat_id"])


@pytest.mark.asyncio
async def test_create_group_chat_without_auth(client: AsyncClient):
    resp = await client.post(
        create_group_chat_url,
        json=create_group_chat_request.model_dump(mode="json")
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_group_chat(
        client,
        user_factory,
        auth_headers_factory,
        db_session
):
    req_data = create_group_chat_request
    user = await user_factory()

    chat_id = await _create_group_chat(
        client_u=client, headers=auth_headers_factory(user)
    )
    chat = await db_session.scalar(
        select(GroupChatModel).where(
            GroupChatModel.chat_id == chat_id
        )
    )
    assert chat is not None
    assert chat.chat_name == req_data.chat_name
    assert chat.chat_desc == req_data.chat_description

    member = await db_session.scalar(
        select(GroupChatMemberModel)
        .where(
            GroupChatMemberModel.chat_id == chat_id,
            GroupChatMemberModel.user_id == user.id
        )
    )
    assert member is not None
    assert member.user_id == user.id
    assert member.role.value == "owner"


@pytest.mark.asyncio
async def test_add_user_to_group_chat(
        client,
        user_factory,
        auth_headers_factory,
        db_session
):
    owner_user = await user_factory(name="owner")
    owner_user_headers = auth_headers_factory(owner_user)
    member_user = await user_factory(name="member")

    chat_id = await _create_group_chat(
        client, headers=owner_user_headers
    )
    resp = await client.post(
        add_user_to_chat_url,
        headers=owner_user_headers,
        json=AddUserGroupChatRequest(
            user_id=str(member_user.id),
            chat_id=str(chat_id)
        ).model_dump(mode="json")
    )
    assert resp.status_code == 200

    members = await db_session.scalars(
        select(GroupChatMemberModel)
        .where(GroupChatMemberModel.chat_id == chat_id)
    )
    member_ids = {item.user_id for item in members}
    assert member_ids == {owner_user.id, member_user.id}
