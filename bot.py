import os
import re
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from keep_alive import keep_alive
keep_alive()

# =============================
# CONFIGURATION
# =============================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # set in Render Environment Variables
CHANNEL_ID = -1001974850367         # your Sage Airdrops channel ID
ADMIN_IDS = [1377923423]            # your Telegram user ID
DB_FILE = "airdrops.db"

# =============================
# DATABASE FUNCTIONS
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
    conn.commit()
    conn.close()


def add_airdrop(title, link, description, category="general"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO airdrops (title, link, description, category, date_added)
        VALUES (?, ?, ?, ?, ?)
    """, (title, link, description, category, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_airdrops(category=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if category:
        c.execute("SELECT title, link, description FROM airdrops WHERE category=? ORDER BY id DESC", (category,))
    else:
        c.execute("SELECT title, link, description FROM airdrops ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return data

# =============================
# HELPERS
# =============================
def is_admin(user_id):
    return user_id in ADMIN_IDS


def detect_category(text: str):
    """Auto-classify airdrop type based on keywords."""
    t = text.lower()
    if "testnet" in t:
        return "testnet"
    if "nft" in t or "game" in t:
        return "nft"
    if "trade" in t or "exchange" in t:
        return "trading"
    if "points" in t or "campaign" in t or "mission" in t:
        return "top"
    return "non_trading"


def extract_airdrop_info(text: str):
    """
    Smartly extract airdrop info from messy post text.
    Finds title, link, description, and category.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Extract first link
    link_match = re.search(r'(https?://\S+)', text)
    link = link_match.group(1) if link_match else "N/A"

    # Detect possible project name
    title = "Untitled"
    for line in lines:
        if any(word in line.lower() for word in ["project", "airdrop", "campaign", "testnet"]):
            title = line.split(":", 1)[-1].strip() if ":" in line else line
            break
    if title == "Untitled" and lines:
        title = lines[0][:50]

    description = "\n".join(lines)
    category = detect_category(text)
    return title, link, description, category


def is_airdrop_post(text: str) -> bool:
    """Detect if a post likely contains a real airdrop, not just updates/news."""
    text = text.lower()
    good_keywords = [
        "airdrop", "reward", "campaign", "claim", "testnet",
        "mission", "task", "points", "join", "quest", "earn"
    ]
    bad_keywords = [
        "update", "news", "maintenance", "announcement",
        "winner", "result", "ended", "phase", "delay", "extension"
    ]

    if any(word in text for word in good_keywords) and not any(word in text for word in bad_keywords):
        return True
    return False

# =============================
# COMMAND HANDLERS
# =============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚀 Top Airdrops", callback_data="top")],
        [InlineKeyboardButton("🧪 Testnet", callback_data="testnet")],
        [InlineKeyboardButton("🎨 NFT / GameFi", callback_data="nft")],
        [InlineKeyboardButton("💰 Trading Required", callback_data="trading")],
        [InlineKeyboardButton("🧩 Non-Trading", callback_data="non_trading")],
        [InlineKeyboardButton("🕓 Latest", callback_data="latest")]
    ]
    await update.message.reply_text(
        "👋 *Welcome to Airdrop Sage Bot!*\n\nSelect a category below 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data if query.data != "latest" else None

    data = get_airdrops(category)
    if not data:
        await query.edit_message_text("⚠️ No airdrops found yet.")
        return

    msg = f"📋 *{category.capitalize() if category else 'Latest'} Airdrops:*\n\n"
    for title, link, desc in data[:10]:
        msg += f"• [{title}]({link})\n_{desc[:150]}..._\n\n"
    await query.edit_message_text(msg, parse_mode="Markdown", disable_web_page_preview=True)

# =============================
# CHANNEL AUTO FETCH
# =============================
async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when a message is posted in your channel."""
    post = update.channel_post
    if not post or post.chat.id != CHANNEL_ID:
        return

    text = post.text or post.caption
    if not text:
        return

    # ✅ Skip updates / announcements
    if not is_airdrop_post(text):
        print("ℹ️ Skipped non-airdrop message.")
        return

    title, link, desc, cat = extract_airdrop_info(text)
    add_airdrop(title, link, desc, cat)
    print(f"✅ Auto-saved from channel: {title} ({cat})")

# =============================
# FORWARDED MESSAGES (ADMIN)
# =============================
async def forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admins can forward posts to bot to save them."""
    user = update.effective_user
    if not is_admin(user.id):
        return

    msg = update.message.text or update.message.caption
    if not msg:
        return

    title, link, desc, cat = extract_airdrop_info(msg)
    add_airdrop(title, link, desc, cat)
    await update.message.reply_text(f"✅ Airdrop '{title}' added under {cat} category.")

# =============================
# MAIN APP
# =============================
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post))
    app.add_handler(MessageHandler(filters.FORWARDED & filters.TEXT, forwarded_message))

    print("🤖 Airdrop Sage Bot is running and monitoring channel...")
    app.run_polling()

if __name__ == "__main__":
    main()
