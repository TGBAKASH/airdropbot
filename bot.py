import os
from telegram.ext import ApplicationBuilder
from keep_alive import keep_alive
from airdrop import register_airdrop_handlers
from wallet import register_wallet_handlers
from telegram.ext import CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
from keep_alive import start_keep_alive


# Optional admin panel if you later add it
# from admin import register_admin_handlers  

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1377923423"))

# ------------------------------
# Basic commands
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Welcome to Airdrop & Wallet Bot!\n\n"
        "Use the menu buttons below to explore available features."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 *Available Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this help message"
    )

# ------------------------------
# Main function
# ------------------------------

def main():
    print("🚀 Starting Telegram Bot...")
    keep_alive()  # keeps your bot alive on Render

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Basic commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Airdrop features
    register_airdrop_handlers(app)

    # Wallet features
    register_wallet_handlers(app)

    # Optional admin panel later
    # register_admin_handlers(app)

    print("🤖 Bot is running... Ready to receive updates!")
    app.run_polling()

if __name__ == "__main__":
    start_keep_alive()
    app.run_polling()
