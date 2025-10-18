import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler, ChatMemberHandler
)

# -----------------------------
# Setup & Configuration
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Add this in Render env vars
CHANNEL_ID = -1001974850367         # Replace with your Sage Airdrops channel ID
ADMIN_IDS = [1377923423]  # Replace with your Telegram user IDs

DB_FILE = "airdrops.db"

# -----------------------------
# Database Setup
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS airdrops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            link TEXT,
            description TEXT,
            date_added TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_airdrop(name, category, link, description):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO airdrops (name, category, link, description, date_added)
        VALUES (?, ?, ?, ?, ?)
    """, (name, category, link, description, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_airdrops(category=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if category:
        cursor.execute("SELECT name, link, description FROM airdrops WHERE category=?", (category,))
    else:
        cursor.execute("SELECT name, link, description FROM airdrops")
    rows = cursor.fetchall()
    conn.close()
    return rows

# -----------------------------
# Admin Authentication
# -----------------------------
def is_admin(user_id):
    return user_id in ADMIN_IDS

# -----------------------------
# Handlers
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚀 Top Airdrops", callback_data="top")],
        [InlineKeyboardButton("🧪 Testnet", callback_data="testnet")],
        [InlineKeyboardButton("🎨 NFT / GameFi", callback_data="nft")],
        [InlineKeyboardButton("💰 Trading Required", callback_data="trading")],
        [InlineKeyboardButton("🧩 Non-Trading", callback_data="non_trading")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to **Airdrop Sage Bot!**\nSelect a category below 👇",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data

    items = get_airdrops(category)
    if not items:
        await query.edit_message_text(text="No airdrops available yet.")
        return

    msg = f"📋 *{category.capitalize()} Airdrops:*\n\n"
    for name, link, desc in items:
        msg += f"• [{name}]({link})\n_{desc}_\n\n"
    await query.edit_message_text(text=msg, parse_mode="Markdown", disable_web_page_preview=True)

# -----------------------------
# Admin Commands
# -----------------------------
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized.")
        return

    try:
        name = context.args[0]
        category = context.args[1]
        link = context.args[2]
        description = " ".join(context.args[3:])
        add_airdrop(name, category, link, description)
        await update.message.reply_text(f"✅ Added {name} to {category} category.")
    except Exception as e:
        await update.message.reply_text("Usage:\n`/add <name> <category> <link> <description>`", parse_mode="Markdown")

# -----------------------------
# Channel Listener (for Sage Airdrops)
# -----------------------------
async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat.id == CHANNEL_ID:
        text = update.channel_post.text or ""
        if "http" in text:
            parts = text.split("\n")
            name = parts[0][:50]
            link = [p for p in parts if "http" in p][0]
            desc = "\n".join(parts[1:])
            add_airdrop(name, "top", link, desc)
            print(f"✅ Auto-saved airdrop: {name}")

# -----------------------------
# Main Function
# -----------------------------
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post))

    print("🤖 Airdrop Sage Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
