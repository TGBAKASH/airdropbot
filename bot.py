import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from web3 import Web3
from datetime import datetime
from keep_alive import keep_alive
from database import Database

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY', os.getenv('ALCHEMY_API_URL', '').split('/')[-1])

# Initialize database
db = Database()

# Web3 connections
w3_eth = None
w3_arb = None
w3_base = None

try:
    if ALCHEMY_API_KEY:
        w3_eth = Web3(Web3.HTTPProvider(f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"))
        w3_arb = Web3(Web3.HTTPProvider(f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"))
        w3_base = Web3(Web3.HTTPProvider(f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"))
        logger.info("Web3 connections initialized")
except Exception as e:
    logger.warning(f"Web3 connection error: {e}")

# Main menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    
    keyboard = [
        [InlineKeyboardButton("👤 Profile", callback_data='profile')],
        [InlineKeyboardButton("🎁 Airdrops", callback_data='airdrops')],
        [InlineKeyboardButton("💰 Wallet", callback_data='wallet')],
        [InlineKeyboardButton("❓ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"Welcome to Sage Airdrops Bot, {user.first_name}!\n\n"
    welcome_text += "Choose an option from the menu below:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Profile handler
async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    profile_text = f"👤 **Your Profile**\n\n"
    profile_text += f"Name: {user.first_name}\n"
    profile_text += f"Username: @{user.username if user.username else 'Not set'}\n"
    profile_text += f"User ID: `{user.id}`\n"
    profile_text += f"Joined: {user_data.get('joined_date', 'Unknown')}\n"
    
    wallet_info = db.get_user_wallet(user.id)
    if wallet_info:
        profile_text += f"\n💰 **Connected Wallets:**\n"
        if wallet_info.get('ethereum'):
            profile_text += f"Ethereum: `{wallet_info['ethereum'][:6]}...{wallet_info['ethereum'][-4:]}`\n"
        if wallet_info.get('solana'):
            profile_text += f"Solana: `{wallet_info['solana'][:6]}...{wallet_info['solana'][-4:]}`\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')

# Airdrops menu
async def airdrops_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🧪 Testnet", callback_data='airdrop_testnet')],
        [InlineKeyboardButton("🚀 Mainnet", callback_data='airdrop_mainnet')],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🎁 **Airdrops**\n\nSelect a category:"
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Testnet airdrops
async def airdrop_testnet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("L1 Chains", callback_data='testnet_l1')],
        [InlineKeyboardButton("L2 Chains", callback_data='testnet_l2')],
        [InlineKeyboardButton("Others", callback_data='testnet_others')],
        [InlineKeyboardButton("🔙 Back", callback_data='airdrops')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🧪 **Testnet Airdrops**\n\nChoose a subcategory:"
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Mainnet airdrops
async def airdrop_mainnet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📊 Trading Related", callback_data='mainnet_trading')],
        [InlineKeyboardButton("🌐 Non-Trading Related", callback_data='mainnet_non_trading')],
        [InlineKeyboardButton("🔙 Back", callback_data='airdrops')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🚀 **Mainnet Airdrops**\n\nChoose a subcategory:"
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Show airdrops by category
async def show_category_airdrops(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, subcategory: str):
    query = update.callback_query
    await query.answer()
    
    airdrops = db.get_airdrops_by_category(category, subcategory)
    
    if not airdrops:
        text = f"No airdrops found in this category yet.\n\nCheck back later!"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=f'airdrop_{category}')]]
    else:
        text = f"**{subcategory.upper()} Airdrops:**\n\n"
        keyboard = []
        for airdrop in airdrops:
            keyboard.append([InlineKeyboardButton(
                airdrop['name'], 
                callback_data=f"view_airdrop_{airdrop['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f'airdrop_{category}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# View specific airdrop
async def view_airdrop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    airdrop_id = int(query.data.split('_')[-1])
    airdrop = db.get_airdrop(airdrop_id)
    
    if not airdrop:
        await query.edit_message_text("Airdrop not found!")
        return
    
    text = f"**{airdrop['name']}**\n\n"
    text += f"{airdrop['description']}\n\n"
    text += f"🔗 Link: {airdrop['link']}\n"
    text += f"📅 Added: {airdrop['added_date']}"
    
    keyboard = [
        [InlineKeyboardButton("🔗 Visit Link", url=airdrop['link'])],
        [InlineKeyboardButton("🔙 Back", callback_data=f"airdrop_{airdrop['category']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Wallet menu
async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    wallet_info = db.get_user_wallet(user_id)
    
    text = "💰 **Your Wallet**\n\n"
    
    if wallet_info:
        if wallet_info.get('ethereum'):
            text += f"✅ Ethereum: `{wallet_info['ethereum'][:6]}...{wallet_info['ethereum'][-4:]}`\n"
        if wallet_info.get('solana'):
            text += f"✅ Solana: `{wallet_info['solana'][:6]}...{wallet_info['solana'][-4:]}`\n"
        
        keyboard = [
            [InlineKeyboardButton("💳 Check Balance", callback_data='check_balance')],
            [InlineKeyboardButton("🔄 Change Wallet", callback_data='connect_wallet')],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data='start')]
        ]
    else:
        text += "No wallet connected yet.\n\n"
        text += "Connect your wallet to receive transaction notifications!"
        keyboard = [
            [InlineKeyboardButton("🔗 Connect Wallet", callback_data='connect_wallet')],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data='start')]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Connect wallet
async def connect_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Ethereum", callback_data='wallet_ethereum')],
        [InlineKeyboardButton("Solana", callback_data='wallet_solana')],
        [InlineKeyboardButton("🔙 Back", callback_data='wallet')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "Choose blockchain to connect your wallet:"
    await query.edit_message_text(text, reply_markup=reply_markup)

# Handle wallet type selection
async def wallet_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    wallet_type = query.data.split('_')[1]
    context.user_data['connecting_wallet'] = wallet_type
    
    text = f"Please send your {wallet_type.capitalize()} wallet address:\n\n"
    text += "⚠️ Make sure you send the correct address!"
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data='wallet')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

# Handle wallet address input
async def handle_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'connecting_wallet' not in context.user_data:
        return
    
    user_id = update.effective_user.id
    address = update.message.text.strip()
    wallet_type = context.user_data['connecting_wallet']
    
    # Validate address
    if wallet_type == 'ethereum':
        if not Web3.is_address(address):
            await update.message.reply_text("❌ Invalid Ethereum address! Please try again.")
            return
        address = Web3.to_checksum_address(address)
    elif wallet_type == 'solana':
        if len(address) < 32 or len(address) > 44:
            await update.message.reply_text("❌ Invalid Solana address! Please try again.")
            return
    
    # Save wallet
    db.save_user_wallet(user_id, wallet_type, address)
    
    # Clear context
    del context.user_data['connecting_wallet']
    
    keyboard = [
        [InlineKeyboardButton("💳 View Wallet", callback_data='wallet')],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Successfully connected your {wallet_type.capitalize()} wallet!\n\n"
        f"Address: `{address[:6]}...{address[-4:]}`\n\n"
        f"You will now receive transaction notifications!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Check balance
async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    wallet_info = db.get_user_wallet(user_id)
    
    if not wallet_info:
        await query.edit_message_text("No wallet connected!")
        return
    
    keyboard = []
    if wallet_info.get('ethereum'):
        keyboard.append([InlineKeyboardButton("ETH Mainnet", callback_data='balance_eth')])
        keyboard.append([InlineKeyboardButton("Arbitrum", callback_data='balance_arb')])
        keyboard.append([InlineKeyboardButton("Base", callback_data='balance_base')])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='wallet')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("Select network to check balance:", reply_markup=reply_markup)

# Get balance for specific network
async def get_network_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Fetching balance...")
    
    user_id = update.effective_user.id
    wallet_info = db.get_user_wallet(user_id)
    network = query.data.split('_')[1]
    
    try:
        address = wallet_info.get('ethereum')
        
        if network == 'eth' and w3_eth:
            balance_wei = w3_eth.eth.get_balance(address)
            balance = w3_eth.from_wei(balance_wei, 'ether')
            network_name = "Ethereum Mainnet"
        elif network == 'arb' and w3_arb:
            balance_wei = w3_arb.eth.get_balance(address)
            balance = w3_arb.from_wei(balance_wei, 'ether')
            network_name = "Arbitrum"
        elif network == 'base' and w3_base:
            balance_wei = w3_base.eth.get_balance(address)
            balance = w3_base.from_wei(balance_wei, 'ether')
            network_name = "Base"
        else:
            text = "❌ Web3 connection not available"
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='check_balance')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)
            return
        
        text = f"💰 **Balance on {network_name}**\n\n"
        text += f"Address: `{address[:6]}...{address[-4:]}`\n"
        text += f"Balance: **{balance:.6f} ETH**"
        
    except Exception as e:
        text = f"❌ Error fetching balance: {str(e)}"
        logger.error(f"Balance fetch error: {e}")
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data=query.data)],
        [InlineKeyboardButton("🔙 Back", callback_data='check_balance')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Help handler
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "❓ **Help & Support**\n\n"
    text += "If you need assistance, please send your message here and our admin will respond shortly.\n\n"
    text += "Type your message or question:"
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data['awaiting_support_message'] = True
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Handle support messages
async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_support_message'):
        return
    
    user = update.effective_user
    message = update.message.text
    
    # Save support message
    db.save_support_message(user.id, message)
    
    # Notify admin
    if ADMIN_ID:
        admin_text = f"📩 **New Support Message**\n\n"
        admin_text += f"From: {user.first_name} (@{user.username if user.username else 'No username'})\n"
        admin_text += f"User ID: `{user.id}`\n\n"
        admin_text += f"Message:\n{message}"
        
        keyboard = [[InlineKeyboardButton("💬 Reply", callback_data=f'reply_{user.id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
    
    # Confirm to user
    context.user_data['awaiting_support_message'] = False
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ Your message has been sent to the admin. We'll get back to you soon!",
        reply_markup=reply_markup
    )

# Admin: Add airdrop
async def admin_add_airdrop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    # Format: /add_airdrop category|subcategory|name|link|description
    try:
        parts = update.message.text.split(' ', 1)[1].split('|')
        if len(parts) != 5:
            raise ValueError("Invalid format")
        
        category, subcategory, name, link, description = [p.strip() for p in parts]
        
        airdrop_id = db.add_airdrop(category, subcategory, name, link, description)
        
        await update.message.reply_text(
            f"✅ Airdrop added successfully!\n\n"
            f"ID: {airdrop_id}\n"
            f"Category: {category} > {subcategory}\n"
            f"Name: {name}"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error adding airdrop!\n\n"
            f"Format: /add_airdrop category|subcategory|name|link|description\n\n"
            f"Categories: testnet, mainnet\n"
            f"Testnet subcategories: l1, l2, others\n"
            f"Mainnet subcategories: trading, non_trading\n\n"
            f"Error: {str(e)}"
        )

# Callback query router
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == 'start':
        await start(update, context)
    elif data == 'profile':
        await profile_handler(update, context)
    elif data == 'airdrops':
        await airdrops_handler(update, context)
    elif data == 'airdrop_testnet':
        await airdrop_testnet(update, context)
    elif data == 'airdrop_mainnet':
        await airdrop_mainnet(update, context)
    elif data.startswith('testnet_'):
        subcategory = data.split('_')[1]
        await show_category_airdrops(update, context, 'testnet', subcategory)
    elif data.startswith('mainnet_'):
        subcategory = data.split('_')[1]
        await show_category_airdrops(update, context, 'mainnet', subcategory)
    elif data.startswith('view_airdrop_'):
        await view_airdrop(update, context)
    elif data == 'wallet':
        await wallet_handler(update, context)
    elif data == 'connect_wallet':
        await connect_wallet(update, context)
    elif data.startswith('wallet_'):
        await wallet_type_handler(update, context)
    elif data == 'check_balance':
        await check_balance(update, context)
    elif data.startswith('balance_'):
        await get_network_balance(update, context)
    elif data == 'help':
        await help_handler(update, context)

# Message handler
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'connecting_wallet' in context.user_data:
        await handle_wallet_address(update, context)
    elif context.user_data.get('awaiting_support_message'):
        await handle_support_message(update, context)

# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")

# Main function
def main():
    """Main function to start the bot"""
    # Start Flask server for keep-alive
    keep_alive()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add_airdrop", admin_add_airdrop))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Run bot with simple polling
    logger.info("🤖 Bot starting...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()