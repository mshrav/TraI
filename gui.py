"""Responsive Tkinter front end for the local stock-analysis pipeline."""
from __future__ import annotations
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from data_fetcher import fetch_stock_data, normalize_symbol
from model_trainer import StockPricePredictor
from trading_strategy import TradingStrategy


class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TraI | Stock Analysis")
        self.root.geometry("680x500")
        self.root.minsize(560, 420)
        self.predictor = StockPricePredictor()
        self.strategy = TradingStrategy()
        self.data = pd.DataFrame()
        self.symbol = None
        self._busy = False
        self._build_ui()

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="TraI — AI Stock Analysis", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Historical market data • model evaluation • technical signals",
                  foreground="#555555").pack(anchor="w", pady=(2, 18))

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 12))
        ttk.Label(controls, text="Ticker symbol").grid(row=0, column=0, sticky="w")
        self.symbol_entry = ttk.Entry(controls, width=24)
        self.symbol_entry.insert(0, "RELIANCE.NS")
        self.symbol_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(controls, text="History period").grid(row=0, column=1, sticky="w")
        self.period_var = tk.StringVar(value="1y")
        period = ttk.Combobox(controls, textvariable=self.period_var,
                              values=["6mo", "1y", "2y", "5y"], state="readonly", width=10)
        period.grid(row=1, column=1, sticky="w", padx=(0, 8))
        controls.columnconfigure(0, weight=1)

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(0, 14))
        self.fetch_btn = ttk.Button(buttons, text="Fetch market data", command=self.fetch_data)
        self.fetch_btn.pack(side="left", padx=(0, 8))
        self.train_btn = ttk.Button(buttons, text="Train & evaluate", command=self.train_model, state="disabled")
        self.train_btn.pack(side="left", padx=(0, 8))
        self.predict_btn = ttk.Button(buttons, text="Predict next close", command=self.predict_price, state="disabled")
        self.predict_btn.pack(side="left")

        self.status_var = tk.StringVar(value="Enter a ticker and fetch historical data to begin.")
        ttk.Label(outer, textvariable=self.status_var, foreground="#245a8d").pack(anchor="w", pady=(0, 10))
        ttk.Separator(outer).pack(fill="x", pady=8)
        self.result = tk.Text(outer, height=13, wrap="word", state="disabled", font=("Consolas", 10))
        self.result.pack(fill="both", expand=True)
        ttk.Label(outer, text="Research / paper analysis only. Not investment advice; no live orders are placed.",
                  foreground="#777777").pack(anchor="w", pady=(10, 0))

    def _set_busy(self, busy: bool, status: str):
        self._busy = busy
        self.status_var.set(status)
        state = "disabled" if busy else "normal"
        self.fetch_btn.configure(state=state)
        self.train_btn.configure(state="disabled" if busy or self.data.empty else "normal")
        self.predict_btn.configure(state="disabled" if busy or not self.predictor.trained else "normal")

    def _write_result(self, text: str):
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("end", text)
        self.result.configure(state="disabled")

    def _run_background(self, work, on_success, failure_title):
        if self._busy:
            return
        self._set_busy(True, "Working… please wait")

        def worker():
            try:
                value = work()
                self.root.after(0, lambda: on_success(value))
            except Exception as exc:
                self.root.after(0, lambda err=str(exc): self._on_failure(failure_title, err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_failure(self, title, error):
        self._set_busy(False, "Operation failed. Check the error details.")
        messagebox.showerror(title, error)

    def fetch_data(self):
        try:
            symbol = normalize_symbol(self.symbol_entry.get())
            period = self.period_var.get()
        except ValueError as exc:
            messagebox.showerror("Invalid ticker", str(exc))
            return

        def work():
            data = fetch_stock_data(symbol, period)
            if data.empty:
                raise RuntimeError(f"No valid market data was returned for {symbol}. Check the ticker, internet and Yahoo Finance availability.")
            return symbol, data

        def done(result):
            self.symbol, self.data = result
            self.predictor = StockPricePredictor()
            self._set_busy(False, f"Loaded {len(self.data)} daily rows for {self.symbol}.")
            self.train_btn.configure(state="normal")
            self.predict_btn.configure(state="disabled")
            self._write_result(f"Ticker: {self.symbol}\nRows: {len(self.data)}\nRange: {self.data.index.min()} → {self.data.index.max()}\nLatest close: {self.data['Close'].iloc[-1]:,.2f}\n\nTrain the model to see chronological holdout metrics.")

        self._run_background(work, done, "Market data error")

    def train_model(self):
        if self.data.empty:
            messagebox.showerror("Missing data", "Fetch market data first.")
            return

        def work():
            metrics = self.predictor.train(self.data)
            signals = self.strategy.generate_signals(self.data)
            return metrics, signals

        def done(result):
            metrics, signals = result
            self._set_busy(False, "Model trained and evaluated on a chronological holdout set.")
            self.predict_btn.configure(state="normal")
            lines = [f"Ticker: {self.symbol}", "", "HOLDOUT EVALUATION"]
            lines += [f"{key}: {value}" for key, value in metrics.items()]
            lines += ["", "TECHNICAL SIGNAL", f"Signal: {signals['signal']}",
                      f"Rule score: {signals['confidence']}/100", f"Reason: {signals['reason']}"]
            for name, value in signals.get("indicators", {}).items():
                lines.append(f"{name}: {value}")
            self._write_result("\n".join(lines))

        self._run_background(work, done, "Model training error")

    def predict_price(self):
        if self.data.empty or not self.predictor.trained:
            messagebox.showerror("Model not ready", "Fetch data and train the model first.")
            return
        try:
            value = self.predictor.predict_next_close(self.data.tail(1))
        except Exception as exc:
            messagebox.showerror("Prediction error", str(exc))
            return
        latest = float(self.data["Close"].iloc[-1])
        change = (value - latest) / latest * 100
        self.status_var.set("Prediction generated. This is an experimental estimate, not a trading instruction.")
        self._write_result(
            f"Ticker: {self.symbol}\nLatest close: {latest:,.2f}\n"
            f"Predicted next close: {value:,.2f}\nEstimated change vs latest close: {change:+.2f}%\n\n"
            "This regression estimate is not a calibrated probability or a guarantee of future performance."
        )


if __name__ == "__main__":
    root = tk.Tk()
    TradingBotGUI(root)
    root.mainloop()
