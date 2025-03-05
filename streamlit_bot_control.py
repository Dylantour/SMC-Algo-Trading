#!/usr/bin/env python3
"""
Streamlit Bot Control UI
This script provides a web-based UI for controlling the trading bots.
"""

import streamlit as st
import time
import threading
import os
import sys
from pathlib import Path
import logging
import traceback

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
sys.path.append(project_root)
logger.info(f"Current directory: {current_dir}")
logger.info(f"Python path: {sys.path}")

try:
    # Import the standalone client instead of the regular BinanceClient
    from BinanceBot.standalone_client import BinanceClient
    logger.info("Successfully imported BinanceClient from standalone_client")
    
    # Import the key
    from BinanceBot.key import key as api_key, secret as api_secret
    logger.info("Successfully imported API keys")
    
    # Check if we're using default keys
    if api_key == 'xYuufQfbXZAEjiK6hhfCuuNeVmRBRGAk6fCpyLUXWpZuenqc5olRuRwn82NzvwCY':
        logger.warning("Using default API key. Please update with your actual Binance API key.")
    
    # Initialize the client
    client = BinanceClient(api_key, api_secret)
    logger.info(f"BinanceClient initialized with base asset: {client.base_asset}, asset: {client.asset}, pair: {client.pair}")
    
except Exception as e:
    logger.error(f"Error importing BinanceClient or initializing: {str(e)}")
    logger.error(f"Traceback: {sys.exc_info()}")
    client = None

# Global variables
bot_running = False
bot_thread = None
stop_event = threading.Event()

def start_bot():
    global bot_running, bot_thread, stop_event
    
    if bot_running:
        st.warning("Bot is already running!")
        return
    
    if client is None:
        st.error("Binance client is not available. Check logs for details.")
        return
    
    stop_event.clear()
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()
    bot_running = True
    st.success("Bot started successfully!")

def stop_bot():
    global bot_running, bot_thread, stop_event
    
    if not bot_running:
        st.warning("Bot is not running!")
        return
    
    stop_event.set()
    if bot_thread:
        bot_thread.join(timeout=2.0)
    bot_running = False
    st.success("Bot stopped successfully!")

def bot_loop():
    logger.info("Bot loop started")
    try:
        # Initialize the trading bot
        client.trade_init()
        logger.info("Trade initialized")
        
        # Main trading loop
        while not stop_event.is_set():
            # Process data and make trading decisions
            client.data_process()
            client.manager()
            
            # Update status in session state
            if 'last_update' not in st.session_state:
                st.session_state.last_update = time.time()
            st.session_state.last_update = time.time()
            
            # Sleep to avoid excessive CPU usage
            time.sleep(1.0)
            
    except Exception as e:
        logger.error(f"Error in bot loop: {str(e)}")
        logger.error(f"Traceback: {sys.exc_info()}")
    finally:
        logger.info("Bot loop ended")

def main():
    st.title("Binance Trading Bot Control")
    
    # Check if client is available
    if client is None:
        st.error("Binance client is not available. Check logs for details.")
        st.stop()
    
    # Display bot status
    st.header("Bot Status")
    status_col1, status_col2 = st.columns(2)
    
    with status_col1:
        status = "Running" if bot_running else "Stopped"
        st.metric("Status", status)
    
    with status_col2:
        if 'last_update' in st.session_state:
            last_update = time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update))
        else:
            last_update = "Never"
        st.metric("Last Update", last_update)
    
    # Bot controls
    st.header("Bot Controls")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Start Bot", type="primary", disabled=bot_running):
            start_bot()
    
    with col2:
        if st.button("Stop Bot", type="secondary", disabled=not bot_running):
            stop_bot()
    
    # Trading pair settings
    st.header("Trading Settings")
    
    # Display current settings
    st.subheader("Current Settings")
    settings_col1, settings_col2 = st.columns(2)
    
    with settings_col1:
        st.metric("Base Asset", client.base_asset)
        st.metric("Trading Pair", client.pair)
    
    with settings_col2:
        st.metric("Asset", client.asset)
        st.metric("Interval", client.interval)
    
    # Update settings form
    with st.form("settings_form"):
        st.subheader("Update Settings")
        
        new_base_asset = st.text_input("Base Asset", value=client.base_asset)
        new_asset = st.text_input("Asset", value=client.asset)
        new_pair = st.text_input("Trading Pair", value=client.pair)
        new_interval = st.selectbox("Interval", 
                                   options=["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"],
                                   index=["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"].index(client.interval))
        
        submitted = st.form_submit_button("Update Settings")
        
        if submitted:
            if bot_running:
                st.warning("Cannot update settings while bot is running. Please stop the bot first.")
            else:
                client.base_asset = new_base_asset
                client.asset = new_asset
                client.pair = new_pair
                client.interval = new_interval
                st.success("Settings updated successfully!")
    
    # Account information
    st.header("Account Information")
    
    if st.button("Refresh Account Info"):
        try:
            client.update()
            st.success("Account information refreshed!")
        except Exception as e:
            st.error(f"Error refreshing account information: {str(e)}")
    
    # Display balances
    st.subheader("Balances")
    
    if hasattr(client, 'balances') and client.balances:
        balance_data = []
        for asset, amount in client.balances.items():
            balance_data.append({"Asset": asset, "Amount": amount})
        
        if balance_data:
            st.table(balance_data)
        else:
            st.info("No balance information available.")
    else:
        st.info("No balance information available. Click 'Refresh Account Info' to update.")
    
    # Display market data if available
    if hasattr(client, 'df') and client.df is not None and not client.df.empty:
        st.header("Market Data")
        st.dataframe(client.df.tail())
    
    # Add a footer
    st.markdown("---")
    st.caption("Binance Trading Bot Control Panel | Refresh every 10 seconds")

if __name__ == "__main__":
    main() 