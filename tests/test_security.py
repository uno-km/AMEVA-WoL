"""Unit tests for security utilities, validation, authorization, and rate limiting."""

import time
import pytest

from ameva_wol.security import (
    RateLimiter,
    is_chat_authorized,
    is_user_authorized,
    redact_secrets,
    validate_alias,
    validate_broadcast,
    validate_ipv4,
    validate_mac,
)


def test_validate_mac_supported_formats() -> None:
    """Test MAC address normalization across all supported formats."""
    expected = "AA:BB:CC:DD:EE:FF"
    assert validate_mac("AA:BB:CC:DD:EE:FF") == expected
    assert validate_mac("aa-bb-cc-dd-ee-ff") == expected
    assert validate_mac("aabbccddeeff") == expected
    assert validate_mac("  AA:bb:CC:dd:EE:ff  ") == expected


def test_validate_mac_invalid_rejection() -> None:
    """Test rejection of invalid MAC addresses."""
    with pytest.raises(ValueError, match="MAC address"):
        validate_mac("INVALID_MAC")
    with pytest.raises(ValueError):
        validate_mac("AA:BB:CC:DD:EE")  # Short
    with pytest.raises(ValueError):
        validate_mac("ZZ:BB:CC:DD:EE:FF")  # Non-hex


def test_validate_alias_valid() -> None:
    """Test alias format validation and lowercase normalization."""
    assert validate_alias("My-Server_01") == "my-server_01"
    assert validate_alias("a") == "a"
    assert validate_alias("12345678901234567890123456789012") == "12345678901234567890123456789012"


def test_validate_alias_invalid_rejection() -> None:
    """Test rejection of invalid alias strings."""
    with pytest.raises(ValueError):
        validate_alias("")  # Empty
    with pytest.raises(ValueError):
        validate_alias("alias with spaces")
    with pytest.raises(ValueError):
        validate_alias("alias@special!")
    with pytest.raises(ValueError):
        validate_alias("a" * 33)  # Exceeds 32 chars


def test_validate_ipv4_and_broadcast() -> None:
    """Test IPv4 and broadcast validation."""
    assert validate_ipv4("192.168.0.1") == "192.168.0.1"
    assert validate_broadcast("192.168.0.255") == "192.168.0.255"

    with pytest.raises(ValueError):
        validate_ipv4("256.0.0.1")
    with pytest.raises(ValueError):
        validate_ipv4("invalid-ip")


def test_authorization_checks() -> None:
    """Test user and chat authorization logic."""
    allowed_users = {100, 200}
    assert is_user_authorized(100, allowed_users) is True
    assert is_user_authorized(999, allowed_users) is False
    assert is_user_authorized(None, allowed_users) is False

    allowed_chats = {-1001, -1002}
    assert is_chat_authorized(-1001, allowed_chats) is True
    assert is_chat_authorized(-9999, allowed_chats) is False
    assert is_chat_authorized(None, allowed_chats) is False

    # Empty chat whitelist means disabled restriction
    assert is_chat_authorized(-9999, set()) is True


def test_rate_limiter() -> None:
    """Test in-memory sliding window rate limiter."""
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    user_id = 42

    assert limiter.is_allowed(user_id) is True
    assert limiter.is_allowed(user_id) is True
    assert limiter.is_allowed(user_id) is False  # Exceeded limit


def test_redact_secrets() -> None:
    """Test redaction of Telegram bot tokens from text strings."""
    token = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken"
    msg = f"Error connecting to https://api.telegram.org/bot{token}/getUpdates"

    redacted = redact_secrets(msg, token=token)
    assert token not in redacted
    assert "[REDACTED_TOKEN]" in redacted
