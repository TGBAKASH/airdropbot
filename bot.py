import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import os
import requests

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Example start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Bot is now running!")

# Example function (like your TXN notifications or any webhook processing)
async def notify_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # Example: handle webhook text
    if "txn" in text.lower():
        await update.message.reply_text("💸 Transaction notification received!")
    else:
        await update.message.reply_text("✅ Message received!")

def main():
    # Create the bot application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, notify_transaction))

    # Start the bot (polling)
    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
