# bot.py
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import database
import airdrop
import wallet
import admin
from keep_alive import keep_alive

# Admin IDs: includes provided admin id and optional ENV overrides
ADMIN_IDS = set([1377923423])
env_admins = os.getenv("ADMIN_IDS", "")
for x in env_admins.split(","):
    if x.strip().isdigit():
        ADMIN_IDS.add(int(x.strip()))

BOT_TOKEN = os.getenv("BOT_TOKEN")

# init DB
database.init_db()

def main_menu_kb(is_admin=False):
    kb = [
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🎁 Airdrops", callback_data="airdrops")],
        [InlineKeyboardButton("💼 Wallet", callback_data="wallet_menu")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    if is_admin:
        kb.insert(3, [InlineKeyboardButton("⚙️ Admin", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    database.ensure_user(user.id, user.username or "", user.first_name or "")
    is_admin = user.id in ADMIN_IDS
    await update.message.reply_text(
        "🌟 Welcome to Sage Airdrops Bot — use the menu below.",
        reply_markup=main_menu_kb(is_admin)
    )

# Button handler central
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # --- Main navigation ---
    if data == "airdrops":
        await airdrop.show_airdrops(query, user_id)
        return
    if data == "wallet_menu":
        await wallet.wallet_menu(query, user_id)
        return
    if data == "profile":
        await query.edit_message_text(f"👤 Name: {query.from_user.first_name}\n🆔 ID: `{query.from_user.id}`", parse_mode="Markdown")
        return
    if data == "help":
        await query.edit_message_text("Use the buttons. Forward a message to add an airdrop. Use Wallet → Add Wallet to save addresses.")
        return

    # --- Admin panel ---
    if data == "admin_panel":
        if user_id not in ADMIN_IDS:
            await query.edit_message_text("❌ Admins only.")
            return
        await admin.admin_panel(query)
        return
    if data == "admin_list_users":
        if user_id not in ADMIN_IDS:
            await query.edit_message_text("❌ Admins only.")
            return
        await admin.list_users(query)
        return
    if data == "admin_add_airdrop_manual":
        if user_id not in ADMIN_IDS:
            await query.edit_message_text("❌ Admins only.")
            return
        # start manual airdrop flow in user_data
        context.user_data['airdrop_add_flow'] = {"step": 1, "data": {}}
        await query.edit_message_text("📝 *Add Airdrop (manual)*\nStep 1/3 — Send the *title* of the airdrop.", parse_mode="Markdown")
        return
    if data == "admin_list_airdrops":
        if user_id not in ADMIN_IDS:
            await query.edit_message_text("❌ Admins only.")
            return
        # reuse airdrop listing for admins
        await airdrop.show_airdrops(query, user_id)
        return

    # Airdrop delete (callback format: airdrop_remove_{id})
    if data.startswith("airdrop_remove_"):
        if user_id not in ADMIN_IDS:
            await query.edit_message_text("❌ Admins only.")
            return
        try:
            aid = int(data.split("_")[-1])
            database.delete_airdrop(aid)
            await query.edit_message_text("✅ Airdrop removed.")
        except Exception:
            await query.edit_message_text("Failed to remove.")
        return

    # --- Wallet add flow ---
    if data == "add_wallet":
        # open pick chain keyboard
        await wallet.pick_chain_for_add(query)
        return
    if data.startswith("addwallet_chain_"):
        # user picked chain; set user_data flag and ask for address
        chain = data.replace("addwallet_chain_", "")
        context.user_data['awaiting_wallet_address'] = True
        context.user_data['add_wallet_chain'] = chain
        await query.edit_message_text(f"✏️ You selected *{chain}*. Now send the wallet address (0x...) to save.", parse_mode="Markdown")
        return
    if data == "view_balances":
        # call wallet to build and send balances; use Bot instance
        bot = context.application.bot
        await query.edit_message_text("⏳ Fetching balances...")
        await wallet.send_balances_for_user(bot, user_id)
        return

    if data == "wallet_menu":
        await wallet.wallet_menu(query, user_id)
        return

    # back navigation
    if data == "main_menu":
        await query.edit_message_text("🌟 Main menu", reply_markup=main_menu_kb(user_id in ADMIN_IDS))
        return

    # fallback
    await query.edit_message_text("Unknown action.")

# Message handler central: handles forwarding saves, airdrop manual flow, and wallet address flow
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.message
    uid = update.effective_user.id
    # ensure user in DB
    database.ensure_user(uid, update.effective_user.username or "", update.effective_user.first_name or "")

    # 1) If admin is in manual airdrop flow
    flow = context.user_data.get('airdrop_add_flow')
    if flow:
        step = flow.get('step', 1)
        if step == 1:
            # treat this message as title
            flow['data']['title'] = m.text or ""
            flow['step'] = 2
            context.user_data['airdrop_add_flow'] = flow
            await m.reply_text("Step 2/3 — Send the *description* (text).", parse_mode="Markdown")
            return
        elif step == 2:
            flow['data']['content'] = m.text or ""
            flow['step'] = 3
            context.user_data['airdrop_add_flow'] = flow
            await m.reply_text("Step 3/3 — Send an optional URL or send `skip` to continue.", parse_mode="Markdown")
            return
        elif step == 3:
            url_text = (m.text or "").strip()
            if url_text.lower() == "skip":
                url_text = ""
            flow['data']['url'] = url_text
            # save to DB
            data = flow['data']
            database.add_airdrop(data.get('title',"No Title"), data.get('content',""), data.get('url',""), uid)
            context.user_data.pop('airdrop_add_flow', None)
            await m.reply_text("✅ Airdrop added.")
            return

    # 2) If user is in wallet add flow and sending address
    if context.user_data.get('awaiting_wallet_address'):
        await wallet.handle_address_message(update, context)
        return

    # 3) If message is forwarded, save to airdrops automatically
    if m.forward_from_chat or m.forward_from:
        title = ""
        if m.forward_from_chat and getattr(m.forward_from_chat, "title", None):
            title = f"Forward from {m.forward_from_chat.title}"
        elif m.forward_from:
            title = f"Forward from {m.forward_from.username or m.forward_from.first_name or 'user'}"
        content = m.text or m.caption or ""
        # attempt to build a t.me link if forward_from_chat has username and message id
        url = ""
        if getattr(m.forward_from_chat, "username", None) and m.message_id:
            url = f"https://t.me/{m.forward_from_chat.username}/{m.message_id}"
        database.add_airdrop(title or "Forwarded post", content, url, uid)
        await m.reply_text("✅ Forward saved as an airdrop.")
        return

    # 4) default help reply
    await m.reply_text("Use the main menu. Forward a public post to add an airdrop or go to Wallet -> Add Wallet to save an address.")

# Admin broadcast utility via /broadcast <message>
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("Admins only.")
        return
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    users = database.list_users()
    bot = context.application.bot
    sent = 0
    for u in users:
        try:
            bot.send_message(chat_id=u, text=text)
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"Broadcast sent to {sent} users.")

def main():
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list_airdrops", airdrop.cmd_list_airdrops))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))

    # callback buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    # message handler (for forwards, flows, and addresses)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))

    print("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
