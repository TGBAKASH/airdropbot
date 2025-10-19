from flask import Flask
from threading import Thread
import asyncio
import time
import requests
import os

# Flask server to keep Render (or Replit) alive
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running and keep_alive is active!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Start Flask in background thread
def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ==============================
# Wallet Notification Logic
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Your bot token from environment variable
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")  # Example for Ethereum/Polygon etc.
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # Telegram chat ID to send updates

# If you don't use env vars, replace with direct values (NOT recommended for security)
# BOT_TOKEN = "1234567890:ABC-XYZ..."
# ADMIN_CHAT_ID = "123456789"

# Sample wallet tracking dictionary {chain: [wallets]}
tracked_wallets = {
    "ethereum": [
        "0x0000000000000000000000000000000000000000"
    ],
    "polygon": []
}

# Track previous balances to detect transactions
wallet_balances = {}

def get_balance(chain, address):
    """Fetch balance from blockchain using Alchemy."""
    try:
        url = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [address, "latest"],
            "id": 1
        }
        response = requests.post(url, json=payload, timeout=10).json()
        balance_wei = int(response["result"], 16)
        return balance_wei / (10 ** 18)
    except Exception as e:
        print(f"[Error] Balance fetch failed for {address}: {e}")
        return None

async def send_telegram_message(text):
    """Send Telegram message via bot token."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": ADMIN_CHAT_ID, "text": text}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[Error sending message]: {e}")

async def notify_users_about_tx():
    """Check for wallet transactions periodically and send updates."""
    while True:
        try:
            for chain, wallets in tracked_wallets.items():
                for wallet in wallets:
                    current_balance = get_balance(chain, wallet)
                    prev_balance = wallet_balances.get(wallet)

                    # On first run, just store the balance
                    if prev_balance is None:
                        wallet_balances[wallet] = current_balance
                        continue

                    # If balance changes — transaction happened
                    if current_balance != prev_balance:
                        diff = current_balance - prev_balance
                        direction = "Received" if diff > 0 else "Sent"
                        message = (
                            f"💸 *{direction} Transaction Detected!*\n"
                            f"Chain: {chain}\n"
                            f"Wallet: `{wallet}`\n"
                            f"Change: {diff:.6f} ETH"
                        )
                        await send_telegram_message(message)
                        wallet_balances[wallet] = current_balance

            # Sleep before next check (every 60 seconds)
            await asyncio.sleep(60)

        except Exception as e:
            print(f"[notify_users_about_tx error]: {e}")
            await asyncio.sleep(30)

# ==============================
# Run Both Flask + Notifier
# ==============================
def start_keep_alive():
    """Launch Flask and TX notifier together."""
    keep_alive()
    asyncio.run(notify_users_about_tx())

if __name__ == "__main__":
    print("🚀 Starting keep_alive with TX monitoring...")
    start_keep_alive()
