import numpy as np
import pandas as pd
from trading_strategy import TradingStrategy, Signal


def prices(values):
    return pd.DataFrame({"Close": values})


def test_rsi_is_bounded():
    strategy = TradingStrategy()
    result = strategy.calculate_rsi(prices(np.linspace(100, 180, 80)))
    valid = result.dropna()
    assert ((valid >= 0) & (valid <= 100)).all()


def test_rsi_constant_series_does_not_divide_by_zero():
    result = TradingStrategy().calculate_rsi(prices(np.repeat(100.0, 40)))
    assert result.dropna().iloc[-1] == 50


def test_insufficient_data_returns_hold():
    result = TradingStrategy().generate_signals(prices(np.linspace(100, 110, 30)))
    assert result["signal"] == Signal.HOLD.value
    assert result["confidence"] == 0


def test_signal_output_contains_indicators_after_warmup():
    values = 100 + np.arange(100) * 0.5 + np.sin(np.arange(100) / 4)
    result = TradingStrategy().generate_signals(prices(values))
    assert result["signal"] in {s.value for s in Signal}
    assert 0 <= result["confidence"] <= 100
    assert "rsi" in result["indicators"]


def test_portfolio_suggestion_rejects_bad_budget():
    import pytest
    with pytest.raises(ValueError):
        TradingStrategy().get_portfolio_suggestion(0, "medium")
