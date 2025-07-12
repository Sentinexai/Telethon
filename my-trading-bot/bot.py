import os
import re
import time
import requests
import asyncio
import threading
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Load environment variables
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
ALPACA_KEY = os.getenv("ALPACA_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET")
ALPACA_URL = os.getenv("ALPACA_URL", "https://paper-api.alpaca.markets")

# Use pre-authenticated session
client = TelegramClient("my-trading-bot/railway", API_ID, API_HASH)

# Sentiment Analyzer
analyzer = SentimentIntensityAnalyzer()

# Trading config
budget = 4000
positions = {}
used_funds = 0

# Confirm volume
def confirm_volume(symbol):
    url = f"{ALPACA_URL}/v2/assets/{symbol}"
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET
    }
    r = requests.get(url, headers=headers)
    return r.ok and r.json().get("tradable", False)

# Get stock price
def get_price(symbol):
    url = f"{ALPACA_URL}/v2/stocks/{symbol}/quotes/latest"
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET
    }
    r = requests.get(url, headers=headers)
    if r.ok:
        return float(r.json()['quote']['ap'])
    return None

# Buy order
def place_order(symbol, qty):
    url = f"{ALPACA_URL}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
        "Content-Type": "application/json"
    }
    data = {
        "symbol": symbol,
        "qty": qty,
        "side": "buy",
        "type": "market",
        "time_in_force": "gtc",
        "extended_hours": True
    }
    print(f"📈 BUY {qty} shares of {symbol}")
    res = requests.post(url, headers=headers, json=data)
    print("✅ Alpaca Response:", res.json())

# Sell order
def place_sell_order(symbol, qty):
    url = f"{ALPACA_URL}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
        "Content-Type": "application/json"
    }
    data = {
        "symbol": symbol,
        "qty": qty,
        "side": "sell",
        "type": "market",
        "time_in_force": "gtc",
        "extended_hours": True
    }
    print(f"🚨 SELL {qty} shares of {symbol}")
    res = requests.post(url, headers=headers, json=data)
    print("📤 Alpaca Sell Response:", res.json())

# Live monitor for take-profit or stop-loss
def monitor_positions():
    while True:
        for symbol in list(positions.keys()):
            price = get_price(symbol)
            if not price:
                continue

            pos = positions[symbol]
            entry = pos['entry']
            peak = max(pos['peak'], price)
            sentiment = pos['sentiment']

            # Stop-loss
            if price <= entry:
                print(f"🔻 Stop-loss triggered for {symbol}")
                place_sell_order(symbol, pos['qty'])
                del positions[symbol]
                continue

            # Trailing take-profit
            trail_pct = 0.2 if sentiment >= 0.9 else 0.05
            if price <= peak * (1 - trail_pct):
                print(f"📉 Trailing take-profit triggered for {symbol}")
                place_sell_order(symbol, pos['qty'])
                del positions[symbol]
                continue

            positions[symbol]['peak'] = peak

        time.sleep(5)

# Telegram message handler
@client.on(events.NewMessage)
async def handler(event):
    global used_funds
    message = event.message.message
    print(f"📨 {datetime.now().strftime('%H:%M:%S')} - {message}")

    match = re.search(r'\$?([A-Z]{2,5})', message)
    if not match:
        return

    symbol = match.group(1)
    sentiment_score = analyzer.polarity_scores(message)['compound']

    if sentiment_score < 0.3:
        print("🟡 Sentiment not strong enough")
        return

    if not confirm_volume(symbol):
        print("🔴 Symbol not tradable or volume low")
        return

    price = get_price(symbol)
    if not price or price <= 0:
        print("⚠️ Invalid price")
        return

    alloc = budget if sentiment_score >= 0.6 else budget * 0.5
    qty = int(alloc // price)

    if qty < 1:
        print("❌ Not enough funds for at least 1 share.")
        return

    used_funds += qty * price
    positions[symbol] = {"entry": price, "qty": qty, "peak": price, "sentiment": sentiment_score}
    place_order(symbol, qty)

# Main function
async def start_bot():
    await client.start()
    print("🤖 SNIPER BOT IS LIVE AND LISTENING...")
    await client.run_until_disconnected()

# Start monitor thread
threading.Thread(target=monitor_positions, daemon=True).start()

# Run bot
if __name__ == "__main__":
    asyncio.run(start_bot())
