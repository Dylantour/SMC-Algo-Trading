#!/usr/bin/env python3
"""
Standalone Binance Client
This is a version of BinanceClient that doesn't depend on PySide2.
"""

from binance.client import Client
import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
import ta
import time
import math
import datetime
import threading

class BinanceClient:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

        self.base_asset = "BUSD"
        self.asset = "BTC"
        self.pair = "BTCBUSD"
        self.interval = "1m"
        self.df_length = 30

        self.tp = [0.0002, 0.0004]
        self.tp_ratio = [0.5, 0.5]
        self.tp1_price = None

        self.trail_stop = 0.85
        self.min_trail = 0.05
        self.max_price = None
        self.TS = None
        self.trail_stop_enabled = True

        self.mode = "trade"
        self.position = -1

        self.trade_history = []
        self.position_open = False
        self.position_data = {}
        self.reset_position()

        self.out_data = {}

        # backtesting data:
        self.backtest_initial_balance = 100000
        self.equity_history = []
        self.backtest_epoch = 0
        self.backtest_start = self.df_length
        self.asset_price = None
        self.plot = False

        self.trading_delay = 0.5
        self.client = Client(self.api_key, self.api_secret)
        self.update_time = 0
        self.balances = {}
        self.tickers = {}
        self.df = pd.DataFrame()

        # Create a data update thread
        self.data_thread = None
        self._stop_event = threading.Event()

    def start_data_thread(self):
        """Start a thread to update data periodically"""
        self._stop_event.clear()
        self.data_thread = threading.Thread(target=self._data_loop)
        self.data_thread.daemon = True
        self.data_thread.start()

    def stop_data_thread(self):
        """Stop the data update thread"""
        if self.data_thread:
            self._stop_event.set()
            self.data_thread.join()

    def _data_loop(self):
        """Background thread to update data"""
        while not self._stop_event.is_set():
            try:
                self.update()
            except Exception as e:
                print(f"Error in data loop: {str(e)}")
            time.sleep(0.8)

    def reset_position(self):
        self.position_data = {
            "open_time": None,
            "close_time": None,
            "open_price": None,
            "close_price": None,
            "profit": None,
            "trail_stop": False
        }

    def update(self):
        # print("BinanceClient.update()")

        # get account balance
        try:
            binance_info = self.client.get_account()
        except Exception as e:
            print(f"Cannot get account info from binance: {str(e)}")
            return

        self.update_time = time.time()

        balance = binance_info['balances']

        balances = {}
        for i in balance:
            if float(i["free"]) > 0.0:
                balances[i["asset"]] = float(i["free"])
        self.balances = balances

        # get bid & ask price
        try:
            tickers = self.client.get_orderbook_tickers()
        except Exception as e:
            print(f"Cannot get ticker info from binance: {str(e)}")
            return

        for i in tickers:
            if i["symbol"] == self.pair:
                self.tickers[self.pair] = {"ask": float(i["askPrice"]), "bid": float(i["bidPrice"])}

        self.df = self.get_candles()

    def trade_init(self):
        self.update()
        self.start_data_thread()
        time.sleep(0.5)

    def trade_loop(self):
        print("BinanceClient.trade()")

        while True:
            if self.mode == "trade":
                time.sleep(self.trading_delay)
                self.data_process()
                self.manager()

    def data_process(self):
        """Process the data for trading decisions"""
        # Implement your trading logic here
        pass

    def manager(self):
        """Manage trading positions"""
        # Implement your position management logic here
        pass

    def get_candles(self):
        """Get candlestick data from Binance"""
        try:
            # Get klines (candlestick data)
            klines = self.client.get_klines(
                symbol=self.pair,
                interval=self.interval,
                limit=self.df_length
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convert string values to float
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except Exception as e:
            print(f"Error getting candles: {str(e)}")
            return pd.DataFrame()

    def start(self):
        """Start the client"""
        self.running = True
        self.thread = threading.Thread(target=self._update_loop)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        """Stop the client"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            
    def _update_loop(self):
        """Background update loop"""
        while self.running:
            try:
                self.update()
            except Exception as e:
                print(f"Error in update loop: {str(e)}")
            time.sleep(1.0)

    def write_order(self, text):
        """Log order information"""
        with open("order.log", "a") as f:
            f.write(f"{datetime.datetime.now()} - {text}\n")
            
    def write_position(self, text):
        """Log position information"""
        with open("position.log", "a") as f:
            f.write(f"{datetime.datetime.now()} - {text}\n")
            
    def buy(self):
        """Execute buy order"""
        print("Executing buy order...")
        self.write_order(f"BUY {self.pair}")
        
    def sell(self):
        """Execute sell order"""
        print("Executing sell order...")
        self.write_order(f"SELL {self.pair}")
        
    def open_position(self, epoch, price):
        """Open a new position"""
        self.position = True
        self.position_price = price
        self.position_time = epoch
        self.write_position(f"OPEN {self.pair} at {price}")
        
    def close_position(self, epoch, price):
        """Close an existing position"""
        profit = price - self.position_price if self.position_price > 0 else 0
        self.write_position(f"CLOSE {self.pair} at {price}, profit: {profit}")
        self.reset_position()
        
    def analyse_data(self):
        """Analyze market data for trading signals"""
        if self.df is None or len(self.df) < 50:
            return
            
        df = self.df
        
        # Simple moving average crossover strategy
        if df['sma_20'].iloc[-1] > df['sma_50'].iloc[-1] and df['sma_20'].iloc[-2] <= df['sma_50'].iloc[-2]:
            # Bullish crossover
            print("Bullish signal detected")
            return "buy"
            
        elif df['sma_20'].iloc[-1] < df['sma_50'].iloc[-1] and df['sma_20'].iloc[-2] >= df['sma_50'].iloc[-2]:
            # Bearish crossover
            print("Bearish signal detected")
            return "sell"
            
        # RSI overbought/oversold
        if df['rsi'].iloc[-1] < 30:
            print("Oversold signal detected")
            return "buy"
            
        if df['rsi'].iloc[-1] > 70:
            print("Overbought signal detected")
            return "sell"
            
        return None
        
    def backtest_loop(self):
        """Backtesting loop"""
        print("Starting backtesting...")
        
        if self.df is None or len(self.df) < 50:
            print("Not enough data for backtesting")
            return
            
        # Reset for backtesting
        self.reset_position()
        self.equity = [1000]  # Starting equity
        
        trades = []
        
        for i in range(50, len(self.df)):
            # Create a slice of data up to current point
            current_df = self.df.iloc[:i+1]
            
            # Simple moving average crossover strategy
            sma_20 = current_df['sma_20'].iloc[-1]
            sma_50 = current_df['sma_50'].iloc[-1]
            sma_20_prev = current_df['sma_20'].iloc[-2]
            sma_50_prev = current_df['sma_50'].iloc[-2]
            
            price = current_df['close'].iloc[-1]
            timestamp = current_df['timestamp'].iloc[-1]
            
            if sma_20 > sma_50 and sma_20_prev <= sma_50_prev and not self.position:
                # Bullish crossover - buy
                self.open_position(timestamp.timestamp(), price)
                trades.append(("buy", timestamp, price))
                
            elif sma_20 < sma_50 and sma_20_prev >= sma_50_prev and self.position:
                # Bearish crossover - sell
                profit = price - self.position_price
                self.equity.append(self.equity[-1] + profit)
                self.close_position(timestamp.timestamp(), price)
                trades.append(("sell", timestamp, price))
                
        # Plot results
        self.plot_backtest_results(trades)
        
    def plot_backtest_results(self, trades):
        """Plot backtesting results"""
        if self.df is None or len(self.df) < 2:
            return
            
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), gridspec_kw={'height_ratios': [3, 1]})
        
        # Plot price and moving averages
        ax1.plot(self.df['timestamp'], self.df['close'], label='Price')
        ax1.plot(self.df['timestamp'], self.df['sma_20'], label='SMA 20')
        ax1.plot(self.df['timestamp'], self.df['sma_50'], label='SMA 50')
        
        # Plot buy/sell signals
        buy_times = [trade[1] for trade in trades if trade[0] == 'buy']
        buy_prices = [trade[2] for trade in trades if trade[0] == 'buy']
        sell_times = [trade[1] for trade in trades if trade[0] == 'sell']
        sell_prices = [trade[2] for trade in trades if trade[0] == 'sell']
        
        ax1.scatter(buy_times, buy_prices, marker='^', color='green', s=100, label='Buy')
        ax1.scatter(sell_times, sell_prices, marker='v', color='red', s=100, label='Sell')
        
        ax1.set_title('Backtest Results')
        ax1.set_ylabel('Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot equity curve
        equity_times = self.df['timestamp'].iloc[50:50+len(self.equity)]
        ax2.plot(equity_times, self.equity, label='Equity')
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Equity')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.savefig('backtest_results.png')
        print("Backtest results saved to backtest_results.png")
        plt.show() 