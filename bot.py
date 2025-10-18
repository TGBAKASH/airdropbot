from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# === Replace this with your actual token ===
TOKEN = "8290143475:AAH0cSVWLQeoTkhXqPEe2Dn6WzH_xnMm0-M"

# === Sample data (later we’ll connect this to a real DB) ===
airdrops = {
    "top": ["Monad Testnet", "LayerZero Points", "ZetaChain"],
    "testnet": ["Monad", "Movement", "Saga Testnet"],
    "nft": ["Parallel Game", "Pixels Drop"],
    "trading": ["Binance Launchpool", "Bitget Airdrop"],
    "non_trading": ["ZetaChain", "Monad Testnet"]
}

# === /start command ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚀 Top Airdrops", callback_data="top")],
        [InlineKeyboardButton("🧪 Testnet", callback_data="testnet")],
        [InlineKeyboardButton("🎨 NFT / GameFi", callback_data="nft")],
        [InlineKeyboardButton("💰 Trading Required", callback_data="trading")],
        [InlineKeyboardButton("🧩 Non-Trading", callback_data="non_trading")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to **Airdrop Sage Bot!**\nSelect a category below 👇", parse_mode="Markdown", reply_markup=reply_markup)

# === When a user clicks a button ===
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data

    items = airdrops.get(category, [])
    if not items:
        text = "No airdrops available yet."
    else:
        text = f"📋 *{category.capitalize()} Airdrops:*\n\n" + "\n".join([f"• {name}" for name in items])
    await query.edit_message_text(text=text, parse_mode="Markdown")

# === Main ===
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    print("Bot is running... ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
