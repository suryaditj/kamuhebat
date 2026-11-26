from analysis.market_structure import classify_structure


def evaluate_entry(
    analysis: dict,
    m5_df,
    entry_style: str = "hybrid",
    risk_reward: float = 2.0,
    sl_buffer: float = 0.5
) -> dict:
    """
    Mesin keputusan Hybrid Entry.

    EARLY:
    Zona + rejection + struktur M5 mendukung.

    CONFIRMED:
    Zona + BOS/CHoCH + displacement
    + rejection + pullback.

    Output: BUY, SELL, atau WAIT.
    """

    if entry_style not in ("hybrid", "early", "confirmed"):
        raise ValueError("Entry style tidak valid")

    if risk_reward <= 0 or sl_buffer < 0:
        raise ValueError("Parameter risk tidak valid")

    if not analysis.get("ready"):
        return wait_result("Data analisis belum siap")

    h1 = analysis["h1"]
    m15 = analysis["m15"]
    m5 = analysis["m5"]

    bias = h1["bias"]

    if bias not in ("BULLISH", "BEARISH"):
        return wait_result("Arah utama H1 belum jelas")

    direction = bias
    target_zone = m15.get("target_zone")

    if not target_zone:
        return wait_result("Belum ada zona searah H1")

    expected_zone = (
        "DEMAND" if direction == "BULLISH"
        else "SUPPLY"
    )

    if target_zone["type"] != expected_zone:
        return wait_result("Jenis zona tidak sesuai arah H1")

    # Harga M5 harus menguji zona.
    candle = m5_df.iloc[-1]

    candle_high = float(candle["high"])
    candle_low = float(candle["low"])
    entry_price = float(candle["close"])

    zone_touched = (
        candle_high >= target_zone["low"]
        and candle_low <= target_zone["high"]
    )

    if not zone_touched:
        return wait_result("Harga M5 belum menguji zona")

    # Rejection harus searah dengan bias H1.
    rejection = m5.get("rejection", {})

    rejection_valid = (
        rejection.get("rejection", False)
        and rejection.get("direction") == direction
    )

    # Struktur kecil M5.
    structure = classify_structure(m5_df)

    last_high = structure["last_high"]
    last_low = structure["last_low"]

    if direction == "BULLISH":
        structure_valid = (
            (last_high and last_high["label"] == "HH")
            or (last_low and last_low["label"] == "HL")
        )
    else:
        structure_valid = (
            (last_high and last_high["label"] == "LH")
            or (last_low and last_low["label"] == "LL")
        )

    # Konfirmasi BOS dan displacement.
    bos = m5.get("bos_choch", {})
    displacement = m5.get("displacement", {})
    pullback = m5.get("pullback") or {}

    bos_valid = (
        bos.get("event") in ("BOS", "CHOCH")
        and bos.get("direction") == direction
    )

    displacement_valid = (
        displacement.get("confirmed", False)
        and displacement.get("direction") == direction
    )

    pullback_valid = (
        pullback.get("detected", False)
        and pullback.get("held", False)
        and pullback.get("direction") == direction
    )

    # Early Entry.
    early_valid = (
        zone_touched
        and rejection_valid
        and structure_valid
    )

    # Confirmed Entry.
    confirmed_valid = (
        zone_touched
        and rejection_valid
        and bos_valid
        and displacement_valid
        and pullback_valid
    )

    entry_type = None

    if entry_style == "early" and early_valid:
        entry_type = "EARLY"

    elif entry_style == "confirmed" and confirmed_valid:
        entry_type = "CONFIRMED"

    elif entry_style == "hybrid":
        if confirmed_valid:
            entry_type = "CONFIRMED"
        elif early_valid:
            entry_type = "EARLY"

    if entry_type is None:
        return wait_result(
            "Bukti entry belum lengkap",
            {
                "zone_touched": zone_touched,
                "rejection": rejection_valid,
                "structure": structure_valid,
                "bos": bos_valid,
                "displacement": displacement_valid,
                "pullback": pullback_valid
            }
        )

    # Perhitungan SL dan TP.
    if direction == "BULLISH":
        stop_loss = target_zone["low"] - sl_buffer
        risk = entry_price - stop_loss
        take_profit = entry_price + risk * risk_reward

    else:
        stop_loss = target_zone["high"] + sl_buffer
        risk = stop_loss - entry_price
        take_profit = entry_price - risk * risk_reward

    if risk <= 0:
        return wait_result("Posisi entry tidak valid terhadap SL")

    return {
        "status": direction,
        "entry_type": entry_type,
        "entry": round(entry_price, 2),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "risk_reward": risk_reward,
        "zone": target_zone,
        "reason": (
            f"{entry_type} {direction}: harga menguji zona, "
            "rejection dan struktur mendukung"
        ),
        "evidence": {
            "zone_touched": zone_touched,
            "rejection": rejection_valid,
            "structure": structure_valid,
            "bos": bos_valid,
            "displacement": displacement_valid,
            "pullback": pullback_valid
        }
    }


def wait_result(reason: str, evidence=None) -> dict:
    return {
        "status": "WAIT",
        "entry_type": None,
        "entry": None,
        "stop_loss": None,
        "take_profit": None,
        "reason": reason,
        "evidence": evidence or {}
    }
