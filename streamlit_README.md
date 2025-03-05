# Streamlit UI for SMC-Algo-Trading

This is a simple, cross-platform UI for the SMC-Algo-Trading project using Streamlit.

## Features

- Interactive market structure analysis
- Candlestick chart visualization
- Market insights and metrics
- Support for multiple timeframes and symbols
- Works on Windows, macOS, and Linux

## Installation

1. Make sure you have the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. If you want to use Binance integration, set your API keys as environment variables:
   ```
   export BINANCE_API_KEY="your_api_key"
   export BINANCE_API_SECRET="your_api_secret"
   ```
   
   Or update the `BinanceBot/key.py` file with your API keys.

## Running the UI

To run the Streamlit UI:

```
streamlit run streamlit_app.py
```

This will start a local web server and open the UI in your default web browser.

## Usage

1. Select a symbol from the dropdown menu in the sidebar
2. Choose a timeframe
3. Adjust the number of candles and smoothing factor as needed
4. The UI will display:
   - A candlestick chart with market structure analysis
   - Market insights including trend information
   - Raw data in tabular format

## Fallback Mode

If Binance integration is not available, the UI will automatically switch to a demo mode with generated sample data. This is useful for testing and development without requiring actual API access.

## Notes

- This UI is designed to be lightweight and cross-platform
- It uses the same core analysis logic as the main application
- For full functionality on Windows, you can still use the main application with MetaTrader 5 integration 