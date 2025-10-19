# admin.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import database

# Only very small helpers here; main heavy lifting in bot.py via callbacks
async def admin_panel(query):
    text = "🛠️ *Admin Panel*\n\nChoose an action:"
    buttons = [
        [InlineKeyboardButton("📋 List Users", callback_data="admin_list_users")],
        [InlineKeyboardButton("➕ Add Airdrop (manual)", callback_data="admin_add_airdrop_manual")],
        [InlineKeyboardButton("🧾 List Airdrops", callback_data="admin_list_airdrops")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def list_users(query):
    users = database.list_users()
    text = "👥 Users:\n\n" + "\n".join(str(u) for u in users[:200])
    await query.edit_message_text(text)
