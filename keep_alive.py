from flask import Flask, jsonify, request
from threading import Thread
import logging

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'bot': 'Sage Airdrops Bot',
        'message': 'Bot is active!'
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'uptime': 'running'
    })

@app.route('/webhook/alchemy', methods=['POST'])
def alchemy_webhook():
    """Handle Alchemy webhook for transaction notifications"""
    try:
        data = request.json
        # This will be handled by the notification system
        print(f"Received webhook: {data}")
        return jsonify({'status': 'received'}), 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    print("Flask server started on port 8080")