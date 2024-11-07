import json
import os
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Set environment variable for development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # For development only

from app import db
from flask import Blueprint, redirect, request, url_for, flash
from flask_login import login_required, login_user, logout_user
from models import User
from oauthlib.oauth2 import WebApplicationClient

GOOGLE_CLIENT_ID = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Make sure to use this redirect URL for proper Google OAuth callback
DEV_REDIRECT_URL = f'https://{os.environ["REPLIT_DEV_DOMAIN"]}/google_login/callback'

# Print setup instructions for Google OAuth configuration
print(f"""To make Google authentication work:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID
3. Add {DEV_REDIRECT_URL} to Authorized redirect URIs

For detailed instructions, see:
https://docs.replit.com/additional-resources/google-auth-in-flask#set-up-your-oauth-app--client
""")

# Initialize OAuth 2.0 client
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Create blueprint for Google authentication routes
google_auth = Blueprint("google_auth", __name__)

@google_auth.route("/google_login")
def login():
    """Initiate Google OAuth login flow"""
    try:
        # Find out what URL to hit for Google login
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL, verify=False).json()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]
        
        # Add debug print
        print(f"Using redirect URI: {DEV_REDIRECT_URL}")
        
        # Use library to construct the request for Google login
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=DEV_REDIRECT_URL,
            scope=["openid", "email", "profile"],
        )
        return redirect(request_uri)
    except Exception as e:
        print(f"Login error: {str(e)}")  # Add error logging
        flash("Failed to initialize login. Please try again.", "error")
        return redirect(url_for("game_routes.index"))

@google_auth.route("/google_login/callback")
def callback():
    """Handle the Google OAuth callback after successful login"""
    try:
        # Get authorization code Google sent back
        code = request.args.get("code")
        if not code:
            flash("Authentication failed. Please try again.", "error")
            return redirect(url_for("game_routes.index"))

        # Find out what URL to hit to get tokens
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL, verify=False).json()
        token_endpoint = google_provider_cfg["token_endpoint"]

        # Prepare and send request to get tokens
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url.replace('http://', 'https://'),
            redirect_url=DEV_REDIRECT_URL,
            code=code,
        )
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
            verify=False
        )

        # Parse the tokens
        client.parse_request_body_response(json.dumps(token_response.json()))

        # Get user info from Google
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body, verify=False)

        # Verify user email
        if not userinfo_response.json().get("email_verified"):
            flash("User email not verified by Google.", "error")
            return redirect(url_for("game_routes.index"))

        # Get user data
        userinfo = userinfo_response.json()
        email = userinfo["email"]
        username = userinfo.get("given_name", email.split("@")[0])

        # Create or update user in database
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(username=username, email=email)
            db.session.add(user)
            db.session.commit()
            flash("Account created successfully!", "success")
        else:
            flash("Welcome back!", "success")

        # Begin user session
        login_user(user)

        # Send user to homepage
        return redirect(url_for("game_routes.index"))

    except Exception as e:
        print(f"Callback error: {str(e)}")  # Add error logging
        flash("Authentication failed. Please try again.", "error")
        return redirect(url_for("game_routes.index"))

@google_auth.route("/logout")
@login_required
def logout():
    """Handle user logout"""
    try:
        logout_user()
        flash("You have been logged out successfully.", "info")
    except Exception as e:
        print(f"Logout error: {str(e)}")  # Add error logging
        flash("Logout failed. Please try again.", "error")
    return redirect(url_for("game_routes.index"))
