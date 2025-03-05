# SMC-Algo-Trading

A Python library for building trading bots following Smart Money Concepts (SMC).

## Overview

This library implements Smart Money Concepts for algorithmic trading, with components for:

1. **Market Structure Analysis**: Identifying market structure vertices (HH, HL, LH, LL)
2. **Candlestick Pattern Recognition**: Analyzing candlestick patterns and trends
3. **Automated Trading**: Integration with Binance and MetaTrader 5
4. **Risk Management**: DrawDown management to control trading risk

## System Requirements

- Python 3.7+
- Dependencies listed in `requirements.txt`
- For MetaTrader 5 integration: Windows OS with MetaTrader 5 installed
- For Binance integration: Valid Binance API keys

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/SMC-Algo-Trading.git
   cd SMC-Algo-Trading
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Platform-specific setup:
   - **For Binance**: Set your API keys as environment variables:
     ```
     export BINANCE_API_KEY="your_api_key"
     export BINANCE_API_SECRET="your_api_secret"
     ```
   - **For MetaTrader 5** (Windows only): Ensure MetaTrader 5 is installed and running

## Running the Application

### Main Application (Requires PySide2 and MetaTrader 5)

The main application provides a graphical interface for market analysis:

```
python main.py
```

Note: This requires PySide2 and MetaTrader 5, which are primarily supported on Windows.

### Binance Bot (Cross-platform)

To run the Binance trading bot:

```
cd BinanceBot
python run_bot.py
```

### Market Analysis Tool (Cross-platform)

For market structure analysis without the full UI:

```
python analyze_market.py
```

## Components

- **Vertex.py**: Market structure analysis
- **Candle.py**: Candlestick representation
- **DrawDownManager.py**: Risk management
- **BinanceBot/**: Binance integration
- **MT5Bot/**: MetaTrader 5 integration (Windows only)

## Platform Compatibility

- **Windows**: Full support for all features
- **macOS/Linux**: Support for Binance integration and market analysis; MetaTrader 5 integration not available

## Contributing

This library is under active development. Anyone can participate in this project.

For more information, join our Discord: https://discord.gg/SQfjY3ha

## License

[Specify your license here]

Vertex class used for represent vertex of the market structure/skeleton

Candle class used for represent the data of a "japanese" candle mainly used on trading charts, functions for convert to Renko / Heiken Ashi type under works
