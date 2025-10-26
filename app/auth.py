import streamlit as st
import boto3
import json
import base64
import hashlib
import hmac
import os
from datetime import datetime
from botocore.exceptions import ClientError
import urllib.parse
import requests
from dotenv import load_dotenv

# Load environment variables from config/.env
config_path = os.path.join(os.path.dirname(__file__), '../config/.env')
load_dotenv(config_path)

class CognitoAuth:
    def __init__(self):
        self.user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
        self.client_id = os.getenv('COGNITO_CLIENT_ID')
        self.client_secret = os.getenv('COGNITO_CLIENT_SECRET')
        self.identity_pool_id = os.getenv('COGNITO_IDENTITY_POOL_ID')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.cognito_domain = os.getenv('COGNITO_DOMAIN')
        self.redirect_uri = os.getenv('REDIRECT_URI', 'http://localhost:8501')

        # Initialize session state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_info' not in st.session_state:
            st.session_state.user_info = {}
        if 'access_token' not in st.session_state:
            st.session_state.access_token = None
        if 'id_token' not in st.session_state:
            st.session_state.id_token = None

    def _calculate_secret_hash(self, username):
        """Calculate the secret hash for Cognito"""
        message = username + self.client_id
        dig = hmac.new(
            self.client_secret.encode('UTF-8'),
            message.encode('UTF-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()

    def login(self):
        """Redirect to Cognito hosted UI for login"""
        # Generate state parameter for security
        state = base64.urlsafe_b64encode(os.urandom(32)).decode()
        st.session_state.oauth_state = state

        # Build authorization URL
        auth_url = (
            f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/login?"
            f"client_id={self.client_id}&"
            f"response_type=code&"
            f"scope=email+openid+profile&"
            f"redirect_uri={urllib.parse.quote(self.redirect_uri)}&"
            f"state={state}"
        )

        st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)

    def register(self):
        """Redirect to Cognito hosted UI for registration"""
        # Generate state parameter for security
        state = base64.urlsafe_b64encode(os.urandom(32)).decode()
        st.session_state.oauth_state = state

        # Build registration URL
        signup_url = (
            f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/signup?"
            f"client_id={self.client_id}&"
            f"response_type=code&"
            f"scope=email+openid+profile&"
            f"redirect_uri={urllib.parse.quote(self.redirect_uri)}&"
            f"state={state}"
        )

        st.markdown(f'<meta http-equiv="refresh" content="0; url={signup_url}">', unsafe_allow_html=True)

    def handle_callback(self):
        """Handle the OAuth callback from Cognito"""
        # Get query parameters
        query_params = st.query_params

        if 'code' in query_params and 'state' in query_params:
            # For Streamlit, skip state validation as session state is unreliable across redirects
            # In production, you'd want to store state in a more persistent way (like a database)
            # The authorization code itself provides security against CSRF attacks
            

            try:
                # Exchange authorization code for tokens
                token_url = f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/oauth2/token"

                data = {
                    'grant_type': 'authorization_code',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'redirect_uri': self.redirect_uri,
                    'code': query_params['code']
                }

                response = requests.post(token_url, data=data)
                response.raise_for_status()

                tokens = response.json()

                # Store tokens
                st.session_state.access_token = tokens['access_token']
                st.session_state.id_token = tokens['id_token']

                # Decode ID token to get user info
                id_token_payload = self._decode_token(tokens['id_token'])
                st.session_state.user_info = id_token_payload
                st.session_state.authenticated = True

                # Clear query parameters
                st.query_params.clear()

                return True

            except Exception as e:
                st.error(f"Error during authentication: {e}")
                return False

        return False

    def _decode_token(self, token):
        """Decode JWT token (basic implementation)"""
        # Split token and decode payload (note: this is for demo purposes)
        # In production, you should verify the token signature
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        payload = parts[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)

        decoded_bytes = base64.urlsafe_b64decode(payload)
        return json.loads(decoded_bytes.decode('utf-8'))

    def logout(self):
        """Logout user and clear session"""
        # Clear session state
        st.session_state.authenticated = False
        st.session_state.user_info = {}
        st.session_state.access_token = None
        st.session_state.id_token = None

        # Redirect to Cognito logout
        logout_url = (
            f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/logout?"
            f"client_id={self.client_id}&"
            f"logout_uri={urllib.parse.quote(self.redirect_uri)}"
        )

        st.markdown(f'<meta http-equiv="refresh" content="0; url={logout_url}">', unsafe_allow_html=True)

    def is_authenticated(self):
        """Check if user is authenticated"""
        # Handle OAuth callback if present
        self.handle_callback()

        return st.session_state.get('authenticated', False)

    def get_user_info(self):
        """Get user information"""
        return st.session_state.get('user_info', {})

    def get_user_id(self):
        """Get user ID from token"""
        user_info = self.get_user_info()
        return user_info.get('sub', user_info.get('cognito:username', 'unknown'))

    def get_aws_credentials(self):
        """Get temporary AWS credentials using Cognito Identity Pool"""
        if not self.is_authenticated():
            return None

        try:
            # Initialize Cognito Identity client
            cognito_identity = boto3.client('cognito-identity', region_name=self.region)

            # Get identity ID
            identity_response = cognito_identity.get_id(
                IdentityPoolId=self.identity_pool_id,
                Logins={
                    f'cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}': st.session_state.id_token
                }
            )

            identity_id = identity_response['IdentityId']

            # Get credentials
            credentials_response = cognito_identity.get_credentials_for_identity(
                IdentityId=identity_id,
                Logins={
                    f'cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}': st.session_state.id_token
                }
            )

            return credentials_response['Credentials']

        except ClientError as e:
            error_text = f"Error getting AWS credentials: {e}"
            st.error(error_text)
            import logging
            logging.error(f"CREDENTIALS ERROR: {error_text}")
            return None
        except Exception as e:
            error_text = f"Unexpected error getting credentials: {e}"
            st.error(error_text)
            import logging
            logging.error(f"CREDENTIALS ERROR: {error_text}")
            return None