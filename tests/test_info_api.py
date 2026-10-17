import pytest

from app.core.configs import settings, api_prefix
from app.web.schemas import FindUserRequest

api_url_prefix = settings.API_V1_STR

info_url_prefix = api_prefix.INFO_ROUTES
find_user_url = f"{api_url_prefix}{info_url_prefix}{api_prefix.FIND_USER}"


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
        json=FindUserRequest(
            name="Test User",
            offset=offset,
            limit=limit
        ).model_dump(mode='json')
    )
    assert resp.status_code == 200
