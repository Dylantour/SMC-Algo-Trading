#!/usr/bin/env python3
"""
Test script to check if BinanceClient can be imported
"""

import os
import sys
import traceback

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

try:
    print("Attempting to import BinanceClient...")
    from BinanceBot.BinanceClient import BinanceClient
    print("BinanceClient imported successfully")
    
    print("Attempting to import Binance key...")
    from BinanceBot import key as binance_key
    print("Binance key imported successfully")
    
    print("Binance is available")
    
    # Try to create a client instance
    print("Creating BinanceClient instance...")
    client = BinanceClient(binance_key.key, binance_key.secret)
    print("BinanceClient instance created successfully")
    
    # Check if required attributes exist
    print("Checking client attributes...")
    print(f"Base asset: {client.base_asset}")
    print(f"Asset: {client.asset}")
    print(f"Pair: {client.pair}")
    print(f"Interval: {client.interval}")
    
except ImportError as e:
    print(f"Import error: {str(e)}")
    print(traceback.format_exc())
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    print(traceback.format_exc()) 