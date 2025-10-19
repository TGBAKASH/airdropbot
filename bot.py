import os
import re
import sqlite3
import json
import requests
from datetime import datetime
from flask import Flask, request
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from keep_alive import keep_alive

keep_alive()
app = Flask(__name__)

# =============================
# CONFIG
# =============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [1377923423]
DB_FILE = "airdrops.db"
CHANNEL_ID = -1001974850367
ALCHEMY_WEBHOOK_SECRET = os.getenv("ALCHEMY_WEBHOOK_SECRET")
ALCHEMY_WEBHOOK_ID = os.getenv("ALCHEMY_WEBHOOK_ID")

# =============================
# DATABASE
# =============================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS airdrops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT,
            description TEXT,
            category TEXT,
            date_added TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            wallet_address TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_airdrop(title, link, desc, cat):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO airdrops (title, link, description, category, date_added)
        VALUES (?, ?, ?, ?, ?)
    """, (title, link, desc, cat, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def set_wallet(user_id, username, address):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (id, username, wallet_address) VALUES (?, ?, ?)",
              (user_id, username, address))
    conn.commit()
    conn.close()

def get_wallet(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT wallet_address FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# =============================
# HELPERS
# =============================
def is_admin(user_id): return user_id in ADMIN_IDS

def detect_category(text):
    t = text.lower()
    if "testnet" in t: return "testnet"
    if "nft" in t or "game" in t: return "nft"
    if "trade" in t or "exchange" in t: return "trading"
    if "points" in t or "campaign" in t or "mission" in t: return "top"
    return "non_trading"

def extract_airdrop_info(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    link = re.search(r'(https?://\S+)', text)
    title = "Untitled"
    for l in lines:
        if any(w in l.lower() for w in ["project", "airdrop", "campaign"]):
            title = l.split(":", 1)[-1].strip() if ":" in l else l
            break
    if title == "Untitled" and lines:
        title = lines[0][:50]
    return title, (link.group(1) if link else "N/A"), "\n".join(lines), detect_category(text)

def is_airdrop_post(text):
    text = text.lower()
    good = ["airdrop","reward","campaign","claim","testnet","mission","earn"]
    bad = ["update","news","winner","ended","delay"]
    return any(w in text for w in good) and not any(w in text for w in bad)

# =============================
# TELEGRAM BOT
# =============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("💰 Wallet", callback_data="wallet")],
        [InlineKeyboardButton("🚀 Airdrops", callback_data="airdrops_menu")]
    ]
    user = update.message.from_user
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel")])

    await update.message.reply_text(
        "👋 *Welcome to Airdrop Sage Bot!*\n\nSelect an option:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def main_menu(query):
    keyboard = [
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("💰 Wallet", callback_data="wallet")],
        [InlineKeyboardButton("🚀 Airdrops", callback_data="airdrops_menu")]
    ]
    if is_admin(query.from_user.id):
        keyboard.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel")])
    await query.edit_message_text("🏠 *Main Menu*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Admin Panel ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("Access denied.")
        return
    keyboard = [
        [InlineKeyboardButton("➕ Add Airdrop", callback_data="admin_add_airdrop")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    await query.edit_message_text("🛠 *Admin Panel*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# Manual Add Workflow
async def admin_add_airdrop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data["adding_airdrop"] = {}
    await query.edit_message_text("✏️ Send *Title* for new airdrop:", parse_mode="Markdown")

async def admin_add_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data.get("adding_airdrop")
    if user_data is None: return
    text = update.message.text.strip()

    if "title" not in user_data:
        user_data["title"] = text
        await update.message.reply_text("🔗 Now send *Link*:")
    elif "link" not in user_data:
        user_data["link"] = text
        await update.message.reply_text("📝 Send *Description*:")
    elif "description" not in user_data:
        user_data["description"] = text
        await update.message.reply_text("📂 Category? (testnet / nft / trading / non_trading / top)")
    elif "category" not in user_data:
        user_data["category"] = text
        add_airdrop(**user_data)
        context.user_data.pop("adding_airdrop")
        await update.message.reply_text("✅ Airdrop added successfully!")

# --- Wallet & Profile Handlers ---
async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    wallet = get_wallet(user.id)
    if wallet:
        msg = f"💳 Your wallet:\n`{wallet}`\n\nYou'll get automatic notifications for incoming or outgoing transactions."
    else:
        msg = "🔗 Please send your *Ethereum wallet address* to link it."
        context.user_data["awaiting_wallet"] = True
    await query.edit_message_text(msg, parse_mode="Markdown")

async def handle_wallet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_wallet"):
        address = update.message.text.strip()
        user = update.effective_user
        if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
            await update.message.reply_text("❌ Invalid address, try again.")
            return
        set_wallet(user.id, user.username, address)
        context.user_data["awaiting_wallet"] = False
        await update.message.reply_text("✅ Wallet linked successfully!")

# =============================
# ALCHEMY WEBHOOK HANDLER
# =============================
@app.route("/alchemy_webhook", methods=["POST"])
def alchemy_webhook():
    data = request.json
    if not data: return "No data", 400

    event = data.get("event")
    if event != "ADDRESS_ACTIVITY": return "Ignored", 200

    for activity in data.get("activity", []):
        wallet = activity.get("address")
        value = int(activity.get("value", "0"))
        if value == 0: continue

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE wallet_address=?", (wallet,))
        user = c.fetchone()
        conn.close()

        if user:
            user_id = user[0]
            direction = "received" if int(activity.get("to", ""), 16) else "sent"
            amount = round(value / 10**18, 6)
            text = f"💸 *Wallet Activity Detected*\n\nYou {direction} {amount} ETH."
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                         params={"chat_id": user_id, "text": text, "parse_mode": "Markdown"})

    return "OK", 200

# =============================
# MAIN
# =============================
def main():
    init_db()
    bot = Application.builder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CallbackQueryHandler(admin_panel, pattern="admin_panel"))
    bot.add_handler(CallbackQueryHandler(admin_add_airdrop, pattern="admin_add_airdrop"))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_step))
    bot.add_handler(CallbackQueryHandler(wallet, pattern="wallet"))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet_input))
    print("🤖 Bot running with Alchemy Webhook Support...")
    bot.run_polling()

if __name__ == "__main__":
    main()
    app.run(host="0.0.0.0", port=8080)
