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
        self.out_file = open("enhanced_ict_strategy.log", 'a')
        self.old_stdout.write(text)
        self.out_file.write(text)
        self.out_file.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        sys.stdout = self.old_stdout


class EnhancedICTStrategyClient(BinanceClient):
    def __init__(self, _key, _secret):
        BinanceClient.__init__(self, _key, _secret)
        
        # Strategy parameters
        self.daily_interval = "1d"    # Daily timeframe for bias
        self.htf_interval = "15m"     # Higher timeframe for market structure
        self.mtf_interval = "5m"      # Medium timeframe for confirmation
        self.ltf_interval = "1m"      # Lower timeframe for entries
        
        self.daily_df_length = 30     # Number of daily candles to fetch
        self.htf_df_length = 100      # Number of HTF candles to fetch
        self.mtf_df_length = 100      # Number of MTF candles to fetch
        self.ltf_df_length = 100      # Number of LTF candles to fetch
        
        # Liquidity & Structure Parameters
        self.liquidity_lookback = 20  # Number of bars to look for liquidity levels
        self.fvg_lookback = 5         # Look for fair value gaps within this range
        
        # Risk Management Parameters
        self.stop_multiplier = 1.5    # Multiplier for setting stop loss distance
        self.take_profit_ratio = 2    # Risk-to-reward ratio
        self.trailing_stop = 0.5      # Percentage-based trailing stop
        
        # Strategy state variables
        self.daily_bias = None        # 'bullish' or 'bearish' based on daily timeframe
        self.htf_bias = None          # 'bullish' or 'bearish' based on HTF
        self.active_fvgs = []         # List of active FVGs
        self.pending_orders = []      # List of pending orders for FVG retests
        self.last_liquidity_sweep = None
        
        # Data frames
        self.daily_df = None          # Daily timeframe dataframe
        self.htf_df = None            # Higher timeframe dataframe
        self.mtf_df = None            # Medium timeframe dataframe
        self.ltf_df = None            # Lower timeframe dataframe
        
        # Risk management
        self.risk_per_trade = 0.01    # 1% risk per trade
        self.risk_reward_ratio = 2    # Risk to reward ratio
        self.partial_tp_ratio = 0.5   # Close 50% of position at first TP
    
    def update(self):
        """Override the update method to fetch all timeframes"""
        super().update()  # Call parent's update first

        # Store the current LTF dataframe
        self.ltf_df = self.df.copy()
        
        # Get all timeframe data
        original_interval = self.interval
        original_df_length = self.df_length
        
        # Get daily data for bias
        self.interval = self.daily_interval
        self.df_length = self.daily_df_length
        self.daily_df = self.get_candles()
        
        # Get HTF data
        self.interval = self.htf_interval
        self.df_length = self.htf_df_length
        self.htf_df = self.get_candles()
        
        # Get MTF data
        self.interval = self.mtf_interval
        self.df_length = self.mtf_df_length
        self.mtf_df = self.get_candles()
        
        # Restore original settings
        self.interval = original_interval
        self.df_length = original_df_length
        
        # Process all dataframes
        self.data_process()
        
    def data_process(self):
        """Process all timeframes"""
        if self.ltf_df is None or self.htf_df is None or self.mtf_df is None or self.daily_df is None:
            return
            
        # Process daily timeframe for overall market bias
        self.process_daily_data()
        
        # Process higher timeframe for market structure
        self.process_htf_data()
        
        # Process medium timeframe for confirmation
        self.process_mtf_data()
        
        # Process lower timeframe for entry setups
        self.process_ltf_data()
        
    def process_daily_data(self):
        """Process daily timeframe data for overall market bias"""
        df = self.daily_df
        
        # Calculate EMAs for daily bias
        df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
        df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
        
        # Determine daily bias based on EMAs
        current_price = df['close'].iloc[-1]
        ema20 = df['ema20'].iloc[-1]
        ema50 = df['ema50'].iloc[-1]
        
        if current_price > ema20 and current_price > ema50:
            self.daily_bias = 'bullish'
        elif current_price < ema20 and current_price < ema50:
            self.daily_bias = 'bearish'
        else:
            self.daily_bias = 'neutral'
        
        print(f"Daily Bias: {self.daily_bias}")
        
    def process_htf_data(self):
        """Process higher timeframe data for market structure"""
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
    
    def process_mtf_data(self):
        """Process medium timeframe data for confirmation"""
        df = self.mtf_df
        
        # Calculate additional indicators for confirmation
        df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        
        # Detect BOS (Break of Structure)
        self.detect_bos(df)
        
        # Detect CHOCH (Change of Character)
        self.detect_choch(df)
    
    def detect_bos(self, df):
        """Detect Break of Structure (BOS)"""
        # Identify recent swing highs and lows
        recent_highs = df[df['swing_high'] == True].tail(3)
        recent_lows = df[df['swing_low'] == True].tail(3)
        
        # Check for bullish BOS (breaking above recent swing high)
        if len(recent_highs) >= 2:
            last_high = recent_highs['high'].iloc[-1]
            prev_high = recent_highs['high'].iloc[-2]
            
            if last_high > prev_high and self.daily_bias == 'bullish':
                print(f"Detected Bullish BOS: {last_high} > {prev_high}")
                return {'type': 'bullish', 'price': last_high}
        
        # Check for bearish BOS (breaking below recent swing low)
        if len(recent_lows) >= 2:
            last_low = recent_lows['low'].iloc[-1]
            prev_low = recent_lows['low'].iloc[-2]
            
            if last_low < prev_low and self.daily_bias == 'bearish':
                print(f"Detected Bearish BOS: {last_low} < {prev_low}")
                return {'type': 'bearish', 'price': last_low}
        
        return None
    
    def detect_choch(self, df):
        """Detect Change of Character (CHOCH)"""
        # CHOCH occurs when price fails to continue in the expected direction after a BOS
        # For bullish CHOCH: Price makes a higher high (BOS) but then fails to make a new higher high
        # For bearish CHOCH: Price makes a lower low (BOS) but then fails to make a new lower low
        
        # This is a simplified implementation
        recent_highs = df[df['swing_high'] == True].tail(3)
        recent_lows = df[df['swing_low'] == True].tail(3)
        
        if len(recent_highs) >= 3 and len(recent_lows) >= 2:
            # Check for bullish CHOCH
            if recent_highs['high'].iloc[-1] < recent_highs['high'].iloc[-2] and \
               recent_lows['low'].iloc[-1] > recent_lows['low'].iloc[-2] and \
               self.daily_bias == 'bullish':
                print(f"Detected Bullish CHOCH")
                return {'type': 'bullish', 'price': recent_lows['low'].iloc[-1]}
        
        if len(recent_lows) >= 3 and len(recent_highs) >= 2:
            # Check for bearish CHOCH
            if recent_lows['low'].iloc[-1] > recent_lows['low'].iloc[-2] and \
               recent_highs['high'].iloc[-1] < recent_highs['high'].iloc[-2] and \
               self.daily_bias == 'bearish':
                print(f"Detected Bearish CHOCH")
                return {'type': 'bearish', 'price': recent_highs['high'].iloc[-1]}
        
        return None
    
    def process_ltf_data(self):
        """Process lower timeframe data for entries"""
        df = self.ltf_df
        
        # Only proceed if daily bias and HTF bias align
        if self.daily_bias != self.htf_bias or self.daily_bias == 'neutral':
            return
        
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
        lookback = self.liquidity_lookback
        if len(df) <= lookback:
            return None
            
        # Find the lowest low and highest high in the lookback period (excluding last 5 candles)
        recent_low = df['low'].iloc[-lookback:-5].min()
        recent_high = df['high'].iloc[-lookback:-5].max()
        
        # Check if recent candles have swept below the swing low and then reversed
        if any(recent_candles['low'] < recent_low * 0.999) and recent_candles['close'].iloc[-1] > recent_candles['open'].iloc[-1]:
            # Bullish sweep (swept lows then reversed up)
            if self.daily_bias == 'bullish':  # Only consider sweeps in the direction of daily bias
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
            if self.daily_bias == 'bearish':  # Only consider sweeps in the direction of daily bias
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
                if fvg_size > 0.001:  # At least 0.1% gap
                    print(f"Detected Bullish FVG: Size {fvg_size:.4%}")
                    
                    # Add to active FVGs
                    fvg = {
                        'type': 'bullish',
                        'top': candle3['low'],
                        'bottom': candle1['high'],
                        'size': fvg_size,
                        'age': 0,
                        'created_at': df.index[candle3_idx]
                    }
                    
                    self.active_fvgs.append(fvg)
                    return fvg
        
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
                if fvg_size > 0.001:  # At least 0.1% gap
                    print(f"Detected Bearish FVG: Size {fvg_size:.4%}")
                    
                    # Add to active FVGs
                    fvg = {
                        'type': 'bearish',
                        'top': candle1['low'],
                        'bottom': candle3['high'],
                        'size': fvg_size,
                        'age': 0,
                        'created_at': df.index[candle3_idx]
                    }
                    
                    self.active_fvgs.append(fvg)
                    return fvg
        
        return None
    
    def update_active_fvgs(self, df):
        """Update active FVGs, removing filled or expired ones"""
        if not self.active_fvgs:
            return
            
        current_price = df['close'].iloc[-1]
        updated_fvgs = []
        
        for fvg in self.active_fvgs:
            # Increment age
            fvg['age'] += 1
            
            # Check if FVG is still valid
            if fvg['age'] > self.fvg_lookback:
                print(f"FVG expired: {fvg['type']} at {fvg['bottom']}-{fvg['top']}")
                continue
                
            # Check if FVG has been filled
            if fvg['type'] == 'bullish' and current_price < fvg['bottom']:
                print(f"Bullish FVG filled: {fvg['bottom']}-{fvg['top']}")
                continue
                
            if fvg['type'] == 'bearish' and current_price > fvg['top']:
                print(f"Bearish FVG filled: {fvg['bottom']}-{fvg['top']}")
                continue
                
            # Keep valid FVGs
            updated_fvgs.append(fvg)
            
        self.active_fvgs = updated_fvgs
    
    def check_fvg_retests(self, df):
        """Check for retests of FVGs for potential entries"""
        if not self.active_fvgs:
            return
            
        current_price = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        # Only consider entries aligned with daily bias
        for fvg in self.active_fvgs:
            # For bullish FVGs, look for price retesting the top of the FVG
            if fvg['type'] == 'bullish' and self.daily_bias == 'bullish':
                if current_low <= fvg['top'] and current_price > fvg['top']:
                    # Price retested the top of bullish FVG and bounced
                    print(f"Bullish entry signal: FVG retest at {fvg['top']}")
                    
                    # Calculate stop loss and take profit
                    stop_loss = fvg['bottom'] - (fvg['top'] - fvg['bottom']) * 0.5
                    take_profit = current_price + (current_price - stop_loss) * self.take_profit_ratio
                    
                    # Check if we have enough room for a good risk-reward
                    if (take_profit - current_price) / (current_price - stop_loss) >= self.risk_reward_ratio:
                        print(f"Taking bullish trade: Entry={current_price}, SL={stop_loss}, TP={take_profit}")
                        self.buy()
                        return True
            
            # For bearish FVGs, look for price retesting the bottom of the FVG
            elif fvg['type'] == 'bearish' and self.daily_bias == 'bearish':
                if current_high >= fvg['bottom'] and current_price < fvg['bottom']:
                    # Price retested the bottom of bearish FVG and bounced
                    print(f"Bearish entry signal: FVG retest at {fvg['bottom']}")
                    
                    # Calculate stop loss and take profit
                    stop_loss = fvg['top'] + (fvg['top'] - fvg['bottom']) * 0.5
                    take_profit = current_price - (stop_loss - current_price) * self.take_profit_ratio
                    
                    # Check if we have enough room for a good risk-reward
                    if (current_price - take_profit) / (stop_loss - current_price) >= self.risk_reward_ratio:
                        print(f"Taking bearish trade: Entry={current_price}, SL={stop_loss}, TP={take_profit}")
                        self.sell()
                        return True
        
        return False
    
    def manager(self):
        """Main strategy manager - override parent method"""
        # Only take trades when daily bias and HTF bias align
        if self.daily_bias == self.htf_bias and self.daily_bias != 'neutral':
            # Check for FVG retests
            self.check_fvg_retests(self.ltf_df)
        
        # Manage existing positions
        if self.position_open:
            self.manage_position()
    
    def manage_position(self):
        """Manage open positions"""
        if not self.position_open:
            return
            
        current_price = self.ltf_df['close'].iloc[-1]
        
        # Update trailing stop if enabled
        if self.trail_stop_enabled:
            self.update_trailstop(current_price)
        
        # Check if we need to close position
        if self.position_data['type'] == 'long':
            # Check if price hit stop loss
            if current_price <= self.position_data['stop_loss']:
                print(f"Closing long position at stop loss: {current_price}")
                self.sell()
            
            # Check if price hit take profit
            elif current_price >= self.position_data['take_profit']:
                print(f"Closing long position at take profit: {current_price}")
                self.sell()
                
        elif self.position_data['type'] == 'short':
            # Check if price hit stop loss
            if current_price >= self.position_data['stop_loss']:
                print(f"Closing short position at stop loss: {current_price}")
                self.buy()
            
            # Check if price hit take profit
            elif current_price <= self.position_data['take_profit']:
                print(f"Closing short position at take profit: {current_price}")
                self.buy() 