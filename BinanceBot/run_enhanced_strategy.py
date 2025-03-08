from enhanced_ict_strategy import EnhancedICTStrategyClient, LoggingPrinter
import key
import time
import sys

def main():
    """Main runner function for Enhanced ICT Strategy Bot"""
    print("=" * 70)
    print("Enhanced ICT Strategy Bot - Multi-Timeframe Analysis with Daily Bias")
    print("=" * 70)
    
    try:
        with LoggingPrinter():
            # Initialize trading client with Enhanced ICT strategy
            trader = EnhancedICTStrategyClient(key.key, key.secret)

            # Set up trading parameters
            trader.trade_history = []
            trader.base_asset = "BUSD"
            trader.asset = "BTC"
            trader.pair = "BTCBUSD"
            
            # Timeframe settings
            trader.interval = "1m"  # Lower timeframe for signal generation
            trader.df_length = 100  # Number of candles to retrieve
            
            # Multi-timeframe settings
            trader.daily_interval = "1d"  # Daily timeframe for bias
            trader.daily_df_length = 30   # Number of daily candles
            
            trader.htf_interval = "15m"   # Higher timeframe for market structure
            trader.htf_df_length = 100    # Number of HTF candles
            
            trader.mtf_interval = "5m"    # Medium timeframe for confirmation
            trader.mtf_df_length = 100    # Number of MTF candles
            
            # Risk management parameters
            trader.risk_per_trade = 0.01  # Risk 1% per trade
            trader.risk_reward_ratio = 2  # Target 2:1 reward-to-risk ratio
            
            # Trail stop and take profit settings
            trader.trail_stop_enabled = True
            trader.trail_stop = 0.8  # Trail at 80% of profits
            
            # FVG parameters
            trader.liquidity_lookback = 20  # Number of bars to look for liquidity levels
            trader.fvg_lookback = 5         # Look for fair value gaps within this range
            
            # Set trading mode
            trader.mode = "trade"  # Use "backtest" for backtesting
            trader.plot = False
            
            # Initialize data
            print("Initializing data and fetching candles from multiple timeframes...")
            trader.update()
            
            print("Starting trading bot with enhanced ICT strategy...")
            time.sleep(0.3)
            trader.start()
            
    except KeyboardInterrupt:
        print("\nStopping the trading bot gracefully...")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 