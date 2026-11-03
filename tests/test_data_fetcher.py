"""Data-fetcher tests stub Yahoo Finance so the suite never needs the network."""
import sys
import types
import numpy as np
import pandas as pd
import pytest

# The data normalisation layer can be tested without installing/calling yfinance.
if "yfinance" not in sys.modules:
    try:
        import yfinance  # noqa: F401
    except ImportError:
        sys.modules["yfinance"] = types.SimpleNamespace(Ticker=None)

import data_fetcher
from data_fetcher import normalize_symbol, fetch_stock_data


def test_normalize_symbol():
    assert normalize_symbol(" reliance.ns ") == "RELIANCE.NS"


@pytest.mark.parametrize("symbol", ["", "   ", "RELIANCE/NS", "bad symbol"])
def test_reject_invalid_symbol(symbol):
    with pytest.raises(ValueError):
        normalize_symbol(symbol)


def test_fetch_cleans_sorts_and_deduplicates(monkeypatch):
    index = pd.to_datetime(["2024-01-03", "2024-01-01", "2024-01-03", "2024-01-02"])
    frame = pd.DataFrame({
        "Open": [103, 101, 104, 102], "High": [105, 103, 106, 104],
        "Low": [102, 100, 103, 101], "Close": [104, 102, 105, np.nan],
        "Volume": [1000, 800, 1200, 900],
    }, index=index)

    class FakeTicker:
        def __init__(self, symbol):
            assert symbol == "RELIANCE.NS"
        def history(self, **kwargs):
            assert kwargs["period"] == "1y"
            return frame

    monkeypatch.setattr(data_fetcher.yf, "Ticker", FakeTicker)
    result = fetch_stock_data("reliance.ns")
    assert list(result.index) == list(pd.to_datetime(["2024-01-01", "2024-01-03"]))
    assert result.loc[pd.Timestamp("2024-01-03"), "Close"] == 105


def test_fetch_returns_empty_frame_on_provider_error(monkeypatch):
    class BrokenTicker:
        def __init__(self, symbol):
            pass
        def history(self, **kwargs):
            raise RuntimeError("network unavailable")
    monkeypatch.setattr(data_fetcher.yf, "Ticker", BrokenTicker)
    assert fetch_stock_data("TCS.NS").empty
