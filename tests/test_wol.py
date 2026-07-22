"""Unit tests for Wake-on-LAN Magic Packet generation and UDP transmission."""

import socket
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from ameva_wol.wol import create_magic_packet, send_magic_packet


def test_create_magic_packet_exact_byte_structure() -> None:
    """Test that create_magic_packet generates an exact 102-byte payload."""
    mac = "AA:BB:CC:DD:EE:FF"
    packet = create_magic_packet(mac)

    assert len(packet) == 102
    # First 6 bytes must be 0xFF
    assert packet[:6] == b"\xff" * 6

    # Target 6-byte MAC sequence
    expected_mac_bytes = bytes.fromhex("AABBCCDDEEFF")
    assert len(expected_mac_bytes) == 6

    # Verify all 16 repeated MAC blocks
    for i in range(16):
        start = 6 + (i * 6)
        end = start + 6
        assert packet[start:end] == expected_mac_bytes


def test_create_magic_packet_invalid_mac() -> None:
    """Test that invalid MAC addresses raise ValueError."""
    with pytest.raises(ValueError):
        create_magic_packet("INVALID_MAC")


@pytest.mark.asyncio
async def test_send_magic_packet_mocked_socket() -> None:
    """Test send_magic_packet executes socket sendto repeat times with SO_BROADCAST set."""
    mac = "11:22:33:44:55:66"
    broadcast = "192.168.1.255"
    port = 9
    repeat = 3
    delay_ms = 10

    mock_sock = MagicMock()
    mock_sock.__enter__.return_value = mock_sock

    with patch("socket.socket", return_value=mock_sock):
        with patch("asyncio.get_running_loop") as mock_loop_getter:
            mock_loop = AsyncMock()
            mock_loop_getter.return_value = mock_loop

            res = await send_magic_packet(
                mac=mac,
                broadcast=broadcast,
                port=port,
                repeat=repeat,
                delay_ms=delay_ms,
            )

            assert res["success"] is True
            assert res["packets_sent"] == 3
            assert res["mac"] == "11:22:33:44:55:66"

            # Check socket options were set
            mock_sock.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            # Check loop.sock_sendto called repeat times
            assert mock_loop.sock_sendto.call_count == 3
