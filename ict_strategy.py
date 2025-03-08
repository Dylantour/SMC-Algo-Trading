"""
ict_strategy.py - Inner Circle Trader (ICT) strategy implementation

This module implements the ICT trading strategy with the following key components:
1. Convert data to New York Time (EST)
2. Determine daily bias
3. Confirm bias on HTF (4H & 1H)
4. Detect liquidity sweeps
5. Detect Market Structure Shifts (MSS)
6. Define SL & TP levels
7. Ensure trades happen inside NY kill zones

The strategy follows Smart Money Concepts and includes extensive error handling
to detect and fix issues without breaking functionality.
"""

import pandas as pd
import numpy as np
import datetime
import pytz
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from streamlit_vertex import Vertex

# Configure logging
logger = logging.getLogger(__name__)

# ------------------------------- Step 1: Convert Data to EST -------------------------------

def convert_to_ny_time(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert all timestamps in the DataFrame to New York Time (EST).
    
    Args:
        df: DataFrame with a 'timestamp' column.
        
    Returns:
        DataFrame with timestamps converted to EST.
    """
    try:
        # Make a copy to avoid modifying the original dataframe
        df_est = df.copy()
        est = pytz.timezone("America/New_York")
        
        # Check if timestamp column exists
        if 'timestamp' not in df_est.columns:
            if 'date' in df_est.columns:
                timestamp_col = 'date'
            elif 'time' in df_est.columns:
                timestamp_col = 'time'
            else:
                logger.warning("No timestamp column found. Using index as timestamp.")
                df_est['timestamp'] = df_est.index
                timestamp_col = 'timestamp'
        else:
            timestamp_col = 'timestamp'
        
        # Convert timestamps
        if pd.api.types.is_datetime64_any_dtype(df_est[timestamp_col]):
            # If already datetime, just convert timezone
            if df_est[timestamp_col].dt.tz is None:
                # If no timezone info, assume UTC
                df_est[timestamp_col] = pd.to_datetime(df_est[timestamp_col], utc=True)
            df_est[timestamp_col] = df_est[timestamp_col].dt.tz_convert(est)
        else:
            # Convert string to datetime with timezone
            df_est[timestamp_col] = pd.to_datetime(df_est[timestamp_col], utc=True).dt.tz_convert(est)
        
        return df_est
    except Exception as e:
        logger.error(f"Error in time conversion: {e}")
        return df  # Return original dataframe if conversion fails

# --------------------------- Step 2: Determine Daily Bias (Parent Timeframe) ---------------------------

def determine_daily_bias(df: pd.DataFrame) -> str:
    """
    Determine daily market bias based on liquidity sweeps and FVGs.
    
    Args:
        df: Daily timeframe DataFrame with OHLC data.
        
    Returns:
        str: "Bullish", "Bearish", or "Neutral" bias.
    """
    try:
        # Ensure we have enough data
        if len(df) < 2:
            logger.warning("Not enough data to determine daily bias")
            return "Neutral"
        
        # Get previous day's high and low
        prev_day_high = df['high'].shift(1).iloc[-1]
        prev_day_low = df['low'].shift(1).iloc[-1]
        
        # Get today's data
        today_high = df['high'].iloc[-1]
        today_low = df['low'].iloc[-1]
        today_open = df['open'].iloc[-1]
        today_close = df['close'].iloc[-1]
        
        # Check for Fair Value Gaps (FVGs)
        # Bullish FVG: Current candle's low is above previous candle's high
        bullish_fvg = today_low > prev_day_high
        
        # Bearish FVG: Current candle's high is below previous candle's low
        bearish_fvg = today_high < prev_day_low
        
        # Check for liquidity sweeps
        # Bullish sweep: Price took out previous low but closed higher
        bullish_sweep = today_low < prev_day_low and today_close > prev_day_low
        
        # Bearish sweep: Price took out previous high but closed lower
        bearish_sweep = today_high > prev_day_high and today_close < prev_day_high
        
        # Determine bias
        if bullish_sweep or bullish_fvg:
            return "Bullish"
        elif bearish_sweep or bearish_fvg:
            return "Bearish"
        elif today_close > today_open:
            return "Bullish"  # Closed higher than open
        elif today_close < today_open:
            return "Bearish"  # Closed lower than open
        else:
            return "Neutral"  # Doji or indecision
            
    except Exception as e:
        logger.error(f"Error determining daily bias: {e}")
        return "Neutral"  # Default to neutral on error

# --------------------------- Step 3: Confirm Bias on 4H & 1H (HTF Confirmation) ---------------------------

def confirm_htf_bias(df: pd.DataFrame, lookback: int = 5) -> str:
    """
    Validate the daily bias by checking BOS or CHoCH on 4H or 1H.
    
    Args:
        df: Higher timeframe DataFrame (4H or 1H) with OHLC data.
        lookback: Number of candles to lookback for swing points.
        
    Returns:
        str: "Bullish", "Bearish", or "Neutral" confirmation.
    """
    try:
        # Ensure we have enough data
        if len(df) < lookback + 1:
            logger.warning(f"Not enough data for HTF confirmation. Need at least {lookback + 1} candles.")
            return "Neutral"
        
        # Identify swing highs and lows
        df = df.copy()
        
        # A swing high is where the price is higher than 'lookback' candles on either side
        df['swing_high'] = df['high'].rolling(window=lookback*2+1, center=True).apply(
            lambda x: 1 if x[lookback] == max(x) else 0, raw=True
        )
        
        # A swing low is where the price is lower than 'lookback' candles on either side
        df['swing_low'] = df['low'].rolling(window=lookback*2+1, center=True).apply(
            lambda x: 1 if x[lookback] == min(x) else 0, raw=True
        )
        
        # Fill NaN values
        df['swing_high'] = df['swing_high'].fillna(0)
        df['swing_low'] = df['swing_low'].fillna(0)
        
        # Get the most recent swing high and low before the current candle
        recent_swing_highs = df[df['swing_high'] == 1]['high'].tolist()
        recent_swing_lows = df[df['swing_low'] == 1]['low'].tolist()
        
        # Get current close
        current_close = df['close'].iloc[-1]
        
        # Check for Break of Structure (BOS)
        if recent_swing_highs and current_close > recent_swing_highs[-1]:
            return "Bullish"  # Bullish BOS
        elif recent_swing_lows and current_close < recent_swing_lows[-1]:
            return "Bearish"  # Bearish BOS
        
        # Check for Change of Character (CHoCH)
        if len(recent_swing_highs) >= 2:
            if recent_swing_highs[-1] > recent_swing_highs[-2] and current_close > recent_swing_highs[-2]:
                return "Bullish"  # Bullish CHoCH
        
        if len(recent_swing_lows) >= 2:
            if recent_swing_lows[-1] < recent_swing_lows[-2] and current_close < recent_swing_lows[-2]:
                return "Bearish"  # Bearish CHoCH
        
        # Look at current momentum
        if df['close'].iloc[-1] > df['open'].iloc[-1] and df['close'].iloc[-2] > df['open'].iloc[-2]:
            return "Bullish"  # Two consecutive bullish candles
        elif df['close'].iloc[-1] < df['open'].iloc[-1] and df['close'].iloc[-2] < df['open'].iloc[-2]:
            return "Bearish"  # Two consecutive bearish candles
            
        return "Neutral"  # No clear bias
        
    except Exception as e:
        logger.error(f"Error confirming HTF bias: {e}")
        return "Neutral"  # Default to neutral on error

# --------------------------- Step 4: Detect Liquidity Sweeps (15m) ---------------------------

def detect_liquidity_sweeps(df: pd.DataFrame, lookback: int = 10) -> str:
    """
    Identify liquidity sweeps at EQH/EQL on 15m timeframe.
    
    Args:
        df: 15m timeframe DataFrame with OHLC data.
        lookback: Number of candles to lookback for equal highs/lows.
        
    Returns:
        str: "Liquidity Grab (Bullish)", "Liquidity Grab (Bearish)", or "No Sweep".
    """
    try:
        # Ensure we have enough data
        if len(df) < lookback + 1:
            logger.warning(f"Not enough data for liquidity sweep detection. Need at least {lookback + 1} candles.")
            return "No Sweep"
        
        # Find recent equal highs and lows
        # For equal highs, we look for consecutive candles with similar highs
        df = df.copy()
        
        # Calculate rolling max highs and min lows
        df['max_high'] = df['high'].rolling(window=lookback).max().shift(1)
        df['min_low'] = df['low'].rolling(window=lookback).min().shift(1)
        
        # Current candle
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        current_close = df['close'].iloc[-1]
        
        # Check for recent highs that are close to each other (equal highs)
        high_threshold = df['high'].iloc[-lookback:-1].std() * 0.5  # 50% of standard deviation
        eq_highs = df.iloc[-lookback:-1][df['high'].diff().abs() < high_threshold]['high']
        
        # Check for recent lows that are close to each other (equal lows)
        low_threshold = df['low'].iloc[-lookback:-1].std() * 0.5  # 50% of standard deviation 
        eq_lows = df.iloc[-lookback:-1][df['low'].diff().abs() < low_threshold]['low']
        
        # Check if current price swept equal highs but failed to hold (bearish)
        if len(eq_highs) >= 2 and current_high > eq_highs.max() and current_close < eq_highs.max():
            return "Liquidity Grab (Bearish)"
        
        # Check if current price swept equal lows but failed to hold (bullish)
        if len(eq_lows) >= 2 and current_low < eq_lows.min() and current_close > eq_lows.min():
            return "Liquidity Grab (Bullish)"
        
        # Check general sweep of major levels
        if current_high > df['max_high'].iloc[-1] and current_close < df['max_high'].iloc[-1]:
            return "Liquidity Grab (Bearish)"
        
        if current_low < df['min_low'].iloc[-1] and current_close > df['min_low'].iloc[-1]:
            return "Liquidity Grab (Bullish)"
        
        return "No Sweep"
        
    except Exception as e:
        logger.error(f"Error detecting liquidity sweeps: {e}")
        return "No Sweep"  # Default to no sweep on error

# --------------------------- Step 5: Detect Market Structure Shift (MSS) on 5m & 1m ---------------------------

def find_entry_mss(df: pd.DataFrame, liquidity_sweep: str, lookback: int = 3) -> str:
    """
    Detect Market Structure Shift (MSS) only after a liquidity sweep.
    
    Args:
        df: 5m or 1m timeframe DataFrame with OHLC data.
        liquidity_sweep: Result from detect_liquidity_sweeps function.
        lookback: Number of candles to lookback for swing points.
        
    Returns:
        str: "Bullish MSS", "Bearish MSS", or "No MSS".
    """
    try:
        # Only process if we have a liquidity sweep
        if liquidity_sweep == "No Sweep":
            return "No MSS"
        
        # Ensure we have enough data
        if len(df) < lookback + 1:
            logger.warning(f"Not enough data for MSS detection. Need at least {lookback + 1} candles.")
            return "No MSS"
        
        # Calculate recent swing highs and lows
        df = df.copy()
        
        df['swing_high'] = np.where(
            (df['high'] > df['high'].shift(1)) & 
            (df['high'] > df['high'].shift(-1).fillna(0)) &
            (df['high'] > df['high'].shift(2).fillna(0)) & 
            (df['high'] > df['high'].shift(-2).fillna(0)),
            df['high'], np.nan
        )
        
        df['swing_low'] = np.where(
            (df['low'] < df['low'].shift(1)) & 
            (df['low'] < df['low'].shift(-1).fillna(9999999)) &
            (df['low'] < df['low'].shift(2).fillna(0)) & 
            (df['low'] < df['low'].shift(-2).fillna(9999999)),
            df['low'], np.nan
        )
        
        # Get recent swings
        recent_swing_highs = df['swing_high'].dropna().tolist()
        recent_swing_lows = df['swing_low'].dropna().tolist()
        
        # Current candle
        current_close = df['close'].iloc[-1]
        
        # Check for MSS (Break of Structure) after liquidity sweep
        if liquidity_sweep == "Liquidity Grab (Bullish)":
            # For bullish MSS after bullish liquidity grab (taking out lows)
            # We need price to break above a recent swing high
            if recent_swing_highs and current_close > recent_swing_highs[-1]:
                return "Bullish MSS"
        
        elif liquidity_sweep == "Liquidity Grab (Bearish)":
            # For bearish MSS after bearish liquidity grab (taking out highs)
            # We need price to break below a recent swing low
            if recent_swing_lows and current_close < recent_swing_lows[-1]:
                return "Bearish MSS"
        
        return "No MSS"  # No confirmed MSS
        
    except Exception as e:
        logger.error(f"Error finding MSS: {e}")
        return "No MSS"  # Default to no MSS on error

# --------------------------- Step 6: Define SL & TP Levels ---------------------------

def calculate_sl_tp(df: pd.DataFrame, trade_direction: str, risk_reward_ratio: float = 2.0) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate smart stop loss (SL) and take profit (TP) based on ICT principles.
    
    Args:
        df: DataFrame with OHLC data.
        trade_direction: "Bullish MSS" or "Bearish MSS".
        risk_reward_ratio: Ratio of reward to risk (default 2.0).
        
    Returns:
        Tuple of (stop_loss, take_profit) levels.
    """
    try:
        if trade_direction not in ["Bullish MSS", "Bearish MSS"]:
            return None, None  # No valid trade setup
        
        # Ensure we have enough data
        if len(df) < 5:
            logger.warning("Not enough data for SL/TP calculation. Need at least 5 candles.")
            return None, None
        
        # Current price
        current_price = df['close'].iloc[-1]
        
        if trade_direction == "Bullish MSS":
            # For bullish trades, SL goes below recent lows
            # Find the lowest low in the last 5 candles
            stop_loss = df['low'].tail(5).min()
            
            # Calculate distance to SL
            sl_distance = current_price - stop_loss
            
            # Calculate TP based on risk:reward ratio
            take_profit = current_price + (sl_distance * risk_reward_ratio)
            
            # Alternative: Look for next significant level
            # Take the highest high in the last 20 candles
            alt_tp = df['high'].tail(20).max()
            
            # Use the better of the two (closer wins)
            if abs(current_price - alt_tp) < abs(current_price - take_profit) and alt_tp > current_price:
                take_profit = alt_tp
            
        else:  # "Bearish MSS"
            # For bearish trades, SL goes above recent highs
            # Find the highest high in the last 5 candles
            stop_loss = df['high'].tail(5).max()
            
            # Calculate distance to SL
            sl_distance = stop_loss - current_price
            
            # Calculate TP based on risk:reward ratio
            take_profit = current_price - (sl_distance * risk_reward_ratio)
            
            # Alternative: Look for next significant level
            # Take the lowest low in the last 20 candles
            alt_tp = df['low'].tail(20).min()
            
            # Use the better of the two (closer wins)
            if abs(current_price - alt_tp) < abs(current_price - take_profit) and alt_tp < current_price:
                take_profit = alt_tp
        
        return stop_loss, take_profit
        
    except Exception as e:
        logger.error(f"Error calculating SL/TP: {e}")
        return None, None  # Default to no levels on error

# --------------------------- Step 7: Ensure Trades Happen Inside New York Kill Zones ---------------------------

def check_ny_kill_zones(timestamp=None) -> bool:
    """
    Check if the trade is happening inside the New York Kill Zones.
    
    Args:
        timestamp: Optional timestamp to check. If None, uses current time.
        
    Returns:
        bool: True if inside NY kill zones, False otherwise.
    """
    try:
        est = pytz.timezone("America/New_York")
        
        # Use provided timestamp or current time
        if timestamp is None:
            current_time = datetime.datetime.now(est).time()
        else:
            # Convert timestamp to datetime with timezone if it's not already
            if isinstance(timestamp, (str, pd.Timestamp)):
                timestamp = pd.to_datetime(timestamp)
            
            # If timestamp has no timezone info, assume UTC and convert to EST
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=pytz.utc)
                timestamp = timestamp.astimezone(est)
            elif timestamp.tzinfo != est:
                timestamp = timestamp.astimezone(est)
                
            current_time = timestamp.time()
        
        # NY AM Kill Zone: 7:00 - 10:00 AM EST
        ny_am_start = datetime.time(7, 0)
        ny_am_end = datetime.time(10, 0)
        
        # NY PM Kill Zone: 2:00 - 4:00 PM EST
        ny_pm_start = datetime.time(14, 0)
        ny_pm_end = datetime.time(16, 0)
        
        # London/NY Overlap: 8:00 - 11:00 AM EST (optional additional window)
        # overlap_start = datetime.time(8, 0)
        # overlap_end = datetime.time(11, 0)
        
        if (ny_am_start <= current_time <= ny_am_end) or (ny_pm_start <= current_time <= ny_pm_end):
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking NY Kill Zones: {e}")
        return False  # Default to no trade on error

# --------------------------- Step 8: Final Trade Execution ---------------------------

def analyze_market_structure_ict(df_daily, df_4h, df_1h, df_15m, df_5m):
    """
    Analyze the market structure based on ICT principles using the hierarchical timeframe approach.
    
    Args:
        df_daily: Daily timeframe DataFrame with OHLC data.
        df_4h: 4-hour timeframe DataFrame with OHLC data.
        df_1h: 1-hour timeframe DataFrame with OHLC data.
        df_15m: 15-minute timeframe DataFrame with OHLC data.
        df_5m: 5-minute timeframe DataFrame with OHLC data.
        
    Returns:
        dict: Dictionary with ICT analysis, including bias, confirmations, and potential trade setups.
    """
    try:
        # Step 1: Convert all dataframes to NY time
        df_daily_ny = convert_to_ny_time(df_daily)
        df_4h_ny = convert_to_ny_time(df_4h)
        df_1h_ny = convert_to_ny_time(df_1h)
        df_15m_ny = convert_to_ny_time(df_15m)
        df_5m_ny = convert_to_ny_time(df_5m)
        
        # Step 2: Determine daily bias
        daily_bias = determine_daily_bias(df_daily_ny)
        
        # Step 3: Confirm bias on HTF (4H & 1H)
        bias_4h = confirm_htf_bias(df_4h_ny)
        bias_1h = confirm_htf_bias(df_1h_ny)
        
        # Step 4: Detect liquidity sweeps on 15m
        liquidity_sweep = detect_liquidity_sweeps(df_15m_ny)
        
        # Step 5: Detect Market Structure Shifts (MSS) on 5m
        mss = find_entry_mss(df_5m_ny, liquidity_sweep)
        
        # Step 6: Calculate SL & TP levels if we have a trade setup
        sl, tp = None, None
        if mss != "No MSS":
            sl, tp = calculate_sl_tp(df_5m_ny, mss)
        
        # Step 7: Check if we're in NY kill zones
        in_kill_zone = check_ny_kill_zones()
        
        # Determine if HTF confirms daily bias (at least one should match)
        htf_confirms_daily = (bias_4h == daily_bias) or (bias_1h == daily_bias)
        
        # Evaluate if we should take a trade
        take_trade = False
        trade_direction = "None"
        
        if htf_confirms_daily and mss != "No MSS" and in_kill_zone and sl is not None and tp is not None:
            if (daily_bias == "Bullish" and mss == "Bullish MSS") or (daily_bias == "Bearish" and mss == "Bearish MSS"):
                take_trade = True
                trade_direction = "BUY" if mss == "Bullish MSS" else "SELL"
        
        # Prepare result dictionary
        result = {
            "daily_bias": daily_bias,
            "bias_4h": bias_4h,
            "bias_1h": bias_1h,
            "htf_confirms_daily": htf_confirms_daily,
            "liquidity_sweep": liquidity_sweep,
            "market_structure_shift": mss,
            "in_ny_kill_zone": in_kill_zone,
            "stop_loss": sl,
            "take_profit": tp,
            "take_trade": take_trade,
            "trade_direction": trade_direction,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error in ICT market analysis: {e}")
        return {
            "error": str(e),
            "take_trade": False,
            "trade_direction": "None",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

def ict_trading_system(df_daily, df_4h, df_1h, df_15m, df_5m, symbol="BTCUSDT"):
    """
    Complete ICT Trading Bot Logic.
    
    Args:
        df_daily: Daily timeframe DataFrame with OHLC data.
        df_4h: 4-hour timeframe DataFrame with OHLC data.
        df_1h: 1-hour timeframe DataFrame with OHLC data.
        df_15m: 15-minute timeframe DataFrame with OHLC data.
        df_5m: 5-minute timeframe DataFrame with OHLC data.
        symbol: Trading symbol.
        
    Returns:
        dict: Dictionary with trade decision and analysis.
    """
    try:
        # Run the ICT analysis
        analysis = analyze_market_structure_ict(df_daily, df_4h, df_1h, df_15m, df_5m)
        
        # Add symbol to the result
        analysis['symbol'] = symbol
        
        # Log the analysis
        if analysis['take_trade']:
            logger.info(f"ICT Strategy: {symbol} {analysis['trade_direction']} signal detected.")
            logger.info(f"SL: {analysis['stop_loss']}, TP: {analysis['take_profit']}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Critical error in ICT trading system: {e}")
        return {
            "error": str(e),
            "take_trade": False,
            "trade_direction": "None",
            "symbol": symbol,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# --------------------------- For Testing ---------------------------

def generate_sample_data(symbol="BTCUSDT", timeframes=None):
    """
    Generate sample data for testing the ICT strategy.
    
    Args:
        symbol: Symbol to generate data for.
        timeframes: List of timeframes to generate data for.
        
    Returns:
        dict: Dictionary with sample dataframes for each timeframe.
    """
    if timeframes is None:
        timeframes = ['1d', '4h', '1h', '15m', '5m']
    
    result = {}
    
    # Generate different candle counts for different timeframes
    counts = {
        '1d': 30,    # 30 days
        '4h': 90,    # ~15 days
        '1h': 168,   # 7 days
        '15m': 384,  # 4 days
        '5m': 576    # 2 days
    }
    
    for tf in timeframes:
        if tf in counts:
            # Create a pandas dataframe with random OHLC data
            count = counts[tf]
            np.random.seed(42)  # For reproducibility
            
            # Start from 30 days ago
            end_date = datetime.datetime.now()
            
            if tf == '1d':
                start_date = end_date - datetime.timedelta(days=count)
                dates = pd.date_range(start=start_date, end=end_date, freq='D')
            elif tf == '4h':
                start_date = end_date - datetime.timedelta(hours=count*4)
                dates = pd.date_range(start=start_date, end=end_date, freq='4H')
            elif tf == '1h':
                start_date = end_date - datetime.timedelta(hours=count)
                dates = pd.date_range(start=start_date, end=end_date, freq='H')
            elif tf == '15m':
                start_date = end_date - datetime.timedelta(minutes=count*15)
                dates = pd.date_range(start=start_date, end=end_date, freq='15min')
            elif tf == '5m':
                start_date = end_date - datetime.timedelta(minutes=count*5)
                dates = pd.date_range(start=start_date, end=end_date, freq='5min')
            else:
                continue
            
            # Generate random price data
            base_price = 30000  # Base price for BTC
            volatility = 0.02   # 2% volatility
            
            # Generate random walk
            random_walk = np.random.normal(0, volatility, size=len(dates))
            
            # Calculate cumulative price changes
            price_changes = np.exp(np.cumsum(random_walk))
            
            # Generate open, high, low, close
            opens = base_price * price_changes
            
            # Generate random intraday volatility
            intraday_vol = volatility / 2
            highs = opens * np.exp(np.random.normal(0, intraday_vol, size=len(dates)))
            lows = opens * np.exp(np.random.normal(0, intraday_vol, size=len(dates)))
            
            # Make sure highs are higher than lows
            for i in range(len(highs)):
                if highs[i] < lows[i]:
                    highs[i], lows[i] = lows[i], highs[i]
            
            # Generate closes with slight bias
            closes = opens * np.exp(np.random.normal(0.0001, intraday_vol, size=len(dates)))
            
            # Make sure closes are between highs and lows
            for i in range(len(closes)):
                closes[i] = min(highs[i], max(lows[i], closes[i]))
            
            # Generate sample volume
            volumes = np.random.normal(1000, 300, size=len(dates))
            volumes = np.maximum(volumes, 100)  # Ensure positive volume
            
            # Create dataframe
            df = pd.DataFrame({
                'timestamp': dates,
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes,
                'volume': volumes
            })
            
            result[tf] = df
    
    return result

def test_ict_strategy():
    """Test the ICT strategy with sample data."""
    # Generate sample data
    sample_data = generate_sample_data()
    
    # Run ICT trading system
    ict_result = ict_trading_system(
        sample_data['1d'],
        sample_data['4h'],
        sample_data['1h'],
        sample_data['15m'],
        sample_data['5m'],
        symbol="BTCUSDT"
    )
    
    # Print results
    print("\n===== ICT Strategy Test Results =====")
    print(f"Symbol: {ict_result['symbol']}")
    print(f"Daily Bias: {ict_result['daily_bias']}")
    print(f"4H Bias: {ict_result['bias_4h']}")
    print(f"1H Bias: {ict_result['bias_1h']}")
    print(f"HTF Confirms Daily: {ict_result['htf_confirms_daily']}")
    print(f"Liquidity Sweep: {ict_result['liquidity_sweep']}")
    print(f"Market Structure Shift: {ict_result['market_structure_shift']}")
    print(f"In NY Kill Zone: {ict_result['in_ny_kill_zone']}")
    print(f"Take Trade: {ict_result['take_trade']}")
    print(f"Trade Direction: {ict_result['trade_direction']}")
    
    if ict_result['take_trade']:
        print(f"Stop Loss: {ict_result['stop_loss']}")
        print(f"Take Profit: {ict_result['take_profit']}")
    
    print("=======================================\n")
    
    return ict_result

if __name__ == "__main__":
    # Test the ICT strategy
    test_ict_strategy() 