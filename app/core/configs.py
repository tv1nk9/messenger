import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

class JWTConfig:
    SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY must be set")
    ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
    REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    ALGORITHM = "HS256"


jwt_config = JWTConfig()

class ChatConfig:
    MAX_LENGTH_CHAT_NAME = 16
    MIN_LENGTH_CHAT_NAME = 2
    MIN_LENGTH_CHAT_DESC = 0
    MAX_LENGTH_CHAT_DESC = 250
    MAX_LENGTH_MESSAGE = 1000
    MIN_LENGTH_MESSAGE = 1

chat_config = ChatConfig()

class UserConfig:
    MAX_LENGTH_USERNAME = 16
    MIN_LENGTH_USERNAME = 2
    MAX_LENGTH_PASSWORD = 16
    MIN_LENGTH_PASSWORD = 4

user_config = UserConfig()


class AppSetting:
    API_V1_STR: str = "/api/v1"


settings = AppSetting()
