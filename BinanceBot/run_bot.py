#!/usr/bin/env python3
"""
Standalone Binance Bot Runner
This script provides a simplified way to run the Binance trading bot
without the PySide2 UI dependencies.
"""

import time
import sys
import os
from BinanceClient import BinanceClient
import key

def setup_logging():
    """Set up logging to file and console"""
    import logging
    
    # Create logger
    logger = logging.getLogger('binance_bot')
    logger.setLevel(logging.INFO)
    
    # Create file handler
    fh = logging.FileHandler('binance_bot.log')
    fh.setLevel(logging.INFO)
    
    # Create console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

def main():
    """Main function to run the Binance bot"""
    logger = setup_logging()
    
    # Print welcome message
    logger.info("=" * 50)
    logger.info("SMC-Algo-Trading Binance Bot")
    logger.info("=" * 50)
    
    # Check if API keys are set
    if key.key == 'xYuufQfbXZAEjiK6hhfCuuNeVmRBRGAk6fCpyLUXWpZuenqc5olRuRwn82NzvwCY':
        logger.warning("Using default API key. Set BINANCE_API_KEY environment variable for security.")
    if key.secret == 'eWqt0YeMRRELycEZFS9haV0n9FCbiJEOi0E9wtJHiUzPSwLhCa0lTX6yzvr9BXrH':
        logger.warning("Using default API secret. Set BINANCE_API_SECRET environment variable for security.")
    
    try:
        # Initialize the Binance client
        logger.info("Initializing Binance client...")
        client = BinanceClient(key.key, key.secret)
        
        # Set trading parameters
        client.base_asset = "BUSD"  # Base currency
        client.asset = "BTC"        # Trading asset
        client.pair = "BTCBUSD"     # Trading pair
        client.interval = "1m"      # Candle interval
        
        # Initialize trading
        logger.info(f"Starting trading for {client.pair} on {client.interval} timeframe")
        client.trade_init()
        
        # Start the trading loop
        logger.info("Starting trading loop...")
        client.trade_loop()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 