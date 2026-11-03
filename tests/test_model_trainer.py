import numpy as np
import pandas as pd
import pytest
from model_trainer import StockPricePredictor


def sample_prices(rows=180):
    idx = pd.date_range("2023-01-01", periods=rows, freq="B")
    close = 100 + np.arange(rows) * 0.3 + np.sin(np.arange(rows) / 5)
    return pd.DataFrame({
        "Open": close - 0.2,
        "High": close + 1.0,
        "Low": close - 1.0,
        "Close": close,
        "Volume": 100000 + np.arange(rows) * 10,
    }, index=idx)


def test_train_returns_chronological_holdout_metrics():
    predictor = StockPricePredictor()
    metrics = predictor.train(sample_prices())
    assert predictor.trained
    assert metrics["train_rows"] > metrics["test_rows"]
    assert metrics["mae"] >= 0
    assert metrics["rmse"] >= 0
    assert 0 <= metrics["directional_accuracy_pct"] <= 100


def test_predict_requires_training():
    with pytest.raises(RuntimeError):
        StockPricePredictor().predict_next_close(sample_prices().tail(1))


def test_train_rejects_too_little_data():
    with pytest.raises(ValueError, match="At least"):
        StockPricePredictor().train(sample_prices(20))


def test_predict_returns_positive_finite_value():
    predictor = StockPricePredictor()
    data = sample_prices()
    predictor.train(data)
    result = predictor.predict_next_close(data.tail(1))
    assert np.isfinite(result) and result > 0


def test_prepare_features_drops_last_target_row():
    X, y = StockPricePredictor().prepare_features(sample_prices(50))
    assert len(X) == 49
    assert len(y) == 49
