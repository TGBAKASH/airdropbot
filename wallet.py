# wallet.py
import os
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import database
from typing import List, Tuple

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_URL") or os.getenv("ALCHEMY_API_KEY") or ""
# Build chain urls (your three chains)
CHAIN_URLS = {
    "Ethereum": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
    "Arbitrum": f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
    "Base": f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
}

# ---- UI ----
async def wallet_menu(query, user_id:int):
    rows = database.get_user_wallets(user_id)
    text = "💼 *Wallet Manager*\n\n"
    if not rows:
        text += "You have no wallets. Use the button below to add one."
        buttons = [
            [InlineKeyboardButton("➕ Add Wallet", callback_data="add_wallet")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return

    for chain, addr, notif in rows:
        text += f"{chain} — `{addr}` — {'🔔' if notif else '🔕'}\n"
    buttons = [
        [InlineKeyboardButton("➕ Add Wallet", callback_data="add_wallet")],
        [InlineKeyboardButton("💰 View Balances", callback_data="view_balances")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

# Called from bot when user selected Add Wallet -> choose chain
async def pick_chain_for_add(query):
    buttons = []
    for chain in CHAIN_URLS.keys():
        buttons.append([InlineKeyboardButton(chain, callback_data=f"addwallet_chain_{chain}")])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="wallet_menu")])
    await query.edit_message_text("Select blockchain to add:", reply_markup=InlineKeyboardMarkup(buttons))

# Validate simple address
def valid_address(addr: str) -> bool:
    addr = addr.strip()
    return addr.startswith("0x") and len(addr) >= 10

# Message handler: when user sends address after choosing chain
async def handle_address_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get("awaiting_wallet_address"):
        addr = (update.message.text or "").strip()
        chain = context.user_data.get("add_wallet_chain")
        if not chain:
            await update.message.reply_text("Chain not selected. Start again with Add Wallet.")
            context.user_data.pop("awaiting_wallet_address", None)
            context.user_data.pop("add_wallet_chain", None)
            return
        if not valid_address(addr):
            await update.message.reply_text("Invalid address. Make sure it starts with 0x. Try again or press Cancel.")
            return
        ok = database.add_wallet(user_id, chain, addr)
        context.user_data.pop("awaiting_wallet_address", None)
        context.user_data.pop("add_wallet_chain", None)
        if ok:
            await update.message.reply_text(f"✅ Wallet saved: {chain} {addr}")
        else:
            await update.message.reply_text("❌ Failed to save wallet (duplicate or invalid).")
        return

    # not in add flow
    return

# Get native balance via Alchemy
def get_eth_balance(wallet: str, url: str):
    try:
        payload = {"jsonrpc":"2.0","method":"eth_getBalance","params":[wallet,"latest"],"id":1}
        r = requests.post(url, json=payload, timeout=10).json()
        wei = int(r.get("result","0x0"), 16)
        return round(wei/1e18, 6)
    except Exception:
        return 0

# token balances (top tokens) — light
def get_token_balances(wallet: str, url: str) -> List[Tuple[str,str,float]]:
    try:
        data = {"jsonrpc":"2.0","method":"alchemy_getTokenBalances","params":[wallet],"id":1}
        r = requests.post(url, json=data, timeout=10).json()
        balances = r.get("result", {}).get("tokenBalances", [])
        tokens = []
        for t in balances[:20]:
            bal_hex = t.get("tokenBalance")
            if not bal_hex or bal_hex == "0x0":
                continue
            token_addr = t.get("contractAddress")
            meta = get_token_metadata(token_addr, url)
            if not meta:
                continue
            name = meta.get("name","Unknown")
            symbol = meta.get("symbol","")
            dec = meta.get("decimals", 18)
            bal = int(bal_hex, 16) / (10 ** dec)
            if bal > 0:
                tokens.append((name, symbol, round(bal,6)))
        return tokens
    except Exception:
        return []

def get_token_metadata(address: str, url: str):
    try:
        data = {"jsonrpc":"2.0","method":"alchemy_getTokenMetadata","params":[address],"id":1}
        r = requests.post(url, json=data, timeout=10).json()
        return r.get("result", {})
    except Exception:
        return {}

# Build and send balances for a user
async def send_balances_for_user(bot, chat_id: int):
    rows = database.get_user_wallets(chat_id)
    if not rows:
        bot.send_message(chat_id=chat_id, text="No wallets saved.")
        return
    text = "💰 *Portfolio Summary*\n\n"
    for chain, addr, notif in rows:
        url = CHAIN_URLS.get(chain)
        native = get_eth_balance(addr, url) if url else 0
        text += f"{chain} — `{addr}`\n  • Native: {native}\n"
        tokens = get_token_balances(addr, url) if url else []
        if tokens:
            text += "  • Tokens:\n"
            for name, sym, b in tokens[:5]:
                text += f"     • {name} ({sym}): {b}\n"
        text += "\n"
    bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")

# Called by keep_alive webhook when a tx event arrives
def notify_users_about_tx(tx_event: dict) -> list:
    """
    returns list of tuples (user_id, message)
    """
    matches = []
    frm = (tx_event.get("from") or "").lower()
    to = (tx_event.get("to") or "").lower()
    txhash = tx_event.get("hash") or tx_event.get("transactionHash") or ""
    value = tx_event.get("value") or ""
    all_wallets = database.list_all_wallets()
    for user_id, chain, address in all_wallets:
        if not address:
            continue
        addr = address.lower()
        if addr == frm or addr == to:
            direction = "outgoing" if addr == frm else "incoming"
            msg = (f"🔔 *Transaction detected* on {chain}\n"
                   f"Address: `{address}`\n"
                   f"Type: {direction}\n"
                   f"Value: {value}\n"
                   f"Tx: `{txhash}`")
            matches.append((user_id, msg))
    return matches
