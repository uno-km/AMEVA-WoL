"""Unit tests for Always-On monitoring scheduler."""

from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from ameva_wol.config import Config
from ameva_wol.models import Device, current_utc_iso
from ameva_wol.registry import DeviceRegistry
from ameva_wol.scheduler import AlwaysOnScheduler, validate_interval_minutes


def test_validate_interval_minutes() -> None:
    """Test interval boundary validation."""
    assert validate_interval_minutes(1) == 1
    assert validate_interval_minutes(5) == 5
    assert validate_interval_minutes(60) == 60
    assert validate_interval_minutes(10080) == 10080

    with pytest.raises(ValueError):
        validate_interval_minutes(0)
    with pytest.raises(ValueError):
        validate_interval_minutes(10081)


@pytest.mark.asyncio
async def test_scheduler_run_cycle_sends_wol_only_when_unreachable(tmp_path: Path) -> None:
    """Test scheduler cycle pings hosts and sends WoL only for unreachable devices."""
    config = Config(
        telegram_bot_token="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken",
        allowed_user_ids={100},
        allowed_chat_ids=set(),
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
    registry = DeviceRegistry(tmp_path)

    # 1. Device A: Online host (192.168.0.10)
    dev_online = Device("online_pc", "11:11:11:11:11:11", "192.168.0.10", "192.168.0.255", 9, current_utc_iso(), current_utc_iso())
    # 2. Device B: Offline host (192.168.0.20)
    dev_offline = Device("offline_pc", "22:22:22:22:22:22", "192.168.0.20", "192.168.0.255", 9, current_utc_iso(), current_utc_iso())
    # 3. Device C: No IP configured
    dev_no_ip = Device("no_ip_pc", "33:33:33:33:33:33", None, "192.168.0.255", 9, current_utc_iso(), current_utc_iso())

    await registry.add(dev_online)
    await registry.add(dev_offline)
    await registry.add(dev_no_ip)

    scheduler = AlwaysOnScheduler(config=config, registry=registry, interval_minutes=5)

    async def mock_ping(ip: str, timeout_seconds: int = 1) -> bool:
        return ip == "192.168.0.10"  # Only online_pc returns True

    with patch("ameva_wol.scheduler.ping_host", side_effect=mock_ping):
        with patch("ameva_wol.scheduler.send_magic_packet", new_callable=AsyncMock) as mock_wol:
            mock_wol.return_value = {"success": True, "packets_sent": 3}

            await scheduler.run_cycle()

            # WoL should be transmitted ONCE for offline_pc only
            mock_wol.assert_called_once()
            call_kwargs = mock_wol.call_args[1]
            assert call_kwargs["mac"] == "22:22:22:22:22:22"
