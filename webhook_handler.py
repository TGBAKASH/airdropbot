# webhook_handler.py
from flask import Flask, request, jsonify
import logging
import os
import hmac
import hashlib
import asyncio

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Store reference to the bot application
bot_app = None

def verify_alchemy_signature(signature: str, body: bytes, secret: str) -> bool:
    """Verify Alchemy webhook signature"""
    if not secret:
        return True  # Skip verification if no secret is set
    
    try:
        expected_signature = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        return False

@app.route('/webhook/alchemy/eth', methods=['POST'])
def alchemy_webhook_eth():
    """Handle Alchemy webhook for Ethereum"""
    try:
        signature = request.headers.get('X-Alchemy-Signature', '')
        secret = os.getenv('ALCHEMY_WEBHOOK_SECRET_ETH', '')
        
        if secret and not verify_alchemy_signature(signature, request.data, secret):
            logger.warning("Invalid webhook signature for ETH")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.json
        logger.info(f"Received ETH webhook: {data}")
        
        # Process webhook in the background
        if bot_app:
            from wallet import handle_webhook_notification
            asyncio.create_task(handle_webhook_notification(bot_app, data))
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        logger.error(f"Error processing ETH webhook: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook/alchemy/arbitrum', methods=['POST'])
def alchemy_webhook_arbitrum():
    """Handle Alchemy webhook for Arbitrum"""
    try:
        signature = request.headers.get('X-Alchemy-Signature', '')
        secret = os.getenv('ALCHEMY_WEBHOOK_SECRET_ARB', '')
        
        if secret and not verify_alchemy_signature(signature, request.data, secret):
            logger.warning("Invalid webhook signature for Arbitrum")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.json
        logger.info(f"Received Arbitrum webhook: {data}")
        
        # Process webhook in the background
        if bot_app:
            from wallet import handle_webhook_notification
            asyncio.create_task(handle_webhook_notification(bot_app, data))
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        logger.error(f"Error processing Arbitrum webhook: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook/alchemy/base', methods=['POST'])
def alchemy_webhook_base():
    """Handle Alchemy webhook for Base"""
    try:
        signature = request.headers.get('X-Alchemy-Signature', '')
        secret = os.getenv('ALCHEMY_WEBHOOK_SECRET_BASE', '')
        
        if secret and not verify_alchemy_signature(signature, request.data, secret):
            logger.warning("Invalid webhook signature for Base")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.json
        logger.info(f"Received Base webhook: {data}")
        
        # Process webhook in the background
        if bot_app:
            from wallet import handle_webhook_notification
            asyncio.create_task(handle_webhook_notification(bot_app, data))
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        logger.error(f"Error processing Base webhook: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return "Bot is alive! 🤖"

def set_bot_app(application):
    """Store reference to the bot application"""
    global bot_app
    bot_app = application

def run_server():
    """Run the webhook server"""
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)