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
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add a file handler to ensure logs are captured
file_handler = logging.FileHandler('bot_control_debug.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
sys.path.append(project_root)
logger.info(f"Current directory: {current_dir}")
logger.info(f"Python path: {sys.path}")

# Initialize session state variables if they don't exist
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'stop_event' not in st.session_state:
    st.session_state.stop_event = threading.Event()
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

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
    try:
        logger.debug("Initializing BinanceClient with API keys")
        client = BinanceClient(api_key, api_secret)
        
        # Test the client connection
        logger.debug("Testing client connection with update() method")
        client.update()
        logger.info(f"BinanceClient initialized with base asset: {client.base_asset}, asset: {client.asset}, pair: {client.pair}")
    except Exception as e:
        logger.error(f"Error initializing BinanceClient: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        client = None
        
except Exception as e:
    logger.error(f"Error importing BinanceClient or initializing: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    client = None

# Global thread variable
bot_thread = None

def start_bot():
    logger.debug("start_bot called, current bot_running status: %s", st.session_state.bot_running)
    
    if st.session_state.bot_running:
        logger.warning("Bot is already running, not starting again")
        st.warning("Bot is already running!")
        return
    
    if client is None:
        error_msg = "Binance client is not available. Cannot start bot."
        logger.error(error_msg)
        st.session_state.error_message = error_msg
        st.error(error_msg)
        return
    
    try:
        logger.debug("Clearing stop event and creating bot thread")
        st.session_state.stop_event.clear()
        
        global bot_thread
        bot_thread = threading.Thread(target=bot_loop)
        bot_thread.daemon = True
        
        logger.debug("Starting bot thread")
        bot_thread.start()
        
        logger.debug("Setting bot_running to True")
        st.session_state.bot_running = True
        
        # Clear any previous error messages
        st.session_state.error_message = None
        
        logger.info("Bot started successfully")
        st.success("Bot started successfully!")
    except Exception as e:
        error_msg = f"Error starting bot: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        st.session_state.error_message = error_msg
        st.error(error_msg)

def stop_bot():
    logger.debug("stop_bot called, current bot_running status: %s", st.session_state.bot_running)
    
    if not st.session_state.bot_running:
        logger.warning("Bot is not running, nothing to stop")
        st.warning("Bot is not running!")
        return
    
    try:
        logger.debug("Setting stop event")
        st.session_state.stop_event.set()
        
        global bot_thread
        if bot_thread:
            logger.debug("Joining bot thread with timeout")
            bot_thread.join(timeout=2.0)
            
        logger.debug("Setting bot_running to False")
        st.session_state.bot_running = False
        
        logger.info("Bot stopped successfully")
        st.success("Bot stopped successfully!")
    except Exception as e:
        logger.error(f"Error stopping bot: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        st.error(f"Error stopping bot: {str(e)}")

def bot_loop():
    logger.debug("Bot loop started")
    try:
        # Initialize the trading bot
        logger.debug("Calling client.trade_init()")
        try:
            client.trade_init()
            logger.info("Trade initialized successfully")
        except Exception as e:
            error_msg = f"Error initializing trading: {str(e)}"
            logger.error(f"Error in client.trade_init(): {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            st.session_state.error_message = error_msg
            st.error(error_msg)
            # Set bot_running to False since initialization failed
            st.session_state.bot_running = False
            return
        
        # Main trading loop
        while not st.session_state.stop_event.is_set():
            try:
                logger.debug("Processing data and managing trades")
                
                # Check if client is still available
                if client is None:
                    error_msg = "Client is None in bot loop"
                    logger.error(error_msg)
                    st.session_state.error_message = error_msg
                    break
                
                # Process data and make trading decisions
                try:
                    logger.debug("Calling client.data_process()")
                    client.data_process()
                except Exception as e:
                    error_msg = f"Error processing data: {str(e)}"
                    logger.error(f"Error in client.data_process(): {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    st.session_state.error_message = error_msg
                    time.sleep(5.0)
                    continue
                
                try:
                    logger.debug("Calling client.manager()")
                    client.manager()
                except Exception as e:
                    error_msg = f"Error managing trades: {str(e)}"
                    logger.error(f"Error in client.manager(): {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    st.session_state.error_message = error_msg
                    time.sleep(5.0)
                    continue
                
                # Update status in session state
                st.session_state.last_update = time.time()
                
                # Sleep to avoid excessive CPU usage
                time.sleep(1.0)
            except Exception as e:
                error_msg = f"Error in bot loop iteration: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Traceback: {traceback.format_exc()}")
                st.session_state.error_message = error_msg
                time.sleep(5.0)  # Wait a bit longer after an error
            
    except Exception as e:
        error_msg = f"Error in bot loop: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        st.session_state.error_message = error_msg
    finally:
        logger.info("Bot loop ended")
        # Make sure to set bot_running to False when the loop ends
        st.session_state.bot_running = False

def main():
    st.title("Binance Trading Bot Control")
    
    # Check if client is available
    if client is None:
        st.error("Binance client is not available. Check logs for details.")
        
        # Display possible solutions
        st.warning("""
        Possible solutions:
        1. Make sure you have set valid Binance API keys in BinanceBot/key.py or as environment variables
        2. Check your internet connection
        3. Verify that the Binance API is accessible from your location
        4. Check the log file (bot_control_debug.log) for detailed error messages
        """)
        
        # Add a button to retry initialization
        if st.button("Retry Connection"):
            st.experimental_rerun()
            
        st.stop()
    
    # Add error display section
    if 'error_message' not in st.session_state:
        st.session_state.error_message = None
        
    if st.session_state.error_message:
        st.error(f"Bot Error: {st.session_state.error_message}")
        if st.button("Clear Error"):
            st.session_state.error_message = None
    
    # Display bot status
    st.header("Bot Status")
    status_col1, status_col2 = st.columns(2)
    
    with status_col1:
        status = "Running" if st.session_state.bot_running else "Stopped"
        st.metric("Status", status)
    
    with status_col2:
        if st.session_state.last_update:
            last_update = time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update))
        else:
            last_update = "Never"
        st.metric("Last Update", last_update)
    
    # Bot controls
    st.header("Bot Controls")
    logger.debug("Rendering bot controls section")
    col1, col2 = st.columns(2)
    
    with col1:
        logger.debug("Rendering Start Bot button (disabled=%s)", st.session_state.bot_running)
        start_button = st.button("Start Bot", type="primary", disabled=st.session_state.bot_running)
        if start_button:
            logger.debug("Start Bot button clicked")
            start_bot()
    
    with col2:
        logger.debug("Rendering Stop Bot button (disabled=%s)", not st.session_state.bot_running)
        stop_button = st.button("Stop Bot", type="secondary", disabled=not st.session_state.bot_running)
        if stop_button:
            logger.debug("Stop Bot button clicked")
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
            if st.session_state.bot_running:
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