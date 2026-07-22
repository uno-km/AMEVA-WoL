"""Asynchronous ICMP ping utility for checking host online reachability."""

import asyncio
import logging
import sys

from ameva_wol.security import validate_ipv4

logger = logging.getLogger("ameva_wol.ping")


async def ping_host(ip: str, timeout_seconds: int = 2) -> bool:
    """Perform an asynchronous ICMP ping check against a target IPv4 address.

    Args:
        ip: Target IPv4 address.
        timeout_seconds: Hard timeout in seconds for ping command execution.

    Returns:
        True if target host responds to ping (exit code 0), False otherwise.
    """
    try:
        norm_ip = validate_ipv4(ip)
    except ValueError as err:
        logger.warning(f"Invalid IP address supplied for ping check '{ip}': {err}")
        return False

    if timeout_seconds < 1:
        timeout_seconds = 1

    # Standard Linux/Termux ping command arguments (1 packet, -W timeout in seconds)
    # On Windows (if running locally during dev), ping uses -n 1 -w <timeout_ms>
    if sys.platform == "win32":
        timeout_ms = str(timeout_seconds * 1000)
        cmd_args = ["ping", "-n", "1", "-w", timeout_ms, norm_ip]
    else:
        cmd_args = ["ping", "-c", "1", "-W", str(timeout_seconds), norm_ip]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        try:
            await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds + 1)
            is_online = (proc.returncode == 0)
            logger.debug(f"Ping check for {norm_ip}: {'ONLINE' if is_online else 'UNREACHABLE'}")
            return is_online
        except asyncio.TimeoutError:
            logger.warning(f"Ping subprocess timed out for host {norm_ip}")
            try:
                proc.kill()
            except Exception:
                pass
            return False

    except FileNotFoundError:
        logger.error("System 'ping' executable not found in PATH.")
        return False
    except Exception as err:
        logger.error(f"Unexpected error executing ping check for {norm_ip}: {err}")
        return False
