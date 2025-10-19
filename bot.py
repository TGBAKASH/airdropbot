import os
import requests
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ====== ENV VARS ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")

# ====== DB SETUP ======
conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, wallet TEXT)")
conn.commit()

def get_wallet(uid):
    cur.execute("SELECT wallet FROM users WHERE id=?", (uid,))
    r = cur.fetchone()
    return r[0] if r else None

def save_wallet(uid, wallet):
    cur.execute("INSERT OR REPLACE INTO users (id, wallet) VALUES (?, ?)", (uid, wallet))
    conn.commit()

# ====== ALCHEMY RPC ENDPOINTS ======
CHAIN_URLS = {
    "Ethereum": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
    "Arbitrum": f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
    "Base": f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
}

# ====== FETCH BALANCES ======
def get_eth_balance(wallet, url):
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [wallet, "latest"],
        "id": 1
    }
    r = requests.post(url, json=payload).json()
    wei = int(r.get("result", "0x0"), 16)
    return round(wei / 1e18, 5)

def get_token_metadata(address, url):
    data = {
        "jsonrpc": "2.0",
        "method": "alchemy_getTokenMetadata",
        "params": [address],
        "id": 1
    }
    try:
        r = requests.post(url, json=data).json()
        return r.get("result", {})
    except:
        return {}

def get_token_balances(wallet, url):
    data = {
        "jsonrpc": "2.0",
        "method": "alchemy_getTokenBalances",
        "params": [wallet],
        "id": 1
    }
    try:
        r = requests.post(url, json=data).json()
        balances = r.get("result", {}).get("tokenBalances", [])
        tokens = []
        for t in balances:
            bal_hex = t.get("tokenBalance")
            if not bal_hex or bal_hex == "0x0": continue
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
    except:
        return []

# ====== TELEGRAM COMMANDS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    wallet = get_wallet(user.id)

    text = "👋 Welcome to *Sage Airdrops Bot*\n\n"
    if wallet:
        text += f"💳 Wallet linked:\n`{wallet}`\n\n"
    else:
        text += "🔗 No wallet linked yet.\n\n"
    text += "Choose an option below:"

    buttons = [
        [InlineKeyboardButton("💳 Link Wallet", callback_data="link_wallet")],
        [InlineKeyboardButton("💼 Portfolio", callback_data="portfolio")]
    ]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data

    if data == "link_wallet":
        await query.message.reply_text("🔗 Send me your wallet address (0x...)")
        context.user_data["awaiting_wallet"] = True
        await query.answer()

    elif data == "portfolio":
        wallet = get_wallet(user.id)
        if not wallet:
            await query.answer("❌ Please link your wallet first.", show_alert=True)
            return

        await query.edit_message_text("⏳ Fetching your portfolio across ETH + ARB + BASE...")
        msg = f"💼 *Portfolio for:* `{wallet}`\n\n"
        for chain, url in CHAIN_URLS.items():
            eth_bal = get_eth_balance(wallet, url)
            msg += f"🌐 *{chain}*\nΞ ETH: {eth_bal}\n"
            tokens = get_token_balances(wallet, url)
            for name, sym, bal in tokens[:5]:
                msg += f"• {name} ({sym}): {bal}\n"
            msg += "\n"
        await query.edit_message_text(msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if context.user_data.get("awaiting_wallet"):
        wallet = update.message.text.strip()
        if wallet.startswith("0x") and len(wallet) == 42:
            save_wallet(user.id, wallet)
            await update.message.reply_text(f"✅ Wallet linked:\n`{wallet}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Invalid wallet address. Please try again.")
        context.user_data["awaiting_wallet"] = False

# ====== MAIN ======
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("about", start))
    app.add_handler(CommandHandler("restart", start))
    app.add_handler(CommandHandler("reload", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(CommandHandler("portfolio", button_click))
    app.add_handler(CommandHandler("wallet", button_click))
    app.add_handler(CommandHandler("link", button_click))
    app.add_handler(CommandHandler("mywallet", start))
    app.add_handler(CommandHandler("connect", start))
    app.add_handler(CommandHandler("setwallet", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("airdrop", start))
    app.add_handler(CommandHandler("stats", start))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("hello", start))
    app.add_handler(CommandHandler("hi", start))
    app.add_handler(telegram.ext.MessageHandler(telegram.ext.filters.TEXT, handle_message))
    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
