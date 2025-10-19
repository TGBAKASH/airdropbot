from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import os

# In-memory storage for airdrops
airdrop_list = []

ADMIN_ID = int(os.getenv("ADMIN_ID", "1377923423"))

# ------------------------------------------------------------------
# Handlers setup function (this is what bot.py imports)
# ------------------------------------------------------------------
def register_airdrop_handlers(app):

    # ✅ Command: /airdrops — opens menu
    async def airdrop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("📩 Forward Airdrop Post", callback_data="forward_airdrop")],
            [InlineKeyboardButton("➕ Add Manual Airdrop", callback_data="add_manual_airdrop")],
            [InlineKeyboardButton("📋 View All Airdrops", callback_data="list_airdrops")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("💰 *Airdrop Management Menu:*", 
                                        reply_markup=reply_markup, parse_mode="Markdown")

    # ✅ Handle button presses
    async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == "forward_airdrop":
            await query.edit_message_text(
                "📩 Forward the airdrop post you want to add."
            )
            context.user_data["awaiting_forward"] = True

        elif query.data == "add_manual_airdrop":
            if query.from_user.id != ADMIN_ID:
                await query.edit_message_text("❌ Only admin can add manual airdrops.")
                return
            await query.edit_message_text("✍️ Send me the *airdrop name* to add manually.", parse_mode="Markdown")
            context.user_data["adding_manual"] = "name"

        elif query.data == "list_airdrops":
            if not airdrop_list:
                await query.edit_message_text("📭 No airdrops added yet.")
            else:
                msg = "📋 *Current Airdrops:*\n\n"
                for i, a in enumerate(airdrop_list, start=1):
                    msg += f"{i}. {a['name']} — {a.get('link', 'No link')}\n"
                await query.edit_message_text(msg, parse_mode="Markdown")

    # ✅ Handle messages after button press
    async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data

        # Forwarded airdrop post
        if user_data.get("awaiting_forward"):
            fwd = update.message
            if fwd.forward_from_chat:
                chat_title = fwd.forward_from_chat.title or "Unnamed Channel"
                link = f"https://t.me/{fwd.forward_from_chat.username}" if fwd.forward_from_chat.username else "No link"
                airdrop_list.append({"name": chat_title, "link": link})
                await update.message.reply_text(f"✅ Added airdrop from *{chat_title}*", parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Please forward a valid channel post.")
            user_data["awaiting_forward"] = False

        # Manual airdrop creation
        elif user_data.get("adding_manual") == "name":
            user_data["manual_name"] = update.message.text
            user_data["adding_manual"] = "link"
            await update.message.reply_text("🔗 Now send the *airdrop link*.", parse_mode="Markdown")

        elif user_data.get("adding_manual") == "link":
            link = update.message.text
            name = user_data.get("manual_name", "Unnamed")
            airdrop_list.append({"name": name, "link": link})
            await update.message.reply_text(f"✅ Airdrop '{name}' added successfully!")
            user_data.clear()

    # ------------------------------------------------------------------
    # Register handlers to the main app
    # ------------------------------------------------------------------
    app.add_handler(CommandHandler("airdrops", airdrop_menu))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))
