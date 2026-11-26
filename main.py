import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from config import config, validate_config

from telegram_bot.handlers import (
    start_command,
    analyze_command,
    refresh_command,
    market_command,
    history_command,
    settings_command,
    help_command,
    button_callback,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


async def error_handler(update, context):
    """Mencatat error tanpa membocorkan detail internal ke pengguna."""
    logger.error(
        "Terjadi error saat memproses update",
        exc_info=context.error,
    )


def create_application():
    """Membuat aplikasi Telegram dan mendaftarkan handler."""

    validate_config()

    if not config.telegram_chat_id:
        raise ValueError("TELEGRAM_CHAT_ID belum diisi")

    application = (
        Application.builder()
        .token(config.telegram_token)
        .build()
    )

    # Perintah Telegram
    application.add_handler(
        CommandHandler("start", start_command)
    )

    application.add_handler(
        CommandHandler("analisa", analyze_command)
    )

    application.add_handler(
        CommandHandler("refresh", refresh_command)
    )

    application.add_handler(
        CommandHandler("market", market_command)
    )

    application.add_handler(
        CommandHandler("history", history_command)
    )

    application.add_handler(
        CommandHandler("settings", settings_command)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    # Tombol inline
    application.add_handler(
        CallbackQueryHandler(button_callback)
    )

    # Penanganan error
    application.add_error_handler(error_handler)

    return application


def main():
    """Menjalankan bot."""

    try:
        application = create_application()

        logger.info("HYBRID SMC HUNTER sedang dijalankan...")

        application.run_polling(
            allowed_updates=Update.ALL_TYPES
        )

    except Exception:
        logger.exception("Bot gagal dijalankan")
        raise


if __name__ == "__main__":
    main()
