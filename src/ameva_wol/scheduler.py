"""Periodic Always-On host keep-alive scheduler for automated Wake-on-LAN maintenance."""

import asyncio
import logging
import time
from typing import Optional

from ameva_wol.config import Config
from ameva_wol.models import Device
from ameva_wol.ping import ping_host
from ameva_wol.registry import DeviceRegistry
from ameva_wol.wol import send_magic_packet

logger = logging.getLogger("ameva_wol.scheduler")

MIN_INTERVAL_MINUTES = 1
MAX_INTERVAL_MINUTES = 10080  # 7 days


def validate_interval_minutes(minutes: int) -> int:
    """Validate scheduler interval range.

    Raises:
        ValueError: If interval is outside allowed bounds (1 to 10080 minutes).
    """
    if not isinstance(minutes, int):
        raise ValueError("Scheduler interval must be an integer.")
    if not (MIN_INTERVAL_MINUTES <= minutes <= MAX_INTERVAL_MINUTES):
        raise ValueError(
            f"Scheduler interval '{minutes}' minutes is out of bounds. "
            f"Must be between {MIN_INTERVAL_MINUTES} and {MAX_INTERVAL_MINUTES} minutes."
        )
    return minutes


class AlwaysOnScheduler:
    """Async background task that periodically pings registered hosts and wakes offline devices."""

    def __init__(self, config: Config, registry: DeviceRegistry, interval_minutes: int = 5) -> None:
        self.config = config
        self.registry = registry
        self.interval_minutes = validate_interval_minutes(interval_minutes)
        self._cycle_lock = asyncio.Lock()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def run_cycle(self) -> None:
        """Executes a single monitoring cycle across all registered devices with overlap prevention."""
        if self._cycle_lock.locked():
            logger.warning("Scheduler cycle skipped: previous monitoring cycle is still executing.")
            return

        async with self._cycle_lock:
            start_time = time.monotonic()
            devices = await self.registry.get_all()

            if not devices:
                logger.info("Scheduler cycle: No registered devices to monitor.")
                return

            logger.info(
                f"Scheduler cycle starting: monitoring {len(devices)} device(s) "
                f"(Interval: {self.interval_minutes} min)..."
            )

            online_count = 0
            unreachable_count = 0
            wol_sent_count = 0
            skipped_count = 0

            sem = asyncio.Semaphore(5)  # Limit concurrent pings to prevent network spikes

            async def _process_device(alias: str, dev: Device) -> None:
                nonlocal online_count, unreachable_count, wol_sent_count, skipped_count

                if not dev.ip:
                    skipped_count += 1
                    logger.info(f"Scheduler: Skipping device '{alias}' (No IP configured).")
                    return

                try:
                    async with sem:
                        is_online = await ping_host(dev.ip, timeout_seconds=self.config.ping_timeout_seconds)

                    if is_online:
                        online_count += 1
                        logger.debug(f"Scheduler: Device '{alias}' ({dev.ip}) is ONLINE.")
                    else:
                        unreachable_count += 1
                        logger.warning(
                            f"Scheduler: Device '{alias}' ({dev.ip}) is UNREACHABLE. Transmitting Wake-on-LAN packets..."
                        )
                        res = await send_magic_packet(
                            mac=dev.mac,
                            broadcast=dev.broadcast,
                            port=dev.port,
                            repeat=self.config.default_wol_repeat,
                            delay_ms=self.config.default_wol_delay_ms,
                        )
                        if res["success"]:
                            wol_sent_count += 1
                        else:
                            logger.error(f"Scheduler: Failed to send WoL for '{alias}': {res.get('error')}")

                except Exception as err:
                    logger.error(f"Scheduler: Unexpected error processing device '{alias}': {err}", exc_info=True)

            # Process all devices concurrently with semaphore limiting
            await asyncio.gather(*[_process_device(alias, dev) for alias, dev in devices.items()])

            elapsed = round(time.monotonic() - start_time, 2)
            logger.info(
                f"Scheduler cycle completed in {elapsed}s: "
                f"{online_count} online, {unreachable_count} unreachable, "
                f"{wol_sent_count} WoL sent, {skipped_count} skipped without IP."
            )

    async def _loop(self) -> None:
        """Main periodic loop."""
        self._running = True
        interval_seconds = self.interval_minutes * 60

        logger.info(f"Always-On mode initialized. Interval: {self.interval_minutes} minutes ({interval_seconds}s).")

        # 1. Run first monitoring cycle immediately on startup
        try:
            await self.run_cycle()
        except Exception as err:
            logger.error(f"Error in initial scheduler cycle: {err}", exc_info=True)

        # 2. Main interval sleep loop
        while self._running:
            try:
                await asyncio.sleep(interval_seconds)
                if self._running:
                    await self.run_cycle()
            except asyncio.CancelledError:
                logger.info("Scheduler task received cancellation signal. Terminating loop.")
                break
            except Exception as err:
                logger.error(f"Error in scheduler loop iteration: {err}", exc_info=True)

    def start(self) -> asyncio.Task:
        """Start the background scheduler task."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop(), name="AlwaysOnScheduler")
        return self._task

    async def stop(self) -> None:
        """Gracefully cancel and stop the background scheduler task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Always-On scheduler stopped gracefully.")
