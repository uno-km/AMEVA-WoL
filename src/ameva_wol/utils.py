"""Utility functions for Telegram message formatting and parsing."""

from typing import List, Optional


def split_message(text: str, max_length: int = 4000) -> List[str]:
    """Safely split a long message string into chunks within Telegram's size limit.

    Args:
        text: Input string to split.
        max_length: Maximum length per message chunk (default 4000, safe below 4096).

    Returns:
        List of message chunk strings.
    """
    if not text:
        return [""]

    if len(text) <= max_length:
        return [text]

    chunks: List[str] = []
    current_chunk: List[str] = []
    current_length = 0

    lines = text.split("\n")
    for line in lines:
        line_len = len(line) + 1  # Including newline
        if line_len > max_length:
            # Single line exceeds max_length; force-split by characters
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0

            for i in range(0, len(line), max_length):
                chunks.append(line[i : i + max_length])
            continue

        if current_length + line_len > max_length:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_length = line_len
        else:
            current_chunk.append(line)
            current_length += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def parse_telegram_command(text: str) -> List[str]:
    """Parse message text into tokens, stripping @BotUsername suffix from command token.

    Example:
        "/wake@MyWoLBot server" -> ["/wake", "server"]
        "/add --overwrite lab AA:BB:CC:DD:EE:FF 192.168.1.10" -> ["/add", "--overwrite", "lab", ...]

    Args:
        text: Raw message text from Telegram update.

    Returns:
        List of cleaned non-empty string argument tokens.
    """
    if not text:
        return []

    tokens = text.strip().split()
    if not tokens:
        return []

    first = tokens[0]
    if first.startswith("/"):
        if "@" in first:
            first = first.split("@", 1)[0]
        tokens[0] = first

    return tokens
