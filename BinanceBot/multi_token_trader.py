#!/usr/bin/env python3
"""
multi_token_trader.py - Run multiple ICT strategy bots for different trading pairs

This script allows running multiple instances of the ICT trading strategy
for different cryptocurrency pairs simultaneously.
"""

import os
import sys
import time
import datetime
import argparse
import logging
import threading
import json
from pathlib import Path
import key
from trade import ICTTraderClient

# Create necessary directories
os.makedirs('logs', exist_ok=True)
os.makedirs('charts', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/multi_token_trader.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Dictionary to store all trader instances
traders = {}

# Dictionary to store status for each trading pair
pair_status = {}

# Lock for thread safety when updating shared data
trader_lock = threading.Lock()

# Import dashboard components after initializing directories
from dashboard import app, update_bot_status, bot_status

def setup_logging():
    """Configure logging for the bot"""
    log_path = "logs"
    
    # Ensure log directory exists
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    
    return logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run multiple ICT Strategy Bots')
    
    parser.add_argument('--pairs', type=str, required=True,
                        help='Comma-separated list of trading pairs (e.g., BTCBUSD,ETHBUSD,BNBBUSD)')
    parser.add_argument('--htf', type=str, default='1h',
                        help='Higher timeframe for market structure (default: 1h)')
    parser.add_argument('--ltf', type=str, default='5m',
                        help='Lower timeframe for entries (default: 5m)')
    parser.add_argument('--risk', type=float, default=0.01,
                        help='Risk per trade as a decimal (default: 0.01)')
    parser.add_argument('--trail', type=float, default=0.8,
                        help='Trail stop ratio (default: 0.8)')
    parser.add_argument('--min-fvg-size', type=float, default=0.0005,
                        help='Minimum fair value gap size (default: 0.0005)')
    parser.add_argument('--port', type=int, default=8080,
                        help='Port for the web dashboard (default: 8080)')
    parser.add_argument('--debug', action='store_true',
                        help='Run Flask in debug mode')
    
    return parser.parse_args()

def bot_status_updater(update_interval=5):
    """Thread function to update the dashboard with bot status for all pairs"""
    global bot_status, pair_status
    
    while True:
        try:
            # Collect status information from all traders
            combined_status = {
                'is_running': True,
                'pairs': [],
                'total_value': 0,
                'total_trades': 0,
                'win_trades': 0,
                'active_positions': 0,
                'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with trader_lock:
                # Process each trader's status
                for pair, trader in traders.items():
                    if not hasattr(trader, 'initialized') or not trader.initialized:
                        continue

                    if pair not in pair_status:
                        pair_status[pair] = {}
                    
                    # Update pair-specific status
                    pair_status[pair] = {
                        'trading_pair': pair,
                        'base_balance': trader.base_balance if hasattr(trader, 'base_balance') else 0,
                        'asset_balance': trader.asset_balance if hasattr(trader, 'asset_balance') else 0,
                        'current_price': trader.asset_price if hasattr(trader, 'asset_price') else 0,
                        'market_bias': trader.htf_bias if hasattr(trader, 'htf_bias') else 'Unknown',
                        'active_fvgs': len(trader.active_fvgs) if hasattr(trader, 'active_fvgs') else 0,
                        'position_open': trader.position_open if hasattr(trader, 'position_open') else False,
                        'position_type': trader.position_type if hasattr(trader, 'position_type') and trader.position_open else 'None',
                    }
                    
                    # Calculate pair value
                    if hasattr(trader, 'base_balance') and hasattr(trader, 'asset_balance') and hasattr(trader, 'asset_price'):
                        pair_value = trader.base_balance + (trader.asset_balance * trader.asset_price)
                        pair_status[pair]['total_value'] = pair_value
                        combined_status['total_value'] += pair_value
                    
                    # Get trade statistics
                    if hasattr(trader, 'trade_history') and trader.trade_history:
                        trades = trader.trade_history
                        pair_status[pair]['total_trades'] = len(trades)
                        combined_status['total_trades'] += len(trades)
                        
                        wins = sum(1 for trade in trades if trade.get('profit_pct', 0) > 0)
                        pair_status[pair]['win_rate'] = round((wins / len(trades)) * 100, 2) if len(trades) > 0 else 0
                        combined_status['win_trades'] += wins
                        
                        profits = [trade.get('profit_pct', 0) for trade in trades]
                        pair_status[pair]['avg_profit'] = round(sum(profits) / len(profits), 2) if profits else 0
                    
                    # Count active positions
                    if trader.position_open:
                        combined_status['active_positions'] += 1
                    
                    # Add to pairs list
                    combined_status['pairs'].append(pair)
            
            # Calculate overall win rate
            if combined_status['total_trades'] > 0:
                combined_status['win_rate'] = round((combined_status['win_trades'] / combined_status['total_trades']) * 100, 2)
            else:
                combined_status['win_rate'] = 0
            
            # Update the dashboard status
            update_bot_status(combined_status)
            
            logger.info(f"Updated dashboard status for {len(traders)} pairs")
            
        except Exception as e:
            logger.error(f"Error updating dashboard status: {e}", exc_info=True)
        
        # Sleep before next update
        time.sleep(update_interval)

def initialize_trader(trader, pair):
    """Initialize trader data and mark as ready"""
    try:
        # Initial data update
        logger.info(f"[{pair}] Initializing market data")
        trader.update()
        
        # Force updating both HTF and LTF data
        logger.info(f"[{pair}] Fetching HTF data")
        htf_candles = trader.client.get_klines(
            symbol=pair,
            interval=trader.htf_interval,
            limit=trader.htf_df_length
        )
        
        # Import pandas here to avoid circular imports
        import pandas as pd
        
        trader.htf_df = pd.DataFrame(htf_candles, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'trades',
            'taker_buy_base', 'taker_buy_quote', 'ignored'
        ])
        
        # Convert string columns to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            trader.htf_df[col] = pd.to_numeric(trader.htf_df[col])
            
        # Convert timestamp to datetime
        trader.htf_df['timestamp'] = pd.to_datetime(trader.htf_df['timestamp'], unit='ms')
        
        # Fetch LTF data separately
        logger.info(f"[{pair}] Fetching LTF data")
        ltf_candles = trader.client.get_klines(
            symbol=pair,
            interval=trader.interval,
            limit=trader.df_length
        )
        
        trader.df = pd.DataFrame(ltf_candles, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'trades',
            'taker_buy_base', 'taker_buy_quote', 'ignored'
        ])
        
        # Convert string columns to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            trader.df[col] = pd.to_numeric(trader.df[col])
            
        # Convert timestamp to datetime
        trader.df['timestamp'] = pd.to_datetime(trader.df['timestamp'], unit='ms')
        
        # Process data for trading
        trader.data_process()
        
        # Mark trader as initialized
        trader.initialized = True
        logger.info(f"[{pair}] Trader initialized successfully")
        return True
    except Exception as e:
        logger.error(f"[{pair}] Error initializing trader: {e}", exc_info=True)
        return False

def run_trader(pair, args):
    """Run a single trader instance for a specific pair"""
    try:
        logger.info(f"Initializing trader for {pair}")
        
        # Extract the base and asset from the pair (e.g., BTCBUSD -> BTC, BUSD)
        if 'BUSD' in pair:
            asset = pair.replace('BUSD', '')
            base = 'BUSD'
        elif 'USDT' in pair:
            asset = pair.replace('USDT', '')
            base = 'USDT'
        else:
            logger.error(f"Unsupported pair format: {pair}")
            return
        
        # Initialize the trader
        trader = ICTTraderClient(key.key, key.secret)
        
        # Set up basic parameters
        trader.trade_history = []
        trader.base_asset = base
        trader.asset = asset
        trader.pair = pair
        trader.interval = args.ltf
        trader.df_length = 100
        trader.initialized = False
        
        # Set ICT strategy specific parameters
        trader.htf_interval = args.htf
        trader.htf_df_length = 50
        trader.min_fvg_size = args.min_fvg_size
        trader.risk_per_trade = args.risk
        
        # Enable trailing stops
        trader.trail_stop_enabled = True
        trader.trail_stop = args.trail
        
        # Set mode
        trader.mode = "trade"
        trader.plot = True  # Enable plotting for visualization
        
        # Store the trader instance
        with trader_lock:
            traders[pair] = trader
        
        # Initialize market data
        initialization_attempts = 0
        max_attempts = 3
        while initialization_attempts < max_attempts and not trader.initialized:
            if initialize_trader(trader, pair):
                break
            initialization_attempts += 1
            logger.warning(f"[{pair}] Initialization attempt {initialization_attempts} failed, retrying...")
            time.sleep(3)  # Wait before retrying
        
        if not trader.initialized:
            logger.error(f"[{pair}] Failed to initialize after {max_attempts} attempts")
            return
        
        # Start trading
        logger.info(f"Starting trading process for {pair}")
        
        # Main trading loop
        while True:
            try:
                # Update market data
                trader.update()
                
                # Run trading logic
                trader.manager()
                
                # Sleep to avoid excessive API calls
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in trading loop for {pair}: {e}", exc_info=True)
                time.sleep(10)  # Longer sleep on error
        
    except Exception as e:
        logger.error(f"Critical error in trader for {pair}: {e}", exc_info=True)

def run_dashboard(args):
    """Run the Flask dashboard in a separate thread"""
    try:
        logger.info(f"Starting web dashboard on port {args.port}")
        print(f"Dashboard available at: http://localhost:{args.port}/")
        app.run(host='0.0.0.0', port=args.port, debug=args.debug, use_reloader=False)
    except Exception as e:
        logger.error(f"Error starting dashboard: {e}", exc_info=True)

def main():
    """Main execution function"""
    # Set up logging
    logger = setup_logging()
    logger.info("Starting Multi-Token ICT Strategy Bot")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Parse trading pairs
    pairs = [pair.strip() for pair in args.pairs.split(',')]
    logger.info(f"Trading pairs: {pairs}")
    
    # Check if API keys are set
    if key.key == "YOUR_API_KEY" or key.secret == "YOUR_API_SECRET":
        logger.warning("You are using default API keys from key.py.")
        logger.warning("Please update the key.py file with your Binance API credentials.")

    try:
        # Import pandas here to avoid circular imports
        import pandas as pd
        
        # Start the status updater thread
        status_thread = threading.Thread(target=bot_status_updater, daemon=True)
        status_thread.start()
        
        # Start a trader thread for each pair
        trader_threads = []
        for pair in pairs:
            trader_thread = threading.Thread(target=run_trader, args=(pair, args), daemon=True)
            trader_thread.start()
            trader_threads.append(trader_thread)
            time.sleep(3)  # Stagger the starts to avoid API rate limits
        
        # Start the dashboard in a separate thread
        dashboard_thread = threading.Thread(target=run_dashboard, args=(args,), daemon=False)
        dashboard_thread.start()
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot manually stopped by user")
            
    except KeyboardInterrupt:
        logger.info("Bot manually stopped by user")
    except Exception as e:
        logger.error(f"Error starting bot and dashboard: {e}", exc_info=True)

if __name__ == "__main__":
    main() 