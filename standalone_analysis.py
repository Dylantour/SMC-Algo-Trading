#!/usr/bin/env python3
"""
Standalone Market Analysis Tool
This script provides market data analysis without any UI dependencies.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from BinanceBot.standalone_client import StandaloneClient
import BinanceBot.key as key
from Candle import Candle
import time
from datetime import datetime

def to_candle_list(data):
    """Convert raw data to Candle objects"""
    candles = []
    for i in range(len(data)):
        row = data.iloc[i]
        c = Candle(None)
        c.date = i
        c.O = row['open']
        c.H = row['high']
        c.L = row['low']
        c.C = row['close']
        c.trend()
        candles.append(c)
    return candles

def identify_structure(candles):
    """Identify market structure from candles"""
    # Identify trend blocks
    blocks = []
    current_block = []
    last_trend = None
    
    for candle in candles:
        current_trend = candle.trend()
        if last_trend is None or current_trend == last_trend:
            current_block.append(candle)
        else:
            blocks.append(current_block)
            current_block = [candle]
        last_trend = current_trend
    
    if current_block:
        blocks.append(current_block)
    
    # Identify swing highs and lows
    swing_points = []
    for i in range(1, len(blocks)):
        prev_block = blocks[i-1]
        curr_block = blocks[i]
        
        if prev_block[0].trend() == "bull":
            # End of bullish block - potential swing high
            high_candle = max(prev_block, key=lambda x: x.H)
            swing_points.append(("H", high_candle.date, high_candle.H))
        else:
            # End of bearish block - potential swing low
            low_candle = min(prev_block, key=lambda x: x.L)
            swing_points.append(("L", low_candle.date, low_candle.L))
    
    return blocks, swing_points

def plot_market_structure(candles, blocks, swing_points):
    """Plot market structure analysis"""
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(15, 8))
    
    # Plot candles
    dates = [c.date for c in candles]
    highs = [c.H for c in candles]
    lows = [c.L for c in candles]
    opens = [c.O for c in candles]
    closes = [c.C for c in candles]
    
    # Plot candlesticks
    for i, candle in enumerate(candles):
        color = 'green' if candle.trend() == 'bull' else 'red'
        # Plot candle body
        ax.plot([i, i], [candle.O, candle.C], color=color, linewidth=4)
        # Plot candle wick
        ax.plot([i, i], [candle.L, candle.H], color='black', linewidth=1)
    
    # Plot swing points
    for point_type, date, price in swing_points:
        if point_type == "H":
            ax.scatter(date, price, color='blue', s=100, marker='^')
            ax.text(date, price*1.01, "H", fontsize=12)
        else:
            ax.scatter(date, price, color='purple', s=100, marker='v')
            ax.text(date, price*0.99, "L", fontsize=12)
    
    # Set labels and title
    ax.set_title(f"Market Structure Analysis - {datetime.now().strftime('%Y-%m-%d')}")
    ax.set_xlabel("Candle Number")
    ax.set_ylabel("Price")
    ax.grid(True)
    
    plt.tight_layout()
    plt.savefig("market_structure.png")
    print(f"Market structure analysis saved to market_structure.png")
    plt.show()

def main():
    """Main function"""
    print("=" * 50)
    print("SMC Market Structure Analysis Tool")
    print("=" * 50)
    
    try:
        # Initialize client
        print("Initializing Binance client...")
        client = StandaloneClient(key.key, key.secret)
        
        # Set parameters
        client.pair = "BTCBUSD"  # Trading pair
        client.interval = "1h"   # 1-hour candles
        client.df_length = 100   # Number of candles to fetch
        
        # Get market data
        print(f"Fetching data for {client.pair} on {client.interval} timeframe...")
        df = client.get_candles()
        
        if df is None or len(df) == 0:
            print("Error: No data received from Binance")
            return 1
        
        print(f"Received {len(df)} candles")
        
        # Convert to candle objects
        candles = to_candle_list(df)
        
        # Identify market structure
        print("Analyzing market structure...")
        blocks, swing_points = identify_structure(candles)
        
        # Print analysis results
        print(f"Identified {len(blocks)} trend blocks")
        print(f"Identified {len(swing_points)} swing points")
        
        # Plot results
        print("Generating market structure plot...")
        plot_market_structure(candles, blocks, swing_points)
        
        # Run backtest
        print("\nRunning backtest...")
        client.backtest_init()
        client.backtest_loop()
        
    except KeyboardInterrupt:
        print("Analysis stopped by user")
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 