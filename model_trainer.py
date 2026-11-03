"""Leakage-aware next-session close predictor with chronological holdout metrics."""
from __future__ import annotations

from typing import Dict, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

FEATURE_COLUMNS = ["Open", "High", "Low", "Volume"]


class StockPricePredictor:
    def __init__(self, test_fraction: float = 0.2, minimum_rows: int = 30):
        if not 0.1 <= test_fraction <= 0.4:
            raise ValueError("test_fraction must be between 0.1 and 0.4")
        self.model = LinearRegression()
        self.trained = False
        self.test_fraction = test_fraction
        self.minimum_rows = minimum_rows
        self.metrics: Dict[str, float] = {}

    def _clean(self, data: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")
        missing = [c for c in FEATURE_COLUMNS + ["Close"] if c not in data.columns]
        if missing:
            raise ValueError(f"Missing required market columns: {', '.join(missing)}")
        frame = data.copy()
        frame = frame.sort_index()
        for col in FEATURE_COLUMNS + ["Close"]:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
        frame = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURE_COLUMNS + ["Close"])
        frame = frame[(frame["Close"] > 0) & (frame["Open"] > 0) & (frame["High"] > 0) & (frame["Low"] > 0)]
        return frame

    def prepare_features(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        frame = self._clean(data)
        frame["Target"] = frame["Close"].shift(-1)
        frame = frame.dropna(subset=["Target"])
        if frame.empty:
            return np.empty((0, len(FEATURE_COLUMNS))), np.empty((0,))
        return frame[FEATURE_COLUMNS].to_numpy(dtype=float), frame["Target"].to_numpy(dtype=float)

    def train(self, data: pd.DataFrame) -> Dict[str, float]:
        X, y = self.prepare_features(data)
        if len(y) < self.minimum_rows:
            raise ValueError(f"At least {self.minimum_rows + 1} clean daily rows are required; got {len(y) + 1}")
        split = int(len(y) * (1 - self.test_fraction))
        if split < 10 or len(y) - split < 3:
            raise ValueError("Not enough observations for chronological train/test evaluation")

        evaluation_model = LinearRegression().fit(X[:split], y[:split])
        predicted = evaluation_model.predict(X[split:])
        actual = y[split:]
        mae = float(mean_absolute_error(actual, predicted))
        rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
        baseline = X[split:, 0]  # open price is a transparent, simple reference baseline
        baseline_mae = float(mean_absolute_error(actual, baseline))
        directional = float(np.mean(np.sign(predicted - X[split:, 0]) == np.sign(actual - X[split:, 0])) * 100)

        # Refit on all historical examples only after holdout metrics are recorded.
        self.model = LinearRegression().fit(X, y)
        self.trained = True
        self.metrics = {
            "mae": mae,
            "rmse": rmse,
            "directional_accuracy_pct": directional,
            "baseline_open_price_mae": baseline_mae,
            "train_rows": int(split),
            "test_rows": int(len(y) - split),
        }
        return dict(self.metrics)

    def predict_next_close(self, latest_data: pd.DataFrame) -> float:
        if not self.trained:
            raise RuntimeError("Model is not trained. Fetch data and train it first.")
        if not isinstance(latest_data, pd.DataFrame) or latest_data.empty:
            raise ValueError("latest_data must contain at least one market-data row")
        missing = [c for c in FEATURE_COLUMNS if c not in latest_data.columns]
        if missing:
            raise ValueError(f"Missing prediction features: {', '.join(missing)}")
        row = latest_data.iloc[[-1]][FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
        values = row.to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values[:, :3] <= 0).any():
            raise ValueError("Latest market-data row contains invalid feature values")
        prediction = float(self.model.predict(values)[0])
        if not np.isfinite(prediction) or prediction <= 0:
            raise ValueError("Model produced an invalid predicted price")
        return prediction
