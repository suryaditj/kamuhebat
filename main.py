
import asyncio
import json
import logging
from pathlib import Path

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

STATE_DIR = Path("state")
OFFSET_FILE = STATE_DIR / "telegram_offset.json"

MAX_UPDATES = 100


def load_offset():
    """Membaca offset terakhir."""
    try:
        if OFFSET_FILE.exists():
            data = json.loads(
                OFFSET_FILE.read_text(encoding="utf-8")
            )
            return max(0, int(data.get("offset", 0)))

    except (ValueError, OSError, json.JSONDecodeError):
        logger.exception("Gagal membaca offset Telegram.")

    return 0


def save_offset(offset):
    """Menyimpan offset secara atomik."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    temporary_file = OFFSET_FILE.with_suffix(".tmp")

    temporary_file.write_text(
        json.dumps({"offset": offset}),
        encoding="utf-8",
    )

    temporary_file.replace(OFFSET_FILE)


def register_handlers(application):
    """Mendaftarkan perintah Telegram."""

    commands = {
        "start": start_command,
        "analisa": analyze_command,
        "refresh": refresh_command,
        "market": market_command,
        "history": history_command,
        "settings": settings_command,
        "help": help_command,
    }

    for command, handler in commands.items():
        application.add_handler(
            CommandHandler(command, handler)
        )

    application.add_handler(
        CallbackQueryHandler(button_callback)
    )


async def run_once():
    """Memproses update Telegram dalam satu eksekusi."""

    validate_config()

    if not config.telegram_chat_id:
        raise ValueError("TELEGRAM_CHAT_ID belum diisi")

    application = (
        Application.builder()
        .token(config.telegram_token)
        .build()
    )

    register_handlers(application)

    await application.initialize()
    await application.start()

    try:
        await application.bot.delete_webhook(
            drop_pending_updates=False
        )

        offset = load_offset()

        updates = await application.bot.get_updates(
            offset=offset if offset > 0 else None,
            limit=MAX_UPDATES,
            timeout=0,
            allowed_updates=Update.ALL_TYPES,
        )

        if not updates:
            logger.info("Tidak ada update baru.")
            return

        logger.info(
            "Ditemukan %s update Telegram.",
            len(updates),
        )

        for update in updates:
            try:
                logger.info(
                    "Memproses update ID %s",
                    update.update_id,
                )

                await application.process_update(update)

                # Simpan posisi setelah handler selesai dipanggil.
                offset = update.update_id + 1
                save_offset(offset)

                logger.info(
                    "Offset tersimpan: %s",
                    offset,
                )

            except Exception:
                logger.exception(
                    "Gagal memproses update ID %s",
                    update.update_id,
                )

                # Hentikan proses agar update berikutnya
                # tidak melewati update yang gagal.
                break

    finally:
        await application.stop()
        await application.shutdown()


def main():
    logger.info("HYBRID SMC HUNTER dimulai.")

    asyncio.run(run_once())

    logger.info("HYBRID SMC HUNTER selesai.")


if __name__ == "__main__":
    main()
