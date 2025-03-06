#!/usr/bin/env python3
"""
Visualization Tool for ICT Strategy

This script allows you to visualize the ICT strategy setups and market structure analysis.
It connects to Binance, fetches market data, and visualizes it using the ICTVisualizer.
"""

import key
import time
import sys
from ict_strategy import ICTStrategyClient
from ict_visualization import ICTVisualizer
import matplotlib.pyplot as plt
import argparse

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Visualize ICT Trading Strategy')
    
    parser.add_argument('--pair', type=str, default='BTCBUSD', help='Trading pair (default: BTCBUSD)')
    parser.add_argument('--htf', type=str, default='1h', help='Higher timeframe for market structure (default: 1h)')
    parser.add_argument('--ltf', type=str, default='5m', help='Lower timeframe for entries (default: 5m)')
    parser.add_argument('--htf-count', type=int, default=50, help='Number of HTF candles to retrieve (default: 50)')
    parser.add_argument('--ltf-count', type=int, default=100, help='Number of LTF candles to retrieve (default: 100)')
    parser.add_argument('--save', action='store_true', help='Save charts to files')
    parser.add_argument('--report', action='store_true', help='Generate a trade report')
    
    return parser.parse_args()

def main():
    """Main function to run the visualizer"""
    args = parse_arguments()
    
    print("=" * 60)
    print("ICT Strategy Visualizer")
    print("=" * 60)
    
    try:
        # Initialize ICT client
        print(f"Initializing client for {args.pair}...")
        client = ICTStrategyClient(key.key, key.secret)
        
        # Configure the client
        client.pair = args.pair
        client.interval = args.ltf
        client.df_length = args.ltf_count
        client.htf_interval = args.htf
        client.htf_df_length = args.htf_count
        
        # Setting strategy parameters
        client.min_fvg_size = 0.0005  # 0.05% minimum FVG size
        client.max_fvg_age = 20       # Maximum age of FVG in candles
        
        # Update to fetch data
        print("Fetching market data...")
        client.update()
        
        # Process the data
        print("Processing data for market structure analysis...")
        client.data_process()
        
        # Initialize visualizer
        visualizer = ICTVisualizer(client)
        
        # Plot the market structure
        print("Generating market structure visualizations...")
        visualizer.plot_market_structure(filename="market_structure.png" if args.save else None)
        
        # If trading history exists, generate report
        if args.report and client.trade_history:
            print("Generating trade report...")
            visualizer.create_trade_report(filename=f"ict_trade_report_{args.pair}.html")
            print(f"Trade report saved to ict_trade_report_{args.pair}.html")
        
    except KeyboardInterrupt:
        print("\nVisualization stopped by user")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 