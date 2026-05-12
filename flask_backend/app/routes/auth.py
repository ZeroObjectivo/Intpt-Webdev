from flask import Blueprint, request, redirect, session, url_for, jsonify, render_template
from services.supabase_client import supabase, engine
from sqlalchemy import text
from functools import wraps
from postgrest.exceptions import APIError

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

def is_jwt_expired_error(error):
    return isinstance(error, APIError) and getattr(error, "code", None) == "PGRST303"

def apply_supabase_auth_token():
    access_token = session.get('access_token')
    if not access_token:
        return False

    supabase.postgrest.auth(access_token)
    return True

def refresh_supabase_auth():
    refresh_token = session.get('refresh_token')
    if not refresh_token:
        return False

    try:
        response = supabase.auth.refresh_session(refresh_token)
        auth_session = getattr(response, "session", None)
        access_token = getattr(auth_session, "access_token", None)
        new_refresh_token = getattr(auth_session, "refresh_token", refresh_token)

        if not access_token:
            return False

        session['access_token'] = access_token
        session['refresh_token'] = new_refresh_token
        supabase.postgrest.auth(access_token)
        return True
    except Exception as e:
        print(f"Supabase session refresh error: {e}")
        return False

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
    Note: Supabase uses a URL fragment (#access_token=...) which is 
    not visible to the server. We need a tiny bit of JS to capture it.
    """
    # For now, we will return a simple page that captures the token
    # and sends it to our session route.
    return """
    <html>
        <body>
            <p>Finishing login...</p>
            <script>
                // Get the hash part of the URL
                const hash = window.location.hash;
                if (hash) {
                    // Send the hash to our server to set the session
                    window.location.href = "/auth/session?" + hash.substring(1);
                } else {
                    document.body.innerHTML = "Login failed: No token found.";
                }
            </script>
        </body>
    </html>
    """

@auth.route('/auth/session')
def set_session():
    """
    Captures tokens, validates @umak.edu.ph domain, and checks if user is new.
    """
    access_token = request.args.get('access_token')
    refresh_token = request.args.get('refresh_token')
    
    if access_token:
        # 1. Get user info from Supabase
        user_response = supabase.auth.get_user(access_token)
        user = user_response.user
        email = user.email
        
        # 2. VALIDATION: Check for @umak.edu.ph
        if not email.endswith('@umak.edu.ph'):
            supabase.auth.sign_out()
            return render_template('unauthorized.html', email=email)

        # 3. Check if user exists in profiles table
        profile_check = supabase.table('profiles').select("id").eq("id", user.id).execute()
        
        # Store tokens and basic user data in session
        session['access_token'] = access_token
        session['refresh_token'] = refresh_token
        session['temp_user'] = user.model_dump()

        # 4. REDIRECT: New user vs Existing user
        if not profile_check.data:
            return redirect(url_for('auth.onboarding'))
        
        # If exists, finalize session and go to dashboard
        session['user'] = session.pop('temp_user')
        return redirect(url_for('core.dashboard'))
    
    return "Session creation failed", 400

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
