from html import escape


def format_price(value):
    """Format harga agar konsisten."""
    if value is None:
        return "-"

    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "-"


def format_analysis(analysis, signal, score=None):
    """Menyusun hasil analisis menjadi pesan Telegram."""

    status = str(signal.get("status", "WAIT")).upper()

    if status == "BULLISH":
        decision = "🟢 BUY"
    elif status == "BEARISH":
        decision = "🔴 SELL"
    else:
        decision = "🟡 WAIT"

    bias = str(analysis.get("bias", "UNKNOWN")).upper()
    zone = analysis.get("target_zone") or {}

    entry = signal.get("entry")
    stop_loss = signal.get("stop_loss")
    take_profit = signal.get("take_profit")
    reason = signal.get("reason", "Belum ada konfirmasi entry.")

    zone_type = zone.get("type", "-")
    zone_low = format_price(zone.get("low"))
    zone_high = format_price(zone.get("high"))

    lines = [
        "🦅 <b>HYBRID SMC HUNTER</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"Instrumen: <b>XAUUSD</b>",
        f"Keputusan: <b>{decision}</b>",
        f"Arah H1: <b>{escape(bias)}</b>",
        "",
        "📍 <b>AREA SUPPLY / DEMAND</b>",
        f"Jenis: {escape(str(zone_type))}",
        f"Zona: {zone_low} - {zone_high}",
        "",
        "🎯 <b>RENCANA ENTRY</b>",
        f"Entry: <b>{format_price(entry)}</b>",
        f"Stop Loss: <b>{format_price(stop_loss)}</b>",
        f"Take Profit: <b>{format_price(take_profit)}</b>",
    ]

    if score is not None:
        score_value = score.get("score", score) if isinstance(score, dict) else score
        lines.extend([
            "",
            f"📊 Skor konfluensi: <b>{escape(str(score_value))}</b>",
        ])

    lines.extend([
        "",
        "📝 <b>ALASAN ANALISIS</b>",
        escape(str(reason)),
        "",
        "━━━━━━━━━━━━━━━━━━",
        "⚠️ Analisis bersifat informatif, bukan jaminan profit.",
    ])

    return "\n".join(lines)


def format_market(analysis):
    """Menyusun ringkasan kondisi pasar."""

    bias = str(analysis.get("bias", "UNKNOWN")).upper()
    structure = str(analysis.get("m15_trend", "UNKNOWN")).upper()
    price = format_price(analysis.get("current_price"))

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
