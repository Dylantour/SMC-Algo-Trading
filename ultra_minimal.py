#!/usr/bin/env python3
"""
Ultra Minimal Dashboard
The simplest possible version with only basic Streamlit components.
"""

import streamlit as st
import time
import threading
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize session state
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'counter' not in st.session_state:
    st.session_state.counter = 0
if 'logs' not in st.session_state:
    st.session_state.logs = []

# Bot thread
bot_thread = None

def bot_loop():
    """Simple bot loop that just increments a counter"""
    try:
        while st.session_state.bot_running:
            # Increment counter
            st.session_state.counter += 1
            
            # Add a log entry
            log_entry = f"Bot iteration {st.session_state.counter} at {time.strftime('%H:%M:%S')}"
            st.session_state.logs.append(log_entry)
            
            # Keep only the last 10 logs
            if len(st.session_state.logs) > 10:
                st.session_state.logs = st.session_state.logs[-10:]
            
            # Sleep for a second
            time.sleep(1)
    except Exception as e:
        st.session_state.logs.append(f"Error: {str(e)}")
    finally:
        st.session_state.bot_running = False

def start_bot():
    """Start the bot"""
    if st.session_state.bot_running:
        return
    
    st.session_state.bot_running = True
    
    global bot_thread
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()

def stop_bot():
    """Stop the bot"""
    st.session_state.bot_running = False
    
    global bot_thread
    if bot_thread:
        bot_thread.join(timeout=2.0)

def main():
    st.title("Ultra Minimal Dashboard")
    
    # Bot controls
    st.header("Bot Controls")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Start Bot", disabled=st.session_state.bot_running):
            start_bot()
    
    with col2:
        if st.button("Stop Bot", disabled=not st.session_state.bot_running):
            stop_bot()
    
    # Bot status
    st.header("Bot Status")
    status = "Running" if st.session_state.bot_running else "Stopped"
    st.write(f"Status: {status}")
    st.write(f"Counter: {st.session_state.counter}")
    
    # Logs
    st.header("Logs")
    for log in st.session_state.logs:
        st.text(log)
    
    # Manual refresh
    if st.button("Refresh"):
        st.experimental_rerun()
    
    # Auto-refresh using HTML
    st.markdown(
        """
        <meta http-equiv="refresh" content="5">
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main() 