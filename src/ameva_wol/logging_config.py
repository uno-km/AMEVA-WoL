"""Structured logging setup for console and rotating log file output."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from ameva_wol.security import redact_secrets


class SecretRedactingFormatter(logging.Formatter):
    """Logging formatter that dynamically redacts sensitive tokens from output strings."""

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, token: Optional[str] = None) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.token = token

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        return redact_secrets(formatted, token=self.token)


def setup_logging(
    log_level: str = "INFO",
    data_dir: Optional[Path] = None,
    bot_token: Optional[str] = None,
) -> logging.Logger:
    """Configure application-wide logger with console and rotating file handlers.

    Args:
        log_level: Level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        data_dir: Optional path for storing rotating log files.
        bot_token: Optional bot token for proactive redaction.

    Returns:
        Configured root logger instance for 'ameva_wol'.
    """
    logger = logging.getLogger("ameva_wol")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = SecretRedactingFormatter(fmt=log_format, datefmt=date_format, token=bot_token)

    # 1. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Rotating File Handler (in data_dir if available)
    if data_dir is not None:
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            log_file = data_dir / "ameva_wol.log"
            file_handler = RotatingFileHandler(
                filename=log_file,
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as err:
            logger.warning(f"Could not initialize rotating log file handler: {err}")

    # Suppress verbose third-party loggers
    for third_party in ("httpx", "telegram", "asyncio", "urllib3"):
        logging.getLogger(third_party).setLevel(logging.WARNING)

    return logger
