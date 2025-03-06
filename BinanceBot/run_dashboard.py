#!/usr/bin/env python3
"""
run_dashboard.py - Run the ICT Trading Bot dashboard

This script starts the web dashboard for monitoring the ICT Trading Bot.
It can be run separately from the trading bot to view the current status.
"""

import os
import sys
import argparse
import logging
from dashboard import app, initialize_demo_data

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
    parser = argparse.ArgumentParser(description='Run ICT Trading Bot Dashboard')
    
    parser.add_argument('--port', type=int, default=8080,
                        help='Port for the web dashboard (default: 8080)')
    parser.add_argument('--debug', action='store_true',
                        help='Run Flask in debug mode')
    
    return parser.parse_args()

def main():
    """Main execution function"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Initialize demo data for testing
    initialize_demo_data()
    
    # Start the dashboard
    logger.info(f"Starting web dashboard on port {args.port}")
    print(f"Dashboard available at: http://localhost:{args.port}/")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=args.port, debug=args.debug)

if __name__ == "__main__":
    main() 