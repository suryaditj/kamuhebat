import pandas as pd
import pytest

from analysis.market_structure import detect_swings
from analysis.rejection import analyze_rejection
from analysis.displacement import analyze_displacement
from signals.risk_manager import (
    calculate_risk_amount,
    calculate_position_size,
    validate_trade,
)


def make_candles(count=40):
    """Membuat data candle simulasi untuk pengujian."""
    data = []

    for i in range(count):
        base = 100 + i * 0.1

        data.append({
            "open": base,
            "high": base + 0.5,
            "low": base - 0.3,
            "close": base + 0.3,
        })

    return pd.DataFrame(data)


def test_detect_swings_returns_dataframe():
    df = make_candles()

    result = detect_swings(df)

    assert isinstance(result, pd.DataFrame)


def test_risk_amount_calculation():
    result = calculate_risk_amount(
        balance=1000,
        risk_percent=1,
    )

    assert result == 10


def test_position_size_calculation():
    result = calculate_position_size(
        balance=1000,
        risk_percent=1,
        entry=2000,
        stop_loss=1999,
        tick_size=0.01,
        tick_value_per_lot=1,
        min_lot=0.01,
        max_lot=100,
        lot_step=0.01,
    )

    assert result["valid"] is True
    assert result["recommended_lot"] == 0.1


def test_position_size_rejects_below_minimum():
    result = calculate_position_size(
        balance=10,
        risk_percent=1,
        entry=2000,
        stop_loss=1990,
        tick_size=0.01,
        tick_value_per_lot=1,
        min_lot=0.01,
        max_lot=100,
        lot_step=0.01,
    )

    assert result["valid"] is False


def test_valid_buy_trade():
    result = validate_trade(
        direction="BUY",
        entry=2000,
        stop_loss=1990,
        take_profit=2020,
        minimum_rr=1.5,
    )

    assert result["valid"] is True
    assert result["risk_reward"] == 2.0


def test_invalid_buy_trade():
    result = validate_trade(
        direction="BUY",
        entry=2000,
        stop_loss=2010,
        take_profit=2020,
    )

    assert result["valid"] is False


def test_invalid_sell_trade():
    result = validate_trade(
        direction="SELL",
        entry=2000,
        stop_loss=1990,
        take_profit=1980,
    )

    assert result["valid"] is False


def test_invalid_risk_percentage():
    with pytest.raises(ValueError):
        calculate_risk_amount(
            balance=1000,
            risk_percent=0,
        )


def test_rejection_function_returns_dictionary():
    candle = pd.Series({
        "open": 2000,
        "high": 2005,
        "low": 1999,
        "close": 2004,
    })

    result = analyze_rejection(candle)

    assert isinstance(result, dict)


def test_displacement_function_returns_dictionary():
    df = make_candles()

    result = analyze_displacement(df)

    assert isinstance(result, dict)
