#!/usr/bin/env python3
"""
trade.py - ICT Trading Strategy Implementation

This script implements the ICT trading strategy for the Binance trading bot.
"""

import os
import sys
import time
import datetime
import logging
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import deque

# Import BinanceClient
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from BinanceBot.BinanceClient import BinanceClient

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(message)s',
                   handlers=[
                       logging.FileHandler("logs/trade_py.log"),
                       logging.StreamHandler(sys.stdout)
                   ])
logger = logging.getLogger(__name__)

class LoggingPrinter:
    def __init__(self):
        self.old_stdout = sys.stdout
        self.log_file = open("logs/trade_py.log", "a")

    def write(self, text):
        self.old_stdout.write(text)
        self.log_file.write(text)
        self.log_file.flush()
    
    def flush(self):
        self.old_stdout.flush()
        self.log_file.flush()

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, type, value, traceback):
        sys.stdout = self.old_stdout
        self.log_file.close()

class ICTTraderClient(BinanceClient):
    def __init__(self, _key, _secret):
        """
        Initialize the ICT Trading Strategy Client.
        
        Args:
            _key (str): Binance API key
            _secret (str): Binance API secret
        """
        logger.info("Initializing ICT Trading Strategy Client")
        super().__init__(_key, _secret)
        
        # ICT specific parameters
        self.htf_interval = "1h"
        self.htf_df_length = 50
        self.min_fvg_size = 0.0005
        self.risk_per_trade = 0.01
        self.rr_ratio = 2.0
        self.position_open = False
        self.position_type = None
        self.htf_bias = "Neutral"
        self.active_fvgs = []
        self.valid_entries = []
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.risk_amount = 0
        self.trail_stop = 0.8
        self.trail_stop_enabled = True
        self.plot = False
        self.trade_history = []
        
        # Create directories for charts and logs
        os.makedirs("charts", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        # Debug mode
        self.debug_mode = True
        logger.info("ICT Trading Strategy Client initialized")
        
    def update(self):
        """
        Update market data and account information.
        """
        try:
            logger.info(f"Updating market data for {self.pair}")
            # Call the parent method to update base data
            super().update()
            
            # Update HTF data
            self.update_htf_data()
            
            # Process data for ICT strategy
            self.data_process()
            
            # Print status (debug)
            if self.debug_mode:
                logger.info(f"Current price: {self.asset_price}")
                logger.info(f"HTF Bias: {self.htf_bias}")
                logger.info(f"Active FVGs: {len(self.active_fvgs)}")
                logger.info(f"Position open: {self.position_open}")
                if self.position_open:
                    logger.info(f"Position type: {self.position_type}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error updating market data: {e}", exc_info=True)
            return False
    
    def update_htf_data(self):
        """
        Update higher timeframe data for market structure analysis.
        """
        try:
            logger.info(f"Updating HTF data ({self.htf_interval})")
            
            # Get HTF candles from Binance
            htf_candles = self.client.get_klines(
                symbol=self.pair,
                interval=self.htf_interval,
                limit=self.htf_df_length
            )
            
            # Create HTF DataFrame
            self.htf_df = pd.DataFrame(htf_candles, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'trades',
                'taker_buy_base', 'taker_buy_quote', 'ignored'
            ])
            
            # Convert string columns to numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                self.htf_df[col] = pd.to_numeric(self.htf_df[col])
                
            # Convert timestamp to datetime
            self.htf_df['timestamp'] = pd.to_datetime(self.htf_df['timestamp'], unit='ms')
            
            if self.debug_mode:
                logger.info(f"HTF data updated - {len(self.htf_df)} candles")
                
            return True
            
        except Exception as e:
            logger.error(f"Error updating HTF data: {e}", exc_info=True)
            return False

    def data_process(self):
        """
        Process market data for ICT strategy.
        """
        try:
            logger.info("Processing market data for ICT strategy")
            
            # Process higher timeframe data for market structure
            self.process_htf_data()
            
            # Process lower timeframe data for entries
            self.process_ltf_data()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing data: {e}", exc_info=True)
            return False
    
    def process_htf_data(self):
        """
        Process higher timeframe data to determine market structure.
        """
        try:
            if not hasattr(self, 'htf_df') or self.htf_df.empty:
                logger.warning("No HTF data available for processing")
                return False
                
            # Calculate swing highs and lows
            self.htf_df = self.calculate_swings(self.htf_df)
            
            # Determine market structure
            self.determine_market_structure(self.htf_df)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing HTF data: {e}", exc_info=True)
            return False
    
    def calculate_swings(self, df, window=5):
        """
        Calculate swing highs and lows in the dataframe.
        
        Args:
            df (DataFrame): Price dataframe
            window (int): Window size for identifying swings
            
        Returns:
            DataFrame: Updated dataframe with swing points
        """
        try:
            # Copy the dataframe to avoid modifying the original
            df = df.copy()
            
            # Initialize swing high/low columns
            df['swing_high'] = False
            df['swing_low'] = False
            
            # Calculate swing highs
            for i in range(window, len(df) - window):
                # Check if current high is the highest in the window
                if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                    df.loc[df.index[i], 'swing_high'] = True
            
            # Calculate swing lows
            for i in range(window, len(df) - window):
                # Check if current low is the lowest in the window
                if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                    df.loc[df.index[i], 'swing_low'] = True
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating swings: {e}", exc_info=True)
            return df
    
    def determine_market_structure(self, df):
        """
        Determine market structure based on swing highs and lows.
        
        Args:
            df (DataFrame): Dataframe with swing high/low columns
        """
        try:
            # Get recent swings
            recent_df = df.iloc[-20:].copy()
            
            # Get swing highs and lows
            swing_highs = recent_df[recent_df['swing_high']]['high'].tolist()
            swing_lows = recent_df[recent_df['swing_low']]['low'].tolist()
            
            # Ensure we have at least 2 swing points of each type
            if len(swing_highs) < 2 or len(swing_lows) < 2:
                logger.warning("Not enough swing points to determine market structure")
                self.htf_bias = "Neutral"
                return
            
            # Check for higher highs and higher lows (uptrend)
            if swing_highs[-1] > swing_highs[-2] and swing_lows[-1] > swing_lows[-2]:
                self.htf_bias = "Bullish"
                logger.info("Market structure: Bullish - Higher Highs, Higher Lows")
                
            # Check for lower highs and lower lows (downtrend)
            elif swing_highs[-1] < swing_highs[-2] and swing_lows[-1] < swing_lows[-2]:
                self.htf_bias = "Bearish"
                logger.info("Market structure: Bearish - Lower Highs, Lower Lows")
                
            # Check for lower highs and higher lows (consolidation - potential reversal up)
            elif swing_highs[-1] < swing_highs[-2] and swing_lows[-1] > swing_lows[-2]:
                self.htf_bias = "Consolidation"
                logger.info("Market structure: Consolidation - Lower Highs, Higher Lows")
                
            # Check for higher highs and lower lows (expansion - potential reversal down)
            elif swing_highs[-1] > swing_highs[-2] and swing_lows[-1] < swing_lows[-2]:
                self.htf_bias = "Expansion"
                logger.info("Market structure: Expansion - Higher Highs, Lower Lows")
                
            else:
                self.htf_bias = "Neutral"
                logger.info("Market structure: Neutral - No clear pattern")
            
            # Save chart if plot is enabled
            if self.plot:
                self.plot_market_structure(recent_df)
                
        except Exception as e:
            logger.error(f"Error determining market structure: {e}", exc_info=True)
            self.htf_bias = "Neutral"
    
    def plot_market_structure(self, df):
        """
        Plot market structure for visualization.
        
        Args:
            df (DataFrame): Dataframe with market structure
        """
        try:
            plt.figure(figsize=(12, 6))
            
            # Plot price
            plt.plot(df.index, df['close'], color='blue', label='Price')
            
            # Plot swing highs and lows
            plt.scatter(df[df['swing_high']].index, df[df['swing_high']]['high'], 
                      color='red', marker='^', s=100, label='Swing High')
            plt.scatter(df[df['swing_low']].index, df[df['swing_low']]['low'], 
                      color='green', marker='v', s=100, label='Swing Low')
            
            # Add labels and title
            plt.title(f'Market Structure Analysis - {self.pair} ({self.htf_interval})')
            plt.xlabel('Time')
            plt.ylabel('Price')
            plt.legend()
            plt.grid(True)
            
            # Save the chart
            chart_path = f'charts/market_structure_{self.pair}_{self.htf_interval}.png'
            plt.savefig(chart_path)
            plt.close()
            logger.info(f"Market structure chart saved to {chart_path}")
            
        except Exception as e:
            logger.error(f"Error plotting market structure: {e}", exc_info=True)
    
    def process_ltf_data(self):
        """
        Process lower timeframe data for trade entries.
        """
        try:
            if not hasattr(self, 'df') or self.df.empty:
                logger.warning("No LTF data available for processing")
                return False
            
            # Detect liquidity sweeps
            self.df = self.detect_liquidity_sweeps(self.df)
            
            # Detect fair value gaps
            self.df = self.detect_fair_value_gaps(self.df)
            
            # Update active FVGs - remove filled ones
            self.update_active_fvgs(self.df)
            
            # Check for FVG retests (potential entries)
            self.check_fvg_retests(self.df)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing LTF data: {e}", exc_info=True)
            return False
    
    def detect_liquidity_sweeps(self, df):
        """
        Detect liquidity sweeps in price action.
        
        Args:
            df (DataFrame): Price dataframe
            
        Returns:
            DataFrame: Updated dataframe with liquidity sweep info
        """
        try:
            # Copy the dataframe to avoid modifying the original
            df = df.copy()
            
            # Calculate swing points
            df = self.calculate_swings(df, window=3)
            
            # Initialize liquidity sweep columns
            df['liquidity_sweep_high'] = False
            df['liquidity_sweep_low'] = False
            
            # Find liquidity sweeps
            sweep_count_high = 0
            sweep_count_low = 0
            
            for i in range(4, len(df)):
                # Bullish liquidity sweep (sweep lows then reverse up)
                if (df['swing_low'].iloc[i-2] and 
                    df['low'].iloc[i-1] < df['low'].iloc[i-2] and 
                    df['close'].iloc[i] > df['close'].iloc[i-1]):
                    df.loc[df.index[i-1], 'liquidity_sweep_low'] = True
                    sweep_count_low += 1
                    logger.debug(f"Bullish liquidity sweep detected at {df.index[i-1]}")
                
                # Bearish liquidity sweep (sweep highs then reverse down)
                if (df['swing_high'].iloc[i-2] and 
                    df['high'].iloc[i-1] > df['high'].iloc[i-2] and 
                    df['close'].iloc[i] < df['close'].iloc[i-1]):
                    df.loc[df.index[i-1], 'liquidity_sweep_high'] = True
                    sweep_count_high += 1
                    logger.debug(f"Bearish liquidity sweep detected at {df.index[i-1]}")
            
            logger.info(f"Detected liquidity sweeps - Bullish: {sweep_count_low}, Bearish: {sweep_count_high}")
            return df
            
        except Exception as e:
            logger.error(f"Error detecting liquidity sweeps: {e}", exc_info=True)
            return df
    
    def detect_fair_value_gaps(self, df):
        """
        Detect fair value gaps after liquidity sweeps.
        
        Args:
            df (DataFrame): Price dataframe with liquidity sweep info
            
        Returns:
            DataFrame: Updated dataframe with FVG info
        """
        try:
            # Copy the dataframe to avoid modifying the original
            df = df.copy()
            
            # Initialize FVG columns
            df['bullish_fvg'] = False
            df['bearish_fvg'] = False
            df['bullish_fvg_low'] = np.nan
            df['bullish_fvg_high'] = np.nan
            df['bearish_fvg_low'] = np.nan
            df['bearish_fvg_high'] = np.nan
            
            # Look for FVGs after liquidity sweeps
            for i in range(3, len(df)):
                # Bullish FVG after liquidity sweep low
                # (Low of the candle after the liquidity sweep is higher than the high of the candle before)
                if df['liquidity_sweep_low'].iloc[i-2]:
                    # Check for a gap up
                    if df['low'].iloc[i] > df['high'].iloc[i-2]:
                        # This is a bullish FVG
                        df.loc[df.index[i], 'bullish_fvg'] = True
                        df.loc[df.index[i], 'bullish_fvg_low'] = df['high'].iloc[i-2]
                        df.loc[df.index[i], 'bullish_fvg_high'] = df['low'].iloc[i]
                        
                        # Calculate FVG size as a percentage
                        fvg_size = (df['low'].iloc[i] - df['high'].iloc[i-2]) / df['high'].iloc[i-2]
                        
                        # Only consider FVGs larger than the minimum size
                        if fvg_size >= self.min_fvg_size:
                            # Add to active FVGs if not already tracked
                            fvg_data = {
                                'type': 'bullish',
                                'created_time': df.index[i],
                                'low': df['high'].iloc[i-2],
                                'high': df['low'].iloc[i],
                                'size': fvg_size,
                                'filled': False,
                                'retested': False
                            }
                            
                            # Check if this FVG is already in our list
                            if not any(fvg['created_time'] == fvg_data['created_time'] for fvg in self.active_fvgs):
                                self.active_fvgs.append(fvg_data)
                                logger.info(f"Bullish FVG detected: {fvg_size:.2%} size")
                
                # Bearish FVG after liquidity sweep high
                # (High of the candle after the liquidity sweep is lower than the low of the candle before)
                if df['liquidity_sweep_high'].iloc[i-2]:
                    # Check for a gap down
                    if df['high'].iloc[i] < df['low'].iloc[i-2]:
                        # This is a bearish FVG
                        df.loc[df.index[i], 'bearish_fvg'] = True
                        df.loc[df.index[i], 'bearish_fvg_low'] = df['high'].iloc[i]
                        df.loc[df.index[i], 'bearish_fvg_high'] = df['low'].iloc[i-2]
                        
                        # Calculate FVG size as a percentage
                        fvg_size = (df['low'].iloc[i-2] - df['high'].iloc[i]) / df['low'].iloc[i-2]
                        
                        # Only consider FVGs larger than the minimum size
                        if fvg_size >= self.min_fvg_size:
                            # Add to active FVGs if not already tracked
                            fvg_data = {
                                'type': 'bearish',
                                'created_time': df.index[i],
                                'low': df['high'].iloc[i],
                                'high': df['low'].iloc[i-2],
                                'size': fvg_size,
                                'filled': False,
                                'retested': False
                            }
                            
                            # Check if this FVG is already in our list
                            if not any(fvg['created_time'] == fvg_data['created_time'] for fvg in self.active_fvgs):
                                self.active_fvgs.append(fvg_data)
                                logger.info(f"Bearish FVG detected: {fvg_size:.2%} size")
            
            return df
            
        except Exception as e:
            logger.error(f"Error detecting fair value gaps: {e}", exc_info=True)
            return df
    
    def update_active_fvgs(self, df):
        """
        Update active FVGs based on current price action.
        
        Args:
            df (DataFrame): Current price dataframe
        """
        try:
            if not self.active_fvgs:
                return
                
            current_price = df['close'].iloc[-1]
            last_low = df['low'].iloc[-1]
            last_high = df['high'].iloc[-1]
            
            # Check each active FVG to see if it's been filled
            for fvg in self.active_fvgs:
                if fvg['filled']:
                    continue
                    
                if fvg['type'] == 'bullish':
                    # Bullish FVG is filled if price trades below the FVG low
                    if last_low <= fvg['low']:
                        fvg['filled'] = True
                        logger.info(f"Bullish FVG from {fvg['created_time']} has been filled")
                        
                elif fvg['type'] == 'bearish':
                    # Bearish FVG is filled if price trades above the FVG high
                    if last_high >= fvg['high']:
                        fvg['filled'] = True
                        logger.info(f"Bearish FVG from {fvg['created_time']} has been filled")
            
            # Remove filled FVGs that are older than 20 candles
            current_time = df.index[-1]
            self.active_fvgs = [fvg for fvg in self.active_fvgs if 
                              not fvg['filled'] or 
                              (current_time - fvg['created_time']).total_seconds() < 20 * 60 * self.get_interval_seconds()]
                              
        except Exception as e:
            logger.error(f"Error updating active FVGs: {e}", exc_info=True)
    
    def get_interval_seconds(self):
        """
        Convert interval string to seconds.
        
        Returns:
            int: Interval in seconds
        """
        interval = self.interval
        if interval.endswith('m'):
            return int(interval[:-1]) * 60
        elif interval.endswith('h'):
            return int(interval[:-1]) * 60 * 60
        elif interval.endswith('d'):
            return int(interval[:-1]) * 60 * 60 * 24
        return 60  # Default to 1m
    
    def check_fvg_retests(self, df):
        """
        Check if price is retesting any FVGs for potential entries.
        
        Args:
            df (DataFrame): Current price dataframe
        """
        try:
            if not self.active_fvgs or self.position_open:
                return
                
            current_price = df['close'].iloc[-1]
            
            # Reset valid entries
            self.valid_entries = []
            
            # Check each active FVG
            for fvg in self.active_fvgs:
                if fvg['filled'] or fvg['retested']:
                    continue
                
                # Only consider entries that align with HTF bias
                if fvg['type'] == 'bullish' and self.htf_bias != 'Bearish':
                    # Bullish entry when price retests the top of the FVG
                    if current_price <= fvg['high'] and current_price >= fvg['low']:
                        # Mark as retested
                        fvg['retested'] = True
                        
                        # Calculate entry parameters
                        entry_price = current_price
                        stop_loss = fvg['low'] * 0.996  # Just below the FVG low
                        risk_amount = entry_price - stop_loss
                        take_profit = entry_price + (risk_amount * self.rr_ratio)
                        
                        # Add to valid entries
                        entry_data = {
                            'type': 'long',
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'risk_amount': risk_amount,
                            'fvg': fvg
                        }
                        
                        self.valid_entries.append(entry_data)
                        logger.info(f"Bullish entry signal: Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}")
                        
                elif fvg['type'] == 'bearish' and self.htf_bias != 'Bullish':
                    # Bearish entry when price retests the bottom of the FVG
                    if current_price >= fvg['low'] and current_price <= fvg['high']:
                        # Mark as retested
                        fvg['retested'] = True
                        
                        # Calculate entry parameters
                        entry_price = current_price
                        stop_loss = fvg['high'] * 1.004  # Just above the FVG high
                        risk_amount = stop_loss - entry_price
                        take_profit = entry_price - (risk_amount * self.rr_ratio)
                        
                        # Add to valid entries
                        entry_data = {
                            'type': 'short',
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'risk_amount': risk_amount,
                            'fvg': fvg
                        }
                        
                        self.valid_entries.append(entry_data)
                        logger.info(f"Bearish entry signal: Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}")
            
            # Take the best entry if multiple are available
            if self.valid_entries:
                # Sort by risk/reward (higher is better)
                self.valid_entries.sort(key=lambda x: abs(x['take_profit'] - x['entry_price']) / abs(x['stop_loss'] - x['entry_price']), reverse=True)
                
                # Log the best entry
                best_entry = self.valid_entries[0]
                logger.info(f"Best entry: {best_entry['type'].upper()} at {best_entry['entry_price']}")
                
        except Exception as e:
            logger.error(f"Error checking FVG retests: {e}", exc_info=True)

    def manager(self):
        """
        Main strategy manager - decides when to enter and exit trades.
        """
        try:
            logger.info("=== MANAGER EXECUTION START ===")
            logger.info(f"Current position open: {self.position_open}")
            logger.info(f"Market bias: {self.htf_bias}")
            logger.info(f"Active FVGs: {len(self.active_fvgs)}")
            
            # Check if we're in a position
            if self.position_open:
                logger.info(f"Position type: {self.position_type}")
                logger.info(f"Entry price: {self.entry_price}")
                logger.info(f"Current price: {self.df['close'].iloc[-1]}")
                logger.info(f"Stop loss: {self.stop_loss}")
                logger.info(f"Take profit: {self.take_profit}")
                
                # Check if stop loss or take profit has been hit
                current_price = self.df['close'].iloc[-1]
                
                if self.position_type == 'long':
                    # Check if take profit hit
                    if current_price >= self.take_profit:
                        logger.info(f"Take profit hit at {current_price}")
                        self.trade_sell()
                        return
                    
                    # Check trailing stop if enabled
                    if self.trail_stop_enabled and current_price > self.entry_price:
                        trail_stop_price = current_price * (1 - self.trail_stop * (self.risk_amount / self.entry_price))
                        if trail_stop_price > self.stop_loss:
                            self.stop_loss = trail_stop_price
                            logger.info(f"Updated trailing stop to {self.stop_loss}")
                    
                    # Check if stop loss hit
                    if current_price <= self.stop_loss:
                        logger.info(f"Stop loss hit at {current_price}")
                        self.trade_sell()
                        return
                
                elif self.position_type == 'short':
                    logger.info("Checking short position conditions")
                    # Check if take profit hit
                    if current_price <= self.take_profit:
                        logger.info(f"Take profit hit at {current_price}")
                        self.trade_buy()
                        return
                    
                    # Check trailing stop if enabled
                    if self.trail_stop_enabled and current_price < self.entry_price:
                        trail_stop_price = current_price * (1 + self.trail_stop * (self.risk_amount / self.entry_price))
                        if trail_stop_price < self.stop_loss:
                            self.stop_loss = trail_stop_price
                            logger.info(f"Updated trailing stop to {self.stop_loss}")
                    
                    # Check if stop loss hit
                    if current_price >= self.stop_loss:
                        logger.info(f"Stop loss hit at {current_price}")
                        self.trade_buy()
                        return
            
            # Check for new entry if not in a position
            else:
                # Process the data for ICT strategy
                self.data_process()
                
                # Log FVG types
                bullish_fvgs = [fvg for fvg in self.active_fvgs if fvg['type'] == 'bullish']
                bearish_fvgs = [fvg for fvg in self.active_fvgs if fvg['type'] == 'bearish']
                logger.info(f"Bullish FVGs: {len(bullish_fvgs)}, Bearish FVGs: {len(bearish_fvgs)}")
                
                # Log valid entries
                logger.info(f"Valid entries: {len(self.valid_entries)}")
                for i, entry in enumerate(self.valid_entries):
                    logger.info(f"Entry {i+1}: Type: {entry['type']}, Price: {entry['entry_price']}, SL: {entry['stop_loss']}, TP: {entry['take_profit']}")
                
                # If we have valid entries, take the best one
                if self.valid_entries:
                    best_entry = self.valid_entries[0]
                    
                    # Set trade parameters
                    self.entry_price = best_entry['entry_price']
                    self.stop_loss = best_entry['stop_loss']
                    self.take_profit = best_entry['take_profit']
                    self.risk_amount = best_entry['risk_amount']
                    self.position_type = best_entry['type']
                    
                    # Enter the position
                    if best_entry['type'] == 'long':
                        logger.info(f"Entering LONG position at {self.entry_price}")
                        self.trade_buy()
                    else:
                        logger.info(f"Entering SHORT position at {self.entry_price}")
                        self.trade_sell()
                else:
                    logger.info("No valid entry signals found")
            
            logger.info("=== MANAGER EXECUTION END ===")
            
        except Exception as e:
            logger.error(f"Error in manager: {e}", exc_info=True)

    def trade_buy(self):
        """
        Execute a buy trade and update position tracking.
        """
        try:
            logger.info("Executing BUY trade")
            
            # Check if we're closing a short position or opening a long position
            if self.position_open and self.position_type == 'short':
                # Closing a short position
                logger.info("Closing SHORT position")
                super().trade_buy()
                
                # Calculate profit
                exit_price = self.df['close'].iloc[-1]
                profit_pct = (self.entry_price - exit_price) / self.entry_price * 100
                
                # Update trade history
                if hasattr(self, 'trade_history') and self.trade_history:
                    last_trade = self.trade_history[-1]
                    last_trade['exit_time'] = datetime.datetime.now()
                    last_trade['exit_price'] = exit_price
                    last_trade['profit_pct'] = profit_pct
                    last_trade['status'] = 'closed'
                    
                    logger.info(f"Closed SHORT position with {profit_pct:.2f}% profit")
                
                # Reset position tracking
                self.position_open = False
                self.position_type = None
            else:
                # Opening a long position
                logger.info("Opening LONG position")
                super().trade_buy()
                
                # Update position tracking
                self.position_open = True
                self.position_type = 'long'
                
                # Record trade in history
                trade = {
                    'type': 'long',
                    'entry_time': datetime.datetime.now(),
                    'entry_price': self.entry_price,
                    'stop_loss': self.stop_loss,
                    'take_profit': self.take_profit,
                    'risk_amount': self.risk_amount
                }
                
                # Add to trade history
                if not hasattr(self, 'trade_history'):
                    self.trade_history = []
                self.trade_history.append(trade)
                
                logger.info(f"LONG position opened at {self.entry_price}")
            
            return True
        except Exception as e:
            logger.error(f"Error executing BUY trade: {e}", exc_info=True)
            return False

    def trade_sell(self):
        """
        Execute a sell trade and update position tracking.
        """
        try:
            logger.info("Executing SELL trade")
            # Check if we're closing a position or opening a short
            if self.position_open and self.position_type == 'long':
                # Closing a long position
                logger.info("Closing LONG position")
                super().trade_sell()
                
                # Calculate profit
                exit_price = self.df['close'].iloc[-1]
                profit_pct = (exit_price - self.entry_price) / self.entry_price * 100
                
                # Update trade history
                if hasattr(self, 'trade_history') and self.trade_history:
                    last_trade = self.trade_history[-1]
                    last_trade['exit_time'] = datetime.datetime.now()
                    last_trade['exit_price'] = exit_price
                    last_trade['profit_pct'] = profit_pct
                    last_trade['status'] = 'closed'
                    
                    logger.info(f"Closed LONG position with {profit_pct:.2f}% profit")
                
                # Reset position tracking
                self.position_open = False
                self.position_type = None
                
            else:
                # Opening a short position
                logger.info("Opening SHORT position")
                super().trade_sell()
                
                # Update position tracking
                self.position_open = True
                self.position_type = 'short'
                
                # Record trade in history
                trade = {
                    'type': 'short',
                    'entry_time': datetime.datetime.now(),
                    'entry_price': self.entry_price,
                    'stop_loss': self.stop_loss,
                    'take_profit': self.take_profit,
                    'risk_amount': self.risk_amount
                }
                
                # Add to trade history
                if not hasattr(self, 'trade_history'):
                    self.trade_history = []
                self.trade_history.append(trade)
                
                logger.info(f"SHORT position opened at {self.entry_price}")
            
            return True
        except Exception as e:
            logger.error(f"Error executing SELL trade: {e}", exc_info=True)
            return False


# Main execution code when run directly
if __name__ == "__main__":
    with LoggingPrinter():
        trader = ICTTraderClient(key.key, key.secret)

        trader.trade_history = []
        trader.base_asset = "BUSD"
        trader.asset = "BTC"
        trader.pair = "BTCBUSD"
        trader.interval = "5m"  # Lower timeframe
        trader.df_length = 100
        trader.trail_stop_enabled = True
        trader.mode = "trade"
        trader.plot = False

        # Initialize and start trading
        trader.update()
        time.sleep(0.3)
        trader.start()



