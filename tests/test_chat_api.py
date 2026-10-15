import uuid
import pytest

from httpx import AsyncClient
from sqlalchemy import select

from app.core.configs import settings, api_prefix
from app.db.models import GroupChatModel
from app.web.schemas import GroupChatCreateRequest

app_url_prefix = settings.API_V1_STR

chat_url_prefix = api_prefix.CHAT_ROUTES
create_group_chat_url = f"{app_url_prefix}{chat_url_prefix}{api_prefix.CREATE_GROUP_CHAT}"

create_group_chat_request = GroupChatCreateRequest(
    chat_name="test_chat",
    chat_description="test_chat_desc"
)

@pytest.mark.asyncio
async def test_create_group_chat_without_auth(client: AsyncClient):
    req_data = create_group_chat_request

    resp = await client.post(
        f"{create_group_chat_url}",
        json=req_data.model_dump(),
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
    headers = auth_headers_factory(await user_factory())

    resp = await client.post(
        f"{create_group_chat_url}",
        headers=headers,
        json=req_data.model_dump(),
    )
    assert resp.status_code == 200

    chat_id = resp.json()["chat_id"]
    result = await db_session.execute(
        select(GroupChatModel).where(
            GroupChatModel.chat_id == uuid.UUID(chat_id)
        )
    )
    chat: GroupChatModel | None = result.scalar_one_or_none()

    assert chat is not None
    assert chat.chat_name == req_data.chat_name
    assert chat.chat_desc == req_data.chat_description


# @pytest.mark.asyncio
# async def test_add_user_to_group_chat(auth_client: AsyncClient):
#     pass
