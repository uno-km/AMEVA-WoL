"""Unit tests for asynchronous ICMP ping reachability check."""

from unittest.mock import AsyncMock, patch
import pytest

from ameva_wol.ping import ping_host


@pytest.mark.asyncio
async def test_ping_host_online() -> None:
    """Test ping_host returns True when subprocess exit code is 0."""
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        online = await ping_host("192.168.0.100", timeout_seconds=2)
        assert online is True
        
        # Verify shell=False (arguments passed as list)
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert args[0] == "ping"
        assert "192.168.0.100" in args


@pytest.mark.asyncio
async def test_ping_host_offline() -> None:
    """Test ping_host returns False when subprocess exit code is non-zero."""
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"")
    mock_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        online = await ping_host("192.168.0.101", timeout_seconds=2)
        assert online is False


@pytest.mark.asyncio
async def test_ping_host_invalid_ip() -> None:
    """Test ping_host returns False for malformed IP address."""
    online = await ping_host("not-an-ip-address")
    assert online is False
