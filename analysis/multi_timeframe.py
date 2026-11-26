from analysis.market_structure import classify_structure
from analysis.bos_choch import detect_bos_choch
from analysis.supply_demand import detect_zones, price_in_zone
from analysis.rejection import analyze_rejection
from analysis.displacement import analyze_displacement
from analysis.pullback import detect_zone_pullback


def get_market_bias(df):
    structure = classify_structure(df)

    return {
        "bias": structure["trend"],
        "last_high": structure["last_high"],
        "last_low": structure["last_low"]
    }


def find_nearest_zone(zones, price, direction=None):
    candidates = zones

    if direction:
        candidates = [
            z for z in zones
            if z["type"] == direction
        ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda z: (
            0 if price_in_zone(price, z)
            else min(
                abs(price - z["low"]),
                abs(price - z["high"])
            )
        )
    )


def analyze_multi_timeframe(h1, m15, m5):
    """
    Menggabungkan analisis H1, M15, dan M5.

    Output bukan sinyal entry final.
    Keputusan entry akan dibuat oleh signals/entry.py.
    """

    for name, df in [
        ("H1", h1),
        ("M15", m15),
        ("M5", m5)
    ]:
        if df is None or len(df) < 30:
            return {
                "ready": False,
                "status": "WAIT",
                "reason": f"Data {name} belum cukup"
            }

    # 1. Arah utama H1
    h1_analysis = get_market_bias(h1)
    h1_bias = h1_analysis["bias"]

    # 2. Struktur M15
    m15_structure = classify_structure(m15)
    m15_bos = detect_bos_choch(m15)

    m15_price = float(m15["close"].iloc[-1])

    m15_zones = detect_zones(
        m15,
        max_zones=3
    )

    demand_zone = find_nearest_zone(
        m15_zones,
        m15_price,
        "DEMAND"
    )

    supply_zone = find_nearest_zone(
        m15_zones,
        m15_price,
        "SUPPLY"
    )

    # Zona yang searah dengan bias H1.
    target_zone = None

    if h1_bias == "BULLISH":
        target_zone = demand_zone

    elif h1_bias == "BEARISH":
        target_zone = supply_zone

    # 3. Kondisi M5
    m5_price = float(m5["close"].iloc[-1])

    m5_bos = detect_bos_choch(m5)

    m5_rejection = analyze_rejection(
        m5.iloc[-1]
    )

    m5_displacement = analyze_displacement(
        m5,
        lookback=20
    )

    m5_pullback = None

    if target_zone:
        direction = (
            "BULLISH"
            if h1_bias == "BULLISH"
            else "BEARISH"
        )

        m5_pullback = detect_zone_pullback(
            m5,
            target_zone,
            direction
        )

    # 4. Pemeriksaan posisi harga terhadap zona
    in_demand = (
        price_in_zone(m15_price, demand_zone)
        if demand_zone else False
    )

    in_supply = (
        price_in_zone(m15_price, supply_zone)
        if supply_zone else False
    )

    # 5. Ringkasan kondisi pasar
    if h1_bias == "RANGE":
        status = "WAIT"
        reason = "Arah utama H1 belum jelas"

    elif m15_structure["trend"] == "RANGE":
        status = "WAIT"
        reason = "Struktur M15 masih sideways"

    elif target_zone is None:
        status = "WAIT"
        reason = "Belum ditemukan zona searah H1"

    elif h1_bias == "BULLISH" and in_demand:
        status = "MONITOR_BUY"
        reason = "Harga berada di zona Demand"

    elif h1_bias == "BEARISH" and in_supply:
        status = "MONITOR_SELL"
        reason = "Harga berada di zona Supply"

    else:
        status = "WAIT"
        reason = "Menunggu harga mendekati zona utama"

    return {
        "ready": True,
        "status": status,
        "reason": reason,

        "h1": {
            "bias": h1_bias,
            "last_high": h1_analysis["last_high"],
            "last_low": h1_analysis["last_low"]
        },

        "m15": {
            "trend": m15_structure["trend"],
            "bos_choch": m15_bos,
            "zones": m15_zones,
            "demand": demand_zone,
            "supply": supply_zone,
            "target_zone": target_zone
        },

        "m5": {
            "price": m5_price,
            "bos_choch": m5_bos,
            "rejection": m5_rejection,
            "displacement": m5_displacement,
            "pullback": m5_pullback
        },

        "market": {
            "price_m15": m15_price,
            "in_demand": in_demand,
            "in_supply": in_supply
        }
    }
