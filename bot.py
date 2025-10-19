# bot.py
import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
# REMOVED THE EXTRA ) HERE
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
    await update.message.reply_text('Hello!')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Use /start to begin.")

# --- Main entry ---
def main():
    keep_alive()  # start Flask keep-alive server

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Core commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Register handlers from other modules
    airdrop.register_airdrop_handlers(app)
    wallet.register_wallet_handlers(app)
    # Admin handlers don't have register_ function; skip for now

    logger.info("🚀 Bot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()  # Just call your main() function