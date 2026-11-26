from math import floor


def calculate_risk_amount(balance: float, risk_percent: float) -> float:
    """Menghitung nominal uang yang siap dirisikokan."""
    if balance <= 0:
        raise ValueError("Balance harus lebih dari 0")

    if not 0 < risk_percent <= 100:
        raise ValueError("Risk percent harus di antara 0 dan 100")

    return balance * (risk_percent / 100)


def calculate_position_size(
    balance: float,
    risk_percent: float,
    entry: float,
    stop_loss: float,
    tick_size: float,
    tick_value_per_lot: float,
    min_lot: float = 0.01,
    max_lot: float = 100.0,
    lot_step: float = 0.01,
) -> dict:
    """
    Menghitung ukuran lot berdasarkan nilai tick dari broker.

    tick_value_per_lot harus menggunakan mata uang akun.
    Jangan gunakan hasil jika spesifikasi kontrak broker belum diketahui.
    """
    values = [
        balance, entry, stop_loss, tick_size,
        tick_value_per_lot, min_lot, max_lot, lot_step
    ]

    if any(value <= 0 for value in values):
        raise ValueError("Semua nilai harus lebih dari 0")

    if min_lot > max_lot:
        raise ValueError("min_lot tidak boleh lebih besar dari max_lot")

    if abs(entry - stop_loss) == 0:
        raise ValueError("Entry dan Stop Loss tidak boleh sama")

    risk_amount = calculate_risk_amount(balance, risk_percent)
    price_distance = abs(entry - stop_loss)

    loss_per_lot = (
        price_distance / tick_size
    ) * tick_value_per_lot

    raw_lot = risk_amount / loss_per_lot

    # Pembulatan ke bawah mengikuti lot step broker.
    lot = floor(raw_lot / lot_step) * lot_step
    lot = round(lot, 8)

    if lot < min_lot:
        return {
            "valid": False,
            "reason": "Lot hasil perhitungan di bawah minimum broker",
            "risk_amount": round(risk_amount, 2),
            "recommended_lot": None,
        }

    lot = min(lot, max_lot)

    estimated_loss = loss_per_lot * lot

    return {
        "valid": True,
        "risk_amount": round(risk_amount, 2),
        "recommended_lot": lot,
        "estimated_loss": round(estimated_loss, 2),
        "price_distance": round(price_distance, 5),
    }


def validate_trade(
    direction: str,
    entry: float,
    stop_loss: float,
    take_profit: float,
    minimum_rr: float = 1.5,
) -> dict:
    """Memvalidasi posisi dan menghitung Risk/Reward."""

    direction = direction.upper()

    if direction not in ("BUY", "SELL"):
        return {"valid": False, "reason": "Arah transaksi tidak valid"}

    if min(entry, stop_loss, take_profit) <= 0:
        return {"valid": False, "reason": "Harga harus lebih dari 0"}

    if minimum_rr <= 0:
        return {"valid": False, "reason": "Minimum RR tidak valid"}

    if direction == "BUY":
        if not stop_loss < entry < take_profit:
            return {
                "valid": False,
                "reason": "Susunan harga BUY tidak valid",
            }

    else:
        if not take_profit < entry < stop_loss:
            return {
                "valid": False,
                "reason": "Susunan harga SELL tidak valid",
            }

    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)
    rr = reward / risk

    if rr < minimum_rr:
        return {
            "valid": False,
            "reason": f"RR terlalu kecil: 1:{rr:.2f}",
            "risk_reward": round(rr, 2),
        }

    return {
        "valid": True,
        "risk": round(risk, 5),
        "reward": round(reward, 5),
        "risk_reward": round(rr, 2),
    }
