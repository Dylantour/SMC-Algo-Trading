#!/usr/bin/env python3
"""
Minimal API Dashboard
A simplified version with minimal dependencies to avoid CSP issues.
"""

import streamlit as st
import logging
import os
import sys
import time
import threading
import traceback
import pandas as pd
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add a file handler to ensure logs are captured
file_handler = logging.FileHandler('minimal_dashboard.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
sys.path.append(project_root)
logger.info(f"Current directory: {current_dir}")
logger.info(f"Python path: {sys.path}")

# Initialize session state variables
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'stop_bot' not in st.session_state:
    st.session_state.stop_bot = False
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'api_logs' not in st.session_state:
    st.session_state.api_logs = []

# Try to import the BinanceClient
try:
    # Import the standalone client
    from BinanceBot.standalone_client import BinanceClient
    logger.info("Successfully imported BinanceClient from standalone_client")
    
    # Import the key
    from BinanceBot.key import key as api_key, secret as api_secret
    logger.info("Successfully imported API keys")
    
    # Check if we're using default keys
    if api_key == 'xYuufQfbXZAEjiK6hhfCuuNeVmRBRGAk6fCpyLUXWpZuenqc5olRuRwn82NzvwCY':
        logger.warning("Using default API key. Please update with your actual Binance API key.")
    
    # Initialize the client with a timeout
    client_initialized = False
    client_error = None
    client = None
    
    try:
        logger.debug("Initializing BinanceClient with API keys")
        client = BinanceClient(api_key, api_secret)
        
        # Test the client connection with a timeout
        def init_client():
            global client_initialized, client_error
            try:
                logger.debug("Testing client connection with update() method")
                client.update()
                client_initialized = True
                logger.info(f"BinanceClient initialized with base asset: {client.base_asset}, asset: {client.asset}, pair: {client.pair}")
            except Exception as e:
                client_error = str(e)
                logger.error(f"Error in client.update(): {str(e)}")
        
        # Start client initialization in a separate thread
        init_thread = threading.Thread(target=init_client)
        init_thread.daemon = True
        init_thread.start()
        
        # Wait for initialization with timeout
        timeout = 5  # 5 seconds timeout
        start_time = time.time()
        while not client_initialized and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        if not client_initialized:
            if client_error:
                logger.error(f"Client initialization timed out with error: {client_error}")
            else:
                logger.error("Client initialization timed out")
            client = None
            
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

def log_api_call(endpoint, status, response_time):
    """Log an API call to the session state"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.api_logs.append({
        "timestamp": timestamp,
        "endpoint": endpoint,
        "status": status,
        "response_time": f"{response_time:.2f}s"
    })
    # Keep only the last 100 logs
    if len(st.session_state.api_logs) > 100:
        st.session_state.api_logs = st.session_state.api_logs[-100:]

def start_bot():
    logger.debug("start_bot called")
    
    if st.session_state.bot_running:
        logger.warning("Bot is already running, not starting again")
        st.warning("Bot is already running!")
        return
    
    if client is None:
        error_msg = "Binance client is not available. Cannot start bot."
        logger.error(error_msg)
        st.error(error_msg)
        return
    
    try:
        logger.debug("Creating bot thread")
        
        global bot_thread
        bot_thread = threading.Thread(target=bot_loop)
        bot_thread.daemon = True
        
        logger.debug("Starting bot thread")
        bot_thread.start()
        
        logger.debug("Setting bot_running to True")
        st.session_state.bot_running = True
        
        logger.info("Bot started successfully")
        st.success("Bot started successfully!")
    except Exception as e:
        error_msg = f"Error starting bot: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        st.error(error_msg)

def stop_bot():
    logger.debug("stop_bot called")
    
    if not st.session_state.bot_running:
        logger.warning("Bot is not running, nothing to stop")
        st.warning("Bot is not running!")
        return
    
    try:
        logger.debug("Setting stop_bot flag")
        st.session_state.stop_bot = True
        
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
            # Simulate an API call
            log_api_call("/api/v3/trade_init", "success", 0.5)
        except Exception as e:
            error_msg = f"Error initializing trading: {str(e)}"
            logger.error(f"Error in client.trade_init(): {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            st.error(error_msg)
            # Set bot_running to False since initialization failed
            st.session_state.bot_running = False
            return
        
        # Main trading loop
        st.session_state.stop_bot = False
        iteration = 0
        while not st.session_state.stop_bot:
            try:
                logger.debug("Processing data and managing trades")
                
                # Check if client is still available
                if client is None:
                    error_msg = "Client is None in bot loop"
                    logger.error(error_msg)
                    break
                
                # Process data and make trading decisions
                try:
                    logger.debug("Calling client.data_process()")
                    client.data_process()
                    # Simulate API calls
                    log_api_call("/api/v3/klines", "success", 0.2)
                    log_api_call("/api/v3/ticker/price", "success", 0.1)
                except Exception as e:
                    error_msg = f"Error processing data: {str(e)}"
                    logger.error(f"Error in client.data_process(): {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    time.sleep(5.0)
                    continue
                
                try:
                    logger.debug("Calling client.manager()")
                    client.manager()
                    # Simulate API calls for trading
                    if iteration % 5 == 0:  # Simulate occasional trades
                        log_api_call("/api/v3/order", "success", 0.3)
                except Exception as e:
                    error_msg = f"Error managing trades: {str(e)}"
                    logger.error(f"Error in client.manager(): {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    time.sleep(5.0)
                    continue
                
                # Update status in session state
                st.session_state.last_update = time.time()
                
                # Sleep to avoid excessive CPU usage
                time.sleep(1.0)
                iteration += 1
            except Exception as e:
                error_msg = f"Error in bot loop iteration: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Traceback: {traceback.format_exc()}")
                time.sleep(5.0)  # Wait a bit longer after an error
            
    except Exception as e:
        error_msg = f"Error in bot loop: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.info("Bot loop ended")
        # Make sure to set bot_running to False when the loop ends
        st.session_state.bot_running = False

def main():
    st.set_page_config(
        page_title="Minimal Binance API Dashboard",
        page_icon="📊",
        layout="wide",
    )
    
    st.title("Minimal Binance API Dashboard")
    
    # Check if client is available
    if client is None:
        st.error("Binance client is not available. Check logs for details.")
        
        # Display possible solutions
        st.warning("""
        Possible solutions:
        1. Make sure you have set valid Binance API keys in BinanceBot/key.py or as environment variables
        2. Check your internet connection
        3. Verify that the Binance API is accessible from your location
        4. Check the log file (minimal_dashboard.log) for detailed error messages
        """)
        
        # Add a button to retry initialization
        if st.button("Retry Connection"):
            st.experimental_rerun()
            
        st.stop()
    
    # Bot controls
    st.header("Bot Controls")
    logger.debug("Rendering bot controls section")
    col1, col2 = st.columns(2)
    
    with col1:
        start_disabled = st.session_state.bot_running
        logger.debug(f"Rendering Start Bot button (disabled={start_disabled})")
        start_button = st.button("Start Bot", type="primary", disabled=start_disabled)
        if start_button:
            logger.debug("Start Bot button clicked")
            start_bot()
    
    with col2:
        stop_disabled = not st.session_state.bot_running
        logger.debug(f"Rendering Stop Bot button (disabled={stop_disabled})")
        stop_button = st.button("Stop Bot", type="secondary", disabled=stop_disabled)
        if stop_button:
            logger.debug("Stop Bot button clicked")
            stop_bot()
    
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
    
    # API Activity visualization (simplified)
    st.header("API Activity")
    
    # Display API logs as a simple table
    if st.session_state.api_logs:
        df = pd.DataFrame(st.session_state.api_logs)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No API activity logged yet. Start the bot to see API calls.")
    
    # Add a refresh button
    if st.button("Refresh Dashboard"):
        st.experimental_rerun()
    
    # Add a footer
    st.markdown("---")
    st.caption("Minimal Binance API Dashboard | Refresh manually with the button above")

if __name__ == "__main__":
    main() 