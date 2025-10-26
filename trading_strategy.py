import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from enum import Enum

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

    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index (RSI)."""
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, data: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        ema_fast = data['Close'].ewm(span=self.macd_fast).mean()
        ema_slow = data['Close'].ewm(span=self.macd_slow).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.macd_signal).mean()
        histogram = macd - signal
        return macd, signal, histogram

    def calculate_moving_averages(self, data: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """Calculate short and long moving averages."""
        ma_short = data['Close'].rolling(window=self.ma_short).mean()
        ma_long = data['Close'].rolling(window=self.ma_long).mean()
        return ma_short, ma_long

    def generate_signals(self, data: pd.DataFrame) -> Dict[str, str]:
        """Generate buy/sell/hold signals based on technical indicators."""
        if len(data) < self.ma_long:
            return {"signal": Signal.HOLD.value, "confidence": 0, "reason": "Insufficient data"}

        # Calculate indicators
        rsi = self.calculate_rsi(data, self.rsi_period)
        macd, signal_line, histogram = self.calculate_macd(data)
        ma_short, ma_long = self.calculate_moving_averages(data)

        # Get latest values
        latest_rsi = rsi.iloc[-1]
        latest_macd = macd.iloc[-1]
        latest_signal = signal_line.iloc[-1]
        latest_ma_short = ma_short.iloc[-1]
        latest_ma_long = ma_long.iloc[-1]
        latest_price = data['Close'].iloc[-1]

        # Signal generation logic
        signals = []
        confidence = 0

        # RSI signals
        if latest_rsi < 30:
            signals.append("RSI oversold")
            confidence += 25
        elif latest_rsi > 70:
            signals.append("RSI overbought")
            confidence += 25

        # MACD signals
        if latest_macd > latest_signal and macd.iloc[-2] <= signal_line.iloc[-2]:
            signals.append("MACD bullish crossover")
            confidence += 30
        elif latest_macd < latest_signal and macd.iloc[-2] >= signal_line.iloc[-2]:
            signals.append("MACD bearish crossover")
            confidence += 30

        # Moving average signals
        if latest_ma_short > latest_ma_long and ma_short.iloc[-2] <= ma_long.iloc[-2]:
            signals.append("Price above moving averages")
            confidence += 20
        elif latest_ma_short < latest_ma_long and ma_short.iloc[-2] >= ma_long.iloc[-2]:
            signals.append("Price below moving averages")
            confidence += 20

        # Determine final signal
        if confidence >= 50 and "oversold" in " ".join(signals).lower():
            final_signal = Signal.BUY.value
        elif confidence >= 50 and "overbought" in " ".join(signals).lower():
            final_signal = Signal.SELL.value
        else:
            final_signal = Signal.HOLD.value

        return {
            "signal": final_signal,
            "confidence": min(confidence, 100),
            "reason": "; ".join(signals) if signals else "No clear signals",
            "indicators": {
                "rsi": round(latest_rsi, 2),
                "macd": round(latest_macd, 4),
                "ma_short": round(latest_ma_short, 2),
                "ma_long": round(latest_ma_long, 2),
                "price": round(latest_price, 2)
            }
        }

    def get_stock_recommendations(self, stocks: List[str], risk_level: str = "medium") -> List[Dict]:
        """Get trading recommendations for multiple stocks."""
        from data_fetcher import fetch_stock_data

        recommendations = []

        for stock in stocks:
            try:
                # Fetch data
                data = fetch_stock_data(stock, "6mo")  # Get 6 months data for better analysis
                if data.empty:
                    continue

                # Generate signals
                signals = self.generate_signals(data)

                # Add recommendation
                recommendation = {
                    "stock": stock,
                    "current_price": round(data['Close'].iloc[-1], 2),
                    "signal": signals["signal"],
                    "confidence": signals["confidence"],
                    "reason": signals["reason"],
                    "indicators": signals["indicators"]
                }
                recommendations.append(recommendation)

            except Exception as e:
                print(f"Error analyzing {stock}: {e}")
                continue

        # Sort by confidence (highest first)
        recommendations.sort(key=lambda x: x["confidence"], reverse=True)
        return recommendations

    def get_portfolio_suggestion(self, budget: float, risk_level: str) -> Dict:
        """Suggest portfolio allocation based on budget and risk level."""
        # Sample stock universe (you can expand this)
        stock_universe = {
            "low_risk": ["HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS"],
            "medium_risk": ["RELIANCE.NS", "HINDUNILVR.NS", "ITC.NS", "KOTAKBANK.NS"],
            "high_risk": ["BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS", "AXISBANK.NS"]
        }

        selected_stocks = stock_universe.get(risk_level, stock_universe["medium_risk"])

        # Get recommendations
        recommendations = self.get_stock_recommendations(selected_stocks, risk_level)

        # Filter buy signals with high confidence
        buy_recommendations = [r for r in recommendations if r["signal"] == Signal.BUY.value and r["confidence"] >= 60]

        # Allocate budget
        allocation = {}
        remaining_budget = budget

        for i, rec in enumerate(buy_recommendations[:3]):  # Top 3 recommendations
            if remaining_budget <= 0:
                break

            # Allocate percentage based on confidence
            percentage = min(rec["confidence"] / 100, remaining_budget / budget)
            amount = budget * percentage
            shares = amount / rec["current_price"]

            allocation[rec["stock"]] = {
                "amount": round(amount, 2),
                "shares": int(shares),
                "confidence": rec["confidence"],
                "reason": rec["reason"]
            }
            remaining_budget -= amount

        return {
            "total_budget": budget,
            "allocated": round(budget - remaining_budget, 2),
            "remaining": round(remaining_budget, 2),
            "recommendations": allocation
        }
