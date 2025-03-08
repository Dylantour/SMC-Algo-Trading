#!/usr/bin/env python3
"""
unified_trader.py - Unified trading bot supporting multiple strategies and tokens

This script allows running multiple instances of trading strategies 
(Original or ICT) for different cryptocurrency pairs simultaneously.
It connects to the dashboard for monitoring and control.
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
from BinanceClient import BinanceClient
from dashboard import app, update_bot_status, update_pair_status, bot_status, pair_status, add_trade

# Create necessary directories
os.makedirs('logs', exist_ok=True)
os.makedirs('charts', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/unified_trader.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Dictionary to store all trader instances
traders = {}

# Lock for thread safety when updating shared data
trader_lock = threading.Lock()

def setup_logging():
    """Configure logging for the bot"""
    log_path = "logs"
    
    # Ensure log directory exists
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    
    return logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run Unified Trading Bot')
    
    parser.add_argument('--pairs', type=str, required=True,
                        help='Comma-separated list of trading pairs (e.g., BTCBUSD,ETHBUSD,BNBBUSD)')
    parser.add_argument('--strategy', type=str, default='ICT', choices=['ICT', 'Original'],
                        help='Trading strategy to use (default: ICT)')
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
                'strategy': bot_status['strategy'],
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
                    combined_status['pairs'].append(pair)
                    
                    # Get trader-specific data
                    trader_data = pair_status.get(pair, {})
                    
                    # Update position status
                    if hasattr(trader, 'position_open'):
                        trader_data['position_open'] = trader.position_open
                        if trader.position_open:
                            combined_status['active_positions'] += 1
                    
                    # Update trade count and win rate
                    if hasattr(trader, 'trade_history') and trader.trade_history:
                        trades = len(trader.trade_history)
                        win_trades = sum(1 for trade in trader.trade_history if trade.get('profit', 0) > 0)
                        win_rate = (win_trades / trades * 100) if trades > 0 else 0
                        
                        trader_data['total_trades'] = trades
                        trader_data['win_rate'] = round(win_rate, 1)
                        
                        combined_status['total_trades'] += trades
                        combined_status['win_trades'] += win_trades
                    
                    # Update market structure info for ICT strategy
                    if hasattr(trader, 'market_bias'):
                        trader_data['market_bias'] = trader.market_bias
                    
                    # Update FVG info for ICT strategy
                    if hasattr(trader, 'bull_fvgs') and hasattr(trader, 'bear_fvgs'):
                        trader_data['active_fvgs'] = len(trader.bull_fvgs) + len(trader.bear_fvgs)
                    
                    # Update balances and price
                    if hasattr(trader, 'balances'):
                        base_asset = trader.base_asset if hasattr(trader, 'base_asset') else 'BUSD'
                        asset = trader.asset if hasattr(trader, 'asset') else pair.replace(base_asset, '')
                        
                        trader_data['base_balance'] = trader.balances.get(base_asset, 0)
                        trader_data['asset_balance'] = trader.balances.get(asset, 0)
                        
                        # Get current price
                        if hasattr(trader, 'asset_price') and trader.asset_price:
                            trader_data['current_price'] = trader.asset_price
                        
                        # Calculate total value
                        total_value = trader_data.get('base_balance', 0)
                        if trader_data.get('asset_balance') and trader_data.get('current_price'):
                            total_value += trader_data['asset_balance'] * trader_data['current_price']
                        
                        trader_data['total_value'] = total_value
                        combined_status['total_value'] += total_value
                    
                    # Update pair status
                    pair_status[pair] = trader_data
            
            # Calculate overall win rate
            if combined_status['total_trades'] > 0:
                combined_status['win_rate'] = round(combined_status['win_trades'] / combined_status['total_trades'] * 100, 1)
            else:
                combined_status['win_rate'] = 0
            
            # Update the dashboard
            update_bot_status(combined_status)
            
            # Sleep for the update interval
            time.sleep(update_interval)
        
        except Exception as e:
            logger.error(f"Error in bot status updater: {e}", exc_info=True)
            time.sleep(update_interval)

def create_trader(strategy, pair, args):
    """Create a trader instance based on the specified strategy"""
    if strategy == 'ICT':
        return create_ict_trader(pair, args)
    else:  # Original strategy
        return create_original_trader(pair, args)

def create_ict_trader(pair, args):
    """Create an ICT strategy trader instance"""
    try:
        # Initialize the ICT trader
        trader = ICTTraderClient(key.key, key.secret)
        
        # Parse the base asset and trading asset from the pair
        if 'BUSD' in pair:
            base_asset = 'BUSD'
            asset = pair.replace('BUSD', '')
        elif 'USDT' in pair:
            base_asset = 'USDT'
            asset = pair.replace('USDT', '')
        else:
            base_asset = 'USDT'  # Default
            asset = pair.split('USDT')[0] if 'USDT' in pair else pair
        
        # Set up basic parameters
        trader.trade_history = []
        trader.base_asset = base_asset
        trader.asset = asset
        trader.pair = pair
        trader.interval = args.ltf
        trader.df_length = 100
        
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
        trader.plot = False
        
        logger.info(f"Created ICT trader for {pair}")
        return trader
    except Exception as e:
        logger.error(f"Error creating ICT trader for {pair}: {e}", exc_info=True)
        return None

def create_original_trader(pair, args):
    """Create an Original strategy trader instance"""
    try:
        # Initialize the original trader
        trader = BinanceClient(key.key, key.secret)
        
        # Parse the base asset and trading asset from the pair
        if 'BUSD' in pair:
            base_asset = 'BUSD'
            asset = pair.replace('BUSD', '')
        elif 'USDT' in pair:
            base_asset = 'USDT'
            asset = pair.replace('USDT', '')
        else:
            base_asset = 'USDT'  # Default
            asset = pair.split('USDT')[0] if 'USDT' in pair else pair
        
        # Set up basic parameters
        trader.trade_history = []
        trader.base_asset = base_asset
        trader.asset = asset
        trader.pair = pair
        trader.interval = args.ltf
        trader.df_length = 100
        
        # Set risk parameters
        trader.risk_per_trade = args.risk
        trader.trail_stop = args.trail
        trader.trail_stop_enabled = True
        
        # Set mode
        trader.mode = "trade"
        trader.plot = False
        
        logger.info(f"Created Original trader for {pair}")
        return trader
    except Exception as e:
        logger.error(f"Error creating Original trader for {pair}: {e}", exc_info=True)
        return None

def initialize_trader(trader, pair):
    """Initialize the trader with necessary market data"""
    try:
        if trader is None:
            logger.error(f"Cannot initialize None trader for {pair}")
            return False
        
        # Initialize market data
        logger.info(f"Initializing market data for {pair}")
        trader.update()
        
        # Check if initialization was successful
        if hasattr(trader, 'df') and not trader.df.empty:
            logger.info(f"Successfully initialized trader for {pair}")
            return True
        else:
            logger.error(f"Failed to initialize market data for {pair}")
            return False
    
    except Exception as e:
        logger.error(f"Error initializing trader for {pair}: {e}", exc_info=True)
        return False

def run_trader(pair, args):
    """Run a trader instance for a specific pair"""
    global traders
    
    try:
        # Create the trader based on the selected strategy
        trader = create_trader(args.strategy, pair, args)
        
        if trader is None:
            logger.error(f"Failed to create trader for {pair}")
            return
        
        # Initialize the trader
        if not initialize_trader(trader, pair):
            logger.error(f"Failed to initialize trader for {pair}, skipping")
            return
        
        # Store the trader instance
        with trader_lock:
            traders[pair] = trader
        
        # Start trading
        logger.info(f"Starting trading process for {pair}")
        
        # Main trading loop
        while bot_status['is_running']:
            try:
                # Skip if bot has been temporarily stopped
                if not bot_status['is_running']:
                    time.sleep(1)
                    continue
                
                # Update market data
                trader.update()
                
                # Run trading logic based on strategy
                if args.strategy == 'ICT':
                    # Call manager method for ICT strategy
                    if hasattr(trader, 'manager'):
                        trader.manager()
                else:
                    # Original strategy trading logic
                    # Implement appropriate trading decision method here
                    pass
                
                # Sleep to avoid API rate limits
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in trading loop for {pair}: {e}", exc_info=True)
                time.sleep(5)  # Wait longer on error
        
        logger.info(f"Trading process stopped for {pair}")
    
    except Exception as e:
        logger.error(f"Fatal error in trader thread for {pair}: {e}", exc_info=True)

def run_dashboard(args):
    """Run the dashboard in a separate thread"""
    logger.info(f"Starting web dashboard on port {args.port}")
    app.run(host='0.0.0.0', port=args.port, debug=args.debug)

def main():
    """Main execution function"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Update initial bot status
    update_bot_status({
        'is_running': True,
        'strategy': args.strategy,
        'pairs': [pair.strip() for pair in args.pairs.split(',')],
        'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # Start status updater thread
    threading.Thread(target=bot_status_updater, daemon=True).start()
    
    # Start dashboard thread
    dashboard_thread = threading.Thread(target=run_dashboard, args=(args,), daemon=True)
    dashboard_thread.start()
    
    # Give the dashboard time to start
    time.sleep(2)
    
    # Start individual trader threads
    trader_threads = []
    for pair in [pair.strip() for pair in args.pairs.split(',')]:
        thread = threading.Thread(target=run_trader, args=(pair, args), daemon=True)
        thread.start()
        trader_threads.append(thread)
        
        # Small delay between starting traders to avoid rate limits
        time.sleep(0.5)
    
    logger.info(f"Started {len(trader_threads)} trader threads")
    print(f"Dashboard available at: http://localhost:{args.port}/")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        update_bot_status({'is_running': False})
        time.sleep(2)  # Give threads time to cleanly exit
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main() 