import asyncio
import json
import logging
import os
import time
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
)

from config import config, validate_config
from telegram_bot.handlers import (
    analyze_command,
    button_callback,
    help_command,
    history_command,
    market_command,
    refresh_command,
    settings_command,
    start_command,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

STATE_DIR = Path("state")
OFFSET_FILE = STATE_DIR / "telegram_offset.json"
MAX_UPDATES = 100

# GitHub Actions bukan host 24/7. Setiap job melayani Telegram selama
# 180 detik, lalu keluar dengan bersih sebelum batas waktu job.
POLL_WINDOW_SECONDS = max(30, int(os.getenv("BOT_RUN_SECONDS", "180")))
POLL_TIMEOUT_SECONDS = 20


def load_offset() -> int:
    """Membaca offset update Telegram terakhir yang sudah diproses."""
    try:
        if not OFFSET_FILE.exists():
            return 0

        data = json.loads(OFFSET_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Format file offset bukan object")

        return max(0, int(data.get("offset", 0)))
    except (ValueError, TypeError, OSError, json.JSONDecodeError):
        logger.exception("Gagal membaca offset Telegram; memakai offset 0.")
        return 0


def save_offset(offset: int) -> None:
    """Menyimpan offset secara atomik agar aman jika proses terhenti."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    temporary_file = OFFSET_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps({"offset": int(offset)}),
        encoding="utf-8",
    )
    temporary_file.replace(OFFSET_FILE)


def register_handlers(application: Application) -> None:
    """Mendaftarkan seluruh command dan inline keyboard handler."""
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
        application.add_handler(CommandHandler(command, handler))

    application.add_handler(CallbackQueryHandler(button_callback))


async def poll_telegram(application: Application) -> None:
    """Long-poll Telegram sampai jendela waktu job hampir habis."""
    offset = load_offset()
    deadline = time.monotonic() + POLL_WINDOW_SECONDS
    processed_count = 0

    logger.info(
        "Long polling aktif selama maksimal %s detik; offset=%s.",
        POLL_WINDOW_SECONDS,
        offset,
    )

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        request_timeout = max(1, min(POLL_TIMEOUT_SECONDS, int(remaining)))

        try:
            updates = await application.bot.get_updates(
                offset=offset if offset > 0 else None,
                limit=MAX_UPDATES,
                timeout=request_timeout,
                read_timeout=request_timeout + 5,
                allowed_updates=Update.ALL_TYPES,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Polling Telegram gagal; mencoba lagi 5 detik.")
            await asyncio.sleep(min(5, max(0, deadline - time.monotonic())))
            continue

        if not updates:
            continue

        logger.info("Menerima %s update Telegram.", len(updates))

        for update in updates:
            logger.info("Memproses update ID %s.", update.update_id)

            # process_update menyelesaikan handler update ini sebelum offset
            # dinaikkan. Jika terjadi exception yang lolos, update tidak dilewati.
            await application.process_update(update)

            offset = update.update_id + 1
            save_offset(offset)
            processed_count += 1

            logger.info(
                "Update %s selesai; offset tersimpan=%s.",
                update.update_id,
                offset,
            )

            if time.monotonic() >= deadline:
                break

    logger.info(
        "Jendela polling selesai. Total update diproses: %s.",
        processed_count,
    )


async def run_once() -> None:
    """Menjalankan satu sesi polling Telegram untuk satu job Actions."""
    validate_config()

    if not config.telegram_chat_id:
        raise ValueError("TELEGRAM_CHAT_ID belum diisi")

    application = Application.builder().token(config.telegram_token).build()
    register_handlers(application)

    await application.initialize()
    try:
        await application.start()
        try:
            # Bot menggunakan getUpdates, sehingga webhook harus nonaktif.
            await application.bot.delete_webhook(drop_pending_updates=False)
            await poll_telegram(application)
        finally:
            await application.stop()
    finally:
        await application.shutdown()


def main() -> None:
    logger.info("HYBRID SMC HUNTER dimulai.")
    asyncio.run(run_once())
    logger.info("HYBRID SMC HUNTER selesai.")


if __name__ == "__main__":
    main()
