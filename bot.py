# bot.py
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request, jsonify
from threading import Thread
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

# Flask app for webhooks
flask_app = Flask(__name__)
bot_application = None

@flask_app.route('/')
def home():
    return "Bot is alive! 🤖"

@flask_app.route('/webhook/alchemy/eth', methods=['POST'])
async def alchemy_webhook_eth():
    """Handle Alchemy webhook for Ethereum"""
    try:
        data = request.json
        logger.info(f"Received ETH webhook")
        if bot_application:
            await wallet.handle_webhook_notification(bot_application, data)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logger.error(f"Error processing ETH webhook: {e}")
        return jsonify({'error': str(e)}), 500

@flask_app.route('/webhook/alchemy/arbitrum', methods=['POST'])
async def alchemy_webhook_arbitrum():
    """Handle Alchemy webhook for Arbitrum"""
    try:
        data = request.json
        logger.info(f"Received Arbitrum webhook")
        if bot_application:
            await wallet.handle_webhook_notification(bot_application, data)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logger.error(f"Error processing Arbitrum webhook: {e}")
        return jsonify({'error': str(e)}), 500

@flask_app.route('/webhook/alchemy/base', methods=['POST'])
async def alchemy_webhook_base():
    """Handle Alchemy webhook for Base"""
    try:
        data = request.json
        logger.info(f"Received Base webhook")
        if bot_application:
            await wallet.handle_webhook_notification(bot_application, data)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logger.error(f"Error processing Base webhook: {e}")
        return jsonify({'error': str(e)}), 500

def run_flask():
    port = int(os.getenv('PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Start Flask server in background thread"""
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    logger.info("🌐 Flask webhook server started")# bot.py
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

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_text = (
        "💰 *Your Wallet*\n\n"
        "Balance: 0\n"
        "Wallet Address: Not connected\n\n"
        "Use /connect\\_wallet to link your wallet"
    )
    
    back_button = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
    back_markup = InlineKeyboardMarkup(back_button)
    
    await update.message.reply_text(wallet_text, parse_mode='Markdown', reply_markup=back_markup)

async def connect_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """This is now handled by wallet.py conversation handler"""
    pass  # Placeholder, actual implementation is in wallet.py

async def airdrops_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    airdrops_text = (
        "🎁 *Available Airdrops*\n\n"
        "No active airdrops at the moment\\.\n"
        "Check back later\\!"
    )
    
    back_button = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
    back_markup = InlineKeyboardMarkup(back_button)
    
    await update.message.reply_text(airdrops_text, parse_mode='MarkdownV2', reply_markup=back_markup)

# --- Callback handler for inline buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Add back button for navigation
    back_button = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
    back_markup = InlineKeyboardMarkup(back_button)
    
    try:
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
            await query.edit_message_text(profile_text, parse_mode='Markdown', reply_markup=back_markup)
        
        elif query.data == 'wallet':
            wallet_text = (
                "💰 *Your Wallet*\n\n"
                "Balance: 0\n"
                "Wallet Address: Not connected\n\n"
                "Use /connect\\_wallet to link your wallet"
            )
            await query.edit_message_text(wallet_text, parse_mode='Markdown', reply_markup=back_markup)
        
        elif query.data == 'airdrops':
            airdrops_text = (
                "🎁 *Available Airdrops*\n\n"
                "No active airdrops at the moment\\.\n"
                "Check back later\\!"
            )
            await query.edit_message_text(airdrops_text, parse_mode='MarkdownV2', reply_markup=back_markup)
        
        elif query.data == 'help':
            help_text = (
                "ℹ️ *Bot Commands:*\n\n"
                "/start - Show main menu\n"
                "/profile - View your profile\n"
                "/wallet - Manage your wallet\n"
                "/airdrops - View available airdrops\n"
                "/help - Show this help message"
            )
            await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=back_markup)
        
        elif query.data == 'back_to_menu':
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
            await query.edit_message_text(welcome_text, reply_markup=reply_markup)
    
    except Exception as e:
        logger.error(f"Error in button callback: {e}")
        await query.answer("⚠️ An error occurred. Please try /start again.", show_alert=True)

# --- Error handler ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Notify user about the error
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred. Please try again later."
        )

# --- Main entry ---
def main():
    global bot_application
    
    keep_alive()  # start Flask keep-alive server

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_application = app  # Store reference for webhooks

    # Core commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("airdrops", airdrops_command))
    
    # Callback handler for inline buttons
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Error handler
    app.add_error_handler(error_handler)

    # Register handlers from other modules (if they exist)
    try:
        wallet.register_wallet_handlers(app)
        logger.info("✅ Wallet handlers registered")
    except Exception as e:
        logger.error(f"⚠️ Failed to register wallet handlers: {e}")
        
    try:
        airdrop.register_airdrop_handlers(app)
        logger.info("✅ Airdrop handlers registered")
    except AttributeError:
        logger.warning("⚠️ airdrop.register_airdrop_handlers not found")
    except Exception as e:
        logger.error(f"⚠️ Failed to register airdrop handlers: {e}")

    logger.info("🚀 Bot is starting...")
    logger.info("📡 Webhook endpoints ready:")
    logger.info("   - /webhook/alchemy/eth")
    logger.info("   - /webhook/alchemy/arbitrum")
    logger.info("   - /webhook/alchemy/base")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()