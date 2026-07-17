"""
User Management Module - Handle user lifecycle, subscriptions, downgrades
"""

from datetime import datetime, timedelta
import json

class UserManager:
    """Manage user accounts, subscriptions, and downgrade logic"""
    
    @staticmethod
    def check_and_downgrade_expired_users(firebase_get, firebase_update):
        """
        Check all pro users and auto-downgrade those whose subscription expired
        Should be called periodically (cron job or on-demand)
        """
        try:
            users = firebase_get('/users') or {}
            downgrades = []
            
            for username, user_data in users.items():
                if not user_data.get('is_pro'):
                    continue
                
                # Check user-level expiry
                pro_expiry = user_data.get('pro_expiry')
                if pro_expiry:
                    expiry_date = datetime.fromisoformat(pro_expiry)
                    if datetime.now() > expiry_date:
                        # Downgrade user
                        firebase_update(f'/users/{username}', {'is_pro': False})
                        firebase_update(f'/usage/{username}', {'is_pro': False})
                        
                        downgrades.append({
                            'username': username,
                            'reason': 'pro_expiry',
                            'expiry_date': pro_expiry
                        })
            
            return {
                'success': True,
                'downgraded_count': len(downgrades),
                'downgrades': downgrades
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def check_and_downgrade_tool_expired_users(firebase_get, firebase_update):
        """
        Check individual tool subscriptions and remove expired ones
        """
        try:
            pro_tools = firebase_get('/user_pro_tools') or {}
            downgrades = []
            
            for username, tools in pro_tools.items():
                for tool_name, tool_data in list(tools.items()):
                    if tool_data.get('is_lifetime'):
                        continue
                    
                    expiry = tool_data.get('expiry')
                    if expiry:
                        try:
                            expiry_date = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                            if datetime.now() > expiry_date:
                                # Remove expired tool access
                                del tools[tool_name]
                                firebase_update(f'/user_pro_tools/{username}', tools)
                                
                                downgrades.append({
                                    'username': username,
                                    'tool': tool_name,
                                    'expiry_date': expiry
                                })
                        except ValueError:
                            pass
            
            return {
                'success': True,
                'downgraded_count': len(downgrades),
                'downgrades': downgrades
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def downgrade_user_manual(username, firebase_get, firebase_update):
        """
        Admin manually downgrade a user to FREE
        """
        try:
            users = firebase_get('/users') or {}
            
            if username not in users:
                return {'success': False, 'error': 'User not found'}
            
            # Remove pro status
            firebase_update(f'/users/{username}', {
                'is_pro': False,
                'pro_expiry': None,
                'downgraded_at': datetime.now().isoformat()
            })
            
            # Reset usage
            firebase_update(f'/usage/{username}', {'is_pro': False})
            
            # Remove all tool-specific access
            firebase_update(f'/user_pro_tools/{username}', {})
            
            return {
                'success': True,
                'message': f'User {username} downgraded to FREE',
                'username': username
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def upgrade_user_pro(username, duration_days=None, firebase_get=None, firebase_update=None):
        """
        Upgrade user to PRO with optional expiry date
        duration_days: days until expiry (None = lifetime)
        """
        try:
            if duration_days is None:
                expiry = None
            else:
                expiry = (datetime.now() + timedelta(days=duration_days)).isoformat()
            
            firebase_update(f'/users/{username}', {
                'is_pro': True,
                'pro_expiry': expiry,
                'upgraded_at': datetime.now().isoformat()
            })
            
            firebase_update(f'/usage/{username}', {'is_pro': True})
            
            return {
                'success': True,
                'message': f'User {username} upgraded to PRO',
                'expiry': expiry
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_user_subscription_status(username, firebase_get):
        """
        Get complete subscription status of a user
        """
        try:
            user = firebase_get(f'/users/{username}') or {}
            pro_tools = firebase_get(f'/user_pro_tools/{username}') or {}
            
            status = {
                'username': username,
                'is_pro': user.get('is_pro', False),
                'pro_expiry': user.get('pro_expiry'),
                'tools': {}
            }
            
            # Check each tool subscription
            for tool_name, tool_data in pro_tools.items():
                is_lifetime = tool_data.get('is_lifetime', False)
                expiry = tool_data.get('expiry')
                
                is_active = True
                if not is_lifetime and expiry:
                    try:
                        expiry_date = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                        is_active = datetime.now() < expiry_date
                    except ValueError:
                        is_active = False
                
                status['tools'][tool_name] = {
                    'is_active': is_active,
                    'is_lifetime': is_lifetime,
                    'expiry': expiry
                }
            
            return status
        except Exception as e:
            return None
