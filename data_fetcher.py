"""Market-data access helpers.

Yahoo Finance is an unofficial data source; requests can be delayed, incomplete,
or rate-limited. The application is analysis/paper-trading software only.
"""
from __future__ import annotations

import logging
import re
import pandas as pd
import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)
_REQUIRED_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


def normalize_symbol(symbol: str) -> str:
    value = (symbol or "").strip().upper()
    if not value or not re.fullmatch(r"[A-Z0-9.^=-]{1,30}", value):
        raise ValueError("Enter a valid ticker symbol, e.g. RELIANCE.NS or TCS.NS")
    return value


def fetch_stock_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Fetch and validate historical OHLCV data for a ticker."""
    ticker = normalize_symbol(symbol)
    try:
        frame = yf.Ticker(ticker).history(
            period=period, interval="1d", auto_adjust=False,
            actions=False, raise_errors=True
        )
        if frame is None or frame.empty:
            logger.warning("No market data returned for %s", ticker)
            return pd.DataFrame(columns=list(_REQUIRED_COLUMNS))
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)
        missing = [name for name in _REQUIRED_COLUMNS if name not in frame.columns]
        if missing:
            logger.warning("Missing columns for %s: %s", ticker, missing)
            return pd.DataFrame(columns=list(_REQUIRED_COLUMNS))
        frame = frame.loc[:, list(_REQUIRED_COLUMNS)].copy()
        for col in _REQUIRED_COLUMNS:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
        frame = frame.replace([np.inf, -np.inf], np.nan)
        frame = frame.dropna(subset=list(_REQUIRED_COLUMNS))
        price_cols = ["Open", "High", "Low", "Close"]
        frame = frame[(frame[price_cols] > 0).all(axis=1) & (frame["Volume"] >= 0)]
        frame = frame[(frame["High"] >= frame["Low"]) &
                      (frame["High"] >= frame[["Open", "Close"]].max(axis=1)) &
                      (frame["Low"] <= frame[["Open", "Close"]].min(axis=1))]
        frame = frame[~frame.index.duplicated(keep="last")].sort_index()
        return frame
    except Exception as exc:
        logger.exception("Market-data fetch failed for %s: %s", ticker, exc)
        return pd.DataFrame(columns=list(_REQUIRED_COLUMNS))
