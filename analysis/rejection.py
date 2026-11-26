
import pandas as pd


def analyze_rejection(
    candle: pd.Series,
    min_wick_ratio: float = 1.5,
    min_body_ratio: float = 0.10
) -> dict:
    """Mendeteksi rejection berdasarkan wick dan posisi penutupan."""

    try:
        open_price = float(candle["open"])
        high = float(candle["high"])
        low = float(candle["low"])
        close = float(candle["close"])
    except (KeyError, TypeError, ValueError):
        return {
            "rejection": False,
            "direction": None,
            "reason": "Data candle tidak valid"
        }

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
            "reason": "Ekor bawah panjang dan penutupan dekat bagian atas"
        }

    if bearish and not bullish:
        return {
            "rejection": True,
            "direction": "BEARISH",
            "wick_ratio": upper_wick / max(body, 0.000001),
            "reason": "Ekor atas panjang dan penutupan dekat bagian bawah"
        }

    return {
        "rejection": False,
        "direction": None,
        "reason": "Belum ada penolakan yang jelas"
    }


def rejection_at_zone(
    candle: pd.Series,
    zone: dict
) -> dict:
    """Memastikan rejection terjadi pada zona yang sesuai."""

    if not isinstance(zone, dict):
        return {
            "rejection": False,
            "confirmed": False,
            "zone_touched": False,
            "direction": None,
            "reason": "Zona tidak valid"
        }

    result = analyze_rejection(candle)

    try:
        high = float(candle["high"])
        low = float(candle["low"])
        zone_low = float(zone["low"])
        zone_high = float(zone["high"])
    except (KeyError, TypeError, ValueError):
        return {
            **result,
            "confirmed": False,
            "zone_touched": False,
            "reason": "Data zona atau candle tidak valid"
        }

    touched = high >= zone_low and low <= zone_high

    expected_direction = (
        "BULLISH" if zone.get("type") == "DEMAND"
        else "BEARISH" if zone.get("type") == "SUPPLY"
        else None
    )

    confirmed = (
        touched
        and result["rejection"]
        and result["direction"] == expected_direction
    )

    return {
        **result,
        "zone_touched": touched,
        "confirmed": confirmed,
        "reason": (
            "Rejection valid pada zona"
            if confirmed
            else "Rejection belum memenuhi syarat zona"
        )
    }


def analyze_recent_zone_rejection(
    df: pd.DataFrame,
    zone: dict,
    lookback: int = 5
) -> dict:
    """
    Memeriksa rejection pada beberapa candle terakhir.

    Candle terakhir dianggap candle berjalan jika kolom isOpen
    tersedia dan bernilai True, sehingga tidak ikut diperiksa.
    """

    empty_result = {
        "rejection": False,
        "detected": False,
        "direction": None,
        "in_zone": False,
        "candle_time": None,
        "reason": "Belum ada rejection valid"
    }

    if (
        not isinstance(df, pd.DataFrame)
        or df.empty
        or not isinstance(zone, dict)
        or lookback < 1
    ):
        return empty_result

    closed_df = df.copy()

    if "isOpen" in closed_df.columns:
        is_open = (
            closed_df["isOpen"]
            .astype(str)
            .str.lower()
            .isin(("true", "1", "yes"))
        )
        closed_df = closed_df.loc[~is_open]

    recent = closed_df.tail(lookback)

    if recent.empty:
        return empty_result

    for timestamp, candle in reversed(list(recent.iterrows())):
        result = rejection_at_zone(candle, zone)

        if result.get("confirmed"):
            return {
                "rejection": True,
                "detected": True,
                "direction": result["direction"],
                "in_zone": True,
                "candle_time": str(timestamp),
                "reason": result["reason"]
            }

    return {
        **empty_result,
        "in_zone": any(
            rejection_at_zone(candle, zone).get("zone_touched", False)
            for _, candle in recent.iterrows()
        ),
        "reason": "Tidak ditemukan rejection valid pada candle tertutup terakhir"
    }


def detect_repeated_rejection(
    df: pd.DataFrame,
    level: float,
    direction: str,
    tolerance: float,
    lookback: int = 10,
    min_touches: int = 2
) -> dict:
    """Mendeteksi rejection berulang di sekitar level."""

    direction = direction.upper()

    if direction not in ("BULLISH", "BEARISH"):
        raise ValueError("Direction harus BULLISH atau BEARISH")

    if tolerance <= 0 or min_touches < 1 or lookback < 1:
        raise ValueError("Parameter tidak valid")

    if not isinstance(df, pd.DataFrame) or df.empty:
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

        price = (
            float(candle["high"])
            if direction == "BEARISH"
            else float(candle["low"])
        )

        if abs(price - level) <= tolerance:
            touches.append({
                "time": str(timestamp),
                "price": price
            })

    confirmed = len(touches) >= min_touches

    return {
        "confirmed": confirmed,
        "touches": len(touches),
        "direction": direction,
        "level": level,
        "touch_details": touches,
        "reason": (
            f"{len(touches)} rejection ditemukan"
            if confirmed
            else "Jumlah rejection belum mencukupi"
        )
    }
