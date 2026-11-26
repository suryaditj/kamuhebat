import pandas as pd


def detect_pullback(
    df: pd.DataFrame,
    level: float,
    direction: str,
    tolerance: float,
    lookback: int = 10
) -> dict:
    """
    Mendeteksi pullback ke level BOS atau area penting.

    BULLISH:
    Harga sebelumnya bergerak di atas level,
    lalu kembali menguji level.

    BEARISH:
    Harga sebelumnya bergerak di bawah level,
    lalu kembali menguji level.
    """

    direction = direction.upper()

    if direction not in ("BULLISH", "BEARISH"):
        raise ValueError("Direction tidak valid")

    if tolerance <= 0:
        raise ValueError("Tolerance harus lebih dari 0")

    if len(df) < 3:
        return {
            "detected": False,
            "direction": direction,
            "reason": "Data candle belum cukup"
        }

    recent = df.tail(lookback + 1)

    previous = recent.iloc[:-1]
    current = recent.iloc[-1]

    previous_close = float(previous["close"].iloc[-1])

    current_high = float(current["high"])
    current_low = float(current["low"])
    current_close = float(current["close"])

    if direction == "BULLISH":
        moved_away = previous_close > level + tolerance
        retested = (
            current_low <= level + tolerance
            and current_high >= level - tolerance
        )
        held = current_close >= level

    else:
        moved_away = previous_close < level - tolerance
        retested = (
            current_high >= level - tolerance
            and current_low <= level + tolerance
        )
        held = current_close <= level

    detected = moved_away and retested

    return {
        "detected": detected,
        "held": detected and held,
        "direction": direction,
        "level": level,
        "current_close": current_close,
        "reason": (
            "Pullback terdeteksi dan level masih bertahan"
            if detected and held
            else "Pullback terdeteksi tetapi level belum bertahan"
            if detected
            else "Belum ada pullback yang valid"
        )
    }


def detect_zone_pullback(
    df: pd.DataFrame,
    zone: dict,
    direction: str
) -> dict:
    """
    Mendeteksi harga kembali memasuki zona Supply/Demand.
    """

    direction = direction.upper()

    if direction not in ("BULLISH", "BEARISH"):
        raise ValueError("Direction tidak valid")

    if len(df) == 0:
        return {
            "detected": False,
            "reason": "Data candle kosong"
        }

    current = df.iloc[-1]

    high = float(current["high"])
    low = float(current["low"])
    close = float(current["close"])

    touched = (
        high >= zone["low"]
        and low <= zone["high"]
    )

    expected_zone = (
        "DEMAND" if direction == "BULLISH"
        else "SUPPLY"
    )

    correct_zone = zone["type"] == expected_zone

    return {
        "detected": touched and correct_zone,
        "direction": direction,
        "zone_type": zone["type"],
        "zone_low": zone["low"],
        "zone_high": zone["high"],
        "current_close": close,
        "reason": (
            "Harga kembali menguji zona yang sesuai"
            if touched and correct_zone
            else "Harga belum menguji zona yang sesuai"
        )
    }


def is_entry_too_late(
    current_price: float,
    entry_level: float,
    max_distance: float
) -> bool:
    """
    Mencegah entry ketika harga sudah terlalu jauh
    dari level rencana.
    """

    if max_distance <= 0:
        raise ValueError("max_distance harus lebih dari 0")

    return abs(current_price - entry_level) > max_distance
