"""Command-line interface (CLI) argument parser and management utilities for AMEVA-WoL."""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Optional

from ameva_wol import __version__
from ameva_wol.config import Config, ConfigurationError
from ameva_wol.locking import InstanceLock, InstanceLockError
from ameva_wol.registry import DeviceRegistry
from ameva_wol.scheduler import validate_interval_minutes
from ameva_wol.security import redact_secrets


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="ameva-wol",
        description="AMEVA-WoL: Lightweight, secure Telegram-controlled Wake-on-LAN gateway.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m ameva_wol                        # Run in default Telegram-only mode\n"
            "  python -m ameva_wol --always-on            # Run Always-On mode with 5-minute interval\n"
            "  python -m ameva_wol --always-on 15         # Run Always-On mode with 15-minute interval\n"
            "  python -m ameva_wol --check-config         # Validate configuration and data files\n"
            "  python -m ameva_wol --list-devices         # Print registered devices to console\n"
        ),
    )

    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "--always-on",
        nargs="?",
        const=5,
        type=int,
        metavar="MINUTES",
        help="Enable Always-On periodic ping & auto-wake mode (default interval: 5 minutes).",
    )

    parser.add_argument(
        "--interval",
        type=int,
        metavar="MINUTES",
        help="Explicit alternative syntax for specifying Always-On interval in minutes.",
    )

    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate configuration, environment secrets, data directory, and exit.",
    )

    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Display all currently registered devices from the data directory and exit.",
    )

    return parser


async def run_check_config() -> int:
    """Perform comprehensive diagnostic verification of environment and storage.

    Returns:
        0 on clean success, 1 on validation error.
    """
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("🔍 AMEVA-WoL Configuration & Environment Check")
    print("=" * 50)

    # 1. Load Configuration
    try:
        cfg = Config.load()
        print("✅ Environment Configuration: VALID")
        redacted_token = redact_secrets(cfg.telegram_bot_token, token=cfg.telegram_bot_token)
        print(f"   • Bot Token: {redacted_token[:10]}... [Redacted]")
        print(f"   • Allowed User IDs: {sorted(list(cfg.allowed_user_ids))}")
        print(f"   • Allowed Chat IDs: {sorted(list(cfg.allowed_chat_ids)) if cfg.allowed_chat_ids else 'Disabled (All chats)'}")
        print(f"   • Default Broadcast: {cfg.default_broadcast}")
        print(f"   • Default WoL Port: {cfg.default_wol_port}")
        print(f"   • Log Level: {cfg.log_level}")
        print(f"   • Data Directory: {cfg.data_dir}")
    except ConfigurationError as err:
        print(f"❌ Environment Configuration ERROR: {err}")
        return 1
    except Exception as err:
        print(f"❌ Unexpected Error Loading Config: {err}")
        return 1

    # 2. Data Directory & Locking Check
    try:
        lock = InstanceLock(cfg.data_dir)
        lock.acquire()
        lock.release()
        print("✅ Data Directory & Instance Lock: OK")
    except InstanceLockError as err:
        print(f"❌ Instance Lock Check ERROR: {err}")
        return 1
    except Exception as err:
        print(f"❌ Data Directory Permission ERROR: {err}")
        return 1

    # 3. Registry JSON Check
    try:
        registry = DeviceRegistry(cfg.data_dir)
        devices = await registry.get_all()
        print(f"✅ Device Registry: OK ({len(devices)} device(s) registered)")
        for alias, dev in devices.items():
            print(f"   • `{alias}` -> MAC: {dev.mac}, IP: {dev.ip or 'None'}, Broadcast: {dev.broadcast}:{dev.port}")
    except Exception as err:
        print(f"❌ Device Registry Read ERROR: {err}")
        return 1

    print("=" * 50)
    print("🎉 All diagnostic checks passed successfully!")
    return 0


async def run_list_devices() -> int:
    """Read and display registered devices to stdout."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    try:
        cfg = Config.load()
        registry = DeviceRegistry(cfg.data_dir)
        devices = await registry.get_all()

        if not devices:
            print("No devices currently registered.")
            return 0

        print(f"Registered Devices ({len(devices)}):")
        for alias in sorted(devices.keys()):
            dev = devices[alias]
            print(f" - Alias:     {dev.alias}")
            print(f"   MAC:       {dev.mac}")
            print(f"   IP:        {dev.ip or 'Not configured'}")
            print(f"   Broadcast: {dev.broadcast}")
            print(f"   Port:      {dev.port}")
            print(f"   Updated:   {dev.updated_at}")
            print()
        return 0
    except Exception as err:
        print(f"Error listing devices: {err}", file=sys.stderr)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint function."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.check_config:
        return asyncio.run(run_check_config())

    if args.list_devices:
        return asyncio.run(run_list_devices())

    # Resolve Always-On interval from --always-on or --interval
    always_on_enabled = False
    interval_minutes = 5

    if args.interval is not None:
        always_on_enabled = True
        interval_minutes = args.interval
    elif args.always_on is not None:
        always_on_enabled = True
        interval_minutes = args.always_on

    if always_on_enabled:
        try:
            interval_minutes = validate_interval_minutes(interval_minutes)
        except ValueError as err:
            print(f"Error: {err}", file=sys.stderr)
            return 1

    # Import app inside main execution path
    from ameva_wol.app import run_app

    try:
        return run_app(always_on=always_on_enabled, interval_minutes=interval_minutes)
    except KeyboardInterrupt:
        print("\nShutdown requested by user. Exiting cleanly.")
        return 0
    except Exception as err:
        print(f"Fatal Application Error: {err}", file=sys.stderr)
        return 1
