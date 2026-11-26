from analysis.market_structure import classify_structure


def detect_bos_choch(df):
    """
    Mendeteksi BOS dan CHoCH berdasarkan candle close.
    """

    if len(df) < 10:
        return {
            "event": None,
            "direction": None,
            "level": None,
            "reason": "Data candle belum cukup"
        }

    structure = classify_structure(df)

    trend = structure["trend"]
    last_high = structure["last_high"]
    last_low = structure["last_low"]

    if last_high is None or last_low is None:
        return {
            "event": None,
            "direction": None,
            "level": None,
            "reason": "Swing belum terbentuk"
        }

    previous_close = float(df["close"].iloc[-2])
    current_close = float(df["close"].iloc[-1])

    high_level = last_high["price"]
    low_level = last_low["price"]

    # Break ke atas
    bullish_break = (
        previous_close <= high_level
        and current_close > high_level
    )

    # Break ke bawah
    bearish_break = (
        previous_close >= low_level
        and current_close < low_level
    )

    if bullish_break:
        event = "CHOCH" if trend == "BEARISH" else "BOS"

        return {
            "event": event,
            "direction": "BULLISH",
            "level": high_level,
            "reason": (
                f"Candle close menembus swing high "
                f"di {high_level}"
            )
        }

    if bearish_break:
        event = "CHOCH" if trend == "BULLISH" else "BOS"

        return {
            "event": event,
            "direction": "BEARISH",
            "level": low_level,
            "reason": (
                f"Candle close menembus swing low "
                f"di {low_level}"
            )
        }

    return {
        "event": None,
        "direction": None,
        "level": None,
        "reason": "Belum ada BOS atau CHoCH"
    }
