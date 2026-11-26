
import pandas as pd

from analysis.market_structure import classify_structure


MIN_CANDLES = 30
OHLC_COLUMNS = ("open", "high", "low", "close")


def _valid_dataframe(df):
    if not isinstance(df, pd.DataFrame):
        return False

    if len(df) < MIN_CANDLES:
        return False

    if not all(column in df.columns for column in OHLC_COLUMNS):
        return False

    data = df[list(OHLC_COLUMNS)].apply(
        pd.to_numeric, errors="coerce"
    )

    if data.isna().any().any():
        return False

    invalid = (
        (data["high"] < data["low"])
        | (data["high"] < data["open"])
        | (data["high"] < data["close"])
        | (data["low"] > data["open"])
        | (data["low"] > data["close"])
    )

    return not invalid.any()


def _get_trend(df):
    try:
        result = classify_structure(df)

        if isinstance(result, dict):
            trend = str(result.get("trend", "")).upper()

            if trend in ("BULLISH", "BEARISH", "RANGE"):
                return trend
    except Exception:
        pass

    closes = df["close"].astype(float)

    recent = closes.tail(10).mean()
    previous = closes.iloc[-20:-10].mean()

    if recent > previous:
        return "BULLISH"

    if recent < previous:
        return "BEARISH"

    return "RANGE"


def _detect_zones(df, max_zones=5):
    zones = []
    average_range = (
        df["high"] - df["low"]
    ).tail(30).mean()

    if not average_range or average_range <= 0:
        return zones

    start = max(0, len(df) - 100)

    for i in range(start, len(df) - 2):
        for base_size in (1, 2, 3):
            base_start = i
            impulse_index = i + base_size

            if impulse_index >= len(df):
                continue

            base = df.iloc[base_start:impulse_index]
            impulse = df.iloc[impulse_index]

            base_range = (
                base["high"] - base["low"]
            ).mean()

            impulse_body = abs(
                float(impulse["close"])
                - float(impulse["open"])
            )

            if base_range > average_range * 0.8:
                continue

            if impulse_body < average_range * 1.5:
                continue

            if float(impulse["close"]) > float(impulse["open"]):
                zone_type = "DEMAND"
            elif float(impulse["close"]) < float(impulse["open"]):
                zone_type = "SUPPLY"
            else:
                continue

            zones.append({
                "type": zone_type,
                "low": float(base["low"].min()),
                "high": float(base["high"].max()),
                "time": str(base.index[-1]),
                "impulse_time": str(df.index[impulse_index]),
            })

    zones.sort(
        key=lambda zone: zone["impulse_time"],
        reverse=True
    )

    unique = []

    for zone in zones:
        overlaps = any(
            zone["type"] == old["type"]
            and zone["low"] <= old["high"]
            and zone["high"] >= old["low"]
            for old in unique
        )

        if not overlaps:
            unique.append(zone)

        if len(unique) >= max_zones:
            break

    return unique


def _select_target_zone(zones, bias, price):
    expected_type = (
        "DEMAND" if bias == "BULLISH" else "SUPPLY"
    )

    candidates = [
        zone for zone in zones
        if zone["type"] == expected_type
    ]

    if not candidates:
        return None

    def distance(zone):
        if zone["low"] <= price <= zone["high"]:
            return 0

        if price < zone["low"]:
            return zone["low"] - price

        return price - zone["high"]

    return min(candidates, key=distance)


def _analyze_rejection(candle, zone):
    result = {
        "detected": False,
        "direction": None,
        "in_zone": False,
        "lower_wick": 0.0,
        "upper_wick": 0.0,
    }

    if not zone:
        return result

    open_price = float(candle["open"])
    high = float(candle["high"])
    low = float(candle["low"])
    close = float(candle["close"])

    in_zone = (
        low <= float(zone["high"])
        and high >= float(zone["low"])
    )

    result["in_zone"] = in_zone

    if not in_zone:
        return result

    body = abs(close - open_price)
    safe_body = max(body, 0.0000001)

    lower_wick = min(open_price, close) - low
    upper_wick = high - max(open_price, close)
    candle_range = max(high - low, 0.0000001)

    close_position = (close - low) / candle_range

    result["lower_wick"] = lower_wick
    result["upper_wick"] = upper_wick

    bullish_rejection = (
        lower_wick >= safe_body * 1.5
        and lower_wick > upper_wick
        and close_position >= 0.60
    )

    bearish_rejection = (
        upper_wick >= safe_body * 1.5
        and upper_wick > lower_wick
        and close_position <= 0.40
    )

    if zone["type"] == "DEMAND" and bullish_rejection:
        result["detected"] = True
        result["direction"] = "BULLISH"

    elif zone["type"] == "SUPPLY" and bearish_rejection:
        result["detected"] = True
        result["direction"] = "BEARISH"

    return result


def _detect_bos(df):
    result = {
        "event": None,
        "direction": None,
        "level": None,
        "detected": False,
    }

    if len(df) < 12:
        return result

    recent = df.tail(12)

    for i in range(1, len(recent)):
        previous = recent.iloc[:i]
        candle = recent.iloc[i]

        previous_high = float(previous["high"].max())
        previous_low = float(previous["low"].min())
        close = float(candle["close"])

        if close > previous_high:
            result = {
                "event": "BOS",
                "direction": "BULLISH",
                "level": previous_high,
                "detected": True,
            }

        elif close < previous_low:
            result = {
                "event": "BOS",
                "direction": "BEARISH",
                "level": previous_low,
                "detected": True,
            }

    return result


def _detect_displacement(df, direction):
    result = {
        "confirmed": False,
        "direction": None,
        "body": 0.0,
        "average_body": 0.0,
    }

    if len(df) < 22:
        return result

    bodies = (
        df["close"] - df["open"]
    ).abs()

    average_body = float(bodies.iloc[-21:-1].mean())

    if average_body <= 0:
        return result

    candle = df.iloc[-1]

    body = abs(
        float(candle["close"]) - float(candle["open"])
    )

    candle_range = max(
        float(candle["high"]) - float(candle["low"]),
        0.0000001
    )

    body_ratio = body / candle_range

    if direction == "BULLISH":
        correct_direction = (
            float(candle["close"]) > float(candle["open"])
        )
    elif direction == "BEARISH":
        correct_direction = (
            float(candle["close"]) < float(candle["open"])
        )
    else:
        correct_direction = False

    confirmed = (
        correct_direction
        and body >= average_body * 1.5
        and body_ratio >= 0.65
    )

    return {
        "confirmed": confirmed,
        "direction": direction if confirmed else None,
        "body": body,
        "average_body": average_body,
    }


def _detect_pullback(df, bos, direction):
    result = {
        "detected": False,
        "held": False,
        "direction": None,
        "level": bos.get("level"),
    }

    level = bos.get("level")

    if not bos.get("detected") or level is None:
        return result

    candle = df.iloc[-1]

    high = float(candle["high"])
    low = float(candle["low"])
    close = float(candle["close"])

    average_range = (
        df["high"] - df["low"]
    ).tail(20).mean()

    tolerance = max(
        float(average_range) * 0.25,
        0.0000001
    )

    touched = (
        low <= float(level) + tolerance
        and high >= float(level) - tolerance
    )

    if direction == "BULLISH":
        held = touched and close >= float(level)
    elif direction == "BEARISH":
        held = touched and close <= float(level)
    else:
        held = False

    result["detected"] = touched
    result["held"] = held
    result["direction"] = direction if held else None

    return result


def analyze_multi_timeframe(h1, m15, m5):
    if not all(
        _valid_dataframe(df)
        for df in (h1, m15, m5)
    ):
        return {
            "ready": False,
            "bias": "RANGE",
            "m15_trend": "RANGE",
            "target_zone": None,
            "current_price": None,
            "reason": "Data OHLC tidak valid atau candle kurang dari 30.",
            "h1": {},
            "m15": {},
            "m5": {},
        }

    h1_trend = _get_trend(h1)
    m15_trend = _get_trend(m15)

    current_price = float(m5["close"].iloc[-1])

    h1_zones = _detect_zones(h1)
    m15_zones = _detect_zones(m15)

    h1_target_zone = _select_target_zone(
        h1_zones,
        h1_trend,
        current_price
    ) if h1_trend in ("BULLISH", "BEARISH") else None

    m15_target_zone = _select_target_zone(
        m15_zones,
        h1_trend,
        current_price
    ) if h1_trend in ("BULLISH", "BEARISH") else None

    # Zona M15 harus searah dengan bias H1.
    # Jika zona H1 tersedia, zona M15 harus berada di dalam
    # atau beririsan dengan area zona H1.
    target_zone = m15_target_zone

    if h1_target_zone and m15_target_zone:
        overlaps_h1 = (
            m15_target_zone["low"] <= h1_target_zone["high"]
            and m15_target_zone["high"] >= h1_target_zone["low"]
        )

        if not overlaps_h1:
            target_zone = None

    last_candle = m5.iloc[-1]

    rejection = _analyze_rejection(
        last_candle,
        target_zone
    )

    bos = _detect_bos(m5)

    displacement = _detect_displacement(
        m5,
        bos.get("direction")
    )

    pullback = _detect_pullback(
        m5,
        bos,
        bos.get("direction")
    )

    ready = h1_trend in ("BULLISH", "BEARISH")

    return {
        "ready": ready,
        "bias": h1_trend,
        "m15_trend": m15_trend,
        "current_price": current_price,
        "target_zone": target_zone,
        "reason": (
            "Analisis multi-timeframe selesai."
            if ready
            else "Arah H1 belum jelas."
        ),
        "h1": {
            "bias": h1_trend,
            "trend": h1_trend,
            "zones": h1_zones,
            "target_zone": h1_target_zone,
        },
        "m15": {
            "trend": m15_trend,
            "zones": m15_zones,
            "target_zone": target_zone,
        },
        "m5": {
            "current_price": current_price,
            "rejection": {
                "rejection": rejection["detected"],
                "detected": rejection["detected"],
                "direction": rejection["direction"],
                "in_zone": rejection["in_zone"],
                "lower_wick": rejection["lower_wick"],
                "upper_wick": rejection["upper_wick"],
            },
            "bos_choch": bos,
            "displacement": displacement,
            "pullback": pullback,
        },
    }
