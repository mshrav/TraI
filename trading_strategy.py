"""Transparent technical-indicator strategy rules; signals are not investment advice."""
from __future__ import annotations

from enum import Enum
from typing import Dict, List
import numpy as np
import pandas as pd


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TradingStrategy:
    def __init__(self):
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.ma_short = 20
        self.ma_long = 50

    def _close(self, data: pd.DataFrame) -> pd.Series:
        if not isinstance(data, pd.DataFrame) or "Close" not in data:
            raise ValueError("DataFrame must contain a Close column")
        close = pd.to_numeric(data["Close"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if (close <= 0).any():
            close = close[close > 0]
        return close

    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        if period < 2:
            raise ValueError("RSI period must be at least 2")
        close = self._close(data)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
        loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
        rs = gain.div(loss.replace(0, np.nan))
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.mask((loss == 0) & (gain > 0), 100)
        rsi = rsi.mask((loss == 0) & (gain == 0), 50)
        return rsi.clip(0, 100)

    def calculate_macd(self, data: pd.DataFrame):
        close = self._close(data)
        fast = close.ewm(span=self.macd_fast, adjust=False, min_periods=self.macd_fast).mean()
        slow = close.ewm(span=self.macd_slow, adjust=False, min_periods=self.macd_slow).mean()
        macd = fast - slow
        signal = macd.ewm(span=self.macd_signal, adjust=False, min_periods=self.macd_signal).mean()
        return macd, signal, macd - signal

    def calculate_moving_averages(self, data: pd.DataFrame):
        close = self._close(data)
        return (close.rolling(self.ma_short, min_periods=self.ma_short).mean(),
                close.rolling(self.ma_long, min_periods=self.ma_long).mean())

    def generate_signals(self, data: pd.DataFrame) -> Dict:
        close = self._close(data)
        if len(close) < self.ma_long + 1:
            return {"signal": Signal.HOLD.value, "confidence": 0,
                    "reason": f"Insufficient valid data: need at least {self.ma_long + 1} closes",
                    "indicators": {}}

        aligned = data.loc[close.index].copy()
        rsi = self.calculate_rsi(aligned, self.rsi_period)
        macd, signal_line, _ = self.calculate_macd(aligned)
        ma_short, ma_long = self.calculate_moving_averages(aligned)
        values = [rsi.iloc[-1], macd.iloc[-1], signal_line.iloc[-1], ma_short.iloc[-1], ma_long.iloc[-1]]
        if not np.isfinite(np.asarray(values, dtype=float)).all():
            return {"signal": Signal.HOLD.value, "confidence": 0, "reason": "Indicators are not ready", "indicators": {}}

        price = float(close.iloc[-1])
        current_rsi = float(rsi.iloc[-1])
        bullish, bearish = 0, 0
        bull_reasons, bear_reasons = [], []
        if current_rsi < 30:
            bullish += 25; bull_reasons.append("RSI oversold")
        elif current_rsi > 70:
            bearish += 25; bear_reasons.append("RSI overbought")
        if float(macd.iloc[-1]) > float(signal_line.iloc[-1]):
            bullish += 30; bull_reasons.append("MACD above signal line")
        elif float(macd.iloc[-1]) < float(signal_line.iloc[-1]):
            bearish += 30; bear_reasons.append("MACD below signal line")
        if float(ma_short.iloc[-1]) > float(ma_long.iloc[-1]):
            bullish += 25; bull_reasons.append("20-day average above 50-day average")
        elif float(ma_short.iloc[-1]) < float(ma_long.iloc[-1]):
            bearish += 25; bear_reasons.append("20-day average below 50-day average")
        if price > float(ma_short.iloc[-1]):
            bullish += 20; bull_reasons.append("Price above short moving average")
        elif price < float(ma_short.iloc[-1]):
            bearish += 20; bear_reasons.append("Price below short moving average")

        if bullish >= 50 and bullish > bearish:
            final, score, reasons = Signal.BUY.value, bullish, bull_reasons
        elif bearish >= 50 and bearish > bullish:
            final, score, reasons = Signal.SELL.value, bearish, bear_reasons
        else:
            final, score = Signal.HOLD.value, max(bullish, bearish)
            reasons = ["Bullish and bearish evidence is mixed"]
        return {
            "signal": final,
            "confidence": int(min(score, 100)),
            "reason": "; ".join(reasons),
            "indicators": {
                "rsi": round(current_rsi, 2),
                "macd": round(float(macd.iloc[-1]), 4),
                "ma_short": round(float(ma_short.iloc[-1]), 2),
                "ma_long": round(float(ma_long.iloc[-1]), 2),
                "price": round(price, 2),
            },
        }

    def get_stock_recommendations(self, stocks: List[str], risk_level: str = "medium") -> List[Dict]:
        from data_fetcher import fetch_stock_data
        from data_fetcher import normalize_symbol
        recommendations = []
        for stock in stocks:
            try:
                symbol = normalize_symbol(stock)
                data = fetch_stock_data(symbol, "6mo")
                if data.empty:
                    continue
                signals = self.generate_signals(data)
                recommendations.append({
                    "stock": symbol,
                    "current_price": round(float(data["Close"].iloc[-1]), 2),
                    **signals,
                })
            except (ValueError, KeyError, TypeError) as exc:
                import logging
                logging.getLogger(__name__).warning("Skipping %s: %s", stock, exc)
        return sorted(recommendations, key=lambda item: item["confidence"], reverse=True)

    def get_portfolio_suggestion(self, budget: float, risk_level: str) -> Dict:
        if not np.isfinite(budget) or budget <= 0:
            raise ValueError("budget must be a positive finite amount")
        stock_universe = {
            "low": ["HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS"],
            "medium": ["RELIANCE.NS", "HINDUNILVR.NS", "ITC.NS", "KOTAKBANK.NS"],
            "high": ["BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS", "AXISBANK.NS"],
        }
        recommendations = self.get_stock_recommendations(stock_universe.get(risk_level, stock_universe["medium"]), risk_level)
        buys = [r for r in recommendations if r["signal"] == Signal.BUY.value and r["confidence"] >= 60][:3]
        remaining = float(budget)
        allocation = {}
        for rec in buys:
            amount = min(budget * (rec["confidence"] / 100), remaining)
            if amount <= 0:
                break
            allocation[rec["stock"]] = {
                "amount": round(amount, 2), "shares": int(amount / rec["current_price"]),
                "confidence": rec["confidence"], "reason": rec["reason"],
            }
            remaining -= amount
        return {"total_budget": round(float(budget), 2), "allocated": round(budget - remaining, 2),
                "remaining": round(remaining, 2), "recommendations": allocation}
