# ============ INTEGRATION FILE FOR app.py ============
# Add these imports at the top of app.py (lines 1-35)

from google_auth import GoogleOAuthHandler, create_user_from_google
from user_management import UserManager
from dashboard_async import AdminDashboardHelper, PaginationHelper

# ============ NEW ROUTES - Google OAuth ============

@app.route('/api/google/auth_url', methods=['GET'])
def google_auth_url():
    """Get Google OAuth authorization URL"""
    try:
        url = GoogleOAuthHandler.get_auth_url()
        return jsonify({'success': True, 'auth_url': url})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/google/callback', methods=['POST'])
def google_callback():
    """Handle Google OAuth callback"""
    try:
        data = request.json
        code = data.get('code')
        
        if not code:
            return jsonify({'success': False, 'error': 'No authorization code'})
        
        # Exchange code for token
        token_response = GoogleOAuthHandler.exchange_code_for_token(code)
        if not token_response or 'error' in token_response:
            return jsonify({'success': False, 'error': 'Failed to get access token'})
        
        id_token = token_response.get('id_token')
        if not id_token:
            return jsonify({'success': False, 'error': 'No ID token in response'})
        
        # Verify token
        google_data = GoogleOAuthHandler.verify_id_token(id_token)
        if not google_data:
            return jsonify({'success': False, 'error': 'Invalid ID token'})
        
        # Create or get user
        user_data = create_user_from_google(google_data)
        users = firebase_get('/users') or {}
        
        email = google_data.get('email')
        username = None
        
        # Check if user exists
        for u_name, u_data in users.items():
            if u_data.get('email') == email or u_data.get('google_id') == google_data.get('google_id'):
                username = u_name
                break
        
        # Create new user if doesn't exist
        if not username:
            username = user_data['username']
            counter = 1
            base_username = username
            while username in users:
                username = f"{base_username}{counter}"
                counter += 1
            
            firebase_set(f'/users/{username}', user_data)
            firebase_set(f'/usage/{username}', {
                'ban7': 0,
                'spam_log': 0,
                'is_pro': False
            })
        
        # Login user
        session['username'] = username
        session['authenticated'] = True
        session['email'] = email
        
        return jsonify({
            'success': True,
            'message': 'Google login successful',
            'username': username,
            'email': email
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ NEW ROUTES - User Downgrade Management ============

@app.route('/api/admin/downgrade_expired', methods=['POST'])
def downgrade_expired():
    """Auto-downgrade users with expired subscriptions"""
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        result = UserManager.check_and_downgrade_expired_users(firebase_get, firebase_update)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/downgrade_tool_expired', methods=['POST'])
def downgrade_tool_expired():
    """Auto-downgrade tool-specific expired subscriptions"""
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        result = UserManager.check_and_downgrade_tool_expired_users(firebase_get, firebase_update)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/downgrade_user/<username>', methods=['POST'])
def downgrade_user_manual(username):
    """Admin manually downgrade a user"""
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        result = UserManager.downgrade_user_manual(username, firebase_get, firebase_update)
        AdminDashboardHelper.clear_cache()  # Clear dashboard cache
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/upgrade_user_pro/<username>', methods=['POST'])
def upgrade_user_pro_manual(username):
    """Admin manually upgrade user to PRO"""
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        data = request.json
        duration_days = data.get('duration_days')  # None = lifetime
        
        result = UserManager.upgrade_user_pro(username, duration_days, firebase_get, firebase_update)
        AdminDashboardHelper.clear_cache()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/user/subscription_status', methods=['GET'])
def user_subscription_status():
    """Get user's subscription status"""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    try:
        username = session.get('username')
        status = UserManager.get_user_subscription_status(username, firebase_get)
        
        if status:
            return jsonify({'success': True, 'status': status})
        else:
            return jsonify({'success': False, 'error': 'User not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ NEW ROUTES - Dashboard Pagination & Caching ============

@app.route('/api/admin/users_paginated', methods=['GET'])
def admin_users_paginated():
    """Get paginated user list with async loading"""
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = AdminDashboardHelper.get_users_paginated(None, page, per_page, firebase_get)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/keys_paginated', methods=['GET'])
def admin_keys_paginated():
    """Get paginated keys list with async loading"""
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = AdminDashboardHelper.get_keys_paginated(None, page, per_page, firebase_get)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/dashboard_stats', methods=['GET'])
def admin_dashboard_stats():
    """Get dashboard statistics (cached)"""
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        stats = AdminDashboardHelper.get_dashboard_stats(firebase_get)
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/clear_cache', methods=['POST'])
def clear_dashboard_cache():
    """Clear dashboard cache"""
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        AdminDashboardHelper.clear_cache()
        return jsonify({'success': True, 'message': 'Cache cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ ENVIRONMENT VARIABLES TO ADD TO tool.env ============
# Add these to your .env file:
#
# GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
# GOOGLE_CLIENT_SECRET=your-client-secret
# GOOGLE_REDIRECT_URI=https://yoursite.com/api/google/callback
#
# For local testing:
# GOOGLE_REDIRECT_URI=http://localhost:5000/api/google/callback
