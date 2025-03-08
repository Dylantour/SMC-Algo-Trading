#!/usr/bin/env python3
"""
trading_bot.py - Trading bot implementation for SMC-Algo-Trading
"""

import threading
import time
import json
import os
import logging
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
import random
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/trading_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

class TradingBot:
    """Trading bot implementation for executing trades based on signals"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.positions = []  # List of open positions
        self.trade_history = []  # List of closed trades
        self.total_trades = 0
        self.winning_trades = 0
        self.strategy = "Smart Money Concepts"
        self.position_size = 10  # Default 10% of available capital
        self.stop_loss_percent = 5
        self.take_profit_percent = 10
        self.symbols = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT"]
        self.active_symbols = ["BTCUSDT", "ETHUSDT"]  # Currently trading symbols
        self.timeframe = "1h"
        self._lock = threading.Lock()  # Thread safety
        self._last_update = datetime.datetime.now()
        
        # Account balance tracking
        self.initial_balance = 10000.0  # Initial account balance in USD
        self.current_balance = 10000.0  # Current balance (excluding open positions)
        self.equity = 10000.0  # Total equity (balance + open position values)
        self.balance_history = []  # Track balance changes over time
        
        # Real-time price data
        self.current_prices = {}  # Current prices for all symbols
        self.price_update_time = {}  # Last update time for each symbol
        self.price_update_thread = None
        self.price_update_interval = 60  # Update prices every 60 seconds (1 minute)
        
        # Initialize balance history with starting value
        self.balance_history.append({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "balance": self.current_balance,
            "equity": self.equity
        })

    def start(self, strategy: str, position_size: int, stop_loss: int, take_profit: int, symbols: List[str], timeframe: str) -> None:
        """Start the trading bot"""
        if self.running:
            logger.warning("Bot is already running")
            return
            
        with self._lock:
            self.strategy = strategy
            self.position_size = position_size
            self.stop_loss_percent = stop_loss
            self.take_profit_percent = take_profit
            self.active_symbols = symbols
            self.timeframe = timeframe
            self.running = True
            self._last_update = datetime.datetime.now()
            
        logger.info(f"Starting trading bot with strategy: {strategy}")
        logger.info(f"Trading symbols: {', '.join(symbols)}")
        
        # Start price update thread
        self.price_update_thread = threading.Thread(target=self._update_prices_thread, daemon=True)
        self.price_update_thread.start()
        
        # Create and start the bot thread
        self.thread = threading.Thread(target=self._run_bot, daemon=True)
        self.thread.start()
        
    def stop(self) -> None:
        """Stop the trading bot"""
        if not self.running:
            logger.warning("Bot is not running")
            return
            
        with self._lock:
            self.running = False
            
        logger.info("Stopping trading bot")
        if self.thread:
            self.thread.join(timeout=2.0)
            
    def get_status(self) -> Dict:
        """Get the current status of the trading bot"""
        with self._lock:
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            
            # Calculate current equity (balance + open position values)
            open_positions_value = sum(pos.get("position_value", 0) + pos.get("pnl_amount", 0) 
                                      for pos in self.positions)
            current_equity = self.current_balance + open_positions_value
            
            return {
                "running": self.running,
                "strategy": self.strategy,
                "position_size": self.position_size,
                "stop_loss": self.stop_loss_percent,
                "take_profit": self.take_profit_percent,
                "total_trades": self.total_trades,
                "win_rate": round(win_rate, 2),
                "open_positions": len(self.positions),
                "active_symbols": self.active_symbols,
                "timeframe": self.timeframe,
                "last_update": self._last_update.strftime("%Y-%m-%d %H:%M:%S"),
                "current_balance": round(self.current_balance, 2),
                "initial_balance": round(self.initial_balance, 2),
                "equity": round(current_equity, 2),
                "balance_change_percent": round((current_equity - self.initial_balance) / self.initial_balance * 100, 2)
            }
            
    def get_positions(self) -> List[Dict]:
        """Get current open positions"""
        with self._lock:
            return self.positions.copy()
            
    def get_trade_history(self) -> List[Dict]:
        """Get trade history"""
        with self._lock:
            return self.trade_history.copy()
            
    def get_balance_history(self) -> List[Dict]:
        """Get account balance history"""
        with self._lock:
            return self.balance_history.copy()
            
    def get_current_price(self, symbol: str) -> float:
        """Get the current price for a symbol"""
        with self._lock:
            # Check if we have a recent price (less than 2x update interval)
            now = datetime.datetime.now()
            if symbol in self.price_update_time:
                last_update = self.price_update_time[symbol]
                if (now - last_update).total_seconds() < (self.price_update_interval * 2):
                    return self.current_prices.get(symbol, 0.0)
            
            # If no recent price, fetch it now
            price = self._fetch_current_price(symbol)
            if price > 0:
                self.current_prices[symbol] = price
                self.price_update_time[symbol] = now
            return price or 0.0
    
    def _fetch_current_price(self, symbol: str) -> float:
        """Fetch the current price from Binance API"""
        try:
            # Use Binance public API to get ticker price
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if "price" in data:
                price = float(data["price"])
                logger.debug(f"Fetched price for {symbol}: {price}")
                return price
            else:
                logger.warning(f"Failed to get price for {symbol}: {data}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return 0.0
    
    def _update_prices_thread(self) -> None:
        """Thread to periodically update all prices"""
        logger.info("Price update thread started")
        
        while self.running:
            try:
                # Update prices for all active symbols
                for symbol in self.active_symbols:
                    price = self._fetch_current_price(symbol)
                    if price > 0:
                        with self._lock:
                            self.current_prices[symbol] = price
                            self.price_update_time[symbol] = datetime.datetime.now()
                
                # Also update positions with new prices
                self._update_positions_with_current_prices()
                
                # Sleep until next update
                time.sleep(self.price_update_interval)
                
            except Exception as e:
                logger.error(f"Error in price update thread: {e}", exc_info=True)
                time.sleep(self.price_update_interval)  # Still sleep on error
        
        logger.info("Price update thread stopped")
    
    def _update_positions_with_current_prices(self) -> None:
        """Update open positions with current market prices"""
        if not self.positions:
            return
            
        with self._lock:
            now = datetime.datetime.now()
            positions_to_remove = []  # Track positions to remove after the loop
            
            for pos in self.positions:
                symbol = pos["symbol"]
                # Get current price from our cached prices
                if symbol in self.current_prices:
                    new_price = self.current_prices[symbol]
                    
                    # Update position values
                    pos["current_price"] = round(new_price, 2)
                    pos["pnl"] = round((new_price - pos["entry_price"]) / pos["entry_price"] * 100, 2)
                    
                    if pos["type"] == "BUY":
                        pos["pnl_amount"] = round((new_price - pos["entry_price"]) * pos["position_size"], 2)
                    else:  # SELL
                        pos["pnl_amount"] = round((pos["entry_price"] - new_price) * pos["position_size"], 2)
                    
                    # Update duration
                    entry_time = datetime.datetime.strptime(pos["entry_time"], "%Y-%m-%d %H:%M:%S")
                    duration = now - entry_time
                    hours, remainder = divmod(duration.total_seconds(), 3600)
                    minutes, _ = divmod(remainder, 60)
                    pos["duration"] = f"{int(hours)}h {int(minutes)}m"
                    
                    # Check for stop loss or take profit
                    if (pos["type"] == "BUY" and new_price <= pos["stop_loss"]) or \
                    (pos["type"] == "SELL" and new_price >= pos["stop_loss"]) or \
                    (pos["type"] == "BUY" and new_price >= pos["take_profit"]) or \
                    (pos["type"] == "SELL" and new_price <= pos["take_profit"]):
                        # Close position and add to history
                        pos["exit_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                        pos["exit_price"] = new_price
                        pos["result"] = "WIN" if pos["pnl"] > 0 else "LOSS"
                        
                        # Add to trade history
                        self.trade_history.append(pos.copy())
                        
                        # Update account balance
                        self.current_balance += pos["pnl_amount"]
                        
                        # Mark for removal
                        positions_to_remove.append(pos)
                        
                        self.total_trades += 1
                        if pos["pnl"] > 0:
                            self.winning_trades += 1
                            
                        logger.info(f"Closed position: {pos['symbol']} {pos['type']} at {pos['exit_price']} with PnL: {pos['pnl']}%")
            
            # Remove closed positions
            for pos in positions_to_remove:
                self.positions.remove(pos)
                
            # Calculate current equity
            open_positions_value = sum(pos.get("position_value", 0) + pos.get("pnl_amount", 0) 
                                    for pos in self.positions)
            self.equity = self.current_balance + open_positions_value
            
            # Update balance history (periodically)
            if random.random() < 0.1:  # 10% chance to record history point
                self.balance_history.append({
                    "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "balance": self.current_balance,
                    "equity": self.equity
                })
                
    def _check_for_signals(self) -> None:
        """Check for new trading signals and open positions"""
        # In a real bot, this would analyze market data and generate signals
        # For this demo, occasionally open new positions randomly
        
        if not self.running or random.random() > 0.02:  # 2% chance of new position each cycle
            return
            
        # Only open new positions if we have room (less than 5 open positions)
        if len(self.positions) >= 5:
            return
            
        with self._lock:
            # Choose a random symbol that isn't already in our positions
            existing_symbols = {p["symbol"] for p in self.positions}
            available_symbols = [s for s in self.active_symbols if s not in existing_symbols]
            
            if not available_symbols:
                return
                
            symbol = random.choice(available_symbols)
            
            # Get current price for the symbol from our real-time data
            entry_price = self.get_current_price(symbol)
            if entry_price <= 0:
                logger.warning(f"Could not get price for {symbol}, skipping signal")
                return
                
            # Decide trade type (buy or sell)
            trade_type = "BUY" if random.random() > 0.5 else "SELL"
            
            # Calculate position size - ensure it fits within account balance
            position_sizes = {
                "BTCUSDT": 0.002,  # Smaller BTC size due to higher price
                "ETHUSDT": 0.05,    # Smaller ETH size 
                "XRPUSDT": 100,
                "ADAUSDT": 500,
                "SOLUSDT": 2,
                "DOTUSDT": 20
            }
            
            # Calculate affordable position size based on available balance and position_size percentage
            max_position_value = self.current_balance * (self.position_size / 100)
            
            # Default position size from the table
            default_position_size = position_sizes.get(symbol, 1)
            
            # Calculate the position value with default size
            default_position_value = default_position_size * entry_price
            
            # If default is too large, adjust to fit within max position value
            if default_position_value > max_position_value:
                position_size = max_position_value / entry_price
            else:
                position_size = default_position_size
                
            position_value = position_size * entry_price
            
            # Check if we have enough balance
            if position_value > self.current_balance:
                logger.info(f"Insufficient balance to open position for {symbol}")
                return
                
            # Deduct position value from balance
            self.current_balance -= position_value
            
            # Calculate stop loss and take profit
            if trade_type == "BUY":
                stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
                take_profit = entry_price * (1 + self.take_profit_percent / 100)
            else:  # SELL
                stop_loss = entry_price * (1 + self.stop_loss_percent / 100)
                take_profit = entry_price * (1 - self.take_profit_percent / 100)
                
            # Create new position
            now = datetime.datetime.now()
            new_position = {
                "symbol": symbol,
                "entry_price": round(entry_price, 2),
                "current_price": round(entry_price, 2),
                "position_size": round(position_size, 5),
                "position_value": round(position_value, 2),
                "pnl": 0.0,
                "pnl_amount": 0.0,
                "entry_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": "0h 0m",
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "type": trade_type
            }
            
            self.positions.append(new_position)
            
            # Update equity after opening position
            open_positions_value = sum(pos.get("position_value", 0) + pos.get("pnl_amount", 0) 
                                      for pos in self.positions)
            self.equity = self.current_balance + open_positions_value
            
            logger.info(f"Opened new position: {symbol} {trade_type} at {entry_price}")

    def _run_bot(self) -> None:
        """Main bot loop - runs in a separate thread"""
        logger.info("Bot thread started")
        
        # Simulate initial positions
        self._simulate_initial_positions_with_real_prices()
        
        while self.running:
            try:
                # We no longer need to simulate market movements as we're getting real prices
                # in the _update_prices_thread
                
                # Check for new trading signals
                self._check_for_signals()
                
                # Update timestamp
                with self._lock:
                    self._last_update = datetime.datetime.now()
                    
                # Save state
                self._save_state()
                
                # Sleep to avoid high CPU usage
                time.sleep(5)  # Check for signals every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in bot thread: {e}", exc_info=True)
                time.sleep(10)  # Wait longer if there was an error
                
        logger.info("Bot thread stopped")
        
    def _simulate_initial_positions_with_real_prices(self) -> None:
        """Initialize positions using real market prices"""
        now = datetime.datetime.now()
        
        # Fetch current prices for our symbols
        for symbol in self.active_symbols:
            price = self._fetch_current_price(symbol)
            if price > 0:
                self.current_prices[symbol] = price
                self.price_update_time[symbol] = now
        
        # Create some mock positions with real prices
        positions = []
        
        # BTC position
        if "BTCUSDT" in self.current_prices and self.current_prices["BTCUSDT"] > 0:
            btc_price = self.current_prices["BTCUSDT"]
            positions.append({
                "symbol": "BTCUSDT",
                "entry_price": round(btc_price * 0.995, 2),  # Slightly below current price
                "current_price": round(btc_price, 2),
                "position_size": 0.01,  # BTC amount
                "position_value": round(btc_price * 0.01 * 0.995, 2),  # USD value
                "pnl": 0.5,  # Percentage
                "pnl_amount": round(btc_price * 0.01 * 0.005, 2),  # USD amount
                "entry_time": (now - datetime.timedelta(hours=4, minutes=21)).strftime("%Y-%m-%d %H:%M:%S"),
                "duration": "4h 21m",
                "stop_loss": round(btc_price * 0.95, 2),
                "take_profit": round(btc_price * 1.05, 2),
                "type": "BUY"
            })
        
        # ETH position
        if "ETHUSDT" in self.current_prices and self.current_prices["ETHUSDT"] > 0:
            eth_price = self.current_prices["ETHUSDT"]
            positions.append({
                "symbol": "ETHUSDT",
                "entry_price": round(eth_price * 0.99, 2),  # Slightly below current price
                "current_price": round(eth_price, 2),
                "position_size": 0.15,  # ETH amount
                "position_value": round(eth_price * 0.15 * 0.99, 2),  # USD value
                "pnl": 1.0,  # Percentage
                "pnl_amount": round(eth_price * 0.15 * 0.01, 2),  # USD amount
                "entry_time": (now - datetime.timedelta(hours=2, minutes=48)).strftime("%Y-%m-%d %H:%M:%S"),
                "duration": "2h 48m",
                "stop_loss": round(eth_price * 0.95, 2),
                "take_profit": round(eth_price * 1.05, 2),
                "type": "BUY"
            })
        
        with self._lock:
            self.positions = positions
            
            # Create some mock trade history
            pnl_sum = 0
            history = []
            
            # Successful BTC trade
            if "BTCUSDT" in self.current_prices:
                btc_price = self.current_prices["BTCUSDT"]
                btc_pnl = round(btc_price * 0.01 * 0.02, 2)  # 2% profit on BTC
                pnl_sum += btc_pnl
                
                history.append({
                    "symbol": "BTCUSDT",
                    "entry_price": round(btc_price * 0.98, 2),
                    "exit_price": round(btc_price, 2),
                    "position_size": 0.01,
                    "pnl": 2.0,
                    "pnl_amount": btc_pnl,
                    "entry_time": (now - datetime.timedelta(hours=16, minutes=33)).strftime("%Y-%m-%d %H:%M:%S"),
                    "exit_time": (now - datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
                    "duration": "7h 33m",
                    "type": "BUY",
                    "result": "WIN"
                })
            
            # Successful SOL trade
            if "SOLUSDT" in self.current_prices:
                sol_price = self.current_prices["SOLUSDT"]
                sol_pnl = round(sol_price * 1.0 * 0.025, 2)  # 2.5% profit on SOL
                pnl_sum += sol_pnl
                
                history.append({
                    "symbol": "SOLUSDT",
                    "entry_price": round(sol_price * 0.975, 2),
                    "exit_price": round(sol_price, 2),
                    "position_size": 1.0,
                    "pnl": 2.5,
                    "pnl_amount": sol_pnl,
                    "entry_time": (now - datetime.timedelta(hours=15)).strftime("%Y-%m-%d %H:%M:%S"),
                    "exit_time": (now - datetime.timedelta(hours=6, minutes=45)).strftime("%Y-%m-%d %H:%M:%S"),
                    "duration": "8h 15m",
                    "type": "BUY",
                    "result": "WIN"
                })
            
            # Successful ETH trade
            if "ETHUSDT" in self.current_prices:
                eth_price = self.current_prices["ETHUSDT"]
                eth_pnl = round(eth_price * 0.1 * 0.027, 2)  # 2.7% profit on ETH
                pnl_sum += eth_pnl
                
                history.append({
                    "symbol": "ETHUSDT",
                    "entry_price": round(eth_price * 0.973, 2),
                    "exit_price": round(eth_price, 2),
                    "position_size": 0.1,
                    "pnl": 2.7,
                    "pnl_amount": eth_pnl,
                    "entry_time": (now - datetime.timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S"),
                    "exit_time": (now - datetime.timedelta(hours=5, minutes=37)).strftime("%Y-%m-%d %H:%M:%S"),
                    "duration": "4h 23m",
                    "type": "BUY",
                    "result": "WIN"
                })
            
            # Losing ADA trade
            if "ADAUSDT" in self.current_prices:
                ada_price = self.current_prices["ADAUSDT"]
                ada_pnl = -round(ada_price * 1000 * 0.034, 2)  # 3.4% loss on ADA
                pnl_sum += ada_pnl
                
                history.append({
                    "symbol": "ADAUSDT",
                    "entry_price": round(ada_price * 1.034, 2),
                    "exit_price": round(ada_price, 2),
                    "position_size": 1000,
                    "pnl": -3.4,
                    "pnl_amount": ada_pnl,
                    "entry_time": (now - datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
                    "exit_time": (now - datetime.timedelta(hours=4, minutes=40)).strftime("%Y-%m-%d %H:%M:%S"),
                    "duration": "3h 20m",
                    "type": "SELL",
                    "result": "LOSS"
                })
            
            # Update account balance based on trade history
            self.current_balance = self.initial_balance + pnl_sum
            
            # Calculate equity (balance + open positions)
            open_positions_value = sum(pos["position_value"] + pos["pnl_amount"] for pos in positions)
            self.equity = self.current_balance + open_positions_value
            
            self.trade_history = history
            self.total_trades = len(history)
            self.winning_trades = sum(1 for trade in history if trade["result"] == "WIN")
            
            # Add current balance to history
            self.balance_history.append({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "balance": self.current_balance,
                "equity": self.equity
            })

    def _save_state(self) -> None:
        """Save the current state to disk for persistence"""
        state = {
            "positions": self.positions,
            "trade_history": self.trade_history,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "strategy": self.strategy,
            "position_size": self.position_size,
            "stop_loss": self.stop_loss_percent,
            "take_profit": self.take_profit_percent,
            "active_symbols": self.active_symbols,
            "timeframe": self.timeframe,
            "last_update": self._last_update.strftime("%Y-%m-%d %H:%M:%S"),
            "current_balance": self.current_balance,
            "initial_balance": self.initial_balance,
            "equity": self.equity,
            "balance_history": self.balance_history
        }
        
        try:
            with open("logs/bot_state.json", "w") as f:
                json.dump(state, f)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
            
    def load_state(self) -> bool:
        """Load the state from disk"""
        try:
            if not os.path.exists("logs/bot_state.json"):
                return False
                
            with open("logs/bot_state.json", "r") as f:
                state = json.load(f)
                
            with self._lock:
                self.positions = state.get("positions", [])
                self.trade_history = state.get("trade_history", [])
                self.total_trades = state.get("total_trades", 0)
                self.winning_trades = state.get("winning_trades", 0)
                self.strategy = state.get("strategy", self.strategy)
                self.position_size = state.get("position_size", self.position_size)
                self.stop_loss_percent = state.get("stop_loss", self.stop_loss_percent)
                self.take_profit_percent = state.get("take_profit", self.take_profit_percent)
                self.active_symbols = state.get("active_symbols", self.active_symbols)
                self.timeframe = state.get("timeframe", self.timeframe)
                self.current_balance = state.get("current_balance", self.initial_balance)
                self.initial_balance = state.get("initial_balance", self.initial_balance)
                self.equity = state.get("equity", self.initial_balance)
                self.balance_history = state.get("balance_history", [])
                
                last_update_str = state.get("last_update", None)
                if last_update_str:
                    try:
                        self._last_update = datetime.datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        self._last_update = datetime.datetime.now()
                        
            return True
            
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return False

# Create a singleton instance
trading_bot = TradingBot()

# Helper functions for external use
def start_bot(strategy="Smart Money Concepts", position_size=10, stop_loss=5, take_profit=10, 
              symbols=None, timeframe="1h") -> None:
    """Start the trading bot with the specified parameters"""
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT"]
    trading_bot.start(strategy, position_size, stop_loss, take_profit, symbols, timeframe)
    
def stop_bot() -> None:
    """Stop the trading bot"""
    trading_bot.stop()
    
def get_bot_status() -> Dict:
    """Get the current bot status"""
    return trading_bot.get_status()
    
def get_open_positions() -> List[Dict]:
    """Get current open positions"""
    return trading_bot.get_positions()
    
def get_trade_history() -> List[Dict]:
    """Get trade history"""
    return trading_bot.get_trade_history()
    
def get_balance_history() -> List[Dict]:
    """Get account balance history"""
    return trading_bot.get_balance_history()
    
def load_bot_state() -> bool:
    """Load the bot state from disk"""
    return trading_bot.load_state()

# Initialize by loading saved state if available
load_bot_state()

# If this file is run directly, start the bot for testing
if __name__ == "__main__":
    print("Starting trading bot for testing...")
    start_bot()
    print("Bot started. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping bot...")
        stop_bot()
        print("Bot stopped.") 