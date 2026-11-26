import pandas as pd


def candle_body(row):
    return abs(float(row["close"]) - float(row["open"]))


def candle_range(row):
    return float(row["high"]) - float(row["low"])


def candle_direction(row):
    if row["close"] > row["open"]:
        return "BULLISH"
    if row["close"] < row["open"]:
        return "BEARISH"
    return "NEUTRAL"


def detect_zones(
    df: pd.DataFrame,
    base_min: int = 1,
    base_max: int = 3,
    impulse_multiplier: float = 1.5,
    max_zones: int = 3
) -> list:
    """
    Mendeteksi zona Supply dan Demand menggunakan pola:
    DBR, RBR, RBD, DBD.

    Zona hanya dibentuk dari base yang diikuti impulse.
    """

    required = {"open", "high", "low", "close"}

    if not required.issubset(df.columns):
        raise ValueError("Kolom OHLC tidak lengkap")

    if len(df) < base_min + 3:
        return []

    if base_min < 1 or base_max < base_min:
        raise ValueError("Parameter base tidak valid")

    ranges = [
        candle_range(row)
        for _, row in df.iterrows()
        if candle_range(row) > 0
    ]

    if not ranges:
        return []

    average_range = sum(ranges) / len(ranges)

    zones = []

    # Scan dari candle lama ke terbaru.
    for base_size in range(base_min, base_max + 1):

        for end in range(
            len(df) - base_size - 1,
            0,
            -1
        ):

            start = end - base_size + 1

            if start < 1:
                continue

            before = df.iloc[start - 1]
            base = df.iloc[start:end + 1]
            after = df.iloc[end + 1]

            before_direction = candle_direction(before)
            after_direction = candle_direction(after)

            base_ranges = [
                candle_range(row)
                for _, row in base.iterrows()
            ]

            base_average = sum(base_ranges) / len(base_ranges)

            # Base harus relatif kecil.
            if base_average >= average_range:
                continue

            impulse = candle_range(after)

            if impulse < average_range * impulse_multiplier:
                continue

            base_high = float(base["high"].max())
            base_low = float(base["low"].min())

            # Demand: DBR atau RBR
            if after_direction == "BULLISH":
                if before_direction in ("BEARISH", "BULLISH"):
                    pattern = (
                        "DBR"
                        if before_direction == "BEARISH"
                        else "RBR"
                    )

                    zones.append({
                        "type": "DEMAND",
                        "pattern": pattern,
                        "low": base_low,
                        "high": base_high,
                        "created_at": df.index[end + 1],
                        "impulse": impulse,
                        "strength": impulse / max(base_average, 0.000001)
                    })

            # Supply: RBD atau DBD
            elif after_direction == "BEARISH":
                if before_direction in ("BULLISH", "BEARISH"):
                    pattern = (
                        "RBD"
                        if before_direction == "BULLISH"
                        else "DBD"
                    )

                    zones.append({
                        "type": "SUPPLY",
                        "pattern": pattern,
                        "low": base_low,
                        "high": base_high,
                        "created_at": df.index[end + 1],
                        "impulse": impulse,
                        "strength": impulse / max(base_average, 0.000001)
                    })

    # Zona terbaru lebih diprioritaskan.
    zones.sort(
        key=lambda zone: zone["created_at"],
        reverse=True
    )

    # Hilangkan zona duplikat atau hampir sama.
    filtered = []

    for zone in zones:
        duplicate = False

        for existing in filtered:
            overlap = (
                min(zone["high"], existing["high"])
                - max(zone["low"], existing["low"])
            )

            if (
                zone["type"] == existing["type"]
                and overlap > 0
            ):
                duplicate = True
                break

        if not duplicate:
            filtered.append(zone)

        if len([
            z for z in filtered
            if z["type"] == zone["type"]
        ]) >= max_zones:
            continue

    return filtered


def price_in_zone(price: float, zone: dict) -> bool:
    return zone["low"] <= price <= zone["high"]


def zone_distance(price: float, zone: dict) -> float:
    if price < zone["low"]:
        return zone["low"] - price

    if price > zone["high"]:
        return price - zone["high"]

    return 0.0
