# ICT Strategy Implementation

This is an implementation of the Institutional Candle Theory (ICT) trading strategy for the Binance trading bot. The strategy identifies market structure, liquidity sweeps, and fair value gaps to determine entry and exit points for trades.

## Strategy Components

1. **Market Structure Analysis**: Analyzes higher timeframe to determine overall market bias (bullish, bearish, or neutral).
2. **Liquidity Sweeps**: Detects when price sweeps beyond significant swing points and then reverses.
3. **Fair Value Gaps (FVGs)**: Identifies gaps in price action that occur after liquidity sweeps.
4. **Entry on FVG Retest**: Enters trades when price pulls back to identified FVGs.
5. **Risk Management**: Implements stop losses, take profits, and trailing stops based on configurable parameters.

## Files

- `trade.py`: Contains the `ICTTraderClient` class with the ICT strategy implementation.
- `run_bot.py`: Main script for running the trading bot with the ICT strategy.
- `run_ict_bot.py`: Alternative runner with more visualization options.
- `ict_visualization.py`: Visualization tools for the ICT strategy components.
- `visualize_ict_strategy.py`: Script for visualizing ICT setups without actual trading.
- `backtest_ict_strategy.py`: Backtesting script for the ICT strategy.

## Usage

### Running the Trading Bot

```bash
python BinanceBot/run_bot.py --pair BTCBUSD --htf 1h --ltf 5m --risk 0.01 --min-fvg-size 0.0005
```

### Command Line Parameters

- `--pair`: Trading pair (default: BTCBUSD)
- `--htf`: Higher timeframe for market structure analysis (default: 1h)
- `--ltf`: Lower timeframe for trade entries (default: 5m)
- `--risk`: Risk per trade as a decimal (default: 0.01 or 1%)
- `--min-fvg-size`: Minimum fair value gap size as percentage (default: 0.0005 or 0.05%)
- `--trail`: Trail stop ratio (default: 0.8)

## Strategy Parameters Explained

### Higher Timeframe (HTF)
Used to establish market bias (bullish or bearish) based on recent swing points. Typical values: 1h, 4h, 1d.

### Lower Timeframe (LTF)
Used for entry signals and trade execution. Typical values: 1m, 5m, 15m.

### Minimum FVG Size
The minimum size of a fair value gap to be considered valid. Expressed as a percentage of price.
- Higher values (e.g., 0.001 or 0.1%) will result in fewer but potentially more significant trades.
- Lower values (e.g., 0.0003 or 0.03%) will generate more trading opportunities but may include weaker setups.

### Risk Per Trade
The percentage of account balance risked per trade. Default is 0.01 (1%).

### Trail Stop Ratio
The percentage of profits to lock in when using trailing stops. Default is 0.8 (80%).

## How the Strategy Works

1. **Market Bias Detection**:
   - Analyzes higher timeframe swing points to determine if the market is making higher highs and higher lows (bullish) or lower highs and lower lows (bearish).
   - Falls back to moving average analysis if not enough swing points are available.

2. **Liquidity Sweep Detection**:
   - Monitors for price movements that exceed recent swing highs or lows and then reverse.
   - Only considers sweeps that align with the higher timeframe bias.

3. **FVG Detection**:
   - After a liquidity sweep, looks for a strong impulse candle followed by a gap in price.
   - For bullish FVGs: Candle 3's low is above Candle 1's high.
   - For bearish FVGs: Candle 3's high is below Candle 1's low.

4. **Trade Entry**:
   - Enters when price retraces back to an identified FVG.
   - Sets stop loss just beyond the liquidity sweep point.
   - Sets take profit based on specified risk-reward ratio.

5. **Position Management**:
   - Implements trailing stops to lock in profits as price moves favorably.
   - Monitors for FVG filling which can invalidate the setup.

## Visualization

The strategy includes visualization tools to help understand the market structure, liquidity sweeps, and FVGs. Use the `visualize_ict_strategy.py` script to see these components without actual trading.

## Backtesting

To test the strategy on historical data:

```bash
python BinanceBot/backtest_ict_strategy.py --pair BTCBUSD --days 30 --report
```

## Custom Modifications

The strategy is highly configurable. If you want to modify specific parameters:

1. Adjust the FVG detection parameters in the `ICTTraderClient` class.
2. Change the risk management settings for different risk/reward profiles.
3. Modify the market structure analysis window for different market conditions.

## Warning

Trading cryptocurrencies involves significant risk. This strategy, like all trading strategies, does not guarantee profits. Always use proper risk management and never trade with funds you cannot afford to lose. 