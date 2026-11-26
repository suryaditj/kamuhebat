import pandas as pd


def detect_swings(
    df: pd.DataFrame,
    left: int = 3,
    right: int = 3
) -> pd.DataFrame:
    """
    Mendeteksi swing high dan swing low.
    Swing baru dikonfirmasi setelah candle di sebelah kanan selesai.
    """

    if not {"high", "low"}.issubset(df.columns):
        raise ValueError("Data harus memiliki kolom high dan low")

    if left < 1 or right < 1:
        raise ValueError("left dan right minimal 1")

    result = df.copy()

    result["swing_high"] = False
    result["swing_low"] = False

    highs = result["high"].tolist()
    lows = result["low"].tolist()

    for i in range(left, len(result) - right):
        high_window = highs[i-left:i+right+1]
        low_window = lows[i-left:i+right+1]

        current_high = highs[i]
        current_low = lows[i]

        if (
            current_high == max(high_window)
            and high_window.count(current_high) == 1
        ):
            result.iloc[
                i, result.columns.get_loc("swing_high")
            ] = True

        if (
            current_low == min(low_window)
            and low_window.count(current_low) == 1
        ):
            result.iloc[
                i, result.columns.get_loc("swing_low")
            ] = True

    return result


def classify_structure(df: pd.DataFrame) -> dict:
    """
    Mengklasifikasikan swing menjadi HH, HL, LH, LL.
    """

    data = detect_swings(df)

    highs = data[data["swing_high"]]
    lows = data[data["swing_low"]]

    high_points = []
    low_points = []

    previous_high = None
    previous_low = None

    for timestamp, row in highs.iterrows():
        price = float(row["high"])

        label = None

        if previous_high is not None:
            label = "HH" if price > previous_high else "LH"

        high_points.append({
            "time": timestamp,
            "price": price,
            "label": label
        })

        previous_high = price

    for timestamp, row in lows.iterrows():
        price = float(row["low"])

        label = None

        if previous_low is not None:
            label = "HL" if price > previous_low else "LL"

        low_points.append({
            "time": timestamp,
            "price": price,
            "label": label
        })

        previous_low = price

    recent_high = high_points[-1] if high_points else None
    recent_low = low_points[-1] if low_points else None

    trend = "RANGE"

    if (
        recent_high
        and recent_low
        and recent_high["label"] == "HH"
        and recent_low["label"] == "HL"
    ):
        trend = "BULLISH"

    elif (
        recent_high
        and recent_low
        and recent_high["label"] == "LH"
        and recent_low["label"] == "LL"
    ):
        trend = "BEARISH"

    return {
        "trend": trend,
        "highs": high_points,
        "lows": low_points,
        "last_high": recent_high,
        "last_low": recent_low
    }
