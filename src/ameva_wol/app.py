"""Application runner and lifecycle management for AMEVA-WoL."""

import asyncio
import logging
import signal
import sys
from typing import Optional

from ameva_wol.config import Config, ConfigurationError
from ameva_wol.locking import InstanceLock, InstanceLockError
from ameva_wol.logging_config import setup_logging
from ameva_wol.registry import DeviceRegistry
from ameva_wol.scheduler import AlwaysOnScheduler
from ameva_wol.telegram_bot import create_telegram_app

logger = logging.getLogger("ameva_wol.app")


async def main_async(always_on: bool = False, interval_minutes: int = 5) -> int:
    """Async main application runner."""
    # 1. Load Configuration
    try:
        config = Config.load()
    except ConfigurationError as err:
        print(f"Configuration Error: {err}", file=sys.stderr)
        return 1

    # 2. Setup Logging
    setup_logging(
        log_level=config.log_level,
        data_dir=config.data_dir,
        bot_token=config.telegram_bot_token,
    )
    logger.info(f"Starting AMEVA-WoL Gateway (Log Level: {config.log_level})...")

    # 3. Acquire Single-Instance Lock
    lock = InstanceLock(config.data_dir)
    try:
        lock.acquire()
        logger.info(f"Acquired single-instance lock on '{config.data_dir}'.")
    except InstanceLockError as err:
        logger.error(f"Failed to acquire instance lock: {err}")
        return 1

    # 4. Initialize Device Registry
    registry = DeviceRegistry(config.data_dir)
    try:
        devices = await registry.load()
        logger.info(f"Loaded device registry ({len(devices)} device(s) registered).")
    except Exception as err:
        logger.error(f"Failed to load device registry: {err}")
        lock.release()
        return 1

    # 5. Build Telegram Application
    tg_app = create_telegram_app(config, registry)

    # 6. Initialize Always-On Scheduler if requested
    scheduler: Optional[AlwaysOnScheduler] = None
    if always_on:
        scheduler = AlwaysOnScheduler(
            config=config,
            registry=registry,
            interval_minutes=interval_minutes,
        )

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Received termination signal (SIGINT/SIGTERM). Initiating graceful shutdown...")
        stop_event.set()

    # Register OS Signal Handlers if supported on current platform/thread
    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                pass

    try:
        # Start Telegram Application polling
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.updater.start_polling(
            poll_interval=1.0,
            timeout=config.telegram_poll_timeout_seconds,
            drop_pending_updates=True,
        )
        logger.info("Telegram Bot long polling started successfully.")

        # Start background scheduler task if enabled
        if scheduler:
            scheduler.start()
            logger.info(f"Always-On scheduler active (Interval: {interval_minutes} minutes).")

        print(f"AMEVA-WoL Gateway running in {'Always-On' if always_on else 'Default'} mode. Press Ctrl+C to exit.")

        # Wait for shutdown signal
        await stop_event.wait()

    except asyncio.CancelledError:
        logger.info("Main loop task cancelled.")
    except Exception as err:
        logger.error(f"Unhandled exception in main application loop: {err}", exc_info=True)
    finally:
        logger.info("Shutting down AMEVA-WoL components...")
        
        if scheduler:
            await scheduler.stop()

        try:
            if tg_app.updater and tg_app.updater.running:
                await tg_app.updater.stop()
            if tg_app.running:
                await tg_app.stop()
            await tg_app.shutdown()
        except Exception as err:
            logger.warning(f"Error shutting down Telegram application: {err}")

        lock.release()
        logger.info("AMEVA-WoL Gateway shutdown complete.")

    return 0


def run_app(always_on: bool = False, interval_minutes: int = 5) -> int:
    """Synchronous launcher wrapper for main_async."""
    try:
        return asyncio.run(main_async(always_on=always_on, interval_minutes=interval_minutes))
    except KeyboardInterrupt:
        print("\nProcess interrupted. Exiting.")
        return 0
