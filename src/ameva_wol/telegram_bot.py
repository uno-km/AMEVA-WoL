"""Telegram bot initialization, route registration, and lifecycle management."""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ameva_wol.commands import CommandDispatcher
from ameva_wol.config import Config
from ameva_wol.registry import DeviceRegistry
from ameva_wol.security import redact_secrets

logger = logging.getLogger("ameva_wol.telegram_bot")


async def error_handler(update: Optional[object], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global Telegram error handler for uncaught exceptions during update processing."""
    token = context.application.bot.token if context.application and context.application.bot else None
    err = context.error
    
    # Redact any accidental tokens in log output
    sanitized_err = redact_secrets(str(err), token=token)
    logger.error(f"Telegram Bot exception caught handling update: {sanitized_err}", exc_info=err)

    if isinstance(update, Update) and update.effective_message:
        try:
            # Send sanitized non-technical error to Telegram user
            await update.effective_message.reply_text(
                "⚠️ An internal system error occurred while processing your command. "
                "The administrator has been notified."
            )
        except Exception:
            pass


def create_telegram_app(config: Config, registry: DeviceRegistry) -> Application:
    """Construct and configure the Telegram python-telegram-bot Application instance.

    Args:
        config: Application configuration instance.
        registry: Persistent device registry.

    Returns:
        Configured Application instance ready for initialization and long polling.
    """
    app = ApplicationBuilder().token(config.telegram_bot_token).build()

    dispatcher = CommandDispatcher(config=config, registry=registry)

    # Register command routes
    app.add_handler(CommandHandler("start", dispatcher.handle_start))
    app.add_handler(CommandHandler("how", dispatcher.handle_how))
    app.add_handler(CommandHandler("id", dispatcher.handle_id))
    app.add_handler(CommandHandler("add", dispatcher.handle_add))
    app.add_handler(CommandHandler("wake", dispatcher.handle_wake))
    app.add_handler(CommandHandler("status", dispatcher.handle_status))
    app.add_handler(CommandHandler("list", dispatcher.handle_list))
    app.add_handler(CommandHandler("remove", dispatcher.handle_remove))
    app.add_handler(CommandHandler("host", dispatcher.handle_host))
    app.add_handler(CommandHandler("test", dispatcher.handle_test))

    # Catch-all handler for unknown commands
    app.add_handler(MessageHandler(filters.COMMAND, dispatcher.handle_unknown))

    # Register global error handler
    app.add_error_handler(error_handler)

    logger.info(
        f"Initialized Telegram Bot application with {len(config.allowed_user_ids)} authorized User ID(s)."
    )
    return app
