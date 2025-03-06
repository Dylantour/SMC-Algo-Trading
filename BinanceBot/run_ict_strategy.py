from ict_strategy import ICTStrategyClient, LoggingPrinter
import key
import time
import sys

def main():
    """Main runner function for ICT Strategy Bot"""
    print("=" * 60)
    print("ICT Strategy Bot - Based on Market Structure, Liquidity & FVGs")
    print("=" * 60)
    
    try:
        with LoggingPrinter():
            # Initialize trading client with ICT strategy
            trader = ICTStrategyClient(key.key, key.secret)

            # Set up trading parameters
            trader.trade_history = []
            trader.base_asset = "BUSD"
            trader.asset = "BTC"
            trader.pair = "BTCBUSD"
            
            # Timeframe settings
            trader.interval = "5m"  # Lower timeframe for signal generation
            trader.df_length = 100  # Number of candles to retrieve
            trader.htf_interval = "1h"  # Higher timeframe for market structure bias
            trader.htf_df_length = 50  # Number of candles for higher timeframe
            
            # Risk management parameters
            trader.risk_per_trade = 0.01  # Risk 1% per trade
            trader.risk_reward_ratio = 2  # Target 2:1 reward-to-risk ratio
            
            # Trail stop and take profit settings
            trader.trail_stop_enabled = True
            trader.trail_stop = 0.8  # Trail at 80% of profits
            
            # FVG parameters
            trader.min_fvg_size = 0.0005  # Minimum FVG size (0.05% of price)
            trader.max_fvg_age = 20  # Maximum age in candles
            
            # Set trading mode
            trader.mode = "trade"  # Use "backtest" for backtesting
            trader.plot = False
            
            # Initialize data
            print("Initializing data and fetching candles...")
            trader.update()
            
            print("Starting trading bot...")
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