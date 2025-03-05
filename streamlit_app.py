#!/usr/bin/env python3
"""
Streamlit UI for SMC-Algo-Trading
This provides a simple, cross-platform UI for the trading algorithm
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
from datetime import datetime
import os
import sys

# Import project modules
from Candle import Candle
from streamlit_vertex import Vertex
try:
    from BinanceBot.standalone_client import StandaloneClient
    import BinanceBot.key as key
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    st.warning("Binance integration not available. Some features will be disabled.")

# Page config
st.set_page_config(
    page_title="SMC Algo Trading",
    page_icon="📈",
    layout="wide",
)

# Header
st.title("Smart Money Concepts Algo Trading")
st.markdown("A Python library for building trading bots following Smart Money Concepts (SMC).")

# Sidebar for controls
st.sidebar.header("Market Controls")
symbol = st.sidebar.selectbox(
    "Select Symbol",
    ["BTCUSDT", "ETHUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT"],
    index=0
)

timeframe = st.sidebar.selectbox(
    "Select Timeframe",
    ["1m", "3m", "5m", "15m", "1h", "4h", "1d", "1w", "1M"],
    index=4
)

candle_count = st.sidebar.slider(
    "Number of Candles", 
    min_value=50, 
    max_value=500, 
    value=150,
    step=50
)

smoothing = st.sidebar.slider(
    "Smoothing Factor", 
    min_value=0, 
    max_value=100, 
    value=50,
    step=5
)

# Function to fetch data from Binance
@st.cache_data(ttl=60)
def fetch_market_data(symbol, timeframe, limit):
    if not BINANCE_AVAILABLE:
        # Return sample data if Binance is not available
        return generate_sample_data(limit)
    
    try:
        # Initialize client
        client = StandaloneClient(key.key, key.secret)
        
        # Fetch candle data
        start = int((time.time() - (60 * limit) - 120 * 60) * 1000)
        
        klines = client.client.get_historical_klines(
            symbol=symbol,
            interval=timeframe,
            start_str=str(start)
        )
        
        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Convert types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return generate_sample_data(limit)

def generate_sample_data(limit):
    """Generate sample data for demonstration when Binance is not available"""
    np.random.seed(42)  # For reproducibility
    
    # Start with a base price
    base_price = 30000.0
    
    # Generate timestamps
    now = datetime.now()
    timestamps = [now - datetime.timedelta(minutes=i) for i in range(limit, 0, -1)]
    
    # Generate price movements with some trend and volatility
    price_changes = np.random.normal(0, 1, limit) * 50  # Random price changes
    
    # Add a trend component
    trend = np.linspace(0, 500, limit) * np.sin(np.linspace(0, np.pi * 2, limit))
    price_changes += trend
    
    # Calculate OHLC data
    data = []
    current_price = base_price
    
    for i in range(limit):
        current_price += price_changes[i]
        
        # Generate candle data with some randomness
        open_price = current_price
        close_price = current_price + np.random.normal(0, 1) * 30
        high_price = max(open_price, close_price) + abs(np.random.normal(0, 1)) * 20
        low_price = min(open_price, close_price) - abs(np.random.normal(0, 1)) * 20
        volume = abs(np.random.normal(0, 1)) * 10 + 5
        
        data.append({
            'timestamp': timestamps[i],
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data)

def to_candle_list(data):
    """Convert raw data to Candle objects"""
    candles = []
    for i in range(len(data)):
        row = data.iloc[i]
        c = Candle(None)
        c.date = i
        c.O = float(row['open'])
        c.H = float(row['high'])
        c.L = float(row['low'])
        c.C = float(row['close'])
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
            if current_block:  # Only append if not empty
                blocks.append(current_block)
            current_block = [candle]
        last_trend = current_trend
    
    if current_block:
        blocks.append(current_block)
    
    # Identify swing points
    swing_points = []
    vertices = []
    
    for i in range(1, len(blocks)):
        prev_block = blocks[i-1]
        curr_block = blocks[i]
        
        if prev_block[0].trend() == "bull" and curr_block[0].trend() == "bear":
            # Higher High (HH) point
            swing_point = max(prev_block, key=lambda x: x.H)
            swing_points.append(('HH', swing_point))
            
            # Create Vertex
            v = Vertex(swing_point.date, swing_point.H)
            v.type = "HH"
            vertices.append(v)
            
        elif prev_block[0].trend() == "bear" and curr_block[0].trend() == "bull":
            # Lower Low (LL) point
            swing_point = min(prev_block, key=lambda x: x.L)
            swing_points.append(('LL', swing_point))
            
            # Create Vertex
            v = Vertex(swing_point.date, swing_point.L)
            v.type = "LL"
            vertices.append(v)
    
    # Connect vertices
    for i in range(1, len(vertices)):
        vertices[i].set_last(vertices[i-1])
        vertices[i-1].set_next(vertices[i])
    
    return blocks, swing_points, vertices

def plot_market_structure(candles, blocks, swing_points):
    """Plot the market structure with matplotlib"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot candles
    dates = range(len(candles))
    
    # Calculate width for candlesticks
    width = 0.6
    
    # Plot up and down candles separately for color
    up_candles = [c for c in candles if c.C >= c.O]
    down_candles = [c for c in candles if c.C < c.O]
    
    # Plot up candles
    for c in up_candles:
        ax.plot([c.date, c.date], [c.L, c.H], color='green', linewidth=1)
        ax.bar(c.date, c.C - c.O, width, bottom=c.O, color='green', alpha=0.5)
    
    # Plot down candles
    for c in down_candles:
        ax.plot([c.date, c.date], [c.L, c.H], color='red', linewidth=1)
        ax.bar(c.date, c.C - c.O, width, bottom=c.O, color='red', alpha=0.5)
    
    # Plot swing points
    for type_point, point in swing_points:
        color = 'blue' if type_point == 'HH' else 'purple'
        value = point.H if type_point == 'HH' else point.L
        ax.scatter(point.date, value, color=color, s=100, marker='o')
        ax.annotate(type_point, (point.date, value), xytext=(5, 5), 
                   textcoords='offset points', color=color, fontweight='bold')
    
    # Connect swing points with lines
    hh_points = [(p.date, p.H) for t, p in swing_points if t == 'HH']
    ll_points = [(p.date, p.L) for t, p in swing_points if t == 'LL']
    
    if len(hh_points) >= 2:
        for i in range(1, len(hh_points)):
            ax.plot([hh_points[i-1][0], hh_points[i][0]], 
                   [hh_points[i-1][1], hh_points[i][1]], 
                   'b--', alpha=0.7)
    
    if len(ll_points) >= 2:
        for i in range(1, len(ll_points)):
            ax.plot([ll_points[i-1][0], ll_points[i][0]], 
                   [ll_points[i-1][1], ll_points[i][1]], 
                   'purple', linestyle='--', alpha=0.7)
    
    # Add grid and labels
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('Candle Index')
    ax.set_ylabel('Price')
    ax.set_title(f'{symbol} Market Structure ({timeframe})')
    
    return fig

def analyze_market_structure(vertices):
    """Analyze the market structure based on vertices"""
    if not vertices:
        return "Insufficient data"
    
    # Count different vertex types
    hh_count = sum(1 for v in vertices if v.type == "HH")
    ll_count = sum(1 for v in vertices if v.type == "LL")
    
    # Determine market structure
    if hh_count > ll_count:
        return "Uptrend"
    elif ll_count > hh_count:
        return "Downtrend"
    else:
        return "Range"

# Main app
if __name__ == "__main__" or 'streamlit' in sys.modules:
    with st.spinner('Fetching market data...'):
        data = fetch_market_data(symbol, timeframe, candle_count)
    
    if not data.empty:
        # Analysis tab
        tab1, tab2, tab3 = st.tabs(["Market Structure", "Raw Data", "About"])
        
        with tab1:
            # Convert data to candles
            candles = to_candle_list(data)
            
            # Analyze market structure
            blocks, swing_points, vertices = identify_structure(candles)
            
            # Plot the results
            fig = plot_market_structure(candles, blocks, swing_points)
            st.pyplot(fig)
            
            # Market insights
            st.subheader("Market Insights")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                hh_count = sum(1 for p in swing_points if p[0] == 'HH')
                ll_count = sum(1 for p in swing_points if p[0] == 'LL')
                st.metric("Higher Highs", hh_count)
                st.metric("Lower Lows", ll_count)
            
            with col2:
                current_trend = "Bullish" if candles[-1].trend() == "bull" else "Bearish"
                st.metric("Current Trend", current_trend)
                
                # Calculate price change percentage
                price_change = ((candles[-1].C - candles[0].C) / candles[0].C) * 100
                st.metric("Price Change", f"{price_change:.2f}%", 
                          delta=f"{price_change:.2f}%")
            
            with col3:
                # Market structure assessment
                structure = analyze_market_structure(vertices)
                st.metric("Market Structure", structure)
                
                # Recent swing
                last_swing = "None"
                if swing_points:
                    last_swing = swing_points[-1][0]
                st.metric("Last Swing Point", last_swing)
        
        with tab2:
            # Display raw data
            st.dataframe(data)
            
        with tab3:
            st.subheader("About SMC-Algo-Trading")
            st.markdown("""
            This is a Python library for building trading bots following Smart Money Concepts (SMC).
            
            ### Components:
            
            1. **Market Structure Analysis**: Identifying market structure vertices (HH, HL, LH, LL)
            2. **Candlestick Pattern Recognition**: Analyzing candlestick patterns and trends
            3. **Automated Trading**: Integration with Binance and MetaTrader 5
            4. **Risk Management**: DrawDown management to control trading risk
            
            ### Platform Compatibility:
            
            - **Windows**: Full support for all features
            - **macOS/Linux**: Support for Binance integration and market analysis; MetaTrader 5 integration not available
            """)
    
    # Add a refresh button
    if st.sidebar.button("Refresh Data"):
        st.experimental_rerun()
    
    # Add information about the project
    st.sidebar.markdown("---")
    st.sidebar.header("About")
    st.sidebar.info(
        "SMC-Algo-Trading is a Python library for "
        "building trading bots following Smart Money Concepts (SMC)."
    )
    st.sidebar.markdown("[GitHub Repository](https://github.com/yourusername/SMC-Algo-Trading)") 