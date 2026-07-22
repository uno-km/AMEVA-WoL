"""Configuration management for AMEVA-WoL using environment variables and .env files."""

import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set

from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when application configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    """Immutable application configuration dataclass."""

    telegram_bot_token: str
    allowed_user_ids: Set[int]
    allowed_chat_ids: Set[int]
    default_broadcast: str
    default_wol_port: int
    default_wol_repeat: int
    default_wol_delay_ms: int
    ping_timeout_seconds: int
    log_level: str
    data_dir: Path
    rate_limit_commands: int
    rate_limit_window_seconds: int
    telegram_poll_timeout_seconds: int

    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> "Config":
        """Load configuration from environment variables or specified .env file."""
        if env_path is not None:
            if not env_path.exists():
                raise ConfigurationError(f"Specified environment file does not exist: {env_path}")
            load_dotenv(dotenv_path=env_path, override=True)
        else:
            load_dotenv(override=False)

        # 1. Telegram Bot Token
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise ConfigurationError("TELEGRAM_BOT_TOKEN must be set in environment or .env file.")
        if ":" not in token or len(token) < 20:
            raise ConfigurationError("TELEGRAM_BOT_TOKEN appears to be invalid or malformed.")

        # 2. Allowed User IDs
        user_ids_str = os.getenv("ALLOWED_USER_IDS", "").strip()
        if not user_ids_str:
            raise ConfigurationError("ALLOWED_USER_IDS must be set and contain at least one numeric Telegram user ID.")
        
        allowed_user_ids: Set[int] = set()
        for item in user_ids_str.split(","):
            cleaned = item.strip()
            if not cleaned:
                continue
            try:
                allowed_user_ids.add(int(cleaned))
            except ValueError:
                raise ConfigurationError(f"Invalid user ID in ALLOWED_USER_IDS: '{cleaned}' must be an integer.")
        
        if not allowed_user_ids:
            raise ConfigurationError("ALLOWED_USER_IDS contains no valid integer User IDs.")

        # 3. Allowed Chat IDs (Optional)
        chat_ids_str = os.getenv("ALLOWED_CHAT_IDS", "").strip()
        allowed_chat_ids: Set[int] = set()
        if chat_ids_str:
            for item in chat_ids_str.split(","):
                cleaned = item.strip()
                if not cleaned:
                    continue
                try:
                    allowed_chat_ids.add(int(cleaned))
                except ValueError:
                    raise ConfigurationError(f"Invalid chat ID in ALLOWED_CHAT_IDS: '{cleaned}' must be an integer.")

        # 4. Default Broadcast Address
        broadcast = os.getenv("DEFAULT_BROADCAST", "192.168.0.255").strip()
        try:
            ipaddress.IPv4Address(broadcast)
        except ValueError:
            raise ConfigurationError(f"DEFAULT_BROADCAST '{broadcast}' is not a valid IPv4 address.")

        # 5. Default WoL Port
        try:
            port = int(os.getenv("DEFAULT_WOL_PORT", "9").strip())
            if not (1 <= port <= 65535):
                raise ValueError()
        except ValueError:
            raise ConfigurationError("DEFAULT_WOL_PORT must be an integer between 1 and 65535.")

        # 6. Default WoL Repeat
        try:
            repeat = int(os.getenv("DEFAULT_WOL_REPEAT", "3").strip())
            if not (1 <= repeat <= 100):
                raise ValueError()
        except ValueError:
            raise ConfigurationError("DEFAULT_WOL_REPEAT must be an integer between 1 and 100.")

        # 7. Default WoL Delay MS
        try:
            delay_ms = int(os.getenv("DEFAULT_WOL_DELAY_MS", "250").strip())
            if not (0 <= delay_ms <= 10000):
                raise ValueError()
        except ValueError:
            raise ConfigurationError("DEFAULT_WOL_DELAY_MS must be an integer between 0 and 10000.")

        # 8. Ping Timeout Seconds
        try:
            ping_timeout = int(os.getenv("PING_TIMEOUT_SECONDS", "2").strip())
            if not (1 <= ping_timeout <= 60):
                raise ValueError()
        except ValueError:
            raise ConfigurationError("PING_TIMEOUT_SECONDS must be an integer between 1 and 60.")

        # 9. Log Level
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigurationError(f"LOG_LEVEL '{log_level}' is invalid. Allowed: DEBUG, INFO, WARNING, ERROR, CRITICAL.")

        # 10. Data Directory
        data_dir_str = os.getenv("DATA_DIR", "./data").strip()
        data_dir = Path(data_dir_str).resolve()
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as err:
            raise ConfigurationError(f"Failed to create or access DATA_DIR '{data_dir}': {err}")

        # 11. Rate Limit Commands
        try:
            rate_limit_commands = int(os.getenv("RATE_LIMIT_COMMANDS", "10").strip())
            if not (1 <= rate_limit_commands <= 1000):
                raise ValueError()
        except ValueError:
            raise ConfigurationError("RATE_LIMIT_COMMANDS must be an integer between 1 and 1000.")

        # 12. Rate Limit Window Seconds
        try:
            rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60").strip())
            if not (1 <= rate_limit_window <= 3600):
                raise ValueError()
        except ValueError:
            raise ConfigurationError("RATE_LIMIT_WINDOW_SECONDS must be an integer between 1 and 3600.")

        # 13. Telegram Poll Timeout Seconds
        try:
            poll_timeout = int(os.getenv("TELEGRAM_POLL_TIMEOUT_SECONDS", "30").strip())
            if not (1 <= poll_timeout <= 300):
                raise ValueError()
        except ValueError:
            raise ConfigurationError("TELEGRAM_POLL_TIMEOUT_SECONDS must be an integer between 1 and 300.")

        return cls(
            telegram_bot_token=token,
            allowed_user_ids=allowed_user_ids,
            allowed_chat_ids=allowed_chat_ids,
            default_broadcast=broadcast,
            default_wol_port=port,
            default_wol_repeat=repeat,
            default_wol_delay_ms=delay_ms,
            ping_timeout_seconds=ping_timeout,
            log_level=log_level,
            data_dir=data_dir,
            rate_limit_commands=rate_limit_commands,
            rate_limit_window_seconds=rate_limit_window,
            telegram_poll_timeout_seconds=poll_timeout,
        )
