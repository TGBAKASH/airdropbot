# bot.py
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from keep_alive import keep_alive
import airdrop
import wallet
import admin

# --- Logging setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN not set in environment variables!")

# --- Basic commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👤 Profile", callback_data='profile')],
        [InlineKeyboardButton("💰 Wallet", callback_data='wallet')],
        [InlineKeyboardButton("🎁 Airdrops", callback_data='airdrops')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🎉 Welcome to the Airdrop Bot!\n\n"
        "Choose an option below to get started:"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ *Bot Commands:*\n\n"
        "/start - Show main menu\n"
        "/profile - View your profile\n"
        "/wallet - Manage your wallet\n"
        "/airdrops - View available airdrops\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    profile_text = (
        f"👤 *Your Profile*\n\n"
        f"Name: {user.first_name}\n"
        f"Username: @{user.username if user.username else 'Not set'}\n"
        f"User ID: `{user.id}`\n"
        f"Points: 0 🪙\n"
        f"Referrals: 0"
    )
    await update.message.reply_text(profile_text, parse_mode='Markdown')

# --- Callback handler for inline buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'profile':
        user = query.from_user
        profile_text = (
            f"👤 *Your Profile*\n\n"
            f"Name: {user.first_name}\n"
            f"Username: @{user.username if user.username else 'Not set'}\n"
            f"User ID: `{user.id}`\n"
            f"Points: 0 🪙\n"
            f"Referrals: 0"
        )
        await query.edit_message_text(profile_text, parse_mode='Markdown')
    
    elif query.data == 'wallet':
        wallet_text = (
            "💰 *Your Wallet*\n\n"
            "Balance: 0 SAGE\n"
            "Wallet Address: Not connected\n\n"
            "Use /connect_wallet to link your wallet"
        )
        await query.edit_message_text(wallet_text, parse_mode='Markdown')
    
    elif query.data == 'airdrops':
        airdrops_text = (
            "🎁 *Available Airdrops*\n\n"
            "No active airdrops at the moment.\n"
            "Check back later!"
        )
        await query.edit_message_text(airdrops_text, parse_mode='Markdown')
    
    elif query.data == 'help':
        help_text = (
            "ℹ️ *Bot Commands:*\n\n"
            "/start - Show main menu\n"
            "/profile - View your profile\n"
            "/wallet - Manage your wallet\n"
            "/airdrops - View available airdrops\n"
            "/help - Show this help message"
        )
        await query.edit_message_text(help_text, parse_mode='Markdown')

# --- Main entry ---
def main():
    keep_alive()  # start Flask keep-alive server

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Core commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile_command))
    
    # Callback handler for inline buttons
    app.add_handler(CallbackQueryHandler(button_callback))

    # Register handlers from other modules (if they exist)
    try:
        airdrop.register_airdrop_handlers(app)
    except AttributeError:
        logger.warning("⚠️ airdrop.register_airdrop_handlers not found")
    
    try:
        wallet.register_wallet_handlers(app)
    except AttributeError:
        logger.warning("⚠️ wallet.register_wallet_handlers not found")

    logger.info("🚀 Bot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()