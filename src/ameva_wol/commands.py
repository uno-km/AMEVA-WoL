"""Telegram command handlers for AMEVA-WoL gateway operations."""

import asyncio
import logging
from typing import Dict, List, Optional

from telegram import Update
from telegram.ext import ContextTypes

from ameva_wol.config import Config
from ameva_wol.models import Device, current_utc_iso
from ameva_wol.ping import ping_host
from ameva_wol.registry import DeviceNotFoundError, DuplicateAliasError, DeviceRegistry
from ameva_wol.security import (
    RateLimiter,
    is_chat_authorized,
    is_user_authorized,
    redact_secrets,
    validate_alias,
    validate_broadcast,
    validate_ipv4,
    validate_mac,
)
from ameva_wol.utils import parse_telegram_command, split_message
from ameva_wol.wol import send_magic_packet
from ameva_wol.sysinfo import collect_sysinfo, run_speedtest_sync

logger = logging.getLogger("ameva_wol.commands")


class CommandDispatcher:
    """Centralized handler for all Telegram commands with auth and security enforcement."""

    def __init__(self, config: Config, registry: DeviceRegistry) -> None:
        self.config = config
        self.registry = registry
        self.rate_limiter = RateLimiter(
            max_requests=config.rate_limit_commands,
            window_seconds=config.rate_limit_window_seconds,
        )

    async def _check_auth_and_rate_limit(self, update: Update) -> bool:
        """Enforce authorization and rate limiting on incoming update.

        Returns:
            True if allowed, False if unauthorized or rate limited.
        """
        user = update.effective_user
        chat = update.effective_chat

        user_id = user.id if user else None
        chat_id = chat.id if chat else None

        if not is_user_authorized(user_id, self.config.allowed_user_ids):
            logger.warning(f"Unauthorized command attempt from user_id={user_id}, chat_id={chat_id}")
            # Silently reject unauthorized requests to prevent device discovery
            return False

        if not is_chat_authorized(chat_id, self.config.allowed_chat_ids):
            logger.warning(f"Unauthorized chat attempt from user_id={user_id}, chat_id={chat_id}")
            return False

        if user_id is not None and not self.rate_limiter.is_allowed(user_id):
            logger.warning(f"Rate limit exceeded for user_id={user_id}")
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Rate limit exceeded. Please wait a moment before sending more commands."
                )
            return False

        return True

    async def _reply_safe(self, update: Update, text: str) -> None:
        """Send message safely, redacting secrets and splitting long text if necessary."""
        if not update.effective_message:
            return
        
        sanitized = redact_secrets(text, token=self.config.telegram_bot_token)
        chunks = split_message(sanitized, max_length=4000)
        for chunk in chunks:
            await update.effective_message.reply_text(chunk)

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/start command handler."""
        if not await self._check_auth_and_rate_limit(update):
            return

        msg = (
            "[AMEVA-WoL Gateway]\n\n"
            "Status: Authorized & Operational\n\n"
            "Command Summary:\n"
            "• /wake [alias|all] - Send Wake-on-LAN packet\n"
            "• /status [alias|all] - Check reachability ping\n"
            "• /list - List registered devices\n"
            "• /add - Register a new device\n"
            "• /remove <alias> - Delete registered device\n"
            "• /id - View your Telegram User & Chat ID\n"
            "• /host - View detailed gateway system information\n"
            "• /how - Comprehensive manual & documentation\n"
        )
        await self._reply_safe(update, msg)

    async def handle_how(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/how command handler - Detailed operational manual."""
        if not await self._check_auth_and_rate_limit(update):
            return

        manual = (
            "📖 **AMEVA-WoL User Manual & Documentation**\n\n"
            "**1. What is AMEVA-WoL?**\n"
            "AMEVA-WoL is an unprivileged Wake-on-LAN gateway. It listens for Telegram commands "
            "and broadcasts UDP Magic Packets on your local network to turn on target computers.\n\n"
            "**2. Adding Devices (/add)**\n"
            "Syntax: `/add [--overwrite] <alias> <mac> [ip] [broadcast] [port]`\n"
            "• `alias`: 1-32 chars (a-z, 0-9, -, _)\n"
            "• `mac`: AA:BB:CC:DD:EE:FF or AA-BB-CC-DD-EE-FF or AABBCCDDEEFF\n"
            "• `ip`: IPv4 address (Optional, required for /status and Always-On)\n"
            "Examples:\n"
            "• `/add PC1 AA:BB:CC:DD:EE:01 192.168.0.100`\n"
            "• `/add server AABBCCDDEEFF 192.168.0.50 192.168.0.255 9`\n"
            "• `/add nas AA:BB:CC:DD:EE:03`\n"
            "• `/add --overwrite PC1 AA:BB:CC:DD:EE:99 192.168.0.105`\n\n"
            "**3. Waking Computers (/wake)**\n"
            "• `/wake`: If only 1 device registered, wakes it immediately.\n"
            "• `/wake <alias>`: Wakes the specified device.\n"
            "• `/wake all`: Broadcasts Magic Packets to ALL registered devices.\n"
            "*(Note: /wake sends UDP packets immediately without pinging first.)*\n\n"
            "**4. Checking Reachability (/status)**\n"
            "• `/status [alias|all]`: Pings target IP(s). Never sends Magic Packets.\n"
            "*(Note: Ping failure does NOT conclusively prove a computer is powered off, "
            "as OS firewalls may block ICMP requests.)*\n\n"
            "**5. Always-On Mode**\n"
            "When running with `--always-on [minutes]`, AMEVA-WoL periodically pings registered "
            "devices with IP addresses. If a host becomes unreachable, it automatically sends Wake-on-LAN packets.\n\n"
            "**6. Important Hardware & Network Notes**\n"
            "• Target computers must have **Wake-on-LAN enabled in BIOS/UEFI** and OS network driver.\n"
            "• The gateway phone/laptop and target PC generally must be connected to the **same local subnet/LAN**.\n"
            "• Wired Ethernet is strongly recommended for target PCs.\n"
            "• Running computers normally ignore incoming Magic Packets.\n"
        )
        await self._reply_safe(update, manual)

    async def handle_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/id command handler - Return user ID and chat ID for setup."""
        user = update.effective_user
        chat = update.effective_chat

        user_id = user.id if user else "Unknown"
        chat_id = chat.id if chat else "Unknown"

        msg = (
            "🆔 **Telegram Account & Chat Identifiers**\n\n"
            f"• **User ID:** `{user_id}`\n"
            f"• **Chat ID:** `{chat_id}`\n\n"
            "Use these IDs in your `.env` configuration (`ALLOWED_USER_IDS` / `ALLOWED_CHAT_IDS`)."
        )
        await self._reply_safe(update, msg)

    async def handle_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/add command handler."""
        if not await self._check_auth_and_rate_limit(update):
            return

        text = update.effective_message.text if update.effective_message else ""
        tokens = parse_telegram_command(text)
        # tokens[0] is '/add'

        args = tokens[1:]
        if not args:
            help_msg = (
                "ℹ️ **Usage: /add**\n\n"
                "**Syntax:**\n"
                "`/add <alias> <mac> <ip>`\n"
                "`/add <alias> <mac> <ip> <broadcast>`\n"
                "`/add <alias> <mac> <ip> <broadcast> <port>`\n"
                "`/add <alias> <mac>`\n"
                "`/add --overwrite <alias> <mac> <ip> [broadcast] [port]`\n\n"
                "**Parameters:**\n"
                "• `alias`: Device name (1-32 chars, a-z0-9_-)\n"
                "• `mac`: Network card MAC address (e.g. AA:BB:CC:DD:EE:FF)\n"
                "• `ip`: IPv4 address for ping status (Optional)\n"
                "• `broadcast`: IPv4 subnet broadcast address (Default: `.env` setting)\n"
                "• `port`: UDP port (Default: 9)\n\n"
                "**Examples:**\n"
                "• `/add 1070 AA:BB:CC:DD:EE:01 192.168.0.107`\n"
                "• `/add young AA-BB-CC-DD-EE-02 192.168.0.108`\n"
                "• `/add server AABBCCDDEEFF 192.168.0.50 192.168.0.255 9`\n"
                "• `/add nas AA:BB:CC:DD:EE:03`\n"
                "• `/add --overwrite young AA:BB:CC:DD:EE:22 192.168.0.122`"
            )
            await self._reply_safe(update, help_msg)
            return

        overwrite = False
        if args[0].lower() == "--overwrite":
            overwrite = True
            args = args[1:]

        if len(args) < 2:
            await self._reply_safe(update, "❌ Error: Both `<alias>` and `<mac>` are required. Type `/add` for examples.")
            return

        raw_alias, raw_mac = args[0], args[1]
        raw_ip = args[2] if len(args) >= 3 else None
        raw_broadcast = args[3] if len(args) >= 4 else self.config.default_broadcast
        raw_port = args[4] if len(args) >= 5 else str(self.config.default_wol_port)

        # Validation
        try:
            norm_alias = validate_alias(raw_alias)
            norm_mac = validate_mac(raw_mac)
            norm_ip = validate_ipv4(raw_ip) if raw_ip else None
            norm_broadcast = validate_broadcast(raw_broadcast)
            try:
                norm_port = int(raw_port)
                if not (1 <= norm_port <= 65535):
                    raise ValueError()
            except ValueError:
                await self._reply_safe(update, f"❌ Error: Invalid UDP port '{raw_port}'. Must be 1-65535.")
                return
        except ValueError as val_err:
            await self._reply_safe(update, f"❌ Validation Error: {val_err}")
            return

        now = current_utc_iso()
        device = Device(
            alias=norm_alias,
            mac=norm_mac,
            ip=norm_ip,
            broadcast=norm_broadcast,
            port=norm_port,
            created_at=now,
            updated_at=now,
        )

        try:
            await self.registry.add(device, overwrite=overwrite)
        except DuplicateAliasError:
            await self._reply_safe(
                update,
                f"⚠️ Device alias '{norm_alias}' is already registered.\n"
                f"Use `/add --overwrite {norm_alias} ...` to replace it."
            )
            return
        except Exception as err:
            logger.error(f"Error adding device '{norm_alias}': {err}", exc_info=True)
            await self._reply_safe(update, f"❌ Failed to save device: {err}")
            return

        response = [
            f"✅ **Device Registered Successfully**\n",
            f"• **Alias:** `{norm_alias}`",
            f"• **MAC:** `{norm_mac}`",
            f"• **IP:** `{norm_ip or 'Not configured'}`",
            f"• **Broadcast:** `{norm_broadcast}`",
            f"• **Port:** `{norm_port}`",
        ]
        if not norm_ip:
            response.append(
                "\n⚠️ *Note: No IP address was provided. Wake-on-LAN will work normally, "
                "but /status and Always-On health checks cannot monitor this device.*"
            )

        await self._reply_safe(update, "\n".join(response))

    async def handle_wake(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/wake command handler."""
        if not await self._check_auth_and_rate_limit(update):
            return

        text = update.effective_message.text if update.effective_message else ""
        tokens = parse_telegram_command(text)
        args = tokens[1:]

        devices = await self.registry.get_all()
        if not devices:
            await self._reply_safe(update, "⚠️ No devices registered. Use `/add` to register a computer first.")
            return

        # 1. /wake all
        if args and args[0].lower() == "all":
            results = []
            for alias, dev in devices.items():
                res = await send_magic_packet(
                    mac=dev.mac,
                    broadcast=dev.broadcast,
                    port=dev.port,
                    repeat=self.config.default_wol_repeat,
                    delay_ms=self.config.default_wol_delay_ms,
                )
                if res["success"]:
                    results.append(f"• `{alias}` ({dev.mac}): ✅ Sent ({res['packets_sent']} packets)")
                else:
                    results.append(f"• `{alias}` ({dev.mac}): ❌ Failed ({res.get('error', 'Unknown')})")

            summary = "⚡ **Wake-on-LAN Broadcast All Results:**\n\n" + "\n".join(results)
            await self._reply_safe(update, summary)
            return

        # 2. /wake with single device or multiple devices without alias
        target_dev: Optional[Device] = None

        if not args:
            if len(devices) == 1:
                target_dev = list(devices.values())[0]
            else:
                alias_list = ", ".join(f"`{a}`" for a in sorted(devices.keys()))
                await self._reply_safe(
                    update,
                    f"ℹ️ Multiple devices registered: {alias_list}\n\n"
                    "Specify which device to wake: `/wake <alias>` or `/wake all`"
                )
                return
        else:
            target_alias = args[0].strip().lower()
            target_dev = devices.get(target_alias)
            if not target_dev:
                await self._reply_safe(update, f"❌ Device alias '{target_alias}' not found. Use `/list` to view registered aliases.")
                return

        # Execute WoL send
        res = await send_magic_packet(
            mac=target_dev.mac,
            broadcast=target_dev.broadcast,
            port=target_dev.port,
            repeat=self.config.default_wol_repeat,
            delay_ms=self.config.default_wol_delay_ms,
        )

        if res["success"]:
            msg = (
                f"⚡ **Wake-on-LAN Magic Packet Sent**\n\n"
                f"• **Alias:** `{target_dev.alias}`\n"
                f"• **MAC:** `{target_dev.mac}`\n"
                f"• **Broadcast:** `{target_dev.broadcast}`\n"
                f"• **Port:** `{target_dev.port}`\n"
                f"• **Packets Sent:** {res['packets_sent']} (repeat count: {res['repeat']})"
            )
        else:
            msg = f"❌ Failed to transmit Magic Packet for `{target_dev.alias}`: {res.get('error', 'Unknown error')}"

        await self._reply_safe(update, msg)

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/status command handler."""
        if not await self._check_auth_and_rate_limit(update):
            return

        text = update.effective_message.text if update.effective_message else ""
        tokens = parse_telegram_command(text)
        args = tokens[1:]

        devices = await self.registry.get_all()
        if not devices:
            await self._reply_safe(update, "⚠️ No devices registered. Use `/add` to register a computer first.")
            return

        # 1. /status all
        if args and args[0].lower() == "all":
            await self._reply_safe(update, "🔍 Checking reachability status for all devices...")
            
            sem = asyncio.Semaphore(10)  # Concurrency limit

            async def _check_dev(alias: str, dev: Device) -> str:
                if not dev.ip:
                    return f"• `{alias}`: ❓ UNKNOWN (No IP configured)"
                async with sem:
                    online = await ping_host(dev.ip, timeout_seconds=self.config.ping_timeout_seconds)
                status_str = "🟢 ONLINE" if online else "🔴 OFFLINE / UNREACHABLE"
                return f"• `{alias}` ({dev.ip}): {status_str}"

            tasks = [_check_dev(alias, dev) for alias, dev in devices.items()]
            results = await asyncio.gather(*tasks)

            header = (
                "📊 **Device Reachability Status Summary:**\n\n"
                + "\n".join(results)
                + "\n\n_*Note: OFFLINE status means ICMP ping failed. OS firewalls may block ICMP packets._"
            )
            await self._reply_safe(update, header)
            return

        # 2. Single or default device
        target_dev: Optional[Device] = None

        if not args:
            if len(devices) == 1:
                target_dev = list(devices.values())[0]
            else:
                alias_list = ", ".join(f"`{a}`" for a in sorted(devices.keys()))
                await self._reply_safe(
                    update,
                    f"ℹ️ Multiple devices registered: {alias_list}\n\n"
                    "Specify a device: `/status <alias>` or `/status all`"
                )
                return
        else:
            target_alias = args[0].strip().lower()
            target_dev = devices.get(target_alias)
            if not target_dev:
                await self._reply_safe(update, f"❌ Device alias '{target_alias}' not found. Use `/list` to view registered aliases.")
                return

        if not target_dev.ip:
            await self._reply_safe(
                update,
                f"❓ **Status for `{target_dev.alias}`:** UNKNOWN\n"
                "Reason: No IP address is configured for this device."
            )
            return

        await self._reply_safe(update, f"🔍 Pinging `{target_dev.alias}` ({target_dev.ip})...")
        online = await ping_host(target_dev.ip, timeout_seconds=self.config.ping_timeout_seconds)

        status_badge = "🟢 ONLINE" if online else "🔴 OFFLINE / UNREACHABLE"
        msg = (
            f"📊 **Device Status: `{target_dev.alias}`**\n\n"
            f"• **IP Address:** `{target_dev.ip}`\n"
            f"• **Reachability:** {status_badge}\n\n"
            "_*Note: Failure to respond to ICMP ping does not prove the system is powered down (e.g. firewall blocking)._"
        )
        await self._reply_safe(update, msg)

    async def handle_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/list command handler."""
        if not await self._check_auth_and_rate_limit(update):
            return

        devices = await self.registry.get_all()
        if not devices:
            await self._reply_safe(update, "📋 No devices registered. Use `/add` to register your first computer.")
            return

        lines = [f"📋 **Registered Device Inventory ({len(devices)})**\n"]
        for alias in sorted(devices.keys()):
            dev = devices[alias]
            lines.append(
                f"• `{dev.alias}`\n"
                f"  - MAC: `{dev.mac}`\n"
                f"  - IP: `{dev.ip or 'Not configured'}`\n"
                f"  - Broadcast: `{dev.broadcast}:{dev.port}`"
            )

        await self._reply_safe(update, "\n".join(lines))

    async def handle_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/remove command handler."""
        if not await self._check_auth_and_rate_limit(update):
            return

        text = update.effective_message.text if update.effective_message else ""
        tokens = parse_telegram_command(text)
        args = tokens[1:]

        if not args:
            await self._reply_safe(update, "ℹ️ Usage: `/remove <alias>`\nExample: `/remove server`")
            return

        target_alias = args[0]
        try:
            removed_dev = await self.registry.remove(target_alias)
            await self._reply_safe(update, f"🗑️ Device `{removed_dev.alias}` ({removed_dev.mac}) removed from registry.")
        except DeviceNotFoundError:
            await self._reply_safe(update, f"❌ No device found with alias '{target_alias}'. Use `/list` to view registered aliases.")
        except Exception as err:
            logger.error(f"Error removing device '{target_alias}': {err}", exc_info=True)
            await self._reply_safe(update, f"❌ Failed to remove device: {err}")

    async def handle_host(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/host command handler to display system info."""
        if not await self._check_auth_and_rate_limit(update):
            return

        if not update.effective_message:
            return

        # 1. Send initial report without speedtest (fast)
        initial_report = await collect_sysinfo(include_speedtest=False)
        msg_obj = await update.effective_message.reply_text(initial_report)

        # 2. Run speedtest in background thread
        try:
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as pool:
                speed_result = await loop.run_in_executor(pool, run_speedtest_sync)
            
            # 3. Re-generate report with speedtest results and edit the message
            final_report = initial_report.replace("`⏳ Measuring...`", f"`{speed_result}`")
            await msg_obj.edit_text(final_report)
        except Exception as e:
            logger.error(f"Error running speedtest: {e}")
            final_report = initial_report.replace("`⏳ Measuring...`", f"`Failed: {e}`")
            await msg_obj.edit_text(final_report)

    async def handle_unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for unrecognized commands."""
        if not await self._check_auth_and_rate_limit(update):
            return

        await self._reply_safe(
            update,
            "❓ Unknown command. Type `/how` to view the comprehensive manual or `/start` for quick help."
        )
