"""
Google OAuth Authentication Module for Free Fire Tools
Handles Google Sign-In via OAuth 2.0
"""

import os
import requests
import json
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.id_token import verify_oauth2_token
import hashlib

# Google OAuth Config
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your-client-id.apps.googleusercontent.com')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/google/callback')

class GoogleOAuthHandler:
    """Handle Google OAuth 2.0 authentication flow"""
    
    @staticmethod
    def get_auth_url():
        """Generate Google OAuth authorization URL"""
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}&"
            f"redirect_uri={GOOGLE_REDIRECT_URI}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile&"
            f"access_type=offline"
        )
    
    @staticmethod
    def exchange_code_for_token(code):
        """Exchange authorization code for access token"""
        try:
            token_url = "https://oauth2.googleapis.com/token"
            payload = {
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'code': code,
                'redirect_uri': GOOGLE_REDIRECT_URI,
                'grant_type': 'authorization_code'
            }
            
            response = requests.post(token_url, data=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"Error exchanging code: {e}")
            return None
    
    @staticmethod
    def verify_id_token(id_token):
        """Verify Google ID token"""
        try:
            # Verify token signature and claims
            idinfo = verify_oauth2_token(id_token, Request(), GOOGLE_CLIENT_ID)
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                return None
            
            return {
                'google_id': idinfo['sub'],
                'email': idinfo.get('email'),
                'name': idinfo.get('name'),
                'picture': idinfo.get('picture'),
                'email_verified': idinfo.get('email_verified', False)
            }
        except Exception as e:
            print(f"Error verifying token: {e}")
            return None
    
    @staticmethod
    def get_user_info(access_token):
        """Get user info from Google using access token"""
        try:
            url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'google_id': data.get('id'),
                    'email': data.get('email'),
                    'name': data.get('name'),
                    'picture': data.get('picture'),
                    'email_verified': data.get('verified_email', False)
                }
            return None
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None


def create_user_from_google(google_data):
    """
    Create or get user from Google OAuth data
    Returns tuple: (username, email, user_data)
    """
    try:
        email = google_data.get('email')
        google_id = google_data.get('google_id')
        name = google_data.get('name', email.split('@')[0])
        
        # Generate username from email
        username = email.split('@')[0]
        # Add google_id suffix if username already exists
        base_username = username
        counter = 1
        
        return {
            'username': username,
            'email': email,
            'google_id': google_id,
            'name': name,
            'picture': google_data.get('picture', ''),
            'password': hashlib.sha256(google_id.encode()).hexdigest(),  # Hash google_id as password
            'created_at': datetime.now().isoformat(),
            'is_pro': False,
            'google_auth': True,
            'email_verified': google_data.get('email_verified', True)
        }
    except Exception as e:
        print(f"Error creating user from Google data: {e}")
        return None
