import pandas as pd


def analyze_displacement(
    df: pd.DataFrame,
    lookback: int = 20,
    body_multiplier: float = 1.5,
    min_body_ratio: float = 0.65
) -> dict:
    """
    Mendeteksi candle displacement berdasarkan:
    - Body dibanding rata-rata body sebelumnya.
    - Rasio body terhadap total range.
    - Dominasi arah candle.
    """

    required = {"open", "high", "low", "close"}

    if not required.issubset(df.columns):
        raise ValueError("Kolom OHLC tidak lengkap")

    if len(df) < lookback + 1:
        return {
            "confirmed": False,
            "direction": None,
            "reason": "Data candle belum cukup"
        }

    if lookback < 2:
        raise ValueError("Lookback minimal 2")

    # Candle terakhir adalah candle yang dianalisis.
    current = df.iloc[-1]

    previous = df.iloc[-(lookback + 1):-1]

    open_price = float(current["open"])
    high = float(current["high"])
    low = float(current["low"])
    close = float(current["close"])

    body = abs(close - open_price)
    total_range = high - low

    if total_range <= 0:
        return {
            "confirmed": False,
            "direction": None,
            "reason": "Range candle tidak valid"
        }

    previous_bodies = (
        previous["close"] - previous["open"]
    ).abs()

    average_body = float(previous_bodies.mean())

    if average_body <= 0:
        return {
            "confirmed": False,
            "direction": None,
            "reason": "Rata-rata body tidak valid"
        }

    body_ratio = body / total_range
    strength = body / average_body

    if close > open_price:
        direction = "BULLISH"
    elif close < open_price:
        direction = "BEARISH"
    else:
        direction = None

    confirmed = (
        direction is not None
        and strength >= body_multiplier
        and body_ratio >= min_body_ratio
    )

    return {
        "confirmed": confirmed,
        "direction": direction if confirmed else None,
        "body": body,
        "average_body": average_body,
        "body_ratio": round(body_ratio, 3),
        "strength": round(strength, 2),
        "reason": (
            f"Displacement {direction} terdeteksi"
            if confirmed
            else "Dorongan harga belum cukup kuat"
        )
    }


def detect_displacement_sequence(
    df: pd.DataFrame,
    lookback: int = 3,
    minimum_candles: int = 2
) -> dict:
    """
    Mendeteksi rangkaian candle searah.

    Berguna untuk mengenali dorongan harga
    yang berlangsung selama beberapa candle.
    """

    required = {"open", "close"}

    if not required.issubset(df.columns):
        raise ValueError("Kolom open dan close diperlukan")

    if lookback < 1 or minimum_candles < 1:
        raise ValueError("Parameter tidak valid")

    if len(df) < lookback:
        return {
            "confirmed": False,
            "direction": None,
            "count": 0,
            "reason": "Data candle belum cukup"
        }

    recent = df.tail(lookback)

    bullish_count = 0
    bearish_count = 0

    for _, candle in recent.iterrows():

        open_price = float(candle["open"])
        close = float(candle["close"])

        if close > open_price:
            bullish_count += 1

        elif close < open_price:
            bearish_count += 1

    direction = None
    count = 0

    if bullish_count >= minimum_candles:
        direction = "BULLISH"
        count = bullish_count

    elif bearish_count >= minimum_candles:
        direction = "BEARISH"
        count = bearish_count

    confirmed = direction is not None

    return {
        "confirmed": confirmed,
        "direction": direction,
        "count": count,
        "reason": (
            f"{count} candle {direction} terdeteksi"
            if confirmed
            else "Belum ada rangkaian candle searah"
        )
    }
