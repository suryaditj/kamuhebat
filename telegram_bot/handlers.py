
import asyncio
import logging

from telegram import Update
from telegram.error import BadRequest, NetworkError, TimedOut
from telegram.ext import ContextTypes

from config import config
from data.biquote import biquote

from analysis.multi_timeframe import analyze_multi_timeframe
from signals.entry import evaluate_entry
from signals.scoring import calculate_score

from data.history import (
    create_signal_record,
    add_signal_record,
    get_recent_history,
)

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


logger = logging.getLogger(__name__)


# ==================================================
# AUTHORIZATION
# ==================================================

def is_authorized(update: Update) -> bool:
    """Memastikan hanya chat yang diizinkan dapat memakai bot."""

    if not config.telegram_chat_id:
        logger.error("TELEGRAM_CHAT_ID belum dikonfigurasi.")
        return False

    chat = update.effective_chat

    if chat is None:
        return False

    return str(chat.id) == str(config.telegram_chat_id)


async def reject_unauthorized(update: Update):
    """Memberi tahu pengguna yang tidak memiliki akses."""

    message = update.effective_message

    if message:
        await message.reply_text(
            "Akses ditolak. Bot ini bersifat pribadi."
        )


# ==================================================
# MARKET ANALYSIS
# ==================================================

def run_market_analysis():
    """
    Mengambil data H1, M15, M5 lalu menjalankan
    analisis SMC Hybrid.
    """

    h1 = biquote.get_ohlc(
        config.timeframe_bias,
        limit=150,
    )

    m15 = biquote.get_ohlc(
        config.timeframe_zone,
        limit=150,
    )

    m5 = biquote.get_ohlc(
        config.timeframe_entry,
        limit=200,
    )

    if h1.empty or m15.empty or m5.empty:
        raise RuntimeError("Data candle tidak mencukupi.")

    # Candle terakhir yang diterima sudah difilter
    # sebagai candle tertutup oleh BiQuoteClient.
    candle_time = m5.index[-1].isoformat()

    analysis = analyze_multi_timeframe(
        h1,
        m15,
        m5,
    )

    if not isinstance(analysis, dict):
        raise RuntimeError(
            "Hasil analisis multi-timeframe tidak valid."
        )

    # Simpan informasi candle M5 untuk riwayat.
    analysis["candle_time"] = candle_time
    analysis["current_price"] = float(m5["close"].iloc[-1])

    signal = evaluate_entry(
        analysis,
        m5,
        entry_style=config.entry_style,
    )

    score = calculate_score(
        analysis,
        signal,
    )

    return analysis, signal, score


# ==================================================
# SIGNAL HISTORY
# ==================================================

def extract_score_value(score):
    """Mengambil angka skor dari hasil scoring."""

    if isinstance(score, dict):
        return score.get("score")

    return score


def save_analysis_history(analysis, signal, score):
    """Menyimpan hasil analisis ke riwayat."""

    status = str(
        signal.get("status", "WAIT")
    ).upper()

    if status not in ("BUY", "SELL", "WAIT"):
        status = "WAIT"

    candle_time = analysis.get("candle_time")

    if not candle_time:
        raise ValueError(
            "Waktu candle M5 tidak tersedia. "
            "Riwayat tidak disimpan."
        )

    record = create_signal_record(
        symbol=config.symbol,
        status=status,
        timeframe=config.timeframe_entry,
        candle_time=candle_time,
        entry=signal.get("entry"),
        stop_loss=signal.get("stop_loss"),
        take_profit=signal.get("take_profit"),
        score=extract_score_value(score),
        reason=signal.get("reason", ""),
    )

    return add_signal_record(record)


# ==================================================
# ANALYSIS RESPONSE
# ==================================================

async def send_analysis(update: Update):
    """Menjalankan analisis dan mengirim hasil ke Telegram."""

    message = update.effective_message

    if message is None:
        return

    status_message = await message.reply_text(
        "🔎 Sedang menganalisis XAUUSD...\n"
        "Mohon tunggu."
    )

    try:
        analysis, signal, score = await asyncio.to_thread(
            run_market_analysis
        )

        saved = save_analysis_history(
            analysis,
            signal,
            score,
        )

        result = format_analysis(
            analysis,
            signal,
            score,
        )

        if not saved:
            logger.info(
                "Riwayat sinyal sudah tersimpan sebelumnya."
            )

        await status_message.edit_text(
            result,
            parse_mode="HTML",
            reply_markup=analysis_keyboard(),
        )

    except Exception as exc:
        logger.exception("Analisis gagal.")

        await status_message.edit_text(
            format_error(str(exc))
        )


# ==================================================
# START COMMAND
# ==================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    message = update.effective_message

    await message.reply_text(
        "🤖 <b>HYBRID SMC HUNTER</b>\n\n"
        "Instrumen: XAUUSD\n"
        "Strategi: SMC Hybrid\n"
        "Timeframe: H1 / M15 / M5\n"
        "Data: BiQuote\n\n"
        "Pilih menu di bawah untuk memulai.",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


# ==================================================
# ANALYZE COMMAND
# ==================================================

async def analyze_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    await send_analysis(update)


# ==================================================
# REFRESH COMMAND
# ==================================================

async def refresh_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    await send_analysis(update)


# ==================================================
# MARKET COMMAND
# ==================================================

async def market_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    message = update.effective_message

    status_message = await message.reply_text(
        "📊 Mengambil kondisi pasar..."
    )

    try:
        analysis, signal, score = await asyncio.to_thread(
            run_market_analysis
        )

        result = format_market(analysis)

        await status_message.edit_text(
            result,
            parse_mode="HTML",
            reply_markup=back_keyboard(),
        )

    except Exception as exc:
        logger.exception("Gagal mengambil kondisi pasar.")

        await status_message.edit_text(
            format_error(str(exc))
        )


# ==================================================
# HISTORY COMMAND
# ==================================================

async def history_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    history = get_recent_history(limit=10)

    if not history:
        await update.effective_message.reply_text(
            "📚 <b>RIWAYAT SINYAL</b>\n\n"
            "Belum ada riwayat analisis.",
            parse_mode="HTML",
            reply_markup=back_keyboard(),
        )
        return

    lines = [
        "📚 <b>RIWAYAT SINYAL XAUUSD</b>",
        "",
    ]

    emoji_map = {
        "BUY": "🟢",
        "SELL": "🔴",
        "WAIT": "🟡",
    }

    for index, item in enumerate(history, start=1):
        status = item.get("status", "WAIT")
        emoji = emoji_map.get(status, "⚪")

        lines.extend([
            f"{index}. {emoji} <b>{status}</b>",
            f"Entry: {item.get('entry') if item.get('entry') is not None else '-'}",
            f"SL: {item.get('stop_loss') if item.get('stop_loss') is not None else '-'}",
            f"TP: {item.get('take_profit') if item.get('take_profit') is not None else '-'}",
            f"Score: {item.get('score') if item.get('score') is not None else '-'}",
            f"Waktu: {item.get('timestamp', '-')}",
            "",
        ])

    await update.effective_message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )


# ==================================================
# SETTINGS COMMAND
# ==================================================

async def settings_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    text = (
        "⚙️ <b>PENGATURAN BOT</b>\n\n"
        f"Instrumen: {config.symbol}\n"
        f"Entry style: {config.entry_style.upper()}\n"
        f"Timeframe bias: {config.timeframe_bias}\n"
        f"Timeframe zona: {config.timeframe_zone}\n"
        f"Timeframe entry: {config.timeframe_entry}\n"
        f"Interval workflow: {config.check_interval_minutes} menit\n"
        f"Risiko konfigurasi: {config.max_risk_percent}%\n\n"
        "Pengaturan saat ini hanya dapat dilihat."
    )

    await update.effective_message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=settings_keyboard(),
    )


# ==================================================
# HELP COMMAND
# ==================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    text = (
        "📖 <b>PANDUAN BOT</b>\n\n"
        "/start - Menu utama\n"
        "/analisa - Analisis XAUUSD\n"
        "/refresh - Analisis ulang\n"
        "/market - Kondisi pasar\n"
        "/history - Riwayat sinyal\n"
        "/settings - Pengaturan\n"
        "/help - Panduan\n\n"
        "<b>Strategi:</b>\n"
        "H1 menentukan arah utama.\n"
        "M15 menentukan struktur dan zona.\n"
        "M5 mencari konfirmasi entry.\n\n"
        "<b>Entry Hybrid:</b>\n"
        "Early Entry dan Confirmed Entry.\n\n"
        "Bot hanya memberikan analisis dan sinyal. "
        "Tidak melakukan transaksi otomatis."
    )

    await update.effective_message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )


# ==================================================
# INLINE BUTTON CALLBACK
# ==================================================

async def button_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    if not is_authorized(update):
        try:
            await query.answer(
                "Akses ditolak.",
                show_alert=True,
            )
        except (BadRequest, TimedOut, NetworkError):
            logger.warning(
                "Gagal menjawab callback pengguna tidak sah."
            )
        return

    # Callback lama mungkin sudah kedaluwarsa karena
    # GitHub Actions tidak berjalan terus-menerus.
    try:
        await query.answer()
    except (BadRequest, TimedOut, NetworkError):
        logger.warning(
            "Callback sudah kedaluwarsa atau gagal dijawab."
        )

    action = query.data

    try:
        if action in ("analyze", "refresh"):
            await send_analysis(update)

        elif action == "market":
            await market_command(update, context)

        elif action == "history":
            await history_command(update, context)

        elif action == "settings":
            await settings_command(update, context)

        elif action == "help":
            await help_command(update, context)

        elif action == "main_menu":
            await query.message.reply_text(
                "🤖 <b>HYBRID SMC HUNTER</b>\n\n"
                "Silakan pilih menu.",
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )

        elif action == "symbol_info":
            await query.message.reply_text(
                f"Instrumen aktif: {config.symbol}",
                reply_markup=back_keyboard(),
            )

        elif action == "entry_info":
            await query.message.reply_text(
                f"Strategi entry: {config.entry_style.upper()}",
                reply_markup=back_keyboard(),
            )

        elif action == "interval_info":
            await query.message.reply_text(
                f"Interval pemeriksaan: "
                f"{config.check_interval_minutes} menit",
                reply_markup=back_keyboard(),
            )

        else:
            await query.message.reply_text(
                "Perintah tombol tidak dikenali.",
                reply_markup=main_keyboard(),
            )

    except Exception:
        logger.exception(
            "Gagal memproses tombol: %s",
            action,
        )

        if query.message:
            await query.message.reply_text(
                "Terjadi kesalahan saat memproses permintaan. "
                "Silakan coba lagi nanti."
            )
