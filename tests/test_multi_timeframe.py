import pandas as pd

from analysis.multi_timeframe import (
    _detect_zones,
    analyze_multi_timeframe,
)


def make_frame(offset=100.0, demand=False, count=50):
    rows = [
        {
            "open": offset + 0.5,
            "high": offset + 1.0,
            "low": offset - 1.0,
            "close": offset + 0.5,
        }
        for _ in range(count)
    ]

    if demand:
        # Candle bearish sebelum base (DBR).
        rows[19] = {
            "open": offset + 1.0,
            "high": offset + 1.2,
            "low": offset - 0.8,
            "close": offset - 0.5,
        }
        # Base kecil.
        rows[20] = {
            "open": offset - 0.1,
            "high": offset + 0.1,
            "low": offset - 0.1,
            "close": offset,
        }
        # Impulse bullish yang meninggalkan base.
        rows[21] = {
            "open": offset,
            "high": offset + 4.5,
            "low": offset - 0.2,
            "close": offset + 4.0,
        }

    return pd.DataFrame(rows)


def test_zone_detector_uses_supply_demand_patterns():
    zones = _detect_zones(make_frame(demand=True))

    assert zones
    assert zones[0]["type"] == "DEMAND"
    assert zones[0]["pattern"] == "DBR"
    assert zones[0]["low"] < zones[0]["high"]


def test_zone_detector_returns_empty_when_no_valid_pattern():
    zones = _detect_zones(make_frame(demand=False))

    assert zones == []


def test_m15_zone_is_not_rejected_when_h1_zone_does_not_overlap(monkeypatch):
    import analysis.multi_timeframe as mtf

    monkeypatch.setattr(mtf, "_get_trend", lambda df: "BULLISH")

    # H1 punya zona demand pada harga sekitar 200.
    h1 = make_frame(offset=200.0, demand=True)
    # M15 punya zona demand pada harga sekitar 100.
    m15 = make_frame(offset=100.0, demand=True)
    # Harga M5 berada di sekitar zona M15.
    m5 = make_frame(offset=100.0, demand=False)

    result = analyze_multi_timeframe(h1, m15, m5)

    assert result["ready"] is True
    assert result["h1"]["target_zone"] is not None
    assert result["m15"]["target_zone"] is not None
    assert result["target_zone"]["type"] == "DEMAND"
    assert result["m15"]["target_zone"]["low"] == 99.9
