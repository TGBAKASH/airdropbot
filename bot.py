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
CHANNEL_ID = -1001974850367
ADMIN_IDS = [1377923423]
DB_FILE = "airdrops.db"

# =============================
# DATABASE FUNCTIONS
# =============================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Airdrops table
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
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            wallet_address TEXT,
            wallet_chain TEXT,
            joined_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_user(user):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at)
        VALUES (?, ?, ?, ?)
    """, (user.id, user.username, user.first_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row


def update_wallet(user_id, address, chain):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        UPDATE users SET wallet_address=?, wallet_chain=? WHERE user_id=?
    """, (address, chain, user_id))
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
    t = text.lower()
    if "testnet" in t:
        if "l1" in t:
            return "testnet_l1"
        elif "l2" in t:
            return "testnet_l2"
        else:
            return "testnet_other"
    if "mainnet" in t or "launch" in t:
        if "trade" in t:
            return "mainnet_trading"
        else:
            return "mainnet_non_trading"
    if "nft" in t or "game" in t:
        return "nft"
    return "general"


def extract_airdrop_info(text: str):
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    link_match = re.search(r'(https?://\S+)', text)
    link = link_match.group(1) if link_match else "N/A"

    title = "Untitled"
    for line in lines:
        if any(word in line.lower() for word in ["project", "airdrop", "campaign", "testnet", "mainnet"]):
            title = line.split(":", 1)[-1].strip() if ":" in line else line
            break
    if title == "Untitled" and lines:
        title = lines[0][:50]

    description = "\n".join(lines)
    category = detect_category(text)
    return title, link, description, category


def is_airdrop_post(text: str) -> bool:
    text = text.lower()
    good_keywords = [
        "airdrop", "reward", "campaign", "claim", "testnet",
        "mission", "task", "points", "join", "quest", "earn"
    ]
    bad_keywords = [
        "update", "news", "maintenance", "announcement",
        "winner", "result", "ended", "phase", "delay", "extension"
    ]
    return any(word in text for word in good_keywords) and not any(word in text for word in bad_keywords)

# =============================
# BOT HANDLERS
# =============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user)
    keyboard = [
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🎁 Airdrops", callback_data="airdrops")],
        [InlineKeyboardButton("💼 Wallet", callback_data="wallet")]
    ]
    await update.message.reply_text(
        f"👋 Welcome *{user.first_name}*!\n\nUse the menu below to navigate:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "profile":
        user = get_user(query.from_user.id)
        if user:
            _, username, first_name, wallet, chain, joined = user
            wallet_info = f"{wallet or '❌ Not Linked'} ({chain or 'N/A'})"
            msg = (
                f"👤 *Your Profile*\n\n"
                f"Name: {first_name}\n"
                f"Username: @{username}\n"
                f"ID: `{query.from_user.id}`\n"
                f"Wallet: {wallet_info}\n"
                f"Joined: {joined}"
            )
        else:
            msg = "⚠️ No profile found. Type /start again."
        await query.edit_message_text(msg, parse_mode="Markdown")

    elif choice == "airdrops":
        keyboard = [
            [InlineKeyboardButton("🧪 Testnet (L1)", callback_data="testnet_l1")],
            [InlineKeyboardButton("🧪 Testnet (L2)", callback_data="testnet_l2")],
            [InlineKeyboardButton("🧪 Testnet (Others)", callback_data="testnet_other")],
            [InlineKeyboardButton("💰 Mainnet (Trading)", callback_data="mainnet_trading")],
            [InlineKeyboardButton("🧩 Mainnet (Non-Trading)", callback_data="mainnet_non_trading")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
        ]
        await query.edit_message_text("🎁 *Select Airdrop Type:*", parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    elif choice == "wallet":
        keyboard = [
            [InlineKeyboardButton("🔗 Link Wallet", callback_data="link_wallet")],
            [InlineKeyboardButton("💰 Portfolio", callback_data="portfolio")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
        ]
        await query.edit_message_text("💼 *Wallet Menu:*", parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    elif choice.startswith("testnet") or choice.startswith("mainnet"):
        data = get_airdrops(choice)
        msg = f"📋 *{choice.replace('_', ' ').title()} Airdrops:*\n\n"
        if not data:
            msg += "No airdrops yet."
        else:
            for title, link, desc in data[:10]:
                msg += f"• [{title}]({link})\n_{desc[:100]}..._\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", disable_web_page_preview=True)

    elif choice == "link_wallet":
        await query.edit_message_text("🔗 Send your wallet chain (e.g. Ethereum, Solana, BSC):")
        context.user_data["awaiting_chain"] = True

    elif choice == "portfolio":
        await query.edit_message_text("💰 Portfolio tracking coming soon (with live balances).")

    elif choice == "back_main":
        keyboard = [
            [InlineKeyboardButton("👤 Profile", callback_data="profile")],
            [InlineKeyboardButton("🎁 Airdrops", callback_data="airdrops")],
            [InlineKeyboardButton("💼 Wallet", callback_data="wallet")]
        ]
        await query.edit_message_text("🏠 *Main Menu:*", parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_wallet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # Step 1: Chain input
    if context.user_data.get("awaiting_chain"):
        context.user_data["wallet_chain"] = text
        context.user_data["awaiting_chain"] = False
        context.user_data["awaiting_address"] = True
        await update.message.reply_text(f"✅ Chain set to *{text}*.\nNow send your wallet address:", parse_mode="Markdown")
        return

    # Step 2: Wallet address input
    if context.user_data.get("awaiting_address"):
        chain = context.user_data.get("wallet_chain", "Unknown")
        update_wallet(user_id, text, chain)
        context.user_data["awaiting_address"] = False
        await update.message.reply_text("✅ Wallet linked successfully!")
        return

# =============================
# CHANNEL AUTO FETCH
# =============================
async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post or post.chat.id != CHANNEL_ID:
        return

    text = post.text or post.caption
    if not text:
        return

    if not is_airdrop_post(text):
        print("ℹ️ Skipped non-airdrop message.")
        return

    title, link, desc, cat = extract_airdrop_info(text)
    add_airdrop(title, link, desc, cat)
    print(f"✅ Auto-saved from channel: {title} ({cat})")

# =============================
# MAIN APP
# =============================
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(main_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet_input))
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post))

    print("🤖 Airdrop Sage Bot v2 is running with user profiles & wallet linking...")
    app.run_polling()

if __name__ == "__main__":
    main()
