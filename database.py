import json
import os
from datetime import datetime
from typing import Optional, Dict, List

class Database:
    def __init__(self):
        self.data_file = 'bot_data.json'
        self.load_data()
    
    def load_data(self):
        """Load data from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.data = json.load(f)
            except:
                self.data = self._get_empty_data()
        else:
            self.data = self._get_empty_data()
    
    def save_data(self):
        """Save data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def _get_empty_data(self):
        """Return empty data structure"""
        return {
            'users': {},
            'wallets': {},
            'airdrops': [],
            'support_messages': [],
            'airdrop_counter': 0
        }
    
    # User management
    def add_user(self, user_id: int, username: str, first_name: str):
        """Add or update user"""
        user_id_str = str(user_id)
        if user_id_str not in self.data['users']:
            self.data['users'][user_id_str] = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'joined_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            self.save_data()
    
    def get_user(self, user_id: int) -> Dict:
        """Get user data"""
        return self.data['users'].get(str(user_id), {})
    
    # Wallet management
    def save_user_wallet(self, user_id: int, wallet_type: str, address: str):
        """Save user wallet"""
        user_id_str = str(user_id)
        if user_id_str not in self.data['wallets']:
            self.data['wallets'][user_id_str] = {}
        
        self.data['wallets'][user_id_str][wallet_type] = address
        self.data['wallets'][user_id_str]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.save_data()
    
    def get_user_wallet(self, user_id: int) -> Optional[Dict]:
        """Get user wallet"""
        return self.data['wallets'].get(str(user_id))
    
    def get_all_wallets(self, wallet_type: str = None) -> Dict:
        """Get all wallets, optionally filtered by type"""
        if wallet_type:
            return {
                user_id: wallet_data 
                for user_id, wallet_data in self.data['wallets'].items() 
                if wallet_type in wallet_data
            }
        return self.data['wallets']
    
    # Airdrop management
    def add_airdrop(self, category: str, subcategory: str, name: str, link: str, description: str) -> int:
        """Add new airdrop"""
        self.data['airdrop_counter'] += 1
        airdrop_id = self.data['airdrop_counter']
        
        airdrop = {
            'id': airdrop_id,
            'category': category.lower(),
            'subcategory': subcategory.lower(),
            'name': name,
            'link': link,
            'description': description,
            'added_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.data['airdrops'].append(airdrop)
        self.save_data()
        return airdrop_id
    
    def get_airdrop(self, airdrop_id: int) -> Optional[Dict]:
        """Get specific airdrop"""
        for airdrop in self.data['airdrops']:
            if airdrop['id'] == airdrop_id:
                return airdrop
        return None
    
    def get_airdrops_by_category(self, category: str, subcategory: str) -> List[Dict]:
        """Get airdrops by category and subcategory"""
        return [
            airdrop for airdrop in self.data['airdrops']
            if airdrop['category'] == category.lower() and airdrop['subcategory'] == subcategory.lower()
        ]
    
    def get_all_airdrops(self) -> List[Dict]:
        """Get all airdrops"""
        return self.data['airdrops']
    
    def update_airdrop(self, airdrop_id: int, **kwargs):
        """Update airdrop fields"""
        for airdrop in self.data['airdrops']:
            if airdrop['id'] == airdrop_id:
                airdrop.update(kwargs)
                self.save_data()
                return True
        return False
    
    def delete_airdrop(self, airdrop_id: int):
        """Delete airdrop"""
        self.data['airdrops'] = [
            airdrop for airdrop in self.data['airdrops']
            if airdrop['id'] != airdrop_id
        ]
        self.save_data()
    
    # Support messages
    def save_support_message(self, user_id: int, message: str):
        """Save support message"""
        support_msg = {
            'user_id': user_id,
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'pending'
        }
        self.data['support_messages'].append(support_msg)
        self.save_data()
    
    def get_support_messages(self, status: str = None) -> List[Dict]:
        """Get support messages, optionally filtered by status"""
        if status:
            return [
                msg for msg in self.data['support_messages']
                if msg.get('status') == status
            ]
        return self.data['support_messages']
    
    def update_support_status(self, user_id: int, timestamp: str, status: str):
        """Update support message status"""
        for msg in self.data['support_messages']:
            if msg['user_id'] == user_id and msg['timestamp'] == timestamp:
                msg['status'] = status
                self.save_data()
                break