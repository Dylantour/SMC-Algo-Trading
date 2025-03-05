import os

# Default to empty strings if environment variables are not set
key = os.environ.get('BINANCE_API_KEY', 'xYuufQfbXZAEjiK6hhfCuuNeVmRBRGAk6fCpyLUXWpZuenqc5olRuRwn82NzvwCY')
secret = os.environ.get('BINANCE_API_SECRET', 'eWqt0YeMRRELycEZFS9haV0n9FCbiJEOi0E9wtJHiUzPSwLhCa0lTX6yzvr9BXrH')

# Print a warning if using default keys
if key == 'xYuufQfbXZAEjiK6hhfCuuNeVmRBRGAk6fCpyLUXWpZuenqc5olRuRwn82NzvwCY':
    print("WARNING: Using default API key. Set BINANCE_API_KEY environment variable for security.")
if secret == 'eWqt0YeMRRELycEZFS9haV0n9FCbiJEOi0E9wtJHiUzPSwLhCa0lTX6yzvr9BXrH':
    print("WARNING: Using default API secret. Set BINANCE_API_SECRET environment variable for security.")