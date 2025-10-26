import yfinance as yf
import pandas as pd

def fetch_stock_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch historical stock data for the given symbol and period using yfinance.

    Args:
        symbol (str): Stock ticker symbol (e.g., "RELIANCE.NS").
        period (str): Data period to fetch (default "1y" for 1 year).

    Returns:
        pd.DataFrame: DataFrame containing historical stock data.
    """
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        if hist.empty:
            raise ValueError(f"No data found for symbol: {symbol}")
        return hist
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()
