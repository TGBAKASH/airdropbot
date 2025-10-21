# wallet.py
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import aiohttp

logger = logging.getLogger(__name__)

# Conversation states
CHOOSING_CHAIN, ENTERING_ADDRESS = range(2)

# Store user wallets (in production, use a database)
user_wallets = {}
wallet_to_user = {}

# Alchemy API keys from environment
ALCHEMY_API_URL = os.getenv("ALCHEMY_API_URL")
ALCHEMY_WEBHOOK_ID_ETH = os.getenv("ALCHEMY_WEBHOOK_ID_ETH")
ALCHEMY_WEBHOOK_SECRET_ETH = os.getenv("ALCHEMY_WEBHOOK_SECRET_ETH")

# RPC endpoints
ETH_RPC = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_URL}" if ALCHEMY_API_URL else "https://eth.llamarpc.com"
ARBITRUM_RPC = f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_URL}" if ALCHEMY_API_URL else "https://arb1.arbitrum.io/rpc"
BASE_RPC = f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_URL}" if ALCHEMY_API_URL else "https://mainnet.base.org"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"

def is_valid_eth_address(address: str) -> bool:
    """Validate Ethereum address"""
    return bool(re.match(r'^0x[a-fA-F0-9]{40}$', address))

def is_valid_solana_address(address: str) -> bool:
    """Validate Solana address (basic validation)"""
    return bool(re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address))

async def get_eth_balance(address: str, rpc_url: str) -> float:
    """Fetch ETH balance from any EVM chain"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [address, "latest"],
                "id": 1
            }
            async with session.post(rpc_url, json=payload) as response:
                data = await response.json()
                if 'result' in data:
                    balance_wei = int(data['result'], 16)
                    balance_eth = balance_wei / 10**18
                    return balance_eth
                return 0.0
    except Exception as e:
        logger.error(f"Error fetching ETH balance: {e}")
        return 0.0

async def get_solana_balance(address: str) -> float:
    """Fetch SOL balance"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "method": "getBalance",
                "params": [address],
                "id": 1
            }
            async with session.post(SOLANA_RPC, json=payload) as response:
                data = await response.json()
                if 'result' in data and 'value' in data['result']:
                    balance_lamports = data['result']['value']
                    balance_sol = balance_lamports / 10**9
                    return balance_sol
                return 0.0
    except Exception as e:
        logger.error(f"Error fetching SOL balance: {e}")
        return 0.0

async def add_address_to_webhook(address: str, webhook_id: str, auth_token: str):
    """Add address to Alchemy webhook for notifications"""
    if not webhook_id or not auth_token:
        logger.warning("Alchemy webhook credentials not configured")
        return False
    
    try:
        url = "https://dashboard.alchemy.com/api/update-webhook-addresses"
        headers = {
            "X-Alchemy-Token": auth_token,
            "Content-Type": "application/json"
        }
        payload = {
            "webhook_id": webhook_id,
            "addresses_to_add": [address.lower()],
            "addresses_to_remove": []
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"Added {address} to webhook {webhook_id}")
                    return True
                else:
                    logger.error(f"Failed to add address to webhook: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Error adding address to webhook: {e}")
        return False

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show wallet menu"""
    user_id = update.effective_user.id
    
    if user_id in user_wallets:
        wallet_info = user_wallets[user_id]
        notifications_status = "🔔 ON" if wallet_info.get('notifications', False) else "🔕 OFF"
        
        wallet_text = (
            f"💰 *Your Wallet*\n\n"
            f"Chain: {wallet_info['chain']}\n"
            f"Address: `{wallet_info['address'][:8]}...{wallet_info['address'][-6:]}`\n"
            f"Notifications: {notifications_status}\n\n"
            f"Commands:\n"
            f"/balance - Check balance\n"
            f"/notifications - Toggle notifications\n"
            f"/change\\_wallet - Change wallet"
        )
        
        await update.message.reply_text(wallet_text, parse_mode='Markdown')
    else:
        wallet_text = (
            "💰 *Your Wallet*\n\n"
            "No wallet connected\\.\n\n"
            "Use /connect\\_wallet to link your wallet"
        )
        await update.message.reply_text(wallet_text, parse_mode='MarkdownV2')

async def connect_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start wallet connection process"""
    keyboard = [
        [InlineKeyboardButton("🔷 Ethereum (ETH/ARB/BASE)", callback_data='chain_ethereum')],
        [InlineKeyboardButton("🟣 Solana", callback_data='chain_solana')],
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel_wallet')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔗 *Connect Your Wallet*\n\n"
        "Please select your blockchain:\n\n"
        "💡 *Note:* Ethereum option includes ETH Mainnet, Arbitrum, and Base!",
        parse_mode='MarkdownV2',
        reply_markup=reply_markup
    )
    
    return CHOOSING_CHAIN

async def chain_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chain selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel_wallet':
        await query.edit_message_text("❌ Wallet connection cancelled.")
        return ConversationHandler.END
    
    chain_map = {
        'chain_ethereum': 'Ethereum',
        'chain_solana': 'Solana'
    }
    
    chain = chain_map.get(query.data)
    if not chain:
        await query.edit_message_text("❌ Invalid selection. Please try again with /connect_wallet")
        return ConversationHandler.END
    
    context.user_data['selected_chain'] = chain
    
    if chain == 'Solana':
        prompt_text = (
            "🟣 *Solana Selected*\n\n"
            "Please send your Solana wallet address:\n\n"
            "Example: `DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK`"
        )
    else:
        prompt_text = (
            "🔷 *Ethereum Selected*\n\n"
            "Please send your Ethereum wallet address:\n\n"
            "Example: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb`\n\n"
            "💡 This address will be monitored on:\n"
            "• Ethereum Mainnet\n"
            "• Arbitrum\n"
            "• Base"
        )
    
    await query.edit_message_text(prompt_text, parse_mode='Markdown')
    
    return ENTERING_ADDRESS

async def address_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle address input"""
    address = update.message.text.strip()
    chain = context.user_data.get('selected_chain')
    user_id = update.effective_user.id
    
    if not chain:
        await update.message.reply_text(
            "❌ Session expired. Please start again with /connect_wallet"
        )
        return ConversationHandler.END
    
    # Validate address
    if chain == 'Solana':
        if not is_valid_solana_address(address):
            await update.message.reply_text(
                "❌ *Invalid Solana address!*\n\n"
                "Please try again with /connect\\_wallet\n\n"
                "A valid Solana address looks like:\n"
                "`DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK`",
                parse_mode='MarkdownV2'
            )
            return ConversationHandler.END
    else:
        if not is_valid_eth_address(address):
            await update.message.reply_text(
                "❌ *Invalid Ethereum address!*\n\n"
                "Please try again with /connect\\_wallet\n\n"
                "A valid Ethereum address looks like:\n"
                "`0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb`",
                parse_mode='MarkdownV2'
            )
            return ConversationHandler.END
    
    # Show processing message
    loading_msg = await update.message.reply_text("⏳ Setting up your wallet...")
    
    # Add to webhook for notifications (only for Ethereum)
    webhook_added = False
    if chain == 'Ethereum' and ALCHEMY_WEBHOOK_ID_ETH:
        webhook_added = await add_address_to_webhook(address, ALCHEMY_WEBHOOK_ID_ETH, ALCHEMY_WEBHOOK_SECRET_ETH)
        logger.info(f"Webhook registration result: {webhook_added}")
    
    # Save wallet
    user_wallets[user_id] = {
        'chain': chain,
        'address': address,
        'notifications': webhook_added
    }
    
    # Map wallet to user for notifications
    wallet_to_user[address.lower()] = user_id
    
    notification_status = "🔔 Enabled" if webhook_added else "⚠️ Not configured"
    
    success_text = (
        f"✅ *Wallet Connected Successfully!*\n\n"
        f"Chain: {chain}\n"
        f"Address: `{address}`\n"
        f"Notifications: {notification_status}\n\n"
        f"📊 Commands:\n"
        f"/balance \\- Check your balance\n"
        f"/wallet \\- View wallet info\n"
        f"/notifications \\- Toggle alerts"
    )
    
    await loading_msg.edit_text(success_text, parse_mode='MarkdownV2')
    
    # Clear user data
    context.user_data.clear()
    
    return ConversationHandler.END

async def cancel_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel wallet connection"""
    await update.message.reply_text("❌ Wallet connection cancelled.")
    return ConversationHandler.END

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch and display wallet balance"""
    user_id = update.effective_user.id
    
    if user_id not in user_wallets:
        await update.message.reply_text(
            "❌ No wallet connected\\. Use /connect\\_wallet first\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    wallet_info = user_wallets[user_id]
    chain = wallet_info['chain']
    address = wallet_info['address']
    
    # Send loading message
    loading_msg = await update.message.reply_text("⏳ Fetching balance from blockchain...")
    
    try:
        if chain == 'Ethereum':
            # Fetch from all EVM chains
            eth_balance = await get_eth_balance(address, ETH_RPC)
            arb_balance = await get_eth_balance(address, ARBITRUM_RPC)
            base_balance = await get_eth_balance(address, BASE_RPC)
            total = eth_balance + arb_balance + base_balance
            
            balance_text = (
                f"💰 *Balance for {chain}*\n\n"
                f"Address: `{address[:8]}...{address[-6:]}`\n\n"
                f"🔷 Ethereum Mainnet: *{eth_balance:.6f}* ETH\n"
                f"🔵 Arbitrum: *{arb_balance:.6f}* ETH\n"
                f"🔵 Base: *{base_balance:.6f}* ETH\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📊 Total: *{total:.6f}* ETH"
            )
        
        elif chain == 'Solana':
            balance = await get_solana_balance(address)
            balance_text = (
                f"💰 *Balance for {chain}*\n\n"
                f"Address: `{address[:8]}...{address[-6:]}`\n\n"
                f"🟣 Solana: *{balance:.6f}* SOL"
            )
        else:
            balance_text = "❌ Unsupported chain"
        
        await loading_msg.edit_text(balance_text, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error fetching balance: {e}")
        await loading_msg.edit_text(
            "❌ Error fetching balance\\. Please try again later\\.",
            parse_mode='MarkdownV2'
        )

async def notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle transaction notifications"""
    user_id = update.effective_user.id
    
    if user_id not in user_wallets:
        await update.message.reply_text(
            "❌ No wallet connected. Use /connect_wallet first."
        )
        return
    
    wallet_info = user_wallets[user_id]
    current_status = wallet_info.get('notifications', False)
    
    if not ALCHEMY_WEBHOOK_ID_ETH:
        await update.message.reply_text(
            "⚠️ Alchemy webhooks are not configured. "
            "Please set up webhook IDs in environment variables."
        )
        return
    
    # Toggle notifications
    new_status = not current_status
    wallet_info['notifications'] = new_status
    
    status_text = "🔔 enabled" if new_status else "🔕 disabled"
    
    await update.message.reply_text(
        f"✅ Transaction notifications {status_text}!"
    )

async def change_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change connected wallet"""
    user_id = update.effective_user.id
    
    if user_id in user_wallets:
        wallet_info = user_wallets[user_id]
        address = wallet_info['address']
        
        # Remove from mappings
        del user_wallets[user_id]
        if address.lower() in wallet_to_user:
            del wallet_to_user[address.lower()]
    
    await update.message.reply_text(
        "🔄 Wallet disconnected. Use /connect_wallet to connect a new wallet."
    )

async def handle_webhook_notification(app, webhook_data: dict):
    """Handle incoming webhook notifications from Alchemy"""
    try:
        event = webhook_data.get('event', {})
        activity = event.get('activity', [])
        
        if not activity:
            return
        
        for tx in activity:
            from_address = tx.get('fromAddress', '').lower()
            to_address = tx.get('toAddress', '').lower()
            value = float(tx.get('value', 0))
            hash_tx = tx.get('hash', '')
            asset = tx.get('asset', 'ETH')
            
            # Find affected users
            affected_users = []
            if from_address in wallet_to_user:
                affected_users.append((wallet_to_user[from_address], 'sent'))
            if to_address in wallet_to_user:
                affected_users.append((wallet_to_user[to_address], 'received'))
            
            # Send notifications
            for user_id, tx_type in affected_users:
                if user_id not in user_wallets:
                    continue
                
                wallet_info = user_wallets[user_id]
                if not wallet_info.get('notifications', False):
                    continue
                
                if tx_type == 'sent':
                    emoji = "📤"
                    action = "Sent"
                    address_label = f"To: `{to_address[:8]}...{to_address[-6:]}`"
                else:
                    emoji = "📥"
                    action = "Received"
                    address_label = f"From: `{from_address[:8]}...{from_address[-6:]}`"
                
                notification_text = (
                    f"{emoji} *Transaction {action}*\n\n"
                    f"Amount: {value:.6f} {asset}\n"
                    f"{address_label}\n"
                    f"Hash: `{hash_tx[:10]}...{hash_tx[-8:]}`\n\n"
                    f"[View on Explorer](https://etherscan.io/tx/{hash_tx})"
                )
                
                try:
                    await app.bot.send_message(
                        chat_id=user_id,
                        text=notification_text,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.error(f"Error sending notification to user {user_id}: {e}")
    
    except Exception as e:
        logger.error(f"Error handling webhook notification: {e}")

def register_wallet_handlers(app):
    """Register all wallet-related handlers"""
    
    # Conversation handler for wallet connection
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('connect_wallet', connect_wallet_start)],
        states={
            CHOOSING_CHAIN: [CallbackQueryHandler(chain_selected, pattern='^(chain_|cancel_)')],
            ENTERING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address_entered)]
        },
        fallbacks=[CommandHandler('cancel', cancel_wallet)],
        name="wallet_conversation",
        persistent=False
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('wallet', wallet_command))
    app.add_handler(CommandHandler('balance', balance_command))
    app.add_handler(CommandHandler('notifications', notifications_command))
    app.add_handler(CommandHandler('change_wallet', change_wallet_command))
    
    logger.info("✅ Wallet handlers registered")