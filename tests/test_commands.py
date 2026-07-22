"""Unit tests for Telegram command dispatcher and command handling."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from ameva_wol.commands import CommandDispatcher
from ameva_wol.config import Config
from ameva_wol.models import Device, current_utc_iso
from ameva_wol.registry import DeviceRegistry


@pytest.fixture
def test_config(tmp_path: Path) -> Config:
    """Fixture providing a mock Config instance."""
    return Config(
        telegram_bot_token="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken",
        allowed_user_ids={100, 200},
        allowed_chat_ids={-1001},
        default_broadcast="192.168.0.255",
        default_wol_port=9,
        default_wol_repeat=3,
        default_wol_delay_ms=10,
        ping_timeout_seconds=1,
        log_level="INFO",
        data_dir=tmp_path,
        rate_limit_commands=10,
        rate_limit_window_seconds=60,
        telegram_poll_timeout_seconds=30,
    )


def make_mock_update(user_id: int = 100, chat_id: int = -1001, text: str = "/start") -> MagicMock:
    """Helper creating a mock Telegram Update object."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat.id = chat_id
    update.effective_message.text = text
    update.effective_message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_command_unauthorized_user_rejected(test_config: Config, tmp_path: Path) -> None:
    """Test that unauthorized user ID is rejected silently."""
    registry = DeviceRegistry(tmp_path)
    dispatcher = CommandDispatcher(test_config, registry)

    unauthorized_update = make_mock_update(user_id=999, chat_id=-1001, text="/start")
    await dispatcher.handle_start(unauthorized_update, MagicMock())

    unauthorized_update.effective_message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_command_unauthorized_chat_rejected(test_config: Config, tmp_path: Path) -> None:
    """Test that unauthorized chat ID is rejected."""
    registry = DeviceRegistry(tmp_path)
    dispatcher = CommandDispatcher(test_config, registry)

    unauthorized_update = make_mock_update(user_id=100, chat_id=-9999, text="/start")
    await dispatcher.handle_start(unauthorized_update, MagicMock())

    unauthorized_update.effective_message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_handle_add_command(test_config: Config, tmp_path: Path) -> None:
    """Test /add command registers a new device."""
    registry = DeviceRegistry(tmp_path)
    dispatcher = CommandDispatcher(test_config, registry)

    update = make_mock_update(text="/add server AA:BB:CC:DD:EE:01 192.168.0.50")
    await dispatcher.handle_add(update, MagicMock())

    update.effective_message.reply_text.assert_called_once()
    reply = update.effective_message.reply_text.call_args[0][0]
    assert "Device Registered Successfully" in reply

    device = await registry.get("server")
    assert device is not None
    assert device.mac == "AA:BB:CC:DD:EE:01"
    assert device.ip == "192.168.0.50"


@pytest.mark.asyncio
async def test_handle_wake_single_device(test_config: Config, tmp_path: Path) -> None:
    """Test /wake with single registered device sends WoL packet."""
    registry = DeviceRegistry(tmp_path)
    dev = Device("nas", "11:22:33:44:55:66", "192.168.0.10", "192.168.0.255", 9, current_utc_iso(), current_utc_iso())
    await registry.add(dev)

    dispatcher = CommandDispatcher(test_config, registry)
    update = make_mock_update(text="/wake")

    with patch("ameva_wol.commands.send_magic_packet", new_callable=AsyncMock) as mock_wol:
        mock_wol.return_value = {"success": True, "packets_sent": 3, "repeat": 3}
        await dispatcher.handle_wake(update, MagicMock())

        mock_wol.assert_called_once()
        reply = update.effective_message.reply_text.call_args[0][0]
        assert "Magic Packet Sent" in reply


@pytest.mark.asyncio
async def test_handle_status_single_device(test_config: Config, tmp_path: Path) -> None:
    """Test /status checks host reachability via ping."""
    registry = DeviceRegistry(tmp_path)
    dev = Device("desktop", "11:22:33:44:55:66", "192.168.0.100", "192.168.0.255", 9, current_utc_iso(), current_utc_iso())
    await registry.add(dev)

    dispatcher = CommandDispatcher(test_config, registry)
    update = make_mock_update(text="/status desktop")

    with patch("ameva_wol.commands.ping_host", new_callable=AsyncMock) as mock_ping:
        mock_ping.return_value = True
        await dispatcher.handle_status(update, MagicMock())

        mock_ping.assert_called_once_with("192.168.0.100", timeout_seconds=1)
        assert update.effective_message.reply_text.call_count == 2
        final_reply = update.effective_message.reply_text.call_args_list[1][0][0]
        assert "ONLINE" in final_reply


@pytest.mark.asyncio
async def test_handle_remove_command(test_config: Config, tmp_path: Path) -> None:
    """Test /remove command deletes registered device."""
    registry = DeviceRegistry(tmp_path)
    dev = Device("old_pc", "11:22:33:44:55:66", "192.168.0.100", "192.168.0.255", 9, current_utc_iso(), current_utc_iso())
    await registry.add(dev)

    dispatcher = CommandDispatcher(test_config, registry)
    update = make_mock_update(text="/remove old_pc")

    await dispatcher.handle_remove(update, MagicMock())

    assert await registry.get("old_pc") is None
    reply = update.effective_message.reply_text.call_args[0][0]
    assert "removed from registry" in reply
