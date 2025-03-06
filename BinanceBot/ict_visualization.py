import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import mplfinance as mpf

class ICTVisualizer:
    """
    Visualization toolkit for ICT trading setups
    """
    def __init__(self, ict_client=None):
        self.client = ict_client
        self.colors = {
            'bullish_fvg': 'lightgreen',
            'bearish_fvg': 'lightcoral',
            'liquidity_sweep_bullish': 'green',
            'liquidity_sweep_bearish': 'red',
            'htf_bullish': 'forestgreen',
            'htf_bearish': 'darkred',
            'entry': 'blue',
            'exit': 'purple',
            'stop_loss': 'red'
        }
    
    def attach_client(self, ict_client):
        """Attach an ICT strategy client to the visualizer"""
        self.client = ict_client
    
    def plot_candles_with_structure(self, df, title="ICT Market Structure", filename=None):
        """Plot the candles with market structure elements"""
        if df is None or len(df) == 0:
            print("No data to visualize")
            return
        
        # Prepare the plot
        fig, ax = plt.subplots(figsize=(15, 8))
        
        # Format the dates for the x-axis
        dates = pd.to_datetime(df.index)
        
        # Plot candlesticks manually 
        for i, (idx, row) in enumerate(df.iterrows()):
            # Determine candle color
            if row['close'] >= row['open']:
                color = 'green'
                body_bottom = row['open']
                body_top = row['close']
            else:
                color = 'red'
                body_bottom = row['close']
                body_top = row['open']
            
            # Plot candle body
            ax.add_patch(plt.Rectangle((i-0.4, body_bottom), 0.8, body_top-body_bottom, fill=True, color=color))
            
            # Plot candle wick
            ax.plot([i, i], [row['low'], row['high']], color='black', linewidth=1)
        
        # Plot swing highs and lows if available
        if 'swing_high' in df.columns and 'swing_low' in df.columns:
            # Swing highs
            swing_highs = df[df['swing_high'] == True]
            for i, (idx, row) in enumerate(swing_highs.iterrows()):
                index_pos = dates.get_loc(idx)
                ax.scatter(index_pos, row['high'], color='blue', s=100, marker='^')
                ax.text(index_pos, row['high']*1.01, "H", fontsize=10)
            
            # Swing lows
            swing_lows = df[df['swing_low'] == True]
            for i, (idx, row) in enumerate(swing_lows.iterrows()):
                index_pos = dates.get_loc(idx)
                ax.scatter(index_pos, row['low'], color='purple', s=100, marker='v')
                ax.text(index_pos, row['low']*0.99, "L", fontsize=10)
        
        # Add any fair value gaps if we have an attached client
        if self.client and hasattr(self.client, 'active_fvgs'):
            for fvg in self.client.active_fvgs:
                # Find the candle index where this FVG was created
                try:
                    idx = dates.get_loc(fvg['created_at'])
                    color = self.colors['bullish_fvg'] if fvg['type'] == 'bullish' else self.colors['bearish_fvg']
                    
                    # Draw a rectangle for the FVG
                    ax.add_patch(plt.Rectangle((idx, fvg['bottom']), len(df)-idx, fvg['top']-fvg['bottom'], 
                                              fill=True, alpha=0.3, color=color))
                    
                    # Label the FVG
                    ax.text(idx+1, fvg['mid'], f"{fvg['type']} FVG", fontsize=8)
                except:
                    pass  # FVG might be from a different timeframe
        
        # Add liquidity sweep if available from the client
        if self.client and hasattr(self.client, 'last_liquidity_sweep') and self.client.last_liquidity_sweep:
            sweep = self.client.last_liquidity_sweep
            try:
                idx = dates.get_loc(sweep['time'])
                color = self.colors['liquidity_sweep_bullish'] if sweep['type'] == 'bullish' else self.colors['liquidity_sweep_bearish']
                
                # Mark the sweep with an arrow
                if sweep['type'] == 'bullish':
                    ax.arrow(idx, sweep['price']*0.997, 0, sweep['price']*0.006, head_width=1, head_length=sweep['price']*0.002, 
                             fc=color, ec=color, alpha=0.7)
                    ax.text(idx, sweep['price']*0.994, "SWEEP", fontsize=8)
                else:
                    ax.arrow(idx, sweep['price']*1.003, 0, -sweep['price']*0.006, head_width=1, head_length=sweep['price']*0.002, 
                            fc=color, ec=color, alpha=0.7)
                    ax.text(idx, sweep['price']*1.006, "SWEEP", fontsize=8)
            except:
                pass
        
        # Set labels and title
        ax.set_title(title)
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        
        # Format the x-axis to show dates
        ax.set_xticks(range(0, len(dates), len(dates)//10))
        ax.set_xticklabels([d.strftime('%Y-%m-%d %H:%M') for d in dates[::len(dates)//10]], rotation=45)
        
        plt.tight_layout()
        
        if filename:
            plt.savefig(filename)
            print(f"Chart saved to {filename}")
        
        plt.show()
    
    def plot_market_structure(self, filename=None):
        """Plot the current market structure from the attached client"""
        if not self.client:
            print("No client attached to visualizer")
            return
        
        # Plot higher timeframe structure
        htf_df = self.client.htf_df
        if htf_df is not None:
            self.plot_candles_with_structure(
                htf_df, 
                title=f"Higher Timeframe Market Structure - {self.client.htf_interval} - {self.client.htf_bias}", 
                filename=f"htf_structure_{datetime.now().strftime('%Y%m%d_%H%M')}.png" if filename else None
            )
        
        # Plot lower timeframe with FVGs
        ltf_df = self.client.ltf_df
        if ltf_df is not None:
            self.plot_candles_with_structure(
                ltf_df, 
                title=f"Lower Timeframe Trading Setups - {self.client.interval}", 
                filename=f"ltf_setups_{datetime.now().strftime('%Y%m%d_%H%M')}.png" if filename else None
            )
    
    def plot_mplfinance(self, df, title="ICT Trading Setup", filename=None):
        """
        Plot candles using the mplfinance library for better visualization
        Requires: pip install mplfinance
        """
        # Prepare the data
        df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df.index):
            df.index = pd.to_datetime(df.index)
        
        # Create custom styles
        mc = mpf.make_marketcolors(
            up='green', down='red',
            wick={'up':'green', 'down':'red'},
            edge={'up':'green', 'down':'red'},
            volume={'up':'green', 'down':'red'}
        )
        
        s = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='--',
            y_on_right=False
        )
        
        # Create a figure
        fig, axes = mpf.plot(
            df,
            type='candle',
            style=s,
            title=title,
            figsize=(15, 8),
            volume=False,
            returnfig=True
        )
        
        # If we have a client attached, we can add market structure elements
        if self.client:
            ax = axes[0]
            # Add FVGs, liquidity sweeps, etc. here
            # This would require translating the datetime indices to matplotlib date format
            
        if filename:
            plt.savefig(filename)
            print(f"Chart saved to {filename}")
        
        plt.show()

    def create_trade_report(self, start_date=None, end_date=None, filename="ict_trade_report.html"):
        """Generate an HTML report of trading activity and performance"""
        if not self.client:
            print("No client attached to visualizer")
            return
        
        # Get trade history
        trades = pd.DataFrame(self.client.trade_history)
        
        # Filter by date if specified
        if start_date and end_date:
            trades = trades[(trades['start_epoch'] >= start_date) & (trades['end_epoch'] <= end_date)]
        
        # Calculate statistics
        if len(trades) == 0:
            print("No trades in the specified period")
            return
        
        # Basic stats
        total_trades = len(trades)
        winning_trades = len(trades[trades['profit'] > 0])
        losing_trades = len(trades[trades['profit'] < 0])
        win_rate = (winning_trades / total_trades) * 100
        avg_profit = trades['profit'].mean() * 100  # Convert to percentage
        
        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ICT Trading Strategy Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #2c3e50; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                .stats {{ display: flex; flex-wrap: wrap; margin-bottom: 20px; }}
                .stat-box {{ flex: 1; min-width: 200px; padding: 15px; margin: 10px; background-color: #f8f9fa; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                tr:hover {{ background-color: #f5f5f5; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>ICT Trading Strategy Report</h1>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <h2>Performance Summary</h2>
                <div class="stats">
                    <div class="stat-box">
                        <h3>Total Trades</h3>
                        <p>{total_trades}</p>
                    </div>
                    <div class="stat-box">
                        <h3>Win Rate</h3>
                        <p class="{'positive' if win_rate > 50 else 'negative'}">{win_rate:.2f}%</p>
                    </div>
                    <div class="stat-box">
                        <h3>Average Profit</h3>
                        <p class="{'positive' if avg_profit > 0 else 'negative'}">{avg_profit:.2f}%</p>
                    </div>
                    <div class="stat-box">
                        <h3>Winning Trades</h3>
                        <p class="positive">{winning_trades}</p>
                    </div>
                    <div class="stat-box">
                        <h3>Losing Trades</h3>
                        <p class="negative">{losing_trades}</p>
                    </div>
                </div>
                
                <h2>Recent Trades</h2>
                <table>
                    <tr>
                        <th>Start Time</th>
                        <th>End Time</th>
                        <th>Buy Price</th>
                        <th>Sell Price</th>
                        <th>Profit %</th>
                        <th>Trail Stop</th>
                    </tr>
        """
        
        # Add rows for each trade (most recent first)
        for _, trade in trades.sort_values('end_epoch', ascending=False).iterrows():
            start_time = datetime.fromtimestamp(trade['start_epoch']/1000 if trade['start_epoch'] > 1e12 else trade['start_epoch']).strftime('%Y-%m-%d %H:%M')
            end_time = datetime.fromtimestamp(trade['end_epoch']/1000 if trade['end_epoch'] > 1e12 else trade['end_epoch']).strftime('%Y-%m-%d %H:%M')
            profit_class = "positive" if trade['profit'] > 0 else "negative"
            
            html += f"""
                <tr>
                    <td>{start_time}</td>
                    <td>{end_time}</td>
                    <td>{trade['buy_price']:.2f}</td>
                    <td>{trade['sell_price']:.2f}</td>
                    <td class="{profit_class}">{trade['profit']*100:.2f}%</td>
                    <td>{"Yes" if trade.get('trail_stop', False) else "No"}</td>
                </tr>
            """
        
        # Close HTML
        html += """
                </table>
            </div>
        </body>
        </html>
        """
        
        # Write to file
        with open(filename, 'w') as f:
            f.write(html)
        
        print(f"Trade report saved to {filename}")


if __name__ == "__main__":
    # Example usage
    visualizer = ICTVisualizer()
    print("To use the visualizer, attach an ICT strategy client:")
    print("from ict_strategy import ICTStrategyClient")
    print("from ict_visualization import ICTVisualizer")
    print("client = ICTStrategyClient(key, secret)")
    print("client.update()")
    print("visualizer = ICTVisualizer(client)")
    print("visualizer.plot_market_structure()") 