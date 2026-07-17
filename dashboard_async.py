"""
Dashboard Async Utils - Optimize admin dashboard performance
Implements pagination, caching, and async loading
"""

import json
from datetime import datetime, timedelta

class DashboardCache:
    """In-memory cache for dashboard data with TTL"""
    
    def __init__(self, ttl_seconds=300):  # 5 minutes default
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key):
        """Get value from cache if not expired"""
        if key not in self.cache:
            return None
        
        value, timestamp = self.cache[key]
        if datetime.now() - timestamp > timedelta(seconds=self.ttl):
            del self.cache[key]
            return None
        
        return value
    
    def set(self, key, value):
        """Store value in cache with timestamp"""
        self.cache[key] = (value, datetime.now())
    
    def clear(self, key=None):
        """Clear cache entry or entire cache"""
        if key:
            self.cache.pop(key, None)
        else:
            self.cache.clear()


class PaginationHelper:
    """Helper for paginating large datasets"""
    
    @staticmethod
    def paginate(items, page=1, per_page=20):
        """
        Paginate items list
        Returns: (paginated_items, total_pages, has_next, has_prev)
        """
        if isinstance(items, dict):
            items = list(items.values())
        
        total = len(items)
        total_pages = (total + per_page - 1) // per_page
        
        # Validate page number
        page = max(1, min(page, total_pages))
        
        start = (page - 1) * per_page
        end = start + per_page
        
        paginated = items[start:end]
        
        return {
            'items': paginated,
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'start_index': start + 1,
            'end_index': min(end, total)
        }
    
    @staticmethod
    def get_page_range(page, total_pages, window=5):
        """Get range of pages to display in pagination UI"""
        half = window // 2
        start = max(1, page - half)
        end = min(total_pages, start + window - 1)
        
        if end - start < window - 1:
            start = max(1, end - window + 1)
        
        return list(range(start, end + 1))


class AdminDashboardHelper:
    """Helper methods for admin dashboard optimization"""
    
    cache = DashboardCache(ttl_seconds=300)
    
    @staticmethod
    def get_users_paginated(users_dict, page=1, per_page=20, firebase_get=None):
        """
        Get paginated user list with usage stats
        Includes caching to reduce database calls
        """
        try:
            # Check cache first
            cache_key = f"users_page_{page}_{per_page}"
            cached = AdminDashboardHelper.cache.get(cache_key)
            if cached:
                return cached
            
            # Get all users and usages
            if not users_dict:
                users_dict = firebase_get('/users') or {}
            
            usages = firebase_get('/usage') or {}
            
            # Build user list with stats
            user_list = []
            for username, user_data in users_dict.items():
                usage = usages.get(username, {'ban7': 0, 'spam_log': 0, 'is_pro': False})
                
                user_list.append({
                    'username': username,
                    'email': user_data.get('email', 'N/A'),
                    'is_pro': user_data.get('is_pro', False),
                    'created_at': user_data.get('created_at', 'N/A'),
                    'ban7_usage': usage.get('ban7', 0),
                    'spam_log_usage': usage.get('spam_log', 0)
                })
            
            # Paginate
            result = PaginationHelper.paginate(user_list, page, per_page)
            
            # Cache result
            AdminDashboardHelper.cache.set(cache_key, result)
            
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_keys_paginated(keys_dict, page=1, per_page=20, firebase_get=None):
        """
        Get paginated key list
        Includes filtering by status
        """
        try:
            # Check cache
            cache_key = f"keys_page_{page}_{per_page}"
            cached = AdminDashboardHelper.cache.get(cache_key)
            if cached:
                return cached
            
            if not keys_dict:
                keys_dict = firebase_get('/keys') or {}
            
            key_list = []
            for code, key_data in keys_dict.items():
                key_list.append({
                    'code': code,
                    'tool_name': key_data.get('tool_name', 'unknown'),
                    'is_lifetime': key_data.get('is_lifetime', False),
                    'expiry': key_data.get('expiry', 'N/A'),
                    'is_used': key_data.get('is_used', False),
                    'used_by': key_data.get('used_by', 'N/A'),
                    'created_at': key_data.get('created_at', 'N/A')
                })
            
            # Sort by created_at descending (newest first)
            key_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Paginate
            result = PaginationHelper.paginate(key_list, page, per_page)
            
            # Cache
            AdminDashboardHelper.cache.set(cache_key, result)
            
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_dashboard_stats(firebase_get=None):
        """
        Get dashboard statistics
        Lightweight aggregation for dashboard cards
        """
        try:
            # Check cache
            cache_key = "dashboard_stats"
            cached = AdminDashboardHelper.cache.get(cache_key)
            if cached:
                return cached
            
            users = firebase_get('/users') or {}
            usage = firebase_get('/usage') or {}
            visits = firebase_get('/visits') or {}
            
            total_users = len(users)
            pro_users = sum(1 for u in users.values() if u.get('is_pro', False))
            free_users = total_users - pro_users
            
            total_ban7 = sum(u.get('ban7', 0) for u in usage.values())
            total_spam_log = sum(u.get('spam_log', 0) for u in usage.values())
            
            today = datetime.now().strftime('%Y-%m-%d')
            visits_today = visits.get(today, 0) if visits else 0
            
            stats = {
                'total_users': total_users,
                'pro_users': pro_users,
                'free_users': free_users,
                'total_ban7': total_ban7,
                'total_spam_log': total_spam_log,
                'visits_today': visits_today,
                'pro_percentage': round((pro_users / total_users * 100) if total_users > 0 else 0, 2)
            }
            
            # Cache for 5 minutes
            AdminDashboardHelper.cache.set(cache_key, stats)
            
            return stats
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def clear_cache(key=None):
        """Clear cache for specific key or all"""
        AdminDashboardHelper.cache.clear(key)
