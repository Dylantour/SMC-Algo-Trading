#!/usr/bin/env python3
"""
run_bot.py - Main entry point to run the Binance trading bot

This script serves as a standalone Binance bot runner, handling initialization,
parameter configuration, and trading execution.
"""

import time
import sys
import os
import logging
import argparse
import key
from trade import ICTTraderClient


def setup_logging():
    """Configure logging for the bot"""
    log_path = "logs"
    
    # Ensure log directory exists
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    
    # Set up logging
    log_file = os.path.join(log_path, "binance_bot.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run the Binance Trading Bot')
    
    parser.add_argument('--pair', type=str, default='BTCBUSD',
                        help='Trading pair (default: BTCBUSD)')
    parser.add_argument('--htf', type=str, default='1h',
                        help='Higher timeframe for market structure analysis (default: 1h)')
    parser.add_argument('--ltf', type=str, default='5m',
                        help='Lower timeframe for entries (default: 5m)')
    parser.add_argument('--risk', type=float, default=0.01,
                        help='Risk per trade as a decimal (default: 0.01)')
    parser.add_argument('--min-fvg-size', type=float, default=0.0005,
                        help='Minimum fair value gap size (default: 0.0005)')
    parser.add_argument('--trail', type=float, default=0.8,
                        help='Trail stop ratio (default: 0.8)')
    
    return parser.parse_args()


def main():
    """Main execution function"""
    # Set up logging
    logger = setup_logging()
    logger.info("Starting Binance Trading Bot")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Check if API keys are set
    if key.key == "YOUR_API_KEY" or key.secret == "YOUR_API_SECRET":
        logger.warning("You are using default API keys from key.py.")
        logger.warning("Please update the key.py file with your Binance API credentials.")

    try:
        # Initialize the Binance client with ICT strategy
        logger.info(f"Initializing trading client for {args.pair} with HTF: {args.htf}, LTF: {args.ltf}")
        
        trader = ICTTraderClient(key.key, key.secret)
        
        # Set up basic parameters
        trader.trade_history = []
        trader.base_asset = "BUSD"
        trader.asset = "BTC"
        trader.pair = args.pair
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
        
        # Initialize and start trading
        logger.info("Starting trading process")
        trader.update()
        time.sleep(0.3)
        trader.start()
    
    except KeyboardInterrupt:
        logger.info("Bot manually stopped by user")
    except Exception as e:
        logger.error(f"Error in trading bot: {e}", exc_info=True)


if __name__ == "__main__":
    main() 