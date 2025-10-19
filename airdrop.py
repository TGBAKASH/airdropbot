from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import os

ADMIN_ID = int(os.getenv("ADMIN_ID", "1377923423"))
airdrop_list = []


def register_airdrop_handlers(app):
    async def airdrop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("📩 Forward Airdrop Post", callback_data="forward_airdrop")],
            [InlineKeyboardButton("➕ Add Manual Airdrop", callback_data="add_manual_airdrop")],
            [InlineKeyboardButton("📋 View All Airdrops", callback_data="list_airdrops")],
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "💰 *Airdrop Management Menu:*", parse_mode="Markdown", reply_markup=markup
        )

    async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == "forward_airdrop":
            await query.edit_message_text("📩 Forward the airdrop post you want to add.")
            context.user_data["awaiting_forward"] = True

        elif query.data == "add_manual_airdrop":
            if query.from_user.id != ADMIN_ID:
                await query.edit_message_text("❌ Only admin can add manual airdrops.")
                return
            await query.edit_message_text("✍️ Send the *airdrop name*.", parse_mode="Markdown")
            context.user_data["adding_manual"] = "name"

        elif query.data == "list_airdrops":
            if not airdrop_list:
                await query.edit_message_text("📭 No airdrops added yet.")
            else:
                msg = "📋 *Airdrops List:*\n\n"
                for i, a in enumerate(airdrop_list, start=1):
                    msg += f"{i}. {a['name']} — {a.get('link', 'No link')}\n"
                await query.edit_message_text(msg, parse_mode="Markdown")

    async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        data = context.user_data

        if data.get("awaiting_forward"):
            msg = update.message
            if msg.forward_from_chat:
                chat_title = msg.forward_from_chat.title or "Unnamed Channel"
                link = (
                    f"https://t.me/{msg.forward_from_chat.username}"
                    if msg.forward_from_chat.username
                    else "No link"
                )
                airdrop_list.append({"name": chat_title, "link": link})
                await msg.reply_text(f"✅ Added airdrop from *{chat_title}*", parse_mode="Markdown")
            else:
                await msg.reply_text("❌ Please forward a valid channel post.")
            data.clear()

        elif data.get("adding_manual") == "name":
            data["manual_name"] = update.message.text
            data["adding_manual"] = "link"
            await update.message.reply_text("🔗 Now send the *airdrop link*.", parse_mode="Markdown")

        elif data.get("adding_manual") == "link":
            link = update.message.text
            name = data.get("manual_name", "Unnamed")
            airdrop_list.append({"name": name, "link": link})
            await update.message.reply_text(f"✅ Airdrop '{name}' added successfully!")
            data.clear()

    app.add_handler(CommandHandler("airdrops", airdrop_menu))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))
