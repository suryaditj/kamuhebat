import pandas as pd


def analyze_rejection(
    candle: pd.Series,
    min_wick_ratio: float = 1.5,
    min_body_ratio: float = 0.10
) -> dict:
    """
    Mendeteksi penolakan harga berdasarkan panjang wick,
    ukuran body, dan posisi penutupan candle.
    """

    open_price = float(candle["open"])
    high = float(candle["high"])
    low = float(candle["low"])
    close = float(candle["close"])

    total_range = high - low

    if total_range <= 0:
        return {
            "rejection": False,
            "direction": None,
            "reason": "Candle tidak memiliki range"
        }

    body = abs(close - open_price)
    upper_wick = high - max(open_price, close)
    lower_wick = min(open_price, close) - low

    body_ratio = body / total_range

    if body_ratio < min_body_ratio:
        return {
            "rejection": False,
            "direction": None,
            "reason": "Body terlalu kecil atau doji"
        }

    bullish = (
        lower_wick >= body * min_wick_ratio
        and close > low + total_range * 0.60
    )

    bearish = (
        upper_wick >= body * min_wick_ratio
        and close < low + total_range * 0.40
    )

    if bullish and not bearish:
        return {
            "rejection": True,
            "direction": "BULLISH",
            "wick_ratio": lower_wick / max(body, 0.000001),
            "reason": "Ekor bawah panjang dan harga ditutup dekat bagian atas"
        }

    if bearish and not bullish:
        return {
            "rejection": True,
            "direction": "BEARISH",
            "wick_ratio": upper_wick / max(body, 0.000001),
            "reason": "Ekor atas panjang dan harga ditutup dekat bagian bawah"
        }

    return {
        "rejection": False,
        "direction": None,
        "reason": "Belum ada penolakan yang jelas"
    }


def detect_repeated_rejection(
    df: pd.DataFrame,
    level: float,
    direction: str,
    tolerance: float,
    lookback: int = 10,
    min_touches: int = 2
) -> dict:
    """
    Mencari penolakan berulang di sekitar level harga.

    direction:
    BEARISH = penolakan dari atas (resistance/supply)
    BULLISH = penolakan dari bawah (support/demand)
    """

    direction = direction.upper()

    if direction not in ("BULLISH", "BEARISH"):
        raise ValueError("Direction harus BULLISH atau BEARISH")

    if tolerance <= 0 or min_touches < 1:
        raise ValueError("Tolerance dan min_touches tidak valid")

    if len(df) == 0:
        return {
            "confirmed": False,
            "touches": 0,
            "direction": direction,
            "reason": "Data candle kosong"
        }

    recent = df.tail(lookback)

    touches = []

    for timestamp, candle in recent.iterrows():

        rejection = analyze_rejection(candle)

        if not rejection["rejection"]:
            continue

        if rejection["direction"] != direction:
            continue

        if direction == "BEARISH":
            touched = (
                float(candle["high"]) >= level - tolerance
                and float(candle["high"]) <= level + tolerance
            )
        else:
            touched = (
                float(candle["low"]) >= level - tolerance
                and float(candle["low"]) <= level + tolerance
            )

        if touched:
            touches.append({
                "time": timestamp,
                "price": (
                    float(candle["high"])
                    if direction == "BEARISH"
                    else float(candle["low"])
                )
            })

    confirmed = len(touches) >= min_touches

    return {
        "confirmed": confirmed,
        "touches": len(touches),
        "direction": direction,
        "level": level,
        "touch_details": touches,
        "reason": (
            f"{len(touches)} penolakan ditemukan di sekitar level"
            if confirmed
            else "Jumlah penolakan belum mencukupi"
        )
    }


def rejection_at_zone(
    candle: pd.Series,
    zone: dict
) -> dict:
    """
    Memeriksa apakah candle menunjukkan penolakan
    sesuai jenis zona Supply atau Demand.
    """

    result = analyze_rejection(candle)

    if not result["rejection"]:
        return result

    high = float(candle["high"])
    low = float(candle["low"])

    touched = (
        high >= zone["low"]
        and low <= zone["high"]
    )

    expected_direction = (
        "BEARISH"
        if zone["type"] == "SUPPLY"
        else "BULLISH"
    )

    confirmed = (
        touched
        and result["direction"] == expected_direction
    )

    return {
        **result,
        "zone_touched": touched,
        "confirmed": confirmed,
        "reason": (
            "Rejection sesuai arah zona"
            if confirmed
            else "Rejection belum sesuai zona"
        )
    }
