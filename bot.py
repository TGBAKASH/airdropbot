import os
import requests
import sqlite3
import asyncio
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
keep_alive()

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

# ====== DB SETUP ======
conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()

# Create tables
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

# ====== DATABASE FUNCTIONS ======
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
    cur.execute(
        "INSERT INTO wallets (user_id, chain, address) VALUES (?, ?, ?)",
        (user_id, chain, address)
    )
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

# ====== ALCHEMY RPC ENDPOINTS ======
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
        "icon": "🔵"
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

# ====== BLOCKCHAIN FUNCTIONS ======
def get_eth_balance(wallet, url):
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [wallet, "latest"],
            "id": 1
        }
        r = requests.post(url, json=payload, timeout=10).json()
        wei = int(r.get("result", "0x0"), 16)
        return round(wei / 1e18, 6)
    except:
        return 0

def get_token_metadata(address, url):
    try:
        data = {
            "jsonrpc": "2.0",
            "method": "alchemy_getTokenMetadata",
            "params": [address],
            "id": 1
        }
        r = requests.post(url, json=data, timeout=10).json()
        return r.get("result", {})
    except:
        return {}

def get_token_balances(wallet, url):
    try:
        data = {
            "jsonrpc": "2.0",
            "method": "alchemy_getTokenBalances",
            "params": [wallet],
            "id": 1
        }
        r = requests.post(url, json=data, timeout=10).json()
        balances = r.get("result", {}).get("tokenBalances", [])
        tokens = []
        for t in balances[:10]:  # Limit to top 10 tokens
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
    except:
        return []

# ====== WEBHOOK MANAGEMENT ======
def add_address_to_webhook(webhook_id, address, chain):
    """Add an address to Alchemy webhook for monitoring"""
    if not webhook_id:
        return False
    
    try:
        url = f"https://dashboard.alchemy.com/api/update-webhook-addresses"
        headers = {
            "Authorization": f"Bearer {ALCHEMY_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "webhook_id": webhook_id,
            "addresses_to_add": [address.lower()],
            "addresses_to_remove": []
        }
        response = requests.patch(url, json=payload, headers=headers, timeout=10)
        return response.status_code == 200
    except:
        return False

def remove_address_from_webhook(webhook_id, address, chain):
    """Remove an address from Alchemy webhook"""
    if not webhook_id:
        return False
    
    try:
        url = f"https://dashboard.alchemy.com/api/update-webhook-addresses"
        headers = {
            "Authorization": f"Bearer {ALCHEMY_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "webhook_id": webhook_id,
            "addresses_to_add": [],
            "addresses_to_remove": [address.lower()]
        }
        response = requests.patch(url, json=payload, headers=headers, timeout=10)
        return response.status_code == 200
    except:
        return False

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
    
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )

# ====== CALLBACK HANDLERS ======
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data
    
    # Profile Section
    if data == "profile":
        get_or_create_user(user.id, user.username, user.first_name)
        wallets = get_user_wallets(user.id)
        
        text = (
            f"👤 *Your Profile*\n\n"
            f"📛 Name: {user.first_name or 'N/A'}\n"
            f"🆔 User ID: `{user.id}`\n"
            f"📱 Username: @{user.username or 'Not set'}\n"
            f"💼 Linked Wallets: {len(wallets)}\n"
        )
        
        buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    # Airdrops Section
    elif data == "airdrops":
        text = (
            "🎁 *Airdrop Opportunities*\n\n"
            "Select category to explore:"
        )
        buttons = [
            [InlineKeyboardButton("🧪 Testnet Airdrops", callback_data="testnet")],
            [InlineKeyboardButton("💎 Mainnet Airdrops", callback_data="mainnet")],
            [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    elif data == "testnet":
        text = (
            "🧪 *Testnet Airdrops*\n\n"
            "Choose network type:"
        )
        buttons = [
            [InlineKeyboardButton("Layer 1", callback_data="testnet_l1")],
            [InlineKeyboardButton("Layer 2", callback_data="testnet_l2")],
            [InlineKeyboardButton("Others", callback_data="testnet_others")],
            [InlineKeyboardButton("⬅️ Back", callback_data="airdrops")]
        ]
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    elif data == "mainnet":
        text = (
            "💎 *Mainnet Airdrops*\n\n"
            "Choose category:"
        )
        buttons = [
            [InlineKeyboardButton("📈 Trading", callback_data="mainnet_trading")],
            [InlineKeyboardButton("🔒 Non-Trading", callback_data="mainnet_nontrading")],
            [InlineKeyboardButton("⬅️ Back", callback_data="airdrops")]
        ]
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    # Airdrop subcategories
    elif data.startswith("testnet_") or data.startswith("mainnet_"):
        category = data.replace("testnet_", "").replace("mainnet_", "").upper()
        text = (
            f"🎯 *{category} Airdrops*\n\n"
            "📋 Coming soon! This section will feature:\n"
            "• Active campaigns\n"
            "• Eligibility requirements\n"
            "• Task tracking\n"
            "• Reward estimates\n"
        )
        buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="airdrops")]]
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    # Wallet Menu
    elif data == "wallet_menu":
        wallets = get_user_wallets(user.id)
        
        text = "💼 *Wallet Management*\n\n"
        if wallets:
            text += "Your connected wallets:\n\n"
            for chain, addr, notif in wallets:
                notif_icon = "🔔" if notif else "🔕"
                text += f"{CHAINS.get(chain, {}).get('icon', '•')} *{chain}*\n`{addr[:8]}...{addr[-6:]}`\n{notif_icon} Notifications: {'On' if notif else 'Off'}\n\n"
        else:
            text += "No wallets connected yet.\n\n"
        
        buttons = [
            [InlineKeyboardButton("➕ Add Wallet", callback_data="add_wallet")],
            [InlineKeyboardButton("💰 View Portfolio", callback_data="portfolio")],
        ]
        if wallets:
            buttons.append([InlineKeyboardButton("⚙️ Manage Wallets", callback_data="manage_wallets")])
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
        
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    # Add Wallet Flow
    elif data == "add_wallet":
        text = "➕ *Add New Wallet*\n\nSelect blockchain:"
        buttons = []
        for chain_name, chain_info in CHAINS.items():
            buttons.append([InlineKeyboardButton(
                f"{chain_info['icon']} {chain_name}",
                callback_data=f"chain_{chain_name}"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="wallet_menu")])
        
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    elif data.startswith("chain_"):
        chain = data.replace("chain_", "")
        context.user_data["selected_chain"] = chain
        context.user_data["awaiting_wallet"] = True
        
        text = (
            f"🔗 *Connect {chain} Wallet*\n\n"
            f"Please send your wallet address (0x...)"
        )
        await query.edit_message_text(text, parse_mode="Markdown")
    
    # Portfolio View
    elif data == "portfolio":
        wallets = get_user_wallets(user.id)
        if not wallets:
            await query.answer("❌ Please add a wallet first.", show_alert=True)
            return
        
        await query.edit_message_text("⏳ *Fetching portfolio data...*", parse_mode="Markdown")
        
        msg = "💼 *Your Portfolio*\n\n"
        total_value_usd = 0
        
        for chain, wallet, _ in wallets:
            chain_info = CHAINS.get(chain)
            if not chain_info:
                continue
            
            url = chain_info["url"]
            symbol = chain_info["symbol"]
            icon = chain_info["icon"]
            
            eth_bal = get_eth_balance(wallet, url)
            msg += f"{icon} *{chain}*\n"
            msg += f"📍 `{wallet[:8]}...{wallet[-6:]}`\n"
            msg += f"💎 {symbol}: {eth_bal}\n"
            
            tokens = get_token_balances(wallet, url)
            if tokens:
                msg += "🪙 *Tokens:*\n"
                for name, sym, bal in tokens[:5]:
                    msg += f"  • {name} ({sym}): {bal}\n"
            msg += "\n"
        
        buttons = [[InlineKeyboardButton("🔄 Refresh", callback_data="portfolio")],
                   [InlineKeyboardButton("⬅️ Back", callback_data="wallet_menu")]]
        
        await query.edit_message_text(
            msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    # Manage Wallets
    elif data == "manage_wallets":
        wallets = get_user_wallets(user.id)
        text = "⚙️ *Manage Wallets*\n\nSelect a wallet:"
        
        buttons = []
        for chain, addr, _ in wallets:
            buttons.append([InlineKeyboardButton(
                f"{CHAINS.get(chain, {}).get('icon', '•')} {chain}: {addr[:8]}...{addr[-6:]}",
                callback_data=f"manage_{addr}"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="wallet_menu")])
        
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    elif data.startswith("manage_"):
        address = data.replace("manage_", "")
        context.user_data["managing_wallet"] = address
        
        wallets = get_user_wallets(user.id)
        wallet_info = next((w for w in wallets if w[1] == address), None)
        
        if wallet_info:
            chain, addr, notif = wallet_info
            text = (
                f"⚙️ *Wallet Settings*\n\n"
                f"{CHAINS.get(chain, {}).get('icon', '•')} {chain}\n"
                f"`{addr}`\n\n"
                f"Notifications: {'🔔 Enabled' if notif else '🔕 Disabled'}"
            )
            
            buttons = [
                [InlineKeyboardButton(
                    f"{'🔕 Disable' if notif else '🔔 Enable'} Notifications",
                    callback_data=f"toggle_notif_{addr}"
                )],
                [InlineKeyboardButton("🗑 Remove Wallet", callback_data=f"remove_{addr}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="manage_wallets")]
            ]
            
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    
    elif data.startswith("toggle_notif_"):
        address = data.replace("toggle_notif_", "")
        toggle_notifications(user.id, address)
        await query.answer("✅ Notification settings updated!")
        await button_handler(update, context)  # Refresh the manage view
    
    elif data.startswith("remove_"):
        address = data.replace("remove_", "")
        
        # Get wallet info before deletion
        wallets = get_user_wallets(user.id)
        wallet_info = next((w for w in wallets if w[1] == address), None)
        
        if wallet_info:
            chain = wallet_info[0]
            # Try to remove from webhook
            chain_info = CHAINS.get(chain, {})
            webhook_id = chain_info.get("webhook_id")
            if webhook_id:
                remove_address_from_webhook(webhook_id, address, chain)
        
        delete_wallet(user.id, address)
        await query.answer("✅ Wallet removed successfully!")
        
        # Go back to manage wallets or wallet menu
        context.user_data["managing_wallet"] = None
        wallets = get_user_wallets(user.id)
        if wallets:
            query.data = "manage_wallets"
        else:
            query.data = "wallet_menu"
        await button_handler(update, context)
    
    # Help Section
    elif data == "help":
        text = (
            "ℹ️ *Help & Information*\n\n"
            "*Available Features:*\n\n"
            "👤 *Profile* - View your user information\n\n"
            "🎁 *Airdrops* - Discover airdrop opportunities\n"
            "  • Testnet (L1, L2, Others)\n"
            "  • Mainnet (Trading, Non-Trading)\n\n"
            "💼 *Wallet* - Manage your crypto wallets\n"
            "  • Add multiple wallets\n"
            "  • View portfolio across chains\n"
            "  • Enable/disable notifications\n"
            "  • Track transactions\n\n"
            "*Supported Chains:*\n"
            "🔷 Ethereum\n"
            "🔵 Arbitrum\n"
            "🔵 Base\n"
            "🟣 Polygon\n"
            "🔴 Optimism\n"
        )
        buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    # Back to main menu
    elif data == "main_menu":
        text = (
            "🌟 *Sage Airdrops Bot*\n\n"
            "Choose an option below:"
        )
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )

# ====== MESSAGE HANDLER ======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if context.user_data.get("awaiting_wallet"):
        wallet = update.message.text.strip()
        chain = context.user_data.get("selected_chain")
        
        if wallet.startswith("0x") and len(wallet) == 42:
            # Check if wallet already exists
            wallets = get_user_wallets(user.id)
            if any(w[1].lower() == wallet.lower() for w in wallets):
                await update.message.reply_text(
                    "⚠️ This wallet is already connected!",
                    parse_mode="Markdown"
                )
            else:
                add_wallet(user.id, chain, wallet)
                
                # Try to register with webhook
                chain_info = CHAINS.get(chain, {})
                webhook_id = chain_info.get("webhook_id")
                webhook_registered = False
                
                if webhook_id:
                    webhook_registered = add_address_to_webhook(webhook_id, wallet, chain)
                
                response_text = (
                    f"✅ *Wallet Connected!*\n\n"
                    f"{CHAINS.get(chain, {}).get('icon', '•')} {chain}\n"
                    f"`{wallet}`\n\n"
                )
                
                if webhook_registered:
                    response_text += "🔔 Real-time notifications enabled!\n💡 You'll be notified of incoming/outgoing transactions."
                else:
                    response_text += "🔔 Notifications enabled (polling mode)\n💡 Balance updates may take a few minutes."
                
                await update.message.reply_text(response_text, parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "⚠️ Invalid wallet address. Please send a valid address starting with 0x (42 characters)."
            )
        
        context.user_data["awaiting_wallet"] = False
        context.user_data["selected_chain"] = None

# ====== MAIN ======
def main():
    # Start keep-alive server
    keep_alive()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Sage Airdrops Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()