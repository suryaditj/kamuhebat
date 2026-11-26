
from html import escape


def format_price(value):
    """Format harga agar konsisten."""

    if value is None:
        return "-"

    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "-"


def normalize_status(status):
    """Menyamakan format status sinyal."""

    status = str(status or "WAIT").upper()

    mapping = {
        "BULLISH": "BUY",
        "BEARISH": "SELL",
        "BUY": "BUY",
        "SELL": "SELL",
        "WAIT": "WAIT",
    }

    return mapping.get(status, "WAIT")


def format_analysis(analysis, signal, score=None):
    """Menyusun hasil analisis menjadi pesan Telegram."""

    status = normalize_status(
        signal.get("status", "WAIT")
    )

    decisions = {
        "BUY": "🟢 BUY",
        "SELL": "🔴 SELL",
        "WAIT": "🟡 WAIT",
    }

    decision = decisions[status]

    bias = str(
        analysis.get("bias", "UNKNOWN")
    ).upper()

    zone = analysis.get("target_zone") or {}

    entry = signal.get("entry")
    stop_loss = signal.get("stop_loss")
    take_profit = signal.get("take_profit")

    reason = signal.get(
        "reason",
        "Belum ada konfirmasi entry.",
    )

    zone_type = escape(str(zone.get("type", "-")))
    zone_low = format_price(zone.get("low"))
    zone_high = format_price(zone.get("high"))

    lines = [
        "🦅 <b>HYBRID SMC HUNTER</b>",
        "━━━━━━━━━━━━━━━━━━",
        "Instrumen: <b>XAUUSD</b>",
        f"Keputusan: <b>{decision}</b>",
        f"Arah H1: <b>{escape(bias)}</b>",
        "",
        "📍 <b>AREA SUPPLY / DEMAND</b>",
        f"Jenis: {zone_type}",
        f"Zona: {zone_low} - {zone_high}",
        "",
        "🎯 <b>RENCANA ENTRY</b>",
        f"Entry: <b>{format_price(entry)}</b>",
        f"Stop Loss: <b>{format_price(stop_loss)}</b>",
        f"Take Profit: <b>{format_price(take_profit)}</b>",
    ]

    if score is not None:
        if isinstance(score, dict):
            score_value = score.get("score", "-")
            category = score.get("category")
        else:
            score_value = score
            category = None

        lines.extend([
            "",
            f"📊 Skor konfluensi: "
            f"<b>{escape(str(score_value))}</b>",
        ])

        if category:
            lines.append(
                f"Kategori: <b>{escape(str(category))}</b>"
            )

    lines.extend([
        "",
        "📝 <b>ALASAN ANALISIS</b>",
        escape(str(reason)),
        "",
        "━━━━━━━━━━━━━━━━━━",
        "⚠️ Analisis bersifat informatif, "
        "bukan jaminan profit.",
    ])

    return "\n".join(lines)


def format_market(analysis):
    """Menyusun ringkasan kondisi pasar."""

    bias = str(
        analysis.get("bias", "UNKNOWN")
    ).upper()

    structure = str(
        analysis.get("m15_trend", "UNKNOWN")
    ).upper()

    price = format_price(
        analysis.get("current_price")
    )

    return "\n".join([
        "📊 <b>KONDISI MARKET XAUUSD</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"Harga terakhir: <b>{price}</b>",
        f"Bias H1: <b>{escape(bias)}</b>",
        f"Struktur M15: <b>{escape(structure)}</b>",
        "━━━━━━━━━━━━━━━━━━",
    ])


def format_error(message):
    """Menyusun pesan kesalahan."""

    return (
        "⚠️ <b>TERJADI KESALAHAN</b>\n\n"
        f"{escape(str(message))}"
    )
