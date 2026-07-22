"""Wake-on-LAN Magic Packet generator and UDP broadcast transmitter."""

import asyncio
import logging
import socket
from typing import Any, Dict

from ameva_wol.security import validate_broadcast, validate_mac

logger = logging.getLogger("ameva_wol.wol")


def create_magic_packet(mac: str) -> bytes:
    """Construct a standard 102-byte Wake-on-LAN Magic Packet.

    Magic Packet Structure:
    - 6 bytes of 0xFF (b'\\xff\\xff\\xff\\xff\\xff\\xff')
    - Target 6-byte binary MAC address repeated 16 times

    Args:
        mac: Validated or unvalidated MAC address string.

    Returns:
        102-byte payload.

    Raises:
        ValueError: If MAC address format is invalid.
    """
    normalized_mac = validate_mac(mac)
    raw_hex = normalized_mac.replace(":", "")
    mac_bytes = bytes.fromhex(raw_hex)
    
    payload = (b"\xff" * 6) + (mac_bytes * 16)
    if len(payload) != 102:
        raise ValueError(f"Magic Packet payload constructed with invalid length ({len(payload)} bytes).")
    
    return payload


async def send_magic_packet(
    mac: str,
    broadcast: str = "255.255.255.255",
    port: int = 9,
    repeat: int = 3,
    delay_ms: int = 250,
) -> Dict[str, Any]:
    """Transmits a Wake-on-LAN Magic Packet over UDP broadcast.

    Args:
        mac: Target device MAC address.
        broadcast: Broadcast IPv4 address.
        port: Target UDP port (typically 9 or 7).
        repeat: Number of packet transmissions.
        delay_ms: Delay in milliseconds between transmissions.

    Returns:
        Structured result dict with status, packet count, MAC, broadcast, and port.
    """
    norm_mac = validate_mac(mac)
    norm_broadcast = validate_broadcast(broadcast)

    if not (1 <= port <= 65535):
        raise ValueError(f"Port '{port}' must be between 1 and 65535.")
    if repeat < 1:
        raise ValueError(f"Repeat count '{repeat}' must be at least 1.")
    if delay_ms < 0:
        raise ValueError(f"Delay '{delay_ms}' cannot be negative.")

    packet = create_magic_packet(norm_mac)
    sent_count = 0

    try:
        # Create non-blocking socket for async operation
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setblocking(False)

            loop = asyncio.get_running_loop()

            for i in range(repeat):
                await loop.sock_sendto(sock, packet, (norm_broadcast, port))
                sent_count += 1
                if i < repeat - 1 and delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000.0)

        logger.info(
            f"Successfully transmitted Wake-on-LAN Magic Packet ({sent_count}/{repeat}) "
            f"for {norm_mac} to {norm_broadcast}:{port}"
        )
        return {
            "success": True,
            "mac": norm_mac,
            "broadcast": norm_broadcast,
            "port": port,
            "packets_sent": sent_count,
            "repeat": repeat,
            "delay_ms": delay_ms,
        }

    except Exception as err:
        logger.error(f"Failed to send Magic Packet to {norm_mac} ({norm_broadcast}:{port}): {err}")
        return {
            "success": False,
            "mac": norm_mac,
            "broadcast": norm_broadcast,
            "port": port,
            "packets_sent": sent_count,
            "repeat": repeat,
            "error": str(err),
        }
