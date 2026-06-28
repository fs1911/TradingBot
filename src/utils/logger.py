"""Centralised logging with Loguru."""
import sys
import os
from loguru import logger


def setup_logger(log_level: str = "INFO", log_dir: str = "logs") -> None:
    os.makedirs(log_dir, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    logger.add(
        f"{log_dir}/bot_{{time:YYYY-MM-DD}}.log",
        level=log_level,
        rotation="00:00",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}",
    )
    logger.add(
        f"{log_dir}/errors.log",
        level="ERROR",
        rotation="10 MB",
        retention="90 days",
        compression="gz",
    )


def get_logger(name: str):
    return logger.bind(name=name)
