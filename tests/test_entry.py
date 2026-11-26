import pandas as pd
import pytest

from signals.entry import evaluate_entry


def make_candles(direction="BULLISH"):
    if direction == "BULLISH":
        return pd.DataFrame([
            {
                "open": 101.0,
                "high": 103.0,
                "low": 101.0,
                "close": 102.5,
            }
        ] * 30)

    return pd.DataFrame([
        {
            "open": 109.0,
            "high": 109.0,
            "low": 107.0,
            "close": 107.5,
        }
    ] * 30)


def make_analysis(direction="BULLISH"):
    if direction == "BULLISH":
        zone = {
            "type": "DEMAND",
            "low": 100.0,
            "high": 102.0,
        }
    else:
        zone = {
            "type": "SUPPLY",
            "low": 108.0,
            "high": 110.0,
        }

    return {
        "ready": True,
        "h1": {
            "bias": direction,
        },
        "m15": {
            "target_zone": zone,
        },
        "m5": {
            "rejection": {
                "rejection": True,
                "direction": direction,
            },
            "bos_choch": {
                "event": "BOS",
                "direction": direction,
            },
            "displacement": {
                "confirmed": True,
                "direction": direction,
            },
            "pullback": {
                "detected": True,
                "held": True,
                "direction": direction,
            },
        },
    }


def mock_structure(direction):
    if direction == "BULLISH":
        return {
            "last_high": {"label": "HH"},
            "last_low": {"label": "HL"},
        }

    return {
        "last_high": {"label": "LH"},
        "last_low": {"label": "LL"},
    }


def prepare_test(monkeypatch, direction="BULLISH"):
    import signals.entry as entry_module

    monkeypatch.setattr(
        entry_module,
        "classify_structure",
        lambda df: mock_structure(direction),
    )

    return (
        make_analysis(direction),
        make_candles(direction),
    )


def test_bullish_early_entry(monkeypatch):
    analysis, candles = prepare_test(monkeypatch)

    result = evaluate_entry(
        analysis,
        candles,
        entry_style="early",
    )

    assert result["status"] == "BUY"
    assert result["direction"] == "BULLISH"
    assert result["entry_type"] == "EARLY"


def test_bearish_early_entry(monkeypatch):
    analysis, candles = prepare_test(
        monkeypatch,
        "BEARISH",
    )

    result = evaluate_entry(
        analysis,
        candles,
        entry_style="early",
    )

    assert result["status"] == "SELL"
    assert result["direction"] == "BEARISH"
    assert result["entry_type"] == "EARLY"


def test_confirmed_entry(monkeypatch):
    analysis, candles = prepare_test(monkeypatch)

    result = evaluate_entry(
        analysis,
        candles,
        entry_style="confirmed",
    )

    assert result["status"] == "BUY"
    assert result["entry_type"] == "CONFIRMED"


def test_hybrid_prefers_confirmed(monkeypatch):
    analysis, candles = prepare_test(monkeypatch)

    result = evaluate_entry(
        analysis,
        candles,
        entry_style="hybrid",
    )

    assert result["status"] == "BUY"
    assert result["entry_type"] == "CONFIRMED"


def test_hybrid_falls_back_to_early(monkeypatch):
    analysis, candles = prepare_test(monkeypatch)

    analysis["m5"]["bos_choch"]["event"] = None

    result = evaluate_entry(
        analysis,
        candles,
        entry_style="hybrid",
    )

    assert result["status"] == "BUY"
    assert result["entry_type"] == "EARLY"


def test_wait_when_analysis_not_ready():
    result = evaluate_entry(
        {"ready": False},
        make_candles(),
    )

    assert result["status"] == "WAIT"


def test_wait_when_h1_direction_unclear(monkeypatch):
    analysis, candles = prepare_test(monkeypatch)

    analysis["h1"]["bias"] = "RANGE"

    result = evaluate_entry(analysis, candles)

    assert result["status"] == "WAIT"


def test_wait_when_zone_missing(monkeypatch):
    analysis, candles = prepare_test(monkeypatch)

    analysis["m15"]["target_zone"] = None

    result = evaluate_entry(analysis, candles)

    assert result["status"] == "WAIT"


def test_wait_when_zone_not_touched(monkeypatch):
    analysis, candles = prepare_test(monkeypatch)

    analysis["m15"]["target_zone"] = {
        "type": "DEMAND",
        "low": 90.0,
        "high": 95.0,
    }

    result = evaluate_entry(analysis, candles)

    assert result["status"] == "WAIT"


def test_wait_when_rejection_missing(monkeypatch):
    analysis, candles = prepare_test(monkeypatch)

    analysis["m5"]["rejection"]["rejection"] = False

    result = evaluate_entry(analysis, candles)

    assert result["status"] == "WAIT"


def test_wait_when_structure_invalid(monkeypatch):
    analysis, candles = prepare_test(monkeypatch)

    import signals.entry as entry_module

    monkeypatch.setattr(
        entry_module,
        "classify_structure",
        lambda df: {
            "last_high": {"label": "HH"},
            "last_low": {"label": "LL"},
        },
    )

    result = evaluate_entry(
        analysis,
        candles,
        entry_style="early",
    )

    assert result["status"] == "WAIT"


def test_wait_when_confirmations_incomplete(monkeypatch):
    analysis, candles = prepare_test(monkeypatch)

    analysis["m5"]["displacement"]["confirmed"] = False

    result = evaluate_entry(
        analysis,
        candles,
        entry_style="confirmed",
    )

    assert result["status"] == "WAIT"


def test_buy_sl_tp_positions(monkeypatch):
    analysis, candles = prepare_test(monkeypatch)

    result = evaluate_entry(analysis, candles)

    assert result["stop_loss"] < result["entry"]
    assert result["take_profit"] > result["entry"]


def test_sell_sl_tp_positions(monkeypatch):
    analysis, candles = prepare_test(
        monkeypatch,
        "BEARISH",
    )

    result = evaluate_entry(analysis, candles)

    assert result["take_profit"] < result["entry"]
    assert result["entry"] < result["stop_loss"]


def test_wait_when_price_has_passed_sl(monkeypatch):
    analysis, candles = prepare_test(monkeypatch)

    candles.loc[candles.index[-1], "close"] = 99.0

    result = evaluate_entry(analysis, candles)

    assert result["status"] == "WAIT"


def test_invalid_entry_style():
    with pytest.raises(ValueError):
        evaluate_entry(
            {"ready": False},
            make_candles(),
            entry_style="invalid",
        )


def test_invalid_risk_reward():
    with pytest.raises(ValueError):
        evaluate_entry(
            {"ready": False},
            make_candles(),
            risk_reward=0,
        )


def test_invalid_sl_buffer():
    with pytest.raises(ValueError):
        evaluate_entry(
            {"ready": False},
            make_candles(),
            sl_buffer=-1,
        )


def test_insufficient_candles():
    analysis = make_analysis()

    result = evaluate_entry(
        analysis,
        make_candles().head(5),
    )

    assert result["status"] == "WAIT"
