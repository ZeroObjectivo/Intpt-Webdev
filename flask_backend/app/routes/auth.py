from flask import Blueprint, request, redirect, session, url_for, jsonify, render_template
from services.supabase_client import supabase
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
    Captures tokens, validates @umak.edu.ph domain, and syncs to DB.
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
            # Sign out immediately from Supabase
            supabase.auth.sign_out()
            return render_template('unauthorized.html', email=email)

        # 3. Store in Flask Session
        session['access_token'] = access_token
        session['refresh_token'] = refresh_token
        session['user'] = user.model_dump()
        
        # 4. SYNC TO DATABASE: Save user to the profiles table
        try:
            user_id = user.id
            full_name = user.user_metadata.get('full_name')
            avatar_url = user.user_metadata.get('avatar_url')
            
            # Use 'upsert' to insert if new, or update if exists
            supabase.table('profiles').upsert({
                "id": str(user_id),
                "email": email,
                "full_name": full_name,
                "avatar_url": avatar_url,
                "updated_at": "now()"
            }).execute()
            
        except Exception as e:
            print(f"Database sync error: {e}")
            # We don't block the login if DB sync fails, but we should log it
            
        return redirect(url_for('core.dashboard'))
    
    return "Session creation failed", 400

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
