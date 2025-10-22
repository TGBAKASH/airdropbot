#!/usr/bin/env python3
"""
Setup script for Sage Airdrops Bot
Run this to verify your configuration before deployment
"""

import os
import sys

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'BOT_TOKEN',
        'ADMIN_ID',
        'ALCHEMY_API_KEY'
    ]
    
    optional_vars = [
        'ALCHEMY_API_URL',
        'ALCHEMY_WEBHOOK_ID_ARB',
        'ALCHEMY_WEBHOOK_ID_BASE',
        'ALCHEMY_WEBHOOK_ID_ETH'
    ]
    
    print("🔍 Checking environment variables...\n")
    
    missing = []
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Missing")
            missing.append(var)
    
    print("\nOptional variables:")
    for var in optional_vars:
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"⚠️  {var}: Not set (can be added later)")
    
    if missing:
        print(f"\n❌ Missing required variables: {', '.join(missing)}")
        print("\nCreate a .env file or set these in your deployment environment:")
        for var in missing:
            print(f"  {var}=your_value_here")
        return False
    
    print("\n✅ All required environment variables are set!")
    return True

def check_dependencies():
    """Check if all required packages are installed"""
    print("\n🔍 Checking dependencies...\n")
    
    required_packages = [
        'telegram',
        'web3',
        'flask'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: Installed")
        except ImportError:
            print(f"❌ {package}: Not installed")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("\nInstall with: pip install -r requirements.txt")
        return False
    
    print("\n✅ All dependencies are installed!")
    return True

def test_bot_token():
    """Test if bot token is valid"""
    print("\n🔍 Testing bot token...\n")
    
    try:
        from telegram import Bot
        import asyncio
        
        token = os.getenv('BOT_TOKEN')
        if not token:
            print("❌ BOT_TOKEN not found")
            return False
        
        async def test():
            bot = Bot(token=token)
            me = await bot.get_me()
            return me
        
        me = asyncio.run(test())
        print(f"✅ Bot token is valid!")
        print(f"   Bot username: @{me.username}")
        print(f"   Bot name: {me.first_name}")
        return True
        
    except Exception as e:
        print(f"❌ Invalid bot token: {str(e)}")
        return False

def test_web3_connection():
    """Test Web3 connection to Alchemy"""
    print("\n🔍 Testing Web3 connection...\n")
    
    try:
        from web3 import Web3
        
        api_key = os.getenv('ALCHEMY_API_KEY')
        if not api_key:
            print("⚠️  ALCHEMY_API_KEY not found - skipping Web3 test")
            return True
        
        w3 = Web3(Web3.HTTPProvider(f"https://eth-mainnet.g.alchemy.com/v2/{api_key}"))
        
        if w3.is_connected():
            print("✅ Successfully connected to Ethereum mainnet via Alchemy")
            block = w3.eth.block_number
            print(f"   Current block: {block}")
            return True
        else:
            print("❌ Could not connect to Alchemy")
            return False
            
    except Exception as e:
        print(f"❌ Web3 connection error: {str(e)}")
        return False

def create_example_env():
    """Create example .env file"""
    print("\n📝 Creating example .env.example file...\n")
    
    env_example = """# Telegram Bot Configuration
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_ID=123456789

# Alchemy Configuration
ALCHEMY_API_KEY=your_alchemy_api_key_here
ALCHEMY_API_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY

# Alchemy Webhook IDs (optional, can be added later)
ALCHEMY_WEBHOOK_ID_ARB=your_arbitrum_webhook_id
ALCHEMY_WEBHOOK_ID_BASE=your_base_webhook_id
ALCHEMY_WEBHOOK_ID_ETH=your_ethereum_webhook_id
"""
    
    try:
        with open('.env.example', 'w') as f:
            f.write(env_example)
        print("✅ Created .env.example file")
        print("   Copy this to .env and fill in your values:")
        print("   cp .env.example .env")
        return True
    except Exception as e:
        print(f"❌ Could not create .env.example: {str(e)}")
        return False

def initialize_database():
    """Initialize database structure"""
    print("\n🔍 Initializing database...\n")
    
    try:
        from database import Database
        
        db = Database()
        print("✅ Database initialized successfully!")
        print(f"   Data file: bot_data.json")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")
        return False

def main():
    """Run all setup checks"""
    print("=" * 60)
    print("     Sage Airdrops Bot - Setup Verification")
    print("=" * 60)
    
    # Load .env if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("\n✅ Loaded .env file")
    except ImportError:
        print("\n⚠️  python-dotenv not installed (optional)")
        print("   Install with: pip install python-dotenv")
    except:
        pass
    
    # Run checks
    checks = [
        ("Environment Variables", check_environment),
        ("Dependencies", check_dependencies),
        ("Bot Token", test_bot_token),
        ("Web3 Connection", test_web3_connection),
        ("Database", initialize_database),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error during {name} check: {str(e)}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("     Setup Summary")
    print("=" * 60)
    
    all_passed = all(result for _, result in results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("\n🎉 All checks passed! Your bot is ready to deploy.")
        print("\nNext steps:")
        print("1. Review DEPLOYMENT.md for deployment instructions")
        print("2. Deploy to Render: https://render.com")
        print("3. Setup Alchemy webhooks")
        print("4. Test your bot on Telegram")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nRefer to:")
        print("- README.md for general setup")
        print("- DEPLOYMENT.md for deployment guide")
        print("- Create .env file with your credentials")
    
    # Create example env if it doesn't exist
    if not os.path.exists('.env') and not os.path.exists('.env.example'):
        create_example_env()
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()