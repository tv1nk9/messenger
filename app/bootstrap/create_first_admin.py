import asyncio
import os

from loguru import logger
from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.models import UserModel, UserRole
from app.db.session import session_factory

REQUIRED_ENV_VARS = (
    "FIRST_ADMIN_EMAIL",
    "FIRST_ADMIN_PASSWORD",
    "FIRST_ADMIN_NAME",
    "FIRST_ADMIN_SURNAME",
)
OPTIONAL_ENV_VARS = ("FIRST_ADMIN_PATRONYMIC",)


def _read_bootstrap_env() -> tuple[dict[str, str], list[str]]:
    payload: dict[str, str] = {}
    missing: list[str] = []

    for key in REQUIRED_ENV_VARS:
        value = os.getenv(key, "").strip()
        if not value:
            missing.append(key)
        else:
            payload[key] = value

    for key in OPTIONAL_ENV_VARS:
        payload[key] = os.getenv(key, "").strip()

    return payload, missing


async def create_first_admin() -> int:
    payload, missing = _read_bootstrap_env()
    if missing:
        logger.error(
            "Bootstrap aborted. Missing env vars: {}",
            ", ".join(sorted(missing)),
        )
        return 1

    async with session_factory() as session:
        existing_admin = await session.scalar(
            select(UserModel.id).where(UserModel.role == UserRole.ADMIN).limit(1)
        )
        if existing_admin:
            logger.error("Bootstrap aborted. Admin user already exists.")
            return 1

        password_hash = await get_password_hash(payload["FIRST_ADMIN_PASSWORD"])
        user = UserModel(
            role=UserRole.ADMIN,
            name=payload["FIRST_ADMIN_NAME"],
            surname=payload["FIRST_ADMIN_SURNAME"],
            patronymic=payload["FIRST_ADMIN_PATRONYMIC"] or None,
            email=payload["FIRST_ADMIN_EMAIL"],
            password_hash=password_hash,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    logger.info(
        "AUDIT event=bootstrap_admin_created user_id={} email={} role={}",
        user.id,
        user.email,
        user.role.value,
    )
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(create_first_admin()))


if __name__ == "__main__":
    main()
