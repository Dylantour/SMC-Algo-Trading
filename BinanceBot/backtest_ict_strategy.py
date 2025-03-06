#!/usr/bin/env python3
"""
Backtesting Tool for ICT Strategy

This script enables backtesting of the ICT strategy on historical data.
It downloads historical data from Binance, runs the strategy, and provides performance metrics.
"""

import key
import time
import sys
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
from ict_strategy import ICTStrategyClient
from ict_visualization import ICTVisualizer

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Backtest ICT Trading Strategy')
    
    parser.add_argument('--pair', type=str, default='BTCBUSD', help='Trading pair (default: BTCBUSD)')
    parser.add_argument('--htf', type=str, default='1h', help='Higher timeframe for market structure (default: 1h)')
    parser.add_argument('--ltf', type=str, default='5m', help='Lower timeframe for entries (default: 5m)')
    parser.add_argument('--days', type=int, default=30, help='Number of days to backtest (default: 30)')
    parser.add_argument('--risk', type=float, default=0.01, help='Risk per trade as decimal (default: 0.01 = 1%)')
    parser.add_argument('--initial-capital', type=float, default=10000, help='Initial capital for backtesting (default: 10000)')
    parser.add_argument('--min-fvg-size', type=float, default=0.0005, help='Minimum FVG size as percentage (default: 0.0005 = 0.05%)')
    parser.add_argument('--rr-ratio', type=float, default=2.0, help='Risk-to-reward ratio (default: 2.0)')
    parser.add_argument('--report', action='store_true', help='Generate HTML report with charts')
    
    return parser.parse_args()

def main():
    """Main function to run the backtesting"""
    args = parse_arguments()
    
    print("=" * 60)
    print("ICT Strategy Backtester")
    print("=" * 60)
    
    # Calculate how many candles we need based on timeframe and days
    ltf_minutes = int(''.join(filter(str.isdigit, args.ltf))) if args.ltf[0].isdigit() else 1
    if 'h' in args.ltf:
        ltf_minutes *= 60
    elif 'd' in args.ltf:
        ltf_minutes *= 1440
    
    # Calculate candle counts
    ltf_candles_per_day = 1440 // ltf_minutes
    ltf_count = ltf_candles_per_day * args.days + 100  # Add buffer
    
    htf_minutes = int(''.join(filter(str.isdigit, args.htf))) if args.htf[0].isdigit() else 1
    if 'h' in args.htf:
        htf_minutes *= 60
    elif 'd' in args.htf:
        htf_minutes *= 1440
    
    htf_candles_per_day = 1440 // htf_minutes
    htf_count = htf_candles_per_day * args.days + 20  # Add buffer
    
    try:
        # Initialize ICT client for backtesting
        print(f"Initializing backtesting for {args.pair} over {args.days} days...")
        client = ICTStrategyClient(key.key, key.secret)
        
        # Configure the client
        client.pair = args.pair
        client.interval = args.ltf
        client.htf_interval = args.htf
        
        # Set backtesting parameters
        client.mode = "backtest"
        client.backtest_initial_balance = args.initial_capital
        client.backtest_length = ltf_count
        client.df_length = client.backtest_length + 50  # Add buffer
        client.htf_df_length = htf_count
        
        # Set strategy parameters
        client.risk_per_trade = args.risk
        client.risk_reward_ratio = args.rr_ratio
        client.min_fvg_size = args.min_fvg_size
        client.max_fvg_age = 20
        client.trail_stop_enabled = True
        client.trail_stop = 0.8
        
        # Plot charts during backtest
        client.plot = False
        
        start_time = time.time()
        
        print(f"Downloading historical data for {args.pair}...")
        print(f"- Lower timeframe ({args.ltf}): {ltf_count} candles")
        print(f"- Higher timeframe ({args.htf}): {htf_count} candles")
        
        # Initialize and run backtest
        client.update()
        
        print("Running backtest...")
        client.backtest_init()
        client.backtest_loop()
        
        elapsed_time = time.time() - start_time
        print(f"Backtest completed in {elapsed_time:.2f} seconds")
        
        # Generate report
        if args.report:
            print("Generating backtest report...")
            visualizer = ICTVisualizer(client)
            
            # Generate equity curve
            equity_df = pd.DataFrame(client.equity_history, columns=['usd'])
            plt.figure(figsize=(12, 6))
            plt.plot(equity_df.index, equity_df['usd'])
            plt.title(f'Equity Curve - {args.pair} - {args.ltf} (Initial: ${args.initial_capital})')
            plt.xlabel('Candles')
            plt.ylabel('Account Balance ($)')
            plt.grid(True)
            plt.savefig('equity_curve.png')
            print("Equity curve saved to equity_curve.png")
            
            # Generate trade report
            visualizer.create_trade_report(filename=f"ict_backtest_{args.pair}_{args.ltf}_{args.days}days.html")
            print(f"Backtest report saved to ict_backtest_{args.pair}_{args.ltf}_{args.days}days.html")
        
        # Print summary statistics
        print("\n" + "=" * 60)
        print("BACKTEST SUMMARY")
        print("=" * 60)
        
        # Get last equity value
        final_equity = client.out_data.get("equity_history", pd.DataFrame({'usd': [args.initial_capital]}))['usd'].iloc[-1]
        total_profit_pct = ((final_equity / args.initial_capital) - 1) * 100
        
        print(f"Initial Capital: ${args.initial_capital:.2f}")
        print(f"Final Capital: ${final_equity:.2f}")
        print(f"Total Profit: {total_profit_pct:.2f}%")
        print(f"Total Trades: {client.out_data.get('trade_nb', 0)}")
        print(f"Win Rate: {client.out_data.get('win_rate', 0) * 100:.2f}%")
        print(f"Average Profit per Trade: {client.out_data.get('mean_profit', 0) * 100:.2f}%")
        print(f"Average Loss per Trade: {client.out_data.get('mean_loss', 0) * 100:.2f}%")
        print(f"Max Drawdown: {client.out_data.get('max_drawdown', 0) * 100:.2f}%")
        
        print("=" * 60)
        print("Strategy Parameters:")
        print(f"- Trading Pair: {args.pair}")
        print(f"- Higher Timeframe: {args.htf}")
        print(f"- Lower Timeframe: {args.ltf}")
        print(f"- Risk per Trade: {args.risk * 100:.2f}%")
        print(f"- Risk-Reward Ratio: {args.rr_ratio}")
        print(f"- Min FVG Size: {args.min_fvg_size * 100:.3f}%")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\nBacktesting stopped by user")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 