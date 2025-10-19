# keep_alive.py
import os
import json
import hmac
import hashlib
import threading
import time
from flask import Flask, request, jsonify
from telegram import Bot
import wallet  # expects notify_users_about_tx(tx_event)
import database  # optional: for polling mode if you add it

app = Flask(__name__)

# === Config (from env) ===
BOT_TOKEN = os.getenv("BOT_TOKEN")                    # required
ALCHEMY_WEBHOOK_SECRET = os.getenv("ALCHEMY_WEBHOOK_SECRET", "")  # optional (for signature verification)
PORT = int(os.getenv("PORT", 8080))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required for keep_alive.py")

bot = Bot(token=BOT_TOKEN)

# === Basic keep-alive route ===
@app.route("/", methods=["GET"])
def home():
    return "✅ Bot is alive", 200

# === Helper: verify Alchemy signature (optional) ===
def verify_alchemy_signature(req):
    """Return True if signature is valid or no secret configured."""
    if not ALCHEMY_WEBHOOK_SECRET:
        return True
    signature = req.headers.get("x-alchemy-signature", "")
    if not signature:
        return False
    # Alchemy uses HMAC-SHA256 over the raw body, secret is bytes
    try:
        body = req.get_data()
        computed = hmac.new(ALCHEMY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        # Alchemy may provide signature as hex; compare safely
        return hmac.compare_digest(computed, signature)
    except Exception:
        return False

# === Helper: send message via telegram Bot (safe wrapper) ===
def send_message_to_user(chat_id: int, text: str, parse_mode: str = "Markdown"):
    try:
        bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        return True
    except Exception as e:
        print(f"[keep_alive] Failed to send message to {chat_id}: {e}")
        return False

# === Webhook endpoint for Alchemy (or other services) ===
@app.route("/webhook", methods=["POST"])
def alchemy_webhook():
    """
    Receives webhook payloads from Alchemy.
    Expects JSON containing either an 'event' or 'events' list.
    For each tx/event, calls wallet.notify_users_about_tx(tx_event)
    which must return a list of (user_id, message_text) to notify.
    """
    # optional verify
    if not verify_alchemy_signature(request):
        return jsonify({"ok": False, "error": "invalid signature"}), 403

    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"ok": False, "error": "invalid json"}), 400

    # Normalize events into a list of event dicts
    tx_events = []
    if isinstance(payload, dict):
        if "events" in payload and isinstance(payload["events"], list):
            tx_events.extend(payload["events"])
        elif "event" in payload and isinstance(payload["event"], dict):
            tx_events.append(payload["event"])
        # Alchemy addresses sometimes nest activity or other keys
        elif "activity" in payload and isinstance(payload["activity"], list):
            tx_events.extend(payload["activity"])
        else:
            tx_events.append(payload)
    elif isinstance(payload, list):
        tx_events.extend(payload)
    else:
        tx_events.append(payload)

    handled = 0
    for ev in tx_events:
        try:
            # wallet.notify_users_about_tx should return [(user_id, msg), ...]
            matches = wallet.notify_users_about_tx(ev)
            for uid, msg in matches:
                send_message_to_user(uid, msg)
                handled += 1
        except Exception as e:
            print(f"[keep_alive] Error processing event: {e}")

    return jsonify({"ok": True, "handled_notifications": handled}), 200

# === Optional: polling-mode notifier (if you want periodic checks) ===
# This will poll the DB for wallets and perform checks if you implement db functions.
# Disabled by default — enable only if you wire it to your database/get_balance logic.
def polling_notifier_loop(interval_seconds: int = 60):
    """
    Example loop: (optional)
    - list all wallets via database.list_all_wallets()
    - check balances via wallet.get_eth_balance() or similar
    - call notify functions if changes are detected
    """
    print("[keep_alive] Polling notifier loop started (disabled until you add DB/balance logic).")
    # Example skeleton (uncomment and implement DB/balance if you enable)
    # last_balances = {}
    # while True:
    #     try:
    #         rows = database.list_all_wallets()  # expected [(user_id, chain, address), ...]
    #         for user_id, chain, address in rows:
    #             # implement wallet.get_eth_balance(address, chain_rpc_url)
    #             current = wallet.get_eth_balance(address, wallet.get_rpc_url_for_chain(chain))
    #             key = f"{chain}:{address.lower()}"
    #             prev = last_balances.get(key)
    #             if prev is None:
    #                 last_balances[key] = current
    #             elif current != prev:
    #                 # create a message and notify user
    #                 diff = current - prev
    #                 direction = "Received" if diff > 0 else "Sent"
    #                 msg = f"🔔 {direction} on {chain}\n`{address}`\nChange: {diff}"
    #                 send_message_to_user(user_id, msg)
    #                 last_balances[key] = current
    #     except Exception as e:
    #         print("[keep_alive] Polling notifier error:", e)
    #     time.sleep(interval_seconds)

# === Run Flask in background thread ===
def run_flask():
    # enable reloader=False in production contexts where code is run in a thread
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    # If you want polling notifier, start it here (uncomment)
    # p = threading.Thread(target=polling_notifier_loop, kwargs={"interval_seconds": 60}, daemon=True)
    # p.start()

# Allow running standalone for local testing
if __name__ == "__main__":
    print("[keep_alive] Starting (standalone mode).")
    keep_alive()
    # keep process alive if run directly
    while True:
        time.sleep(60)
