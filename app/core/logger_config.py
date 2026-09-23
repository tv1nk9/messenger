import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger


def setup_logger():
    logger.remove()

    # Формат разработка
    dev_format = (
        "<green>{time:HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )

    # Формат продакшен
    prod_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function} | {message}"

    # Конфигурация разработка
    if os.getenv("ENV_TYPE", "dev") == "dev":
        logger.add(sys.stderr, level="DEBUG", format=dev_format, colorize=True)
        logger.info("Config DEV")

    # Конфигурация продакшен
    else:
        logger.add(sys.stderr, level="INFO", format=prod_format)

        os.makedirs("logs", exist_ok=True)

        LOCAL_TZ = ZoneInfo("Europe/Moscow")
        log_filename = f"logs/app_{datetime.now(LOCAL_TZ).strftime('%Y-%m-%d_%H-%M-%S')}.log"

        logger.add(
            log_filename,
            level="DEBUG",
            rotation="10 MB",
            retention="1 week",
            compression="zip",
            serialize=True, # JSON
        )
        logger.info("Config PROD")