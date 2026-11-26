import pandas as pd
import pytest
import requests

from data.biquote import BiQuoteClient


class MockResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class MockSession:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.headers = {}

    def get(self, *args, **kwargs):
        if self.error:
            raise self.error

        return MockResponse(self.payload)


def sample_bars():
    return [
        {
            "openTime": "2026-11-26T10:10:00Z",
            "open": 2650,
            "high": 2655,
            "low": 2648,
            "close": 2653,
            "isOpen": False,
        },
        {
            "openTime": "2026-11-26T10:15:00Z",
            "open": 2653,
            "high": 2658,
            "low": 2651,
            "close": 2656,
            "isOpen": True,
        },
        {
            "openTime": "2026-11-26T10:05:00Z",
            "open": 2648,
            "high": 2652,
            "low": 2645,
            "close": 2650,
            "isOpen": False,
        },
    ]


def create_client(payload=None, error=None):
    client = BiQuoteClient()
    client.base_url = "https://example.test/api"
    client.session = MockSession(payload, error)
    return client


def test_only_closed_candles_are_returned():
    client = create_client({"bars": sample_bars()})

    result = client.get_ohlc("5m")

    assert len(result) == 2
    assert isinstance(result.index, pd.DatetimeIndex)


def test_candles_are_sorted_oldest_first():
    client = create_client({"bars": sample_bars()})

    result = client.get_ohlc("5m")

    assert result.index.is_monotonic_increasing


def test_open_candle_is_removed():
    client = create_client({"bars": sample_bars()})

    result = client.get_ohlc("5m")

    assert not result.empty
    assert len(result) == 2


def test_invalid_timeframe_is_rejected():
    client = create_client({"bars": sample_bars()})

    with pytest.raises(ValueError):
        client.get_ohlc("2m")


def test_invalid_limit_is_rejected():
    client = create_client({"bars": sample_bars()})

    with pytest.raises(ValueError):
        client.get_ohlc("5m", limit=0)


def test_empty_response_is_rejected():
    client = create_client({"bars": []})

    with pytest.raises(RuntimeError):
        client.get_ohlc("5m")


def test_missing_columns_are_rejected():
    client = create_client({
        "bars": [
            {
                "openTime": "2026-11-26T10:00:00Z",
                "open": 2650,
                "close": 2652,
            }
        ]
    })

    with pytest.raises(RuntimeError):
        client.get_ohlc("5m")


def test_invalid_ohlc_is_removed():
    client = create_client({
        "bars": [
            {
                "openTime": "2026-11-26T10:00:00Z",
                "open": 2650,
                "high": 2640,
                "low": 2645,
                "close": 2652,
                "isOpen": False,
            }
        ]
    })

    with pytest.raises(RuntimeError):
        client.get_ohlc("5m")


def test_connection_error_is_handled():
    client = create_client(
        error=requests.ConnectionError("Connection failed")
    )

    with pytest.raises(RuntimeError):
        client.get_ohlc("5m")
