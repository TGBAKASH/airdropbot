import os
import requests
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from keep_alive import keep_alive

# ====== ENV VARS ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_URL")

# Alchemy Webhook IDs and Secrets
ALCHEMY_WEBHOOK_ETH = os.getenv("ALCHEMY_WEBHOOK_ID_ETH")
ALCHEMY_WEBHOOK_ARB = os.getenv("ALCHEMY_WEBHOOK_ID_ARB")
ALCHEMY_WEBHOOK_BASE = os.getenv("ALCHEMY_WEBHOOK_ID_BASE")

ALCHEMY_SECRET_ETH = os.getenv("ALCHEMY_WEBHOOK_SECRET_ETH")
ALCHEMY_SECRET_ARB = os.getenv("ALCHEMY_WEBHOOK_SECRET_ARB")
ALCHEMY_SECRET_BASE = os.getenv("ALCHEMY_WEBHOOK_SECRET_BASE")

# ====== DATABASE SETUP ======
conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS wallets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        chain TEXT,
        address TEXT,
        notifications_enabled INTEGER DEFAULT 1,
        last_balance TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
""")

conn.commit()

# ====== DB FUNCTIONS ======
def get_or_create_user(user_id, username, first_name):
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        conn.commit()

def get_user_wallets(user_id):
    cur.execute("SELECT chain, address, notifications_enabled FROM wallets WHERE user_id=?", (user_id,))
    return cur.fetchall()

def add_wallet(user_id, chain, address):
    cur.execute("INSERT INTO wallets (user_id, chain, address) VALUES (?, ?, ?)", (user_id, chain, address))
    conn.commit()

def delete_wallet(user_id, address):
    cur.execute("DELETE FROM wallets WHERE user_id=? AND address=?", (user_id, address))
    conn.commit()

def toggle_notifications(user_id, address):
    cur.execute(
        "UPDATE wallets SET notifications_enabled = 1 - notifications_enabled WHERE user_id=? AND address=?",
        (user_id, address)
    )
    conn.commit()

# ====== CHAINS ======
CHAINS = {
    "Ethereum": {
        "url": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
        "webhook_id": ALCHEMY_WEBHOOK_ETH,
        "webhook_secret": ALCHEMY_SECRET_ETH,
        "symbol": "ETH",
        "icon": "🔷"
    },
    "Arbitrum": {
        "url": f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
        "webhook_id": ALCHEMY_WEBHOOK_ARB,
        "webhook_secret": ALCHEMY_SECRET_ARB,
        "symbol": "ETH",
        "icon": "🔵"
    },
    "Base": {
        "url": f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
        "webhook_id": ALCHEMY_WEBHOOK_BASE,
        "webhook_secret": ALCHEMY_SECRET_BASE,
        "symbol": "ETH",
        "icon": "🟦"
    },
    "Polygon": {
        "url": f"https://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
        "webhook_id": None,
        "webhook_secret": None,
        "symbol": "MATIC",
        "icon": "🟣"
    },
    "Optimism": {
        "url": f"https://opt-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
        "webhook_id": None,
        "webhook_secret": None,
        "symbol": "ETH",
        "icon": "🔴"
    }
}

# ====== WEB3 HELPERS ======
def get_eth_balance(wallet, url):
    try:
        payload = {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [wallet, "latest"], "id": 1}
        r = requests.post(url, json=payload, timeout=10).json()
        wei = int(r.get("result", "0x0"), 16)
        return round(wei / 1e18, 6)
    except Exception:
        return 0

def get_token_metadata(address, url):
    try:
        data = {"jsonrpc": "2.0", "method": "alchemy_getTokenMetadata", "params": [address], "id": 1}
        r = requests.post(url, json=data, timeout=10).json()
        return r.get("result", {})
    except Exception:
        return {}

def get_token_balances(wallet, url):
    try:
        data = {"jsonrpc": "2.0", "method": "alchemy_getTokenBalances", "params": [wallet], "id": 1}
        r = requests.post(url, json=data, timeout=10).json()
        balances = r.get("result", {}).get("tokenBalances", [])
        tokens = []
        for t in balances[:10]:
            bal_hex = t.get("tokenBalance")
            if not bal_hex or bal_hex == "0x0":
                continue
            token_addr = t.get("contractAddress")
            meta = get_token_metadata(token_addr, url)
            if meta:
                name = meta.get("name", "Unknown")
                symbol = meta.get("symbol", "")
                dec = meta.get("decimals", 18)
                bal = int(bal_hex, 16) / (10 ** dec)
                if bal > 0:
                    tokens.append((name, symbol, round(bal, 4)))
        return tokens
    except Exception:
        return []

# ====== MAIN MENU ======
def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🎁 Airdrops", callback_data="airdrops")],
        [InlineKeyboardButton("💼 Wallet", callback_data="wallet_menu")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ])

# ====== COMMAND HANDLERS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.first_name)
    text = (
        "🌟 *Welcome to Sage Airdrops Bot!*\n\n"
        "Your comprehensive crypto companion for:\n"
        "• 👤 Profile Management\n"
        "• 🎁 Airdrop Opportunities\n"
        "• 💼 Multi-chain Wallet Tracking\n"
        "• 🔔 Real-time Notifications\n\n"
        "Choose an option below to get started:"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_menu())

# ====== CALLBACK HANDLER ======
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data == "profile":
        wallets = get_user_wallets(user.id)
        text = (
            f"👤 *Your Profile*\n\n"
            f"📛 Name: {user.first_name or 'N/A'}\n"
            f"🆔 User ID: `{user.id}`\n"
            f"📱 Username: @{user.username or 'Not set'}\n"
            f"💼 Linked Wallets: {len(wallets)}"
        )
        buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "help":
        text = (
            "ℹ️ *Help & Information*\n\n"
            "👤 Profile — View your user info\n"
            "🎁 Airdrops — Explore testnet/mainnet airdrops\n"
            "💼 Wallet — Manage your wallets & balances"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]))

    elif data == "main_menu":
        await query.edit_message_text("🌟 *Sage Airdrops Bot*\n\nChoose an option below:", parse_mode="Markdown", reply_markup=get_main_menu())

# ====== MESSAGE HANDLER ======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please use the menu buttons below 👇")

# ====== MAIN ======
def main():
    keep_alive()  # Run Flask server on Render
    print("🚀 Starting Sage Airdrops Bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is now running...")
    app.run_polling()

if __name__ == "__main__":
    main()
