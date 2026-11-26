from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import config
from data.biquote import biquote

from analysis.multi_timeframe import analyze_multi_timeframe
from signals.entry import evaluate_entry
from signals.scoring import calculate_score

from telegram_bot.keyboards import (
    main_keyboard,
    settings_keyboard,
    back_keyboard,
    analysis_keyboard,
)

from telegram_bot.formatter import (
    format_analysis,
    format_market,
    format_error,
)


def is_authorized(update: Update) -> bool:
    """Membatasi penggunaan bot ke chat ID yang terdaftar."""
    if not config.telegram_chat_id:
        return False

    chat = update.effective_chat
    if chat is None:
        return False

    return str(chat.id) == str(config.telegram_chat_id)


async def check_access(update: Update) -> bool:
    """Memeriksa izin sebelum menjalankan perintah."""
    if is_authorized(update):
        return True

    if update.effective_message:
        await update.effective_message.reply_text(
            "Akses ditolak atau TELEGRAM_CHAT_ID belum dikonfigurasi."
        )

    return False


def run_market_analysis():
    """Mengambil candle dan menjalankan seluruh mesin analisis."""

    h1 = biquote.get_ohlc(config.timeframe_bias, limit=200)
    m15 = biquote.get_ohlc(config.timeframe_zone, limit=200)
    m5 = biquote.get_ohlc(config.timeframe_entry, limit=200)

    analysis = analyze_multi_timeframe(h1, m15, m5)

    signal = evaluate_entry(
        analysis,
        m5,
        entry_style=config.entry_style,
    )

    score = calculate_score(analysis, signal)

    return analysis, signal, score


async def send_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menjalankan analisis dan mengirim hasilnya."""

    if not await check_access(update):
        return

    message = update.effective_message

    if message:
        status_message = await message.reply_text(
            "⏳ Sedang mengambil data XAUUSD dan menganalisis market..."
        )
    else:
        status_message = None

    try:
        analysis, signal, score = run_market_analysis()

        text = format_analysis(analysis, signal, score)

        if status_message:
            await status_message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=analysis_keyboard(),
            )

    except Exception as exc:
        error_text = format_error(exc)

        if status_message:
            await status_message.edit_text(
                error_text,
                parse_mode=ParseMode.HTML,
                reply_markup=back_keyboard(),
            )


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not await check_access(update):
        return

    await update.effective_message.reply_text(
        "🦅 <b>HYBRID SMC HUNTER</b>\n\n"
        "Bot analisis XAUUSD berbasis SMC Hybrid.\n\n"
        "Pilih menu di bawah untuk memulai.",
        parse_mode=ParseMode.HTML,
        reply_markup=main_keyboard(),
    )


async def analyze_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await send_analysis(update, context)


async def refresh_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await send_analysis(update, context)


async def market_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not await check_access(update):
        return

    message = update.effective_message

    status_message = await message.reply_text(
        "⏳ Memeriksa kondisi market..."
    )

    try:
        analysis, _, _ = run_market_analysis()

        await status_message.edit_text(
            format_market(analysis),
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )

    except Exception as exc:
        await status_message.edit_text(
            format_error(exc),
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )


async def history_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not await check_access(update):
        return

    await update.effective_message.reply_text(
        "📜 Riwayat sinyal belum tersedia.\n"
        "Fitur penyimpanan riwayat akan dibuat pada tahap integrasi.",
        reply_markup=back_keyboard(),
    )


async def settings_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not await check_access(update):
        return

    await update.effective_message.reply_text(
        "⚙️ <b>PENGATURAN BOT</b>\n\n"
        f"Instrumen: {config.symbol}\n"
        f"Strategi: {config.entry_style.upper()}\n"
        f"Bias: {config.timeframe_bias}\n"
        f"Zona: {config.timeframe_zone}\n"
        f"Entry: {config.timeframe_entry}\n"
        f"Interval pemeriksaan: {config.check_interval_minutes} menit",
        parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard(),
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not await check_access(update):
        return

    await update.effective_message.reply_text(
        "📖 <b>PANDUAN HYBRID SMC HUNTER</b>\n\n"
        "/start - Menu utama\n"
        "/analisa - Analisis XAUUSD\n"
        "/refresh - Ambil data dan analisis ulang\n"
        "/market - Kondisi market\n"
        "/history - Riwayat sinyal\n"
        "/settings - Pengaturan bot\n"
        "/help - Panduan\n\n"
        "BUY dan SELL hanya muncul jika aturan entry terpenuhi. "
        "Jika belum terpenuhi, bot memberikan WAIT.",
        parse_mode=ParseMode.HTML,
        reply_markup=back_keyboard(),
    )


async def button_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Menangani semua tombol inline Telegram."""

    query = update.callback_query

    if not is_authorized(update):
        await query.answer("Akses ditolak.", show_alert=True)
        return

    await query.answer()

    action = query.data

    if action in ("analyze", "refresh"):
        await query.edit_message_text(
            "⏳ Sedang menganalisis XAUUSD..."
        )

        try:
            analysis, signal, score = run_market_analysis()

            await query.edit_message_text(
                format_analysis(analysis, signal, score),
                parse_mode=ParseMode.HTML,
                reply_markup=analysis_keyboard(),
            )

        except Exception as exc:
            await query.edit_message_text(
                format_error(exc),
                parse_mode=ParseMode.HTML,
                reply_markup=back_keyboard(),
            )

    elif action == "market":
        try:
            analysis, _, _ = run_market_analysis()

            await query.edit_message_text(
                format_market(analysis),
                parse_mode=ParseMode.HTML,
                reply_markup=back_keyboard(),
            )

        except Exception as exc:
            await query.edit_message_text(
                format_error(exc),
                parse_mode=ParseMode.HTML,
                reply_markup=back_keyboard(),
            )

    elif action == "history":
        await query.edit_message_text(
            "📜 Riwayat sinyal belum tersedia. "
            "Penyimpanan riwayat akan dibuat pada tahap integrasi.",
            reply_markup=back_keyboard(),
        )

    elif action == "settings":
        await query.edit_message_text(
            "⚙️ <b>PENGATURAN BOT</b>\n\n"
            f"Instrumen: {config.symbol}\n"
            f"Strategi: {config.entry_style.upper()}\n"
            f"Timeframe: H1 / M15 / M5\n"
            f"Interval: {config.check_interval_minutes} menit",
            parse_mode=ParseMode.HTML,
            reply_markup=settings_keyboard(),
        )

    elif action == "help":
        await query.edit_message_text(
            "📖 Gunakan tombol Analisis untuk memeriksa XAUUSD.\n\n"
            "BUY/SELL hanya diberikan jika aturan entry terpenuhi. "
            "Jika belum, keputusan tetap WAIT.",
            reply_markup=back_keyboard(),
        )

    elif action in ("symbol_info", "entry_info", "interval_info"):
        details = {
            "symbol_info": "Instrumen aktif: XAUUSD",
            "entry_info": "Strategi aktif: Hybrid Entry",
            "interval_info": (
                f"Interval pemeriksaan: "
                f"{config.check_interval_minutes} menit"
            ),
        }

        await query.edit_message_text(
            details[action],
            reply_markup=settings_keyboard(),
        )

    elif action == "main_menu":
        await query.edit_message_text(
            "🦅 <b>HYBRID SMC HUNTER</b>\n\nPilih menu:",
            parse_mode=ParseMode.HTML,
            reply_markup=main_keyboard(),
        )
