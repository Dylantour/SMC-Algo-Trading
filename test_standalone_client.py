#!/usr/bin/env python3
"""
Test script for the standalone Binance client
"""

import os
import sys
import traceback

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
sys.path.append(project_root)

print(f"Current directory: {current_dir}")
print(f"Python path: {sys.path}")

try:
    # Import the standalone client
    print("Importing BinanceClient from standalone_client...")
    from BinanceBot.standalone_client import BinanceClient
    print("Successfully imported BinanceClient")
    
    # Import the key
    print("Importing API keys...")
    from BinanceBot.key import key as api_key, secret as api_secret
    print("Successfully imported API keys")
    
    # Check if we're using default keys
    if api_key == 'xYuufQfbXZAEjiK6hhfCuuNeVmRBRGAk6fCpyLUXWpZuenqc5olRuRwn82NzvwCY':
        print("WARNING: Using default API key. Please update with your actual Binance API key.")
    
    # Initialize the client
    print("Initializing BinanceClient...")
    client = BinanceClient(api_key, api_secret)
    print(f"BinanceClient initialized with base asset: {client.base_asset}, asset: {client.asset}, pair: {client.pair}")
    
    # Test update method
    print("Testing update method...")
    client.update()
    print("Update method completed")
    
    # Print balances
    print("Balances:")
    if hasattr(client, 'balances') and client.balances:
        for asset, amount in client.balances.items():
            print(f"  {asset}: {amount}")
    else:
        print("  No balance information available.")
    
    # Print tickers
    print("Tickers:")
    if hasattr(client, 'tickers') and client.tickers:
        for pair, data in client.tickers.items():
            print(f"  {pair}: ask={data['ask']}, bid={data['bid']}")
    else:
        print("  No ticker information available.")
    
    # Print dataframe
    print("Dataframe:")
    if hasattr(client, 'df') and client.df is not None and not client.df.empty:
        print(f"  Shape: {client.df.shape}")
        print(f"  Columns: {client.df.columns.tolist()}")
        print(f"  Latest close price: {client.df['close'].iloc[-1]}")
    else:
        print("  No dataframe available.")
    
    print("Test completed successfully!")
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    print(f"Traceback: {traceback.format_exc()}") 