from signals.scoring import calculate_score


def make_analysis():
    return {
        "h1": {"bias": "BULLISH"},
        "m15": {
            "trend": "BULLISH",
            "target_zone": {"type": "DEMAND"},
        },
    }


def test_buy_signal_is_scored_using_bullish_direction():
    signal = {
        "status": "BUY",
        "evidence": {
            "zone_touched": True,
            "rejection": True,
            "structure": True,
            "bos": True,
            "displacement": True,
            "pullback": True,
        },
    }

    result = calculate_score(make_analysis(), signal)

    assert result["score"] == 100
    assert result["quality"] == "KUAT"


def test_sell_signal_is_scored_using_bearish_direction():
    analysis = {
        "h1": {"bias": "BEARISH"},
        "m15": {
            "trend": "BEARISH",
            "target_zone": {"type": "SUPPLY"},
        },
    }
    signal = {
        "status": "SELL",
        "evidence": {
            "zone_touched": True,
            "rejection": True,
            "structure": True,
            "bos": True,
            "displacement": True,
            "pullback": True,
        },
    }

    result = calculate_score(analysis, signal)

    assert result["score"] == 100
    assert result["quality"] == "KUAT"


def test_wait_signal_has_zero_score():
    result = calculate_score(make_analysis(), {"status": "WAIT"})

    assert result["score"] == 0
    assert result["quality"] == "TIDAK ADA SETUP"
