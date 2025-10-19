# airdrop.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import database

# UI helpers
async def show_airdrops(query, user_id:int):
    rows = database.list_airdrops(20)
    if not rows:
        await query.edit_message_text("No airdrops yet. Admins can forward posts to add or use Admin → Add Airdrop.")
        return

    text = "🎁 *Airdrops (latest)*\n\n"
    buttons = []
    for r in rows:
        aid, title, content, url, added_by, created_at = r
        title_short = (title[:60] + "...") if len(title) > 60 else title
        text += f"• *{title_short}*  `id:{aid}`\n"
        if content:
            c = (content[:140] + "...") if len(content) > 140 else content
            text += f"_{c}_\n"
        if url:
            text += f"[link]({url})\n"
        text += "\n"
        # delete button for admin will be shown in main button handler
        buttons.append([InlineKeyboardButton(f"Remove {aid}", callback_data=f"airdrop_remove_{aid}")])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def cmd_list_airdrops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = database.list_airdrops(50)
    if not rows:
        await update.message.reply_text("No airdrops.")
        return
    text = "🎁 Airdrops:\n\n"
    for aid, title, content, url, added_by, created_at in rows:
        text += f"{aid}. {title} — added_by:{added_by} — {created_at}\n"
        if url:
            text += f"{url}\n"
    await update.message.reply_text(text)
