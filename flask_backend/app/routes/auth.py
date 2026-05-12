from flask import Blueprint, request, redirect, session, url_for, jsonify, render_template
from services.supabase_client import supabase, engine
from sqlalchemy import text
from functools import wraps

auth = Blueprint('auth', __name__)

def login_required(f):
    """
    Decorator to protect routes from unauthorized access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('core.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth.route('/auth/login')
def login():
    """
    Initiates the Google OAuth flow via Supabase.
    """
    # redirect_to is where Supabase will send the user AFTER Google login
    # In local dev, this is our callback route
    scheme = "https" if request.is_secure else "http"
    callback_url = f"{scheme}://{request.host}/auth/callback"
    
    try:
        # Request Supabase to start Google OAuth
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": callback_url
            }
        })
        
        # This will be the Google Auth URL
        return redirect(response.url)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth.route('/auth/callback')
def callback():
    """
    Supabase redirects here after successful Google login.
    Handles both Fragment (Implicit) and Code (PKCE) flows.
    """
    return """
    <html>
        <body style="font-family: sans-serif; padding: 20px;">
            <h3>Processing login...</h3>
            <p id="status">Checking for tokens...</p>
            <div id="debug" style="background: #f4f4f4; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 12px; margin-top: 20px;">
                <strong>Debug Info:</strong><br>
                URL: <span id="url"></span><br>
                Hash: <span id="hash"></span><br>
                Search: <span id="search"></span>
            </div>
            <script>
                const url = window.location.href;
                const hash = window.location.hash;
                const search = window.location.search;
                const params = new URLSearchParams(search);

                document.getElementById('url').innerText = url;
                document.getElementById('hash').innerText = hash || "(none)";
                document.getElementById('search').innerText = search || "(none)";

                if (hash) {
                    document.getElementById('status').innerText = "Token found in fragment. Redirecting...";
                    window.location.href = "/auth/session?" + hash.substring(1);
                } else if (params.has('code')) {
                    document.getElementById('status').innerText = "Auth code found in query. Redirecting...";
                    window.location.href = "/auth/session" + search;
                } else if (params.has('error')) {
                    document.getElementById('status').innerHTML = "<b>OAuth Error:</b> " + params.get('error_description');
                } else {
                    document.getElementById('status').innerText = "No token or code found. Please check your Supabase redirect settings.";
                }
            </script>
        </body>
    </html>
    """

@auth.route('/auth/session')
def set_session():
    """
    Captures tokens or codes, validates @umak.edu.ph domain, and sets up session.
    """
    access_token = request.args.get('access_token')
    refresh_token = request.args.get('refresh_token')
    code = request.args.get('code')
    
    try:
        if code:
            # Handle PKCE Code Exchange
            res = supabase.auth.exchange_code_for_session({"auth_code": code})
            session_data = res.session
            user = res.user
            access_token = session_data.access_token
            refresh_token = session_data.refresh_token
        elif access_token:
            # Handle Implicit Flow
            user_response = supabase.auth.get_user(access_token)
            user = user_response.user
        else:
            return "No valid session data found", 400

        email = user.email
        
        # 1. VALIDATION: Check for @umak.edu.ph
        if not email.endswith('@umak.edu.ph'):
            supabase.auth.sign_out()
            return render_template('unauthorized.html', email=email)

        # 2. Check if user exists in profiles table
        profile_check = supabase.table('profiles').select("id").eq("id", user.id).execute()
        
        # Store tokens and basic user data in session
        session['access_token'] = access_token
        session['refresh_token'] = refresh_token
        session['temp_user'] = {
            "id": user.id,
            "email": user.email,
            "user_metadata": user.user_metadata
        }

        # 3. REDIRECT: New user vs Existing user
        if not profile_check.data:
            return redirect(url_for('auth.onboarding'))
        
        # If exists, finalize session and go to dashboard
        session['user'] = session.pop('temp_user')
        return redirect(url_for('core.dashboard'))
        
    except Exception as e:
        print(f"Session Error: {e}")
        return f"Authentication failed: {str(e)}", 500


@auth.route('/onboarding')
def onboarding():
    """
    Shows the onboarding page with T&C and logo animation.
    """
    if 'temp_user' not in session:
        return redirect(url_for('core.login'))
    return render_template('onboarding.html', user=session['temp_user'])

@auth.route('/onboarding/complete', methods=['POST'])
def complete_onboarding():
    """
    Finalizes the registration after agreeing to terms.
    """
    if 'temp_user' not in session or 'access_token' not in session:
        return redirect(url_for('core.login'))
    
    user = session['temp_user']
    access_token = session['access_token']
    
    # 1. Create the profile in Supabase (using user's token to satisfy RLS)
    try:
        # Set the JWT for this specific request
        supabase.postgrest.auth(access_token)
        
        supabase.table('profiles').upsert({
            "id": str(user['id']),
            "email": user['email'],
            "full_name": user['user_metadata'].get('full_name'),
            "avatar_url": user['user_metadata'].get('avatar_url'),
            "updated_at": "now()"
        }).execute()
        
        # 2. Move from temp_user to full user session
        session['user'] = session.pop('temp_user')
        return redirect(url_for('core.dashboard'))
    except Exception as e:
        print(f"Onboarding completion error: {e}")
        return "Failed to complete onboarding", 500

@auth.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html', email="Unknown")

@auth.route('/auth/logout')
def logout():
    """
    Clears the session and signs out from Supabase.
    """
    supabase.auth.sign_out()
    session.clear()
    return redirect(url_for('core.home'))

@auth.route('/auth/user')
def get_current_user():
    """
    Helper route to check current session user.
    """
    return jsonify(session.get('user', {"message": "Not logged in"}))
