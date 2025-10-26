import tkinter as tk
from tkinter import messagebox
from data_fetcher import fetch_stock_data
from model_trainer import StockPricePredictor
import pandas as pd

class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Trading Bot")
        self.root.geometry("400x300")

        self.predictor = StockPricePredictor()
        self.data = None

        # Stock symbol input
        tk.Label(root, text="Stock Symbol (e.g., RELIANCE.NS):").pack(pady=10)
        self.symbol_entry = tk.Entry(root)
        self.symbol_entry.pack()

        # Buttons
        tk.Button(root, text="Fetch Data", command=self.fetch_data).pack(pady=5)
        tk.Button(root, text="Train Model", command=self.train_model).pack(pady=5)
        tk.Button(root, text="Predict Next Price", command=self.predict_price).pack(pady=5)

        # Result display
        self.result_label = tk.Label(root, text="")
        self.result_label.pack(pady=20)

    def fetch_data(self):
        symbol = self.symbol_entry.get().strip()
        if not symbol:
            messagebox.showerror("Error", "Please enter a stock symbol.")
            return

        self.data = fetch_stock_data(symbol)
        if self.data.empty:
            messagebox.showerror("Error", f"Failed to fetch data for {symbol}.")
        else:
            messagebox.showinfo("Success", f"Data fetched for {symbol}. Rows: {len(self.data)}")

    def train_model(self):
        if self.data is None or self.data.empty:
            messagebox.showerror("Error", "Please fetch data first.")
            return

        try:
            self.predictor.train(self.data)
            messagebox.showinfo("Success", "Model trained successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Training failed: {str(e)}")

    def predict_price(self):
        if self.data is None or self.data.empty:
            messagebox.showerror("Error", "Please fetch data first.")
            return

        if not self.predictor.trained:
            messagebox.showerror("Error", "Please train the model first.")
            return

        try:
            latest = self.data.tail(1)
            prediction = self.predictor.predict_next_close(latest)
            self.result_label.config(text=f"Predicted Next Close: {prediction:.2f}")
        except Exception as e:
            messagebox.showerror("Error", f"Prediction failed: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()




