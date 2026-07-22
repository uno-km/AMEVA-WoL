"""Unit tests for configuration loading and validation."""

import os
from pathlib import Path
import pytest

from ameva_wol.config import Config, ConfigurationError


def test_config_load_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading valid configuration from environment variables."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken")
    monkeypatch.setenv("ALLOWED_USER_IDS", "100, 200,300")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "-10012345")
    monkeypatch.setenv("DEFAULT_BROADCAST", "192.168.1.255")
    monkeypatch.setenv("DEFAULT_WOL_PORT", "7")
    monkeypatch.setenv("DEFAULT_WOL_REPEAT", "5")
    monkeypatch.setenv("DEFAULT_WOL_DELAY_MS", "100")
    monkeypatch.setenv("PING_TIMEOUT_SECONDS", "3")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    config = Config.load()

    assert config.telegram_bot_token == "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken"
    assert config.allowed_user_ids == {100, 200, 300}
    assert config.allowed_chat_ids == {-10012345}
    assert config.default_broadcast == "192.168.1.255"
    assert config.default_wol_port == 7
    assert config.default_wol_repeat == 5
    assert config.default_wol_delay_ms == 100
    assert config.ping_timeout_seconds == 3
    assert config.log_level == "DEBUG"
    assert (tmp_path / "data").exists()


def test_config_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that missing bot token raises ConfigurationError."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("ALLOWED_USER_IDS", "100")
    
    with pytest.raises(ConfigurationError, match="TELEGRAM_BOT_TOKEN"):
        Config.load()


def test_config_invalid_user_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that non-numeric user IDs raise ConfigurationError."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken")
    monkeypatch.setenv("ALLOWED_USER_IDS", "100, invalid_id")

    with pytest.raises(ConfigurationError, match="ALLOWED_USER_IDS"):
        Config.load()


def test_config_invalid_broadcast(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test invalid broadcast IPv4 validation."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken")
    monkeypatch.setenv("ALLOWED_USER_IDS", "100")
    monkeypatch.setenv("DEFAULT_BROADCAST", "999.999.999.999")

    with pytest.raises(ConfigurationError, match="DEFAULT_BROADCAST"):
        Config.load()


def test_config_empty_chat_ids_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that empty ALLOWED_CHAT_IDS results in empty set (disabled restriction)."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken")
    monkeypatch.setenv("ALLOWED_USER_IDS", "100")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "")

    config = Config.load()
    assert config.allowed_chat_ids == set()
