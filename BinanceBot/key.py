import os
import dotenv

dotenv.load_dotenv()

# Use provided API keys - adding 'e' prefix to secret key that was missing
key = os.getenv("BINANCE_API_KEY")
secret = os.getenv("BINANCE_API_SECRET")

