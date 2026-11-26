
from math import isfinite

from analysis.market_structure import classify_structure


VALID_STYLES = ("hybrid", "early", "confirmed")


def wait_result(reason: str, evidence=None) -> dict:
    return {
        "status": "WAIT",
        "direction": None,
        "entry_type": None,
        "entry": None,
        "stop_loss": None,
        "take_profit": None,
        "risk_reward": None,
        "zone": None,
        "reason": reason,
        "evidence": evidence or {},
    }


def normalize_number(value):
    try:
        number = float(value)
        if isfinite(number):
            return number
    except (TypeError, ValueError):
        pass

    return None


def evaluate_entry(
    analysis: dict,
    m5_df,
    entry_style: str = "hybrid",
    risk_reward: float = 2.0,
    sl_buffer: float = 0.5,
) -> dict:
    """
    Hybrid Entry:
    H1 = arah utama.
    M15 = zona supply/demand.
    M5 = konfirmasi entry.

    EARLY:
    Zona + rejection + struktur M5.

    CONFIRMED:
    Zona + rejection + BOS/CHoCH
    + displacement + pullback.
    """

    if entry_style not in VALID_STYLES:
        raise ValueError("Entry style tidak valid")

    if (
        not isfinite(risk_reward)
        or not isfinite(sl_buffer)
        or risk_reward <= 0
        or sl_buffer < 0
    ):
        raise ValueError("Parameter risk tidak valid")

    if not isinstance(analysis, dict):
        return wait_result("Format analisis tidak valid")

    if not analysis.get("ready"):
        return wait_result("Data analisis belum siap")

    if m5_df is None or len(m5_df) < 10:
        return wait_result("Data candle M5 tidak mencukupi")

    required_columns = {"open", "high", "low", "close"}

    if not required_columns.issubset(m5_df.columns):
        return wait_result("Kolom OHLC M5 tidak lengkap")

    h1 = analysis.get("h1") or {}
    m15 = analysis.get("m15") or {}
    m5 = analysis.get("m5") or {}

    bias = h1.get("bias")

    if bias not in ("BULLISH", "BEARISH"):
        return wait_result("Arah utama H1 belum jelas")

    direction = bias

    # ==========================================
    # 1. VALIDASI ZONA M15
    # ==========================================

    target_zone = m15.get("target_zone")

    if not isinstance(target_zone, dict):
        return wait_result("Belum ada zona M15")

    expected_zone = (
        "DEMAND" if direction == "BULLISH"
        else "SUPPLY"
    )

    if target_zone.get("type") != expected_zone:
        return wait_result("Zona tidak searah dengan H1")

    zone_low = normalize_number(target_zone.get("low"))
    zone_high = normalize_number(target_zone.get("high"))

    if (
        zone_low is None
        or zone_high is None
        or zone_low >= zone_high
    ):
        return wait_result("Batas zona tidak valid")

    # ==========================================
    # 2. VALIDASI CANDLE M5
    # ==========================================

    candle = m5_df.iloc[-1]

    candle_high = normalize_number(candle["high"])
    candle_low = normalize_number(candle["low"])
    entry_price = normalize_number(candle["close"])

    if (
        candle_high is None
        or candle_low is None
        or entry_price is None
        or candle_high < candle_low
        or not candle_low <= entry_price <= candle_high
    ):
        return wait_result("Candle M5 tidak valid")

    zone_touched = (
        candle_high >= zone_low
        and candle_low <= zone_high
    )

    if not zone_touched:
        return wait_result("Harga M5 belum menguji zona")

    # ==========================================
    # 3. REJECTION M5
    # ==========================================

    rejection = m5.get("rejection") or {}

    rejection_valid = (
        rejection.get("rejection") is True
        and rejection.get("direction") == direction
    )

    # ==========================================
    # 4. STRUKTUR M5
    # ==========================================

    try:
        structure = classify_structure(m5_df)
    except (KeyError, IndexError, TypeError, ValueError):
        return wait_result("Struktur M5 gagal dianalisis")

    last_high = structure.get("last_high")
    last_low = structure.get("last_low")

    if direction == "BULLISH":
        structure_valid = (
            bool(last_high and last_high.get("label") == "HH")
            and bool(last_low and last_low.get("label") == "HL")
        )
    else:
        structure_valid = (
            bool(last_high and last_high.get("label") == "LH")
            and bool(last_low and last_low.get("label") == "LL")
        )

    # ==========================================
    # 5. BOS / DISPLACEMENT / PULLBACK
    # ==========================================

    bos = m5.get("bos_choch") or {}
    displacement = m5.get("displacement") or {}
    pullback = m5.get("pullback") or {}

    bos_valid = (
        bos.get("event") in ("BOS", "CHOCH")
        and bos.get("direction") == direction
    )

    displacement_valid = (
        displacement.get("confirmed") is True
        and displacement.get("direction") == direction
    )

    pullback_valid = (
        pullback.get("detected") is True
        and pullback.get("held") is True
        and pullback.get("direction") == direction
    )

    evidence = {
        "zone_touched": zone_touched,
        "rejection": rejection_valid,
        "structure": structure_valid,
        "bos": bos_valid,
        "displacement": displacement_valid,
        "pullback": pullback_valid,
    }

    # ==========================================
    # 6. HYBRID ENTRY DECISION
    # ==========================================

    early_valid = (
        zone_touched
        and rejection_valid
        and structure_valid
    )

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

    # ==========================================
    # 7. DIAGNOSIS WAIT
    # ==========================================

    if entry_type is None:
        early_requirements = {
            "zona tersentuh": zone_touched,
            "rejection": rejection_valid,
            "struktur M5": structure_valid,
        }

        confirmed_requirements = {
            "zona tersentuh": zone_touched,
            "rejection": rejection_valid,
            "BOS/CHoCH": bos_valid,
            "displacement": displacement_valid,
            "pullback": pullback_valid,
        }

        early_missing = [
            name
            for name, valid in early_requirements.items()
            if not valid
        ]

        confirmed_missing = [
            name
            for name, valid in confirmed_requirements.items()
            if not valid
        ]

        evidence["early_missing"] = early_missing
        evidence["confirmed_missing"] = confirmed_missing

        if entry_style == "early":
            reason = (
                "EARLY belum lengkap: "
                + ", ".join(early_missing)
            )

        elif entry_style == "confirmed":
            reason = (
                "CONFIRMED belum lengkap: "
                + ", ".join(confirmed_missing)
            )

        else:
            reason = (
                "EARLY belum lengkap: "
                + ", ".join(early_missing)
                + " | CONFIRMED belum lengkap: "
                + ", ".join(confirmed_missing)
            )

        return wait_result(reason, evidence)

    # ==========================================
    # 8. STOP LOSS
    # ==========================================

    if direction == "BULLISH":
        stop_loss = zone_low - sl_buffer
        risk = entry_price - stop_loss
    else:
        stop_loss = zone_high + sl_buffer
        risk = stop_loss - entry_price

    if risk <= 0:
        return wait_result(
            "Harga entry sudah melewati batas SL",
            evidence,
        )

    # ==========================================
    # 9. TAKE PROFIT
    # ==========================================

    if direction == "BULLISH":
        take_profit = entry_price + risk * risk_reward
        status = "BUY"

        if not stop_loss < entry_price < take_profit:
            return wait_result("Posisi BUY tidak valid", evidence)

    else:
        take_profit = entry_price - risk * risk_reward
        status = "SELL"

        if not take_profit < entry_price < stop_loss:
            return wait_result("Posisi SELL tidak valid", evidence)

    # ==========================================
    # 10. FINAL RESULT
    # ==========================================

    return {
        "status": status,
        "direction": direction,
        "entry_type": entry_type,
        "entry": round(entry_price, 2),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "risk_reward": risk_reward,
        "zone": target_zone,
        "reason": (
            f"{entry_type} {status}: "
            "zona, rejection, dan konfirmasi struktur "
            "memenuhi aturan entry."
        ),
        "evidence": evidence,
    }
