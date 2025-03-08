#!/usr/bin/env python3
"""
run_dashboard.py - Run the Trading Bot dashboard

This script starts the web dashboard for monitoring the Trading Bot.
It can be run separately from the trading bot to view the current status.
The dashboard supports both original and ICT strategies and multi-token trading.
"""

import os
import sys
import argparse
import logging
import threading
import datetime
from dashboard import app, update_bot_status, update_pair_status, bot_status, pair_status, add_trade

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/dashboard.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run Trading Bot Dashboard')
    
    parser.add_argument('--pairs', type=str, default='BTCBUSD',
                        help='Comma-separated list of trading pairs (e.g., BTCBUSD,ETHBUSD,BNBBUSD)')
    parser.add_argument('--strategy', type=str, default='Original', choices=['ICT', 'Original'],
                        help='Trading strategy to use (default: Original)')
    parser.add_argument('--port', type=int, default=8080,
                        help='Port for the web dashboard (default: 8080)')
    parser.add_argument('--debug', action='store_true',
                        help='Run Flask in debug mode')
    parser.add_argument('--btc-price', type=float, default=90000.0,
                        help='Current BTC price for demo (default: 90000.0)')
    
    return parser.parse_args()

def update_demo_data(args):
    """Update demo data based on command-line arguments"""
    global bot_status, pair_status
    
    # Get pairs from command line
    pairs = [pair.strip() for pair in args.pairs.split(',')]
    
    # Update bot status
    bot_status['is_running'] = True
    bot_status['strategy'] = args.strategy
    bot_status['pairs'] = pairs
    bot_status['last_update'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Set up demo pair status for each pair
    total_value = 0
    total_trades = 0
    active_positions = 0
    
    for pair in pairs:
        if pair not in pair_status:
            pair_status[pair] = {
                'trading_pair': pair,
                'base_balance': 500.0 if pair == 'BTCBUSD' else 200.0,
                'asset_balance': 0.01 if pair == 'BTCBUSD' else 0.0,
                'current_price': args.btc_price if 'BTC' in pair else 
                                3800.0 if 'ETH' in pair else 
                                600.0 if 'BNB' in pair else 
                                100.0,
                'market_bias': 'Bullish' if pair == 'BTCBUSD' else 'Bearish' if pair == 'ETHBUSD' else 'Neutral',
                'active_fvgs': 2 if pair == 'BTCBUSD' else 1 if pair == 'ETHBUSD' else 0,
                'position_open': True if pair == 'BTCBUSD' else False,
                'total_trades': 8 if pair == 'BTCBUSD' else 5 if pair == 'ETHBUSD' else 2,
                'win_rate': 62.5 if pair == 'BTCBUSD' else 60.0 if pair == 'ETHBUSD' else 50.0,
                'avg_profit': 1.8 if pair == 'BTCBUSD' else 1.5 if pair == 'ETHBUSD' else 0.8,
                'total_value': 800.0 if pair == 'BTCBUSD' else 200.0 if pair == 'ETHBUSD' else 0.0
            }
        
        total_value += pair_status[pair]['total_value']
        total_trades += pair_status[pair]['total_trades']
        if pair_status[pair]['position_open']:
            active_positions += 1
    
    # Update bot status with aggregated data
    bot_status['total_value'] = total_value
    bot_status['total_trades'] = total_trades
    bot_status['win_rate'] = 60.0  # Average win rate
    bot_status['active_positions'] = active_positions

def update_real_time_data():
    """Update real-time data from the Binance API (demo for now)"""
    # This would be replaced with actual API calls in production
    # For now, we just update the timestamp
    bot_status['last_update'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # In a real implementation, we would:
    # 1. Fetch current prices from Binance
    # 2. Update position status
    # 3. Calculate portfolio value
    # 4. Update market bias based on analysis

def main():
    """Main execution function"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Update demo data based on command-line arguments
    update_demo_data(args)
    
    # Create a background thread to periodically update data
    def update_thread():
        while True:
            try:
                update_real_time_data()
                threading.Event().wait(5)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Error updating data: {e}", exc_info=True)
    
    # Start update thread
    threading.Thread(target=update_thread, daemon=True).start()
    
    # Start the dashboard
    logger.info(f"Starting web dashboard on port {args.port} with strategy: {args.strategy}")
    logger.info(f"Monitoring pairs: {', '.join(bot_status['pairs'])}")
    print(f"Dashboard available at: http://localhost:{args.port}/")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=args.port, debug=args.debug)

if __name__ == "__main__":
    main() 