import jwt
import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import datetime, timezone

from app.core.configs import jwt_config

ph = PasswordHasher()


def verify_token(token: str) -> None | dict:
    try:
        payload = jwt.decode(
            token, jwt_config.SECRET_KEY, algorithms=jwt_config.ALGORITHM
        )
        if payload.get("sub") is None:
            return None
        return payload
    except InvalidTokenError:
        return None


def generate_token(subject: str, token_type: str, jti: str, ver: int) -> None | str:
    if not subject:
        return None

    expires = (
        jwt_config.REFRESH_TOKEN_EXPIRES
        if token_type == "refresh"
        else jwt_config.ACCESS_TOKEN_EXPIRES
    )
    if not expires:
        return None

    payload = {
        "sub": subject,
        "jti": jti,
        "type": token_type,
        "ver": ver,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + expires,
    }
    return jwt.encode(payload, jwt_config.SECRET_KEY, algorithm=jwt_config.ALGORITHM)


def issue_tokens(
    user_id: str, ver: int, access_jti: str, refresh_jti: str
) -> None | dict:
    if not user_id:
        return None

    return {
        "access_token": generate_token(user_id, "access", access_jti, ver),
        "refresh_token": generate_token(user_id, "refresh", refresh_jti, ver),
    }

async def verify_password(password_hash: str, password: str) -> bool:
    try:
        await asyncio.to_thread(ph.verify, password_hash, password)
        return True
    except VerifyMismatchError:
        return False
    except Exception:
        return False

async def get_password_hash(password: str) -> str:
    return await asyncio.to_thread(ph.hash, password)
