# wallet.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    filters,
)
import json
import os

# File to store wallet data persistently
WALLETS_FILE = "wallets.json"

# States for ConversationHandler
SELECT_BLOCKCHAIN, ENTER_ADDRESS = range(2)

# Load and save wallet data
def load_wallets():
    if os.path.exists(WALLETS_FILE):
        with open(WALLETS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_wallets(wallets):
    with open(WALLETS_FILE, "w") as f:
        json.dump(wallets, f, indent=2)

wallets = load_wallets()

# -------------------------------
# Telegram bot handlers
# -------------------------------

async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main wallet menu with buttons."""
    keyboard = [
        [InlineKeyboardButton("➕ Add Wallet", callback_data="add_wallet")],
        [InlineKeyboardButton("💰 View Balances", callback_data="view_balance")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🪙 *Wallet Manager*", parse_mode="Markdown", reply_markup=reply_markup)

async def wallet_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main wallet menu selections."""
    query = update.callback_query
    await query.answer()

    if query.data == "add_wallet":
        keyboard = [
            [InlineKeyboardButton("Ethereum", callback_data="chain_eth")],
            [InlineKeyboardButton("Polygon", callback_data="chain_poly")],
            [InlineKeyboardButton("BSC", callback_data="chain_bsc")],
        ]
        await query.edit_message_text("Select blockchain:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_BLOCKCHAIN

    elif query.data == "view_balance":
        user_id = str(query.from_user.id)
        user_wallets = wallets.get(user_id, [])
        if not user_wallets:
            await query.edit_message_text("❌ No wallets added yet.")
        else:
            msg = "💰 *Your Wallets:*\n"
            for w in user_wallets:
                msg += f"🔗 {w['blockchain']}: `{w['address']}`\n"
            await query.edit_message_text(msg, parse_mode="Markdown")
        return ConversationHandler.END

async def blockchain_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for wallet address after blockchain selection."""
    query = update.callback_query
    await query.answer()
    blockchain = query.data.replace("chain_", "").capitalize()
    context.user_data["selected_blockchain"] = blockchain
    await query.edit_message_text(f"Enter your *{blockchain}* wallet address:", parse_mode="Markdown")
    return ENTER_ADDRESS

async def address_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save wallet address for user."""
    user_id = str(update.message.from_user.id)
    address = update.message.text.strip()
    blockchain = context.user_data.get("selected_blockchain", "Unknown")

    wallets.setdefault(user_id, []).append({
        "blockchain": blockchain,
        "address": address
    })
    save_wallets(wallets)

    await update.message.reply_text(
        f"✅ Wallet saved!\n\n*Blockchain:* {blockchain}\n*Address:* `{address}`",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

# -------------------------------
# Webhook integration (Alchemy)
# -------------------------------

def notify_users_about_tx(tx_event):
    """
    Called by keep_alive.py when a transaction webhook is received.
    Returns list of (user_id, message) tuples to notify via Telegram.
    """
    matches = []
    try:
        from_address = tx_event.get("fromAddress")
        to_address = tx_event.get("toAddress")
        value = tx_event.get("value")
        tx_hash = tx_event.get("hash", "")
        blockchain = tx_event.get("network", "Unknown")

        for user_id, user_wallets in wallets.items():
            for w in user_wallets:
                if w["address"].lower() in (from_address.lower(), to_address.lower()):
                    msg = (
                        f"🔔 *New Transaction on {w['blockchain']}!*\n"
                        f"💸 From: `{from_address}`\n"
                        f"➡️ To: `{to_address}`\n"
                        f"💰 Value: `{value}`\n"
                        f"🔗 [View Transaction](https://etherscan.io/tx/{tx_hash})"
                    )
                    matches.append((user_id, msg))
    except Exception as e:
        print("Error in notify_users_about_tx:", e)

    return matches

# -------------------------------
# Register handlers for bot.py
# -------------------------------
def register_wallet_handlers(application):
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(wallet_menu_callback, pattern="^(add_wallet|view_balance)$")],
        states={
            SELECT_BLOCKCHAIN: [CallbackQueryHandler(blockchain_selected, pattern="^chain_")],
            ENTER_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address_entered)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("wallet", wallet_menu))
    application.add_handler(conv_handler)
