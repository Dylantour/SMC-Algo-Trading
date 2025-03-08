from BinanceClient import BinanceClient
import key
import time, datetime
import pandas as pd
import numpy as np
import ta
import sys


class LoggingPrinter:
    def __init__(self):
        self.old_stdout = sys.stdout
        sys.stdout = self
    
    def write(self, text):
        self.out_file = open("trade_py.log", 'a')
        self.old_stdout.write(text)
        self.out_file.write(text)
        self.out_file.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        sys.stdout = self.old_stdout


class ICTTraderClient(BinanceClient):
    def __init__(self, _key, _secret):
        BinanceClient.__init__(self, _key, _secret)
        
        # Strategy parameters
        self.htf_interval = "1h"  # Higher timeframe for market structure bias
        self.ltf_interval = "5m"  # Lower timeframe for entries
        self.ltf_df_length = 100  # Number of candles to fetch for lower timeframe
        self.htf_df_length = 50   # Number of candles to fetch for higher timeframe
        
        # FVG Parameters
        self.min_fvg_size = 0.0005  # Minimum FVG size as percentage of price (0.05%)
        self.max_fvg_age = 20       # Maximum age of FVG in candles
        
        # Strategy state variables
        self.htf_bias = None        # 'bullish' or 'bearish'
        self.active_fvgs = []       # List of active FVGs
        self.pending_orders = []    # List of pending orders for FVG retests
        self.last_liquidity_sweep = None
        
        # Data frames
        self.htf_df = None         # Higher timeframe dataframe
        self.ltf_df = None         # Lower timeframe dataframe
        
        # Risk management
        self.risk_per_trade = 0.01  # 1% risk per trade
        self.risk_reward_ratio = 2  # Risk to reward ratio
        self.partial_tp_ratio = 0.5 # Close 50% of position at first TP
    
    def update(self):
        """Override the update method to fetch both timeframes"""
        super().update()  # Call parent's update first

        # Store the current LTF dataframe
        self.ltf_df = self.df.copy()
        
        # Get HTF data
        original_interval = self.interval
        original_df_length = self.df_length
        
        self.interval = self.htf_interval
        self.df_length = self.htf_df_length
        
        self.htf_df = self.get_candles()
        
        # Restore original settings
        self.interval = original_interval
        self.df_length = original_df_length
        
        # Process both dataframes
        self.data_process()
        
    def data_process(self):
        """Process both timeframes"""
        if self.ltf_df is None or self.htf_df is None:
            return
            
        # Process higher timeframe for market structure bias
        self.process_htf_data()
        
        # Process lower timeframe for entry setups
        self.process_ltf_data()
        
    def process_htf_data(self):
        """Process higher timeframe data for market structure bias"""
        df = self.htf_df
        
        # Calculate swing highs and lows on HTF
        self.calculate_swings(df, window=5)
        
        # Determine market structure based on recent swings
        self.htf_bias = self.determine_market_structure(df)
        
        # Log the current bias
        print(f"HTF Bias: {self.htf_bias}")
    
    def calculate_swings(self, df, window=5):
        """Calculate swing highs and lows"""
        df['swing_high'] = False
        df['swing_low'] = False
        
        for i in range(window, len(df) - window):
            # Check for swing high
            if all(df['high'].iloc[i] > df['high'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['high'].iloc[i] > df['high'].iloc[i+j] for j in range(1, window+1)):
                df.at[df.index[i], 'swing_high'] = True
            
            # Check for swing low
            if all(df['low'].iloc[i] < df['low'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['low'].iloc[i] < df['low'].iloc[i+j] for j in range(1, window+1)):
                df.at[df.index[i], 'swing_low'] = True
        
    def determine_market_structure(self, df):
        """Determine market structure as bullish or bearish"""
        # Get last 4 swing points
        recent_swings = pd.DataFrame()
        
        # Extract swing highs
        swing_highs = df[df['swing_high'] == True].copy()
        swing_highs['type'] = 'high'
        swing_highs['value'] = swing_highs['high']
        
        # Extract swing lows
        swing_lows = df[df['swing_low'] == True].copy()
        swing_lows['type'] = 'low'
        swing_lows['value'] = swing_lows['low']
        
        # Combine and sort
        swings = pd.concat([swing_highs, swing_lows])
        swings = swings.sort_index().tail(4)
        
        if len(swings) < 4:
            # Not enough swing points, use SMA slope as fallback
            sma50 = df['close'].rolling(50).mean()
            sma20 = df['close'].rolling(20).mean()
            
            if sma20.iloc[-1] > sma50.iloc[-1] and sma20.iloc[-1] > sma20.iloc[-2]:
                return 'bullish'
            elif sma20.iloc[-1] < sma50.iloc[-1] and sma20.iloc[-1] < sma20.iloc[-2]:
                return 'bearish'
            else:
                return 'neutral'
        
        # Check if we have higher highs and higher lows (bullish)
        if swings['type'].iloc[-2] == 'high' and swings['type'].iloc[-4] == 'high':
            if swings['value'].iloc[-2] > swings['value'].iloc[-4]:
                return 'bullish'
        
        # Check if we have lower lows and lower highs (bearish)
        if swings['type'].iloc[-2] == 'low' and swings['type'].iloc[-4] == 'low':
            if swings['value'].iloc[-2] < swings['value'].iloc[-4]:
                return 'bearish'
        
        # Default to neutral
        return 'neutral'
    
    def process_ltf_data(self):
        """Process lower timeframe data for entries"""
        df = self.ltf_df
        
        # Detect liquidity sweeps
        self.detect_liquidity_sweeps(df)
        
        # Detect fair value gaps
        self.detect_fair_value_gaps(df)
        
        # Update active FVGs (remove filled or expired ones)
        self.update_active_fvgs(df)
        
        # Look for FVG retests
        self.check_fvg_retests(df)
    
    def detect_liquidity_sweeps(self, df):
        """Detect liquidity sweeps of recent swing points"""
        # Look at the last 5 candles
        recent_candles = df.tail(5)
        
        # Find recent swing lows and highs
        lookback = 20
        if len(df) <= lookback:
            return None
            
        # Find the lowest low and highest high in the lookback period (excluding last 5 candles)
        recent_low = df['low'].iloc[-lookback:-5].min()
        recent_high = df['high'].iloc[-lookback:-5].max()
        
        # Check if recent candles have swept below the swing low and then reversed
        if any(recent_candles['low'] < recent_low * 0.999) and recent_candles['close'].iloc[-1] > recent_candles['open'].iloc[-1]:
            # Bullish sweep (swept lows then reversed up)
            if self.htf_bias == 'bullish':  # Only consider sweeps in the direction of HTF bias
                print(f"Detected Bullish Liquidity Sweep: Swept low at {recent_low}")
                self.last_liquidity_sweep = {
                    'type': 'bullish',
                    'price': recent_low,
                    'candle_index': len(df) - 1,
                    'time': df.index[-1]
                }
                return self.last_liquidity_sweep
        
        # Check if recent candles have swept above the swing high and then reversed
        if any(recent_candles['high'] > recent_high * 1.001) and recent_candles['close'].iloc[-1] < recent_candles['open'].iloc[-1]:
            # Bearish sweep (swept highs then reversed down)
            if self.htf_bias == 'bearish':  # Only consider sweeps in the direction of HTF bias
                print(f"Detected Bearish Liquidity Sweep: Swept high at {recent_high}")
                self.last_liquidity_sweep = {
                    'type': 'bearish',
                    'price': recent_high,
                    'candle_index': len(df) - 1,
                    'time': df.index[-1]
                }
                return self.last_liquidity_sweep
        
        return None
    
    def detect_fair_value_gaps(self, df):
        """Detect fair value gaps (FVGs) after displacement candles"""
        if self.last_liquidity_sweep is None:
            return
            
        # Look for displacement after liquidity sweep
        sweep_idx = self.last_liquidity_sweep['candle_index']
        
        # We need at least 3 candles after the sweep to form an FVG
        if len(df) < sweep_idx + 3:
            return
            
        # Check for bullish FVG (Candle 3's low is above Candle 1's high)
        if self.last_liquidity_sweep['type'] == 'bullish':
            # Get candles involved in potential FVG
            candle1_idx = sweep_idx
            candle2_idx = sweep_idx + 1  # Displacement candle
            candle3_idx = sweep_idx + 2
            
            candle1 = df.iloc[candle1_idx]
            candle2 = df.iloc[candle2_idx]
            candle3 = df.iloc[candle3_idx]
            
            # Check if candle 2 is a strong bullish candle
            is_bullish_displacement = (candle2['close'] > candle2['open'] and 
                                    (candle2['close'] - candle2['open']) / candle2['open'] > 0.001)
            
            # Check if there's a gap between candle 1 high and candle 3 low
            if is_bullish_displacement and candle3['low'] > candle1['high']:
                fvg_size = (candle3['low'] - candle1['high']) / candle1['high']
                
                # Only consider significant FVGs
                if fvg_size >= self.min_fvg_size:
                    fvg = {
                        'type': 'bullish',
                        'top': candle3['low'],
                        'bottom': candle1['high'],
                        'mid': (candle3['low'] + candle1['high']) / 2,
                        'size': fvg_size,
                        'age': 0,
                        'created_at': df.index[candle3_idx],
                        'filled': False
                    }
                    
                    self.active_fvgs.append(fvg)
                    print(f"Detected Bullish FVG: {fvg['bottom']} to {fvg['top']}, size: {fvg['size']*100:.2f}%")
        
        # Check for bearish FVG (Candle 3's high is below Candle 1's low)
        elif self.last_liquidity_sweep['type'] == 'bearish':
            # Get candles involved in potential FVG
            candle1_idx = sweep_idx
            candle2_idx = sweep_idx + 1  # Displacement candle
            candle3_idx = sweep_idx + 2
            
            candle1 = df.iloc[candle1_idx]
            candle2 = df.iloc[candle2_idx]
            candle3 = df.iloc[candle3_idx]
            
            # Check if candle 2 is a strong bearish candle
            is_bearish_displacement = (candle2['close'] < candle2['open'] and 
                                     (candle2['open'] - candle2['close']) / candle2['open'] > 0.001)
            
            # Check if there's a gap between candle 1 low and candle 3 high
            if is_bearish_displacement and candle3['high'] < candle1['low']:
                fvg_size = (candle1['low'] - candle3['high']) / candle1['low']
                
                # Only consider significant FVGs
                if fvg_size >= self.min_fvg_size:
                    fvg = {
                        'type': 'bearish',
                        'top': candle1['low'],
                        'bottom': candle3['high'],
                        'mid': (candle1['low'] + candle3['high']) / 2,
                        'size': fvg_size,
                        'age': 0,
                        'created_at': df.index[candle3_idx],
                        'filled': False
                    }
                    
                    self.active_fvgs.append(fvg)
                    print(f"Detected Bearish FVG: {fvg['top']} to {fvg['bottom']}, size: {fvg['size']*100:.2f}%")
    
    def update_active_fvgs(self, df):
        """Update active FVGs (remove filled or expired ones)"""
        if not self.active_fvgs:
            return
            
        latest_price = df['close'].iloc[-1]
        updated_fvgs = []
        
        for fvg in self.active_fvgs:
            # Increment age
            fvg['age'] += 1
            
            # Check if FVG has been filled
            if fvg['type'] == 'bullish':
                # A bullish FVG is filled if price drops below the middle of the gap
                if df['low'].iloc[-1] <= fvg['mid']:
                    fvg['filled'] = True
                    print(f"Bullish FVG from {fvg['created_at']} has been filled")
            else:
                # A bearish FVG is filled if price rises above the middle of the gap
                if df['high'].iloc[-1] >= fvg['mid']:
                    fvg['filled'] = True
                    print(f"Bearish FVG from {fvg['created_at']} has been filled")
            
            # Keep FVG if it's not too old and not filled
            if fvg['age'] <= self.max_fvg_age and not fvg['filled']:
                updated_fvgs.append(fvg)
        
        self.active_fvgs = updated_fvgs
    
    def check_fvg_retests(self, df):
        """Check for retests of active FVGs to generate entry signals"""
        if not self.active_fvgs or self.position_open:
            return
            
        latest_candle = df.iloc[-1]
        latest_price = latest_candle['close']
        
        for fvg in self.active_fvgs:
            # Check if price is retesting the FVG
            if fvg['type'] == 'bullish':
                # For bullish FVG, we enter when price pulls back to the FVG area
                if latest_candle['low'] <= fvg['top'] and latest_candle['high'] >= fvg['bottom']:
                    # Price is within FVG range, trigger entry
                    entry_price = latest_price
                    stop_loss = self.last_liquidity_sweep['price'] * 0.998  # Just below sweep low
                    
                    # Calculate take profit based on risk-reward
                    risk = entry_price - stop_loss
                    take_profit = entry_price + (risk * self.risk_reward_ratio)
                    
                    print(f"Bullish FVG Retest Triggered: Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}")
                    
                    # Place order
                    self.buy()
                    
                    # Set custom stop loss and take profit
                    self.tp = [take_profit]
                    self.tp_ratio = [1.0]
                    self.trail_stop_enabled = True
                    self.trail_stop = 0.8  # Keep 80% of profits
                    
                    # Remove this FVG from active list
                    self.active_fvgs.remove(fvg)
                    return
                    
            elif fvg['type'] == 'bearish':
                # For bearish FVG, we enter when price pulls back to the FVG area
                if latest_candle['high'] >= fvg['bottom'] and latest_candle['low'] <= fvg['top']:
                    # Price is within FVG range, trigger entry
                    entry_price = latest_price
                    stop_loss = self.last_liquidity_sweep['price'] * 1.002  # Just above sweep high
                    
                    # Calculate take profit based on risk-reward
                    risk = stop_loss - entry_price
                    take_profit = entry_price - (risk * self.risk_reward_ratio)
                    
                    print(f"Bearish FVG Retest Triggered: Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}")
                    
                    # Place order
                    self.sell()
                    
                    # Set custom stop loss and take profit
                    self.tp = [take_profit]
                    self.tp_ratio = [1.0]
                    self.trail_stop_enabled = True
                    self.trail_stop = 0.8  # Keep 80% of profits
                    
                    # Remove this FVG from active list
                    self.active_fvgs.remove(fvg)
                    return
    
    def manager(self):
        """Main manager method to handle trading decisions"""
        # Check for trail stop conditions first
        ts = self.update_trailstop(self.df.iloc[-1])
        if ts:
            return 1
            
        # No need to do anything if the strategy is off
        if self.htf_bias == 'neutral':
            print("Market structure is neutral, no new trades")
            return 0
            
        # Check for FVG retests to generate entry signals
        self.check_fvg_retests(self.ltf_df)
        
        return 0


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



