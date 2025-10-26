import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np

class StockPricePredictor:
    def __init__(self):
        self.model = LinearRegression()
        self.trained = False

    def prepare_features(self, data: pd.DataFrame) -> (np.ndarray, np.ndarray):
        """
        Prepare features and target arrays from historical stock data.

        Features: Open, High, Low, Volume of each day.
        Target: Close price of the next day.

        Args:
            data (pd.DataFrame): Historical stock data.

        Returns:
            X (np.ndarray): Features array.
            y (np.ndarray): Target array.
        """
        data = data.copy()
        data['Target'] = data['Close'].shift(-1)
        data = data.dropna()

        X = data[['Open', 'High', 'Low', 'Volume']].values
        y = data['Target'].values
        return X, y

    def train(self, data: pd.DataFrame):
        """
        Train the linear regression model on the given data.

        Args:
            data (pd.DataFrame): Historical stock data.
        """
        X, y = self.prepare_features(data)
        self.model.fit(X, y)
        self.trained = True

    def predict_next_close(self, latest_data: pd.DataFrame) -> float:
        """
        Predict the next day's closing price based on the latest data row.

        Args:
            latest_data (pd.DataFrame): Latest stock data row with features.

        Returns:
            float: Predicted next closing price.
        """
        if not self.trained:
            raise Exception("Model is not trained yet.")

        features = latest_data[['Open', 'High', 'Low', 'Volume']].values.reshape(1, -1)
        prediction = self.model.predict(features)
        return prediction[0]
