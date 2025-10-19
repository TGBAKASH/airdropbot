from flask import Flask, request, jsonify
from threading import Thread
from telegram import Bot
import os, json
import wallet

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot alive ✅"

@app.route('/alchemy-webhook', methods=['POST'])
def alchemy_webhook():
    """Receive Alchemy webhook and forward notifications to users."""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid json'}), 400

    events = []
    if isinstance(data, dict) and data.get("events"):
        events = data["events"]
    else:
        events = [data]

    bot = Bot(token=os.getenv("BOT_TOKEN"))
    for ev in events:
        matches = wallet.notify_users_about_tx(ev)
        for uid, msg in matches:
            try:
                bot.send_message(chat_id=uid, text=msg, parse_mode="Markdown")
            except Exception:
                pass

    return jsonify({'ok': True, 'handled': len(events)})

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()
