import uuid

from httpx import AsyncClient

from app.web.schemas import GroupChatCreateRequest, PrivateChatCreateRequest, AddUserGroupChatRequest
from app.core.configs import settings, api_prefix

app_url_prefix = settings.API_V1_STR

chat_url_prefix = api_prefix.CHAT_ROUTES
create_group_chat_url = f"{app_url_prefix}{chat_url_prefix}{api_prefix.CREATE_GROUP_CHAT}"
add_user_to_chat_url = f"{app_url_prefix}{chat_url_prefix}{api_prefix.ADD_USER_TO_CHAT}"
create_private_chat_url = f"{app_url_prefix}{chat_url_prefix}{api_prefix.CREATE_PRIVATE_CHAT}"

create_group_chat_request = GroupChatCreateRequest(
    chat_name="test_chat",
    chat_description="test_chat_desc"
)

async def create_group_chat(
        client_u: AsyncClient,
        headers: dict
) -> uuid.UUID:
    resp = await client_u.post(
        create_group_chat_url,
        headers=headers,
        json=create_group_chat_request.model_dump(mode="json")
    )

    assert resp.status_code == 200
    return uuid.UUID(resp.json()["chat_id"])


async def create_private_chat(
        client_u: AsyncClient,
        user_2_id: uuid.UUID,
        headers: dict,
) -> uuid.UUID:
    resp = await client_u.post(
        create_private_chat_url,
        headers=headers,
        json=PrivateChatCreateRequest(user_2_id=str(user_2_id)).model_dump(mode="json")
    )
    assert resp.status_code == 200
    return uuid.UUID(resp.json()["chat_id"])

async def add_user_to_chat(
        client_u: AsyncClient,
        user_id: uuid.UUID,
        chat_id: uuid.UUID,
        headers: dict
):
    resp = await client_u.post(
        add_user_to_chat_url,
        headers=headers,
        json=AddUserGroupChatRequest(
            user_id=str(user_id),
            chat_id=str(chat_id)
        ).model_dump(mode="json")
    )
    assert resp.status_code == 200
