#!/usr/bin/env python3
"""
Streamlit UI for SMC-Algo-Trading
This provides a simple, cross-platform UI for the trading algorithm
"""

import streamlit as st

# Page config - must be the first Streamlit command
st.set_page_config(
    page_title="SMC Algo Trading",
    page_icon="📈",
    layout="wide",
)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
from datetime import datetime, timedelta
import os
import sys

# Import trading bot
try:
    import trading_bot
    BOT_AVAILABLE = True
except ImportError:
    BOT_AVAILABLE = False
    st.warning("Trading bot module not found. Some features will be disabled.")

# Import project modules
from Candle import Candle
from streamlit_vertex import Vertex
try:
    from BinanceBot.standalone_client import BinanceClient as StandaloneClient
    import BinanceBot.key as key
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    st.warning("Binance integration not available. Some features will be disabled.")

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

# Add Trading Bot Controls
st.sidebar.markdown("---")
st.sidebar.header("Trading Bot Controls")

if BOT_AVAILABLE:
    # Get current bot status
    bot_status = trading_bot.get_bot_status()
    bot_running = bot_status["running"]
    
    # Bot on/off status display
    if bot_running:
        st.sidebar.success("Trading Bot is ACTIVE")
    else:
        st.sidebar.error("Trading Bot is INACTIVE")
    
    # Active trading symbols
    trading_symbols = st.sidebar.multiselect(
        "Trading Symbols",
        ["BTCUSDT", "ETHUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT"],
        default=bot_status["active_symbols"] if bot_running else ["BTCUSDT", "ETHUSDT"]
    )
    
    # Risk management settings
    st.sidebar.subheader("Risk Management")
    position_size = st.sidebar.slider("Position Size (%)", 1, 100, 
                                     bot_status["position_size"] if bot_running else 10)
    stop_loss = st.sidebar.slider("Stop Loss (%)", 1, 20, 
                                 bot_status["stop_loss"] if bot_running else 5)
    take_profit = st.sidebar.slider("Take Profit (%)", 1, 30, 
                                  bot_status["take_profit"] if bot_running else 10)
    
    # Trading strategy selection
    strategy = st.sidebar.selectbox(
        "Trading Strategy",
        ["Smart Money Concepts", "Breakout", "Mean Reversion", "Trend Following"],
        index=0 if bot_status["strategy"] == "Smart Money Concepts" else 0
    )
    
    # Add the start/stop bot button
    if bot_running:
        if st.sidebar.button("STOP TRADING BOT", type="primary"):
            trading_bot.stop_bot()
            st.rerun()
    else:
        if st.sidebar.button("START TRADING BOT", type="primary"):
            trading_bot.start_bot(
                strategy=strategy,
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                symbols=trading_symbols,
                timeframe=timeframe
            )
            st.rerun()
else:
    # If trading bot module is not available, display dummy controls
    st.sidebar.warning("Trading bot module not available")
    bot_running = st.sidebar.checkbox("Enable Trading Bot", value=False)
    if bot_running:
        st.sidebar.success("Trading Bot is ACTIVE (DEMO)")
    else:
        st.sidebar.error("Trading Bot is INACTIVE (DEMO)")

    # Risk management settings
    st.sidebar.subheader("Risk Management")
    position_size = st.sidebar.slider("Position Size (%)", 1, 100, 10)
    stop_loss = st.sidebar.slider("Stop Loss (%)", 1, 20, 5)
    take_profit = st.sidebar.slider("Take Profit (%)", 1, 30, 10)

    # Trading strategy selection
    strategy = st.sidebar.selectbox(
        "Trading Strategy",
        ["Smart Money Concepts", "Breakout", "Mean Reversion", "Trend Following"],
        index=0
    )
    
    # Add the start/stop bot button
    if bot_running:
        if st.sidebar.button("STOP TRADING BOT", type="primary"):
            bot_running = False
            st.rerun()
    else:
        if st.sidebar.button("START TRADING BOT", type="primary"):
            bot_running = True
            st.rerun()

# Function to fetch data from Binance
@st.cache_data(ttl=60)
def fetch_market_data(symbol, timeframe, limit):
    if not BINANCE_AVAILABLE:
        # Return sample data if Binance is not available
        return generate_sample_data(limit, timeframe, symbol)
    
    try:
        # Initialize client
        client = StandaloneClient(key.key, key.secret)
        
        # Calculate start time based on timeframe
        # For daily and above, we need a much longer lookback
        timeframe_multipliers = {
            '1m': 60,         # 1 minute in seconds
            '3m': 60 * 3,     # 3 minutes in seconds
            '5m': 60 * 5,     # 5 minutes in seconds
            '15m': 60 * 15,   # 15 minutes in seconds
            '30m': 60 * 30,   # 30 minutes in seconds
            '1h': 60 * 60,    # 1 hour in seconds
            '2h': 60 * 60 * 2, # 2 hours in seconds
            '4h': 60 * 60 * 4, # 4 hours in seconds
            '6h': 60 * 60 * 6, # 6 hours in seconds
            '8h': 60 * 60 * 8, # 8 hours in seconds
            '12h': 60 * 60 * 12, # 12 hours in seconds
            '1d': 60 * 60 * 24, # 1 day in seconds
            '3d': 60 * 60 * 24 * 3, # 3 days in seconds
            '1w': 60 * 60 * 24 * 7, # 1 week in seconds
            '1M': 60 * 60 * 24 * 30, # 1 month (approx) in seconds
        }
        
        # Get the multiplier for the selected timeframe (default to 60 if not found)
        multiplier = timeframe_multipliers.get(timeframe, 60)
        
        # Calculate start time: current time - (interval duration * number of candles)
        start = int((time.time() - (multiplier * limit) - multiplier * 2) * 1000)
        
        st.info(f"Fetching {limit} {timeframe} candles from Binance API for {symbol}...")
        
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
        
        # If we got no data, try a longer timespan for higher timeframes
        if len(df) == 0 and timeframe in ['1d', '3d', '1w', '1M']:
            st.warning(f"No data returned for {timeframe} timeframe. Trying with a longer lookback period...")
            # For daily and higher timeframes, look much further back
            start = int((time.time() - (multiplier * limit * 10)) * 1000)  # 10x longer lookback
            
            klines = client.client.get_historical_klines(
                symbol=symbol,
                interval=timeframe,
                start_str=str(start)
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
        
        # Convert types
        if len(df) > 0:
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Ensure we limit to the requested number of candles
            if len(df) > limit:
                df = df.tail(limit)
                
            return df
        else:
            st.error(f"No data available for {symbol} on {timeframe} timeframe")
            return generate_sample_data(limit, timeframe, symbol)
            
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        # Log more detailed error information
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            st.error(f"API Response: {e.response.text}")
        elif hasattr(e, 'status_code'):
            st.error(f"Status Code: {e.status_code}")
        
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        
        # Return sample data as fallback
        return generate_sample_data(limit, timeframe, symbol)

def generate_sample_data(limit, timeframe='1h', symbol='BTCUSDT'):
    """Generate sample data for demonstration when Binance is not available or API fails"""
    np.random.seed(42)  # For reproducibility
    
    # Set base prices for different assets to current market values
    base_prices = {
        'BTCUSDT': 86000.0,
        'ETHUSDT': 2100.0,
        'XRPUSDT': 0.65,
        'ADAUSDT': 0.70,
        'SOLUSDT': 145.0,
        'DOTUSDT': 9.5,
    }
    
    # Use default BTC price if symbol not specified
    base_price = base_prices.get(symbol, 86000.0)
    
    # Generate timestamps based on timeframe
    now = datetime.now()
    
    if timeframe == '1d':
        # For daily, go back by days
        timestamps = [now - timedelta(days=i) for i in range(limit, 0, -1)]
        volatility_factor = 500  # Higher volatility for daily
    elif timeframe == '1w':
        # For weekly, go back by weeks
        timestamps = [now - timedelta(weeks=i) for i in range(limit, 0, -1)]
        volatility_factor = 1000  # Even higher for weekly
    elif timeframe == '1M':
        # For monthly, go back by months (approximate)
        timestamps = [now - timedelta(days=i*30) for i in range(limit, 0, -1)]
        volatility_factor = 2000  # Very high for monthly
    else:
        # Default to hourly or lower
        # Convert timeframe to minutes
        minutes_map = {
            '1m': 1,
            '3m': 3,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '2h': 120,
            '4h': 240,
            '6h': 360,
            '8h': 480,
            '12h': 720
        }
        minutes = minutes_map.get(timeframe, 60)  # Default to 1h if unknown
        timestamps = [now - timedelta(minutes=i*minutes) for i in range(limit, 0, -1)]
        volatility_factor = 50 * (minutes / 60)  # Scale volatility with timeframe
    
    # Generate price movements with some trend and volatility
    price_changes = np.random.normal(0, 1, limit) * volatility_factor
    
    # Add a trend component
    trend = np.linspace(0, base_price * 0.05, limit) * np.sin(np.linspace(0, np.pi * 2, limit))
    
    # Combine random changes and trend
    changes = price_changes + trend
    
    # Calculate prices
    prices = [base_price]
    for i in range(1, limit):
        # Ensure no negative prices
        new_price = max(prices[-1] + changes[i], prices[-1] * 0.7)
        prices.append(new_price)
    
    # Generate OHLC data with some intracandle movement
    data = []
    for i in range(limit):
        # Base price for this candle
        base = prices[i]
        
        # Generate some intracandle volatility
        volatility = base * 0.01 * (1 + np.random.random()) * (volatility_factor / 100)
        
        # OHLC with some movement
        open_price = base
        high_price = base + volatility * np.random.random()
        low_price = base - volatility * np.random.random()
        close_price = base + volatility * (np.random.random() - 0.5)
        
        # Ensure high is highest and low is lowest
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        # Generate volume
        volume = base * np.random.random() * 10
        
        data.append([timestamps[i], open_price, high_price, low_price, close_price, volume])
    
    # Convert to DataFrame
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    return df

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

def identify_structure(candles, timeframe='1h'):
    """
    Identify market structure from candles according to ICT principles.
    
    This function implements proper ICT market structure analysis with:
    - Correct swing point detection (HH, LL, internal structure)
    - Break of Structure (BOS) identification
    - Change of Character (CHoCH) recognition
    - Filtering of liquidity sweeps and false breakouts
    - Timeframe-specific swing detection parameters
    """
    # Setup timeframe-specific parameters
    if timeframe in ['1d', '4h', 'D', '4H', 'daily', '1w', '1M']:
        # Higher timeframe - use more stringent detection
        lookback_bars = 4  # Minimum candles on each side to validate a swing
        confirmation_bars = 2  # Candles needed to confirm a swing
        is_htf = True
    else:
        # Lower timeframe - use more lenient detection
        lookback_bars = 2  # Minimum candles on each side 
        confirmation_bars = 1  # Candles needed to confirm
        is_htf = False

    # Identify trend blocks (sequences of bullish or bearish candles)
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
    
    # Find potential swing highs and lows
    # A proper HH requires at least lookback_bars lower highs on both sides
    # A proper LL requires at least lookback_bars higher lows on both sides
    potential_swing_highs = []
    potential_swing_lows = []
    
    # We need enough candles to properly identify swings
    if len(candles) < (lookback_bars * 2 + 1):
        return blocks, [], []  # Not enough data for reliable swing detection
    
    # Identify potential swing points
    for i in range(lookback_bars, len(candles) - lookback_bars):
        # Check for swing high
        is_swing_high = True
        for j in range(1, lookback_bars + 1):
            # Check if there are lower highs on both sides
            if (candles[i].H <= candles[i - j].H) or (candles[i].H <= candles[i + j].H):
                is_swing_high = False
                break
        
        if is_swing_high:
            # Validate that the swing is respected for confirmation_bars
            is_valid = True
            for j in range(1, min(confirmation_bars + 1, len(candles) - i)):
                if candles[i + j].H > candles[i].H:
                    is_valid = False
                    break
            
            if is_valid:
                potential_swing_highs.append((i, candles[i]))
        
        # Check for swing low
        is_swing_low = True
        for j in range(1, lookback_bars + 1):
            # Check if there are higher lows on both sides
            if (candles[i].L >= candles[i - j].L) or (candles[i].L >= candles[i + j].L):
                is_swing_low = False
                break
        
        if is_swing_low:
            # Validate that the swing is respected for confirmation_bars
            is_valid = True
            for j in range(1, min(confirmation_bars + 1, len(candles) - i)):
                if candles[i + j].L < candles[i].L:
                    is_valid = False
                    break
            
            if is_valid:
                potential_swing_lows.append((i, candles[i]))
    
    # Filter out minor swing points that are too close to each other
    # Keep only major swings, especially on HTF
    filtered_highs = []
    filtered_lows = []
    
    # Filter swing highs
    if potential_swing_highs:
        # Sort by price (highest first)
        sorted_highs = sorted(potential_swing_highs, key=lambda x: x[1].H, reverse=True)
        
        # Always keep the highest high
        filtered_highs.append(sorted_highs[0])
        
        # If HTF, be more selective (only keep major swings)
        if is_htf:
            # Filter out swings that are too close in price (< 0.5% difference)
            prev_high = sorted_highs[0][1].H
            for idx, candle in sorted_highs[1:]:
                # If price difference is significant, keep it
                if (prev_high - candle.H) / prev_high > 0.005:  # 0.5% difference
                    filtered_highs.append((idx, candle))
                    prev_high = candle.H
        else:
            # For LTF, keep more swing points but still filter minor ones
            filtered_highs = sorted(potential_swing_highs, key=lambda x: x[0])  # Sort by index
    
    # Filter swing lows (similar logic)
    if potential_swing_lows:
        # Sort by price (lowest first)
        sorted_lows = sorted(potential_swing_lows, key=lambda x: x[1].L)
        
        # Always keep the lowest low
        filtered_lows.append(sorted_lows[0])
        
        # If HTF, be more selective
        if is_htf:
            prev_low = sorted_lows[0][1].L
            for idx, candle in sorted_lows[1:]:
                # If price difference is significant, keep it
                if (candle.L - prev_low) / prev_low > 0.005:  # 0.5% difference
                    filtered_lows.append((idx, candle))
                    prev_low = candle.L
        else:
            # For LTF, keep more swing points but still filter minor ones
            filtered_lows = sorted(potential_swing_lows, key=lambda x: x[0])  # Sort by index
    
    # Sort filtered highs and lows by index for chronological order
    filtered_highs = sorted(filtered_highs, key=lambda x: x[0])
    filtered_lows = sorted(filtered_lows, key=lambda x: x[0])
    
    # Prepare swing points and vertices
    swing_points = []
    vertices = []
    
    # Process swing highs
    for idx, candle in filtered_highs:
        swing_points.append(('HH', candle))
        v = Vertex(candle.date, candle.H)
        v.type = "HH"
        vertices.append((idx, v))
    
    # Process swing lows
    for idx, candle in filtered_lows:
        swing_points.append(('LL', candle))
        v = Vertex(candle.date, candle.L)
        v.type = "LL"
        vertices.append((idx, v))
    
    # Sort vertices chronologically by index
    vertices.sort(key=lambda x: x[0])
    vertices = [v for _, v in vertices]
    
    # Connect vertices and identify BOS and CHoCH
    for i in range(1, len(vertices)):
        vertices[i].set_last(vertices[i-1])
        vertices[i-1].set_next(vertices[i])
        
        # Check for BOS (Break of Structure)
        if (vertices[i].type == "HH" and vertices[i-1].type == "HH" and 
            vertices[i].y > vertices[i-1].y):
            # Bullish market structure (higher high)
            vertices[i].breaks = True
        
        elif (vertices[i].type == "LL" and vertices[i-1].type == "LL" and 
              vertices[i].y < vertices[i-1].y):
            # Bearish market structure (lower low)
            vertices[i].breaks = True
        
        # Check for CHoCH (Change of Character)
        # HH after LL or LL after HH can indicate CHoCH
        elif ((vertices[i].type == "HH" and vertices[i-1].type == "LL") or
              (vertices[i].type == "LL" and vertices[i-1].type == "HH")):
            vertices[i].is_choch = True
    
    # Identify first and last vertices
    if vertices:
        vertices[0].is_first = True
        vertices[-1].is_last = True
    
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
    
    # Plot swing points with different markers for HH/LL
    for type_point, point in swing_points:
        if type_point == 'HH':
            color = 'blue'
            marker = '^'  # Triangle up for HH
            value = point.H
            label = 'HH'
        else:  # LL
            color = 'purple'
            marker = 'v'  # Triangle down for LL
            value = point.L
            label = 'LL'
        
        ax.scatter(point.date, value, color=color, s=100, marker=marker)
        ax.annotate(label, (point.date, value), xytext=(5, 5), 
                  textcoords='offset points', color=color, fontweight='bold')
    
    # Connect swing points with lines
    hh_points = [(p.date, p.H) for t, p in swing_points if t == 'HH']
    ll_points = [(p.date, p.L) for t, p in swing_points if t == 'LL']
    
    if len(hh_points) >= 2:
        for i in range(1, len(hh_points)):
            # Check if this is a higher high (bullish structure)
            if hh_points[i][1] > hh_points[i-1][1]:
                line_style = '-'  # Solid line for bearish structure
                line_width = 2
                line_color = 'purple'
            else:
                line_style = '--'  # Dashed line for bullish structure
                line_width = 1.5
                line_color = 'purple'
                
            ax.plot([hh_points[i-1][0], hh_points[i][0]], 
                  [hh_points[i-1][1], hh_points[i][1]], 
                  color=line_color, linestyle=line_style, alpha=0.7, linewidth=line_width)
    
    if len(ll_points) >= 2:
        for i in range(1, len(ll_points)):
            # Check if this is a lower low (bearish structure)
            if ll_points[i][1] < ll_points[i-1][1]:
                line_style = '-'  # Solid line for bearish structure
                line_width = 2
                line_color = 'purple'
            else:
                line_style = '--'  # Dashed line for bullish structure
                line_width = 1.5
                line_color = 'purple'
                
            ax.plot([ll_points[i-1][0], ll_points[i][0]], 
                  [ll_points[i-1][1], ll_points[i][1]], 
                  color=line_color, linestyle=line_style, alpha=0.7, linewidth=line_width)
    
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
        tab1, tab2, tab3, tab4 = st.tabs(["Market Structure", "Trading Dashboard", "Raw Data", "About"])
        
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
            # Trading Dashboard Tab
            st.subheader("Trading Dashboard")
            
            if BOT_AVAILABLE:
                # Get real data from trading bot
                bot_status = trading_bot.get_bot_status()
                open_positions = trading_bot.get_open_positions()
                trade_history = trading_bot.get_trade_history()
                balance_history = trading_bot.get_balance_history()
                
                if bot_status["running"]:
                    status = "ACTIVE"
                    status_color = "green"
                else:
                    status = "INACTIVE"
                    status_color = "red"
                
                # Account Balance Section
                st.subheader("Account Balance")
                
                # Display account metrics in 4 columns
                bal_col1, bal_col2, bal_col3, bal_col4 = st.columns(4)
                
                with bal_col1:
                    st.metric("Starting Balance", f"${bot_status['initial_balance']:,.2f}")
                
                with bal_col2:
                    st.metric("Available Balance", 
                             f"${bot_status['current_balance']:,.2f}", 
                             f"{((bot_status['current_balance'] - bot_status['initial_balance']) / bot_status['initial_balance'] * 100):.2f}%")
                
                with bal_col3:
                    st.metric("Total Equity", 
                             f"${bot_status['equity']:,.2f}", 
                             f"{bot_status['balance_change_percent']}%")
                
                with bal_col4:
                    open_pos_value = bot_status['equity'] - bot_status['current_balance']
                    st.metric("Position Value", f"${open_pos_value:,.2f}")
                
                # Display last update time
                st.info(f"Prices last updated: {bot_status['last_update']} (updates every minute)")
                
                # Trading statistics
                st.subheader("Trading Statistics")
                st.markdown(f"<h3 style='color:{status_color}'>Bot Status: {status}</h3>", unsafe_allow_html=True)
                
                # Display trading stats in columns
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Trades", bot_status["total_trades"])
                    st.metric("Win Rate", f"{bot_status['win_rate']}%")
                    pnl_total = sum(trade.get("pnl_amount", 0) for trade in trade_history)
                    st.metric("Profit/Loss", f"${pnl_total:.2f}")
                    
                with col2:
                    st.metric("Open Positions", len(open_positions))
                    st.metric("Active Pairs", ", ".join(bot_status["active_symbols"]))
                    st.metric("Strategy", bot_status["strategy"])
                    
                with col3:
                    st.metric("Position Size", f"{bot_status['position_size']}%")
                    st.metric("Stop Loss", f"{bot_status['stop_loss']}%")
                    st.metric("Take Profit", f"{bot_status['take_profit']}%")
                
                # Open positions table
                st.subheader("Open Positions")
                if open_positions:
                    # Convert to DataFrame for display
                    positions_for_display = []
                    for pos in open_positions:
                        positions_for_display.append({
                            "Symbol": pos["symbol"],
                            "Type": pos["type"],
                            "Entry Price": f"${pos['entry_price']:,.2f}",
                            "Current Price": f"${pos['current_price']:,.2f}",
                            "PnL": f"{pos['pnl']}% (${pos['pnl_amount']:,.2f})",
                            "Entry Time": pos["entry_time"],
                            "Duration": pos["duration"],
                            "Stop Loss": f"${pos['stop_loss']:,.2f}",
                            "Take Profit": f"${pos['take_profit']:,.2f}"
                        })
                    
                    pos_df = pd.DataFrame(positions_for_display)
                    st.dataframe(pos_df, use_container_width=True)
                else:
                    st.info("No open positions currently.")
                
                # Trade history
                st.subheader("Recent Trade History")
                if trade_history:
                    # Convert to DataFrame for display
                    history_for_display = []
                    for trade in trade_history:
                        history_for_display.append({
                            "Symbol": trade["symbol"],
                            "Type": trade["type"],
                            "Entry Price": f"${trade['entry_price']:,.2f}",
                            "Exit Price": f"${trade['exit_price']:,.2f}",
                            "PnL": f"{trade['pnl']}% (${trade['pnl_amount']:,.2f})",
                            "Entry Time": trade["entry_time"],
                            "Exit Time": trade["exit_time"],
                            "Duration": trade["duration"],
                            "Result": trade["result"]
                        })
                    
                    history_df = pd.DataFrame(history_for_display)
                    st.dataframe(history_df, use_container_width=True)
                else:
                    st.info("No trade history available.")
                    
                # Add balance history chart if we have data
                if len(balance_history) > 1:
                    st.subheader("Account Balance History")
                    
                    # Convert to DataFrame for charting
                    balance_df = pd.DataFrame(balance_history)
                    balance_df['timestamp'] = pd.to_datetime(balance_df['timestamp'])
                    
                    # Create a line chart
                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.plot(balance_df['timestamp'], balance_df['equity'], label='Total Equity', color='blue')
                    ax.plot(balance_df['timestamp'], balance_df['balance'], label='Available Balance', color='green', linestyle='--')
                    
                    # Format the chart
                    ax.set_title('Account Balance History')
                    ax.set_xlabel('Time')
                    ax.set_ylabel('USD')
                    ax.grid(True, alpha=0.3)
                    ax.legend()
                    
                    # Display the chart
                    st.pyplot(fig)
                    
            else:
                # Mock data for demonstration
                if bot_running:
                    status = "ACTIVE"
                    status_color = "green"
                else:
                    status = "INACTIVE"
                    status_color = "red"
                    
                # Account Balance Section (Mock data)
                st.subheader("Account Balance")
                
                # Display account metrics in 4 columns
                bal_col1, bal_col2, bal_col3, bal_col4 = st.columns(4)
                
                with bal_col1:
                    st.metric("Starting Balance", "$10,000.00")
                
                with bal_col2:
                    st.metric("Available Balance", "$10,342.15", "+3.4%")
                
                with bal_col3:
                    st.metric("Total Equity", "$11,289.73", "+12.9%")
                
                with bal_col4:
                    st.metric("Position Value", "$947.58")
                
                # Display last update time
                st.info(f"Prices last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (updates every minute)")
                
                # Trading statistics
                st.subheader("Trading Statistics")
                st.markdown(f"<h3 style='color:{status_color}'>Bot Status: {status}</h3>", unsafe_allow_html=True)
                
                # Display trading stats in columns
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Trades", "24")
                    st.metric("Win Rate", "68%")
                    st.metric("Profit/Loss", "+$342.15", delta="+12.8%")
                    
                with col2:
                    st.metric("Open Positions", "2")
                    st.metric("Average Trade Duration", "3h 24m")
                    st.metric("Risk/Reward Ratio", "1:2.5")
                    
                with col3:
                    st.metric("Current Strategy", strategy)
                    st.metric("Position Size", f"{position_size}%")
                    st.metric("Stop Loss", f"{stop_loss}%")
                
                # Open positions table
                st.subheader("Open Positions")
                if bot_running:
                    open_positions = {
                        "Symbol": ["BTCUSDT", "ETHUSDT"],
                        "Entry Price": ["$85,420.50", "$2,045.75"],
                        "Current Price": ["$86,050.25", "$2,108.10"],
                        "PnL": ["+$629.75 (+0.74%)", "+$62.35 (+3.05%)"],
                        "Entry Time": ["2025-03-08 06:42:15", "2025-03-08 08:15:30"],
                        "Position Duration": ["4h 21m", "2h 48m"]
                    }
                    
                    open_pos_df = pd.DataFrame(open_positions)
                    st.dataframe(open_pos_df, use_container_width=True)
                else:
                    st.info("No open positions. Trading bot is currently inactive.")
                
                # Trade history
                st.subheader("Recent Trade History")
                trade_history = {
                    "Symbol": ["BTCUSDT", "SOLUSDT", "ETHUSDT", "ADAUSDT", "BTCUSDT"],
                    "Type": ["SELL", "SELL", "BUY", "SELL", "BUY"],
                    "Entry Price": ["$84,125.50", "$144.75", "$2,050.30", "$0.59", "$85,420.50"],
                    "Exit Price": ["$85,890.25", "$148.20", "$2,105.75", "$0.57", "Open"],
                    "PnL": ["+$1,764.75 (+2.10%)", "+$3.45 (+2.38%)", "+$55.45 (+2.70%)", "-$0.02 (-3.38%)", "Open"],
                    "Entry Time": ["2025-03-07 18:42:15", "2025-03-07 20:15:30", "2025-03-08 01:22:45", "2025-03-08 03:10:20", "2025-03-08 06:42:15"],
                    "Exit Time": ["2025-03-08 02:15:30", "2025-03-08 04:30:15", "2025-03-08 05:45:20", "2025-03-08 06:30:40", "Open"],
                    "Duration": ["7h 33m", "8h 15m", "4h 23m", "3h 20m", "4h 21m"]
                }
                
                trade_df = pd.DataFrame(trade_history)
                st.dataframe(trade_df, use_container_width=True)
        
        with tab3:
            # Display raw data
            st.dataframe(data)
            
        with tab4:
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
        st.rerun()
    
    # Add information about the project
    st.sidebar.markdown("---")
    st.sidebar.header("About")
    st.sidebar.info(
        "SMC-Algo-Trading is a Python library for "
        "building trading bots following Smart Money Concepts (SMC)."
    )
    st.sidebar.markdown("[GitHub Repository](https://github.com/yourusername/SMC-Algo-Trading)") 