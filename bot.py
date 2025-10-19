import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from keep_alive import keep_alive

BOT_TOKEN = os.getenv("BOT_TOKEN")  # make sure this is set in Render

# === START COMMAND ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👤 Profile", callback_data='profile')],
        [InlineKeyboardButton("🎁 Airdrops", callback_data='airdrops')],
        [InlineKeyboardButton("💰 Wallet", callback_data='wallet')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Welcome {update.effective_user.first_name}!\n\n"
        "Use the menu below to navigate:",
        reply_markup=reply_markup
    )

# === CALLBACK HANDLER ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == 'profile':
        await query.edit_message_text("👤 Your Profile Details ...")
    elif choice == 'airdrops':
        await query.edit_message_text("🎁 Available Airdrops ...")
    elif choice == 'wallet':
        await query.edit_message_text("💰 Your Wallet Info ...")

# === MAIN ===
def main():
    keep_alive()  # runs Flask in background
    print("Starting bot polling...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
