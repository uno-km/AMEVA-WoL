"""Security utilities: validation, authorization, rate limiting, and secret redaction."""

import ipaddress
import re
import time
from typing import Dict, List, Optional, Set


class SecurityError(Exception):
    """Raised when validation or authorization fails."""


# Alias format regex: 1-32 characters, lowercase letters, numbers, hyphen, underscore
ALIAS_REGEX = re.compile(r"^[a-z0-9_-]{1,32}$")

# General Telegram bot token regex pattern for redaction fallback
BOT_TOKEN_PATTERN = re.compile(r"\b\d{5,12}:[A-Za-z0-9_-]{30,50}\b")


def validate_alias(alias: str) -> str:
    """Validate and normalize a device alias.

    Rules:
    - 1 to 32 characters
    - Lowercase letters, numbers, hyphens, and underscores
    - Normalized to lowercase

    Returns:
        Normalized lowercase alias string.

    Raises:
        ValueError: If alias violates format rules.
    """
    if not isinstance(alias, str):
        raise ValueError("Alias must be a string.")
    
    cleaned = alias.strip().lower()
    if not cleaned:
        raise ValueError("Alias cannot be empty.")
    
    if not ALIAS_REGEX.match(cleaned):
        raise ValueError(
            "Invalid alias format. Alias must be 1-32 characters long and contain "
            "only lowercase letters, numbers, hyphens (-), and underscores (_)."
        )
    
    return cleaned


def validate_mac(mac: str) -> str:
    """Validate and normalize a MAC address.

    Supported Formats:
    - AA:BB:CC:DD:EE:FF
    - AA-BB-CC-DD-EE-FF
    - AABBCCDDEEFF

    Returns:
        Normalized uppercase colon-separated MAC address (e.g., 'AA:BB:CC:DD:EE:FF').

    Raises:
        ValueError: If MAC address format is invalid.
    """
    if not isinstance(mac, str):
        raise ValueError("MAC address must be a string.")
    
    cleaned = mac.strip().replace(":", "").replace("-", "").replace(".", "")
    if len(cleaned) != 12:
        raise ValueError("Invalid MAC address length. Must contain exactly 12 hexadecimal characters.")
    
    try:
        raw_bytes = bytes.fromhex(cleaned)
    except ValueError:
        raise ValueError("Invalid MAC address. Contains non-hexadecimal characters.")
    
    if len(raw_bytes) != 6:
        raise ValueError("Invalid MAC address byte length.")
    
    hex_str = cleaned.upper()
    normalized = ":".join(hex_str[i : i + 2] for i in range(0, 12, 2))
    return normalized


def validate_ipv4(ip: str) -> str:
    """Validate IPv4 address using Python's ipaddress module.

    Returns:
        Normalized IPv4 address string.

    Raises:
        ValueError: If IP address is invalid.
    """
    if not isinstance(ip, str):
        raise ValueError("IP address must be a string.")
    
    cleaned = ip.strip()
    try:
        obj = ipaddress.IPv4Address(cleaned)
        return str(obj)
    except ValueError as err:
        raise ValueError(f"Invalid IPv4 address '{cleaned}': {err}")


def validate_broadcast(broadcast: str) -> str:
    """Validate IPv4 broadcast address.

    Returns:
        Normalized IPv4 broadcast address string.

    Raises:
        ValueError: If broadcast address is invalid.
    """
    return validate_ipv4(broadcast)


def is_user_authorized(user_id: Optional[int], allowed_user_ids: Set[int]) -> bool:
    """Check if the requesting Telegram user ID is authorized."""
    if user_id is None:
        return False
    return user_id in allowed_user_ids


def is_chat_authorized(chat_id: Optional[int], allowed_chat_ids: Set[int]) -> bool:
    """Check if the requesting Telegram chat ID is authorized.

    If allowed_chat_ids is empty, chat restriction is disabled (returns True).
    """
    if not allowed_chat_ids:
        return True
    if chat_id is None:
        return False
    return chat_id in allowed_chat_ids


def redact_secrets(text: str, token: Optional[str] = None) -> str:
    """Redact sensitive bot tokens from log messages or user responses.

    Args:
        text: Input message or error string.
        token: Specific bot token to redact if available.

    Returns:
        Sanitized string with tokens replaced by '[REDACTED_TOKEN]'.
    """
    if not text:
        return text

    sanitized = text
    if token and token in sanitized:
        sanitized = sanitized.replace(token, "[REDACTED_TOKEN]")

    # Fallback pattern match for any standard Bot API token
    sanitized = BOT_TOKEN_PATTERN.sub("[REDACTED_TOKEN]", sanitized)
    return sanitized


class RateLimiter:
    """In-memory sliding window rate limiter per user ID."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: Dict[int, List[float]] = {}

    def is_allowed(self, user_id: int) -> bool:
        """Check if request from user_id is permitted under rate limit policy."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        
        timestamps = self._history.get(user_id, [])
        # Prune outdated timestamps
        valid_timestamps = [t for t in timestamps if t > cutoff]
        
        if len(valid_timestamps) >= self.max_requests:
            self._history[user_id] = valid_timestamps
            return False

        valid_timestamps.append(now)
        self._history[user_id] = valid_timestamps
        return True
