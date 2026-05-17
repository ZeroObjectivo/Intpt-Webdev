import logging
import os
from flask import Blueprint, request, redirect, session, url_for, jsonify, render_template, flash
from services.supabase_client import (
    supabase,
    supabase_service,
    engine,
    get_public_client,
    get_user_client,
)
from sqlalchemy import text
from functools import wraps
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__)

def normalize_domain(raw_value):
    raw = (raw_value or '').strip().lower()
    if not raw:
        return ''
    if '://' in raw:
        raw = raw.split('://', 1)[1]
    raw = raw.split('/', 1)[0]
    raw = raw.split('@')[-1]
    raw = raw.split(':', 1)[0]
    return raw.strip().strip('.')

def current_request_domain():
    forwarded = request.headers.get('X-Forwarded-Host', '')
    raw_host = forwarded.split(',')[0].strip() if forwarded else request.host
    return normalize_domain(raw_host)

def is_admin_domain_request():
    admin_domain = normalize_domain(os.getenv('ADMIN_DOMAIN', ''))
    host = current_request_domain()
    if admin_domain and host == admin_domain:
        return True
    return host.startswith('dev.')

def wants_json_response():
    if request.is_json:
        return True
    accept = (request.headers.get('Accept') or '').lower()
    if 'application/json' in accept:
        return True
    requested_with = (request.headers.get('X-Requested-With') or '').lower()
    return requested_with == 'xmlhttprequest'

def login_required(f):
    """
    Decorator to protect routes from unauthorized access.
    Proactively refreshes expired tokens before the route runs.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or 'access_token' not in session:
            if wants_json_response():
                return jsonify({"status": "error", "reason": "unauthenticated"}), 401
            return redirect(url_for('core.login'))

        # Proactively refresh if we know the token has expired
        expires_at = session.get('expires_at')
        now_ts = __import__('time').time()
        try:
            expires_ts = float(expires_at) if expires_at is not None else None
        except (TypeError, ValueError):
            expires_ts = None
        if expires_ts and expires_ts < now_ts:
            if not refresh_supabase_auth():
                session.clear()
                if wants_json_response():
                    return jsonify({"status": "error", "reason": "session_expired"}), 401
                return redirect(url_for('core.login', error="session_expired"))

        return f(*args, **kwargs)
    return decorated_function

def is_jwt_error(error):
    """Detect any JWT-related Supabase error (expired, malformed, invalid)."""
    if not isinstance(error, APIError):
        return False
    code = getattr(error, "code", None)
    # PGRST301 = malformed JWT, PGRST302 = no anonymous role, PGRST303 = expired JWT
    return code in ("PGRST301", "PGRST302", "PGRST303")

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
        expires_at = getattr(auth_session, "expires_at", None)
        if expires_at is not None:
            session['expires_at'] = expires_at
        return True
    except Exception as e:
        logger.error("Supabase session refresh error: %s", e)
        return False

@auth.route('/auth/login')
def login():
    """
    Initiates the Google OAuth flow via Supabase.
    """
    # redirect_to is where Supabase will send the user AFTER Google login
    # In local dev, this is our callback route
    # Behind a reverse proxy (DO App Platform), check X-Forwarded-Proto
    scheme = request.headers.get('X-Forwarded-Proto', 'https' if request.is_secure else 'http')
    forwarded_host = request.headers.get('X-Forwarded-Host', '')
    callback_host = forwarded_host.split(',')[0].strip() if forwarded_host else request.host
    callback_url = f"{scheme}://{callback_host}/auth/callback"
    
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
        logger.error("OAuth login error: %s", e)
        return jsonify({"error": "Login failed. Please try again."}), 500

@auth.route('/auth/callback')
def callback():
    """
    Supabase redirects here after successful Google login.
    Handles both Fragment (Implicit) and Code (PKCE) flows.
    """
    return """
    <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Signing In...</title>
            <script defer src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>
            <style>
                html, body {
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 100%;
                    background: #ffffff;
                    overflow: hidden;
                }

                body {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-family: 'Metropolis', 'Inter', system-ui, sans-serif;
                }

                .loader-wrap {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 12px;
                    opacity: 1;
                    transition: opacity 800ms ease-out;
                }

                .loader-wrap.exit {
                    opacity: 0;
                }

                #logoTransition {
                    width: min(360px, 72vw);
                    height: min(360px, 72vw);
                    max-width: 420px;
                    max-height: 420px;
                }

                #status {
                    margin: 0;
                    color: #64748b;
                    font-size: 14px;
                    font-weight: 600;
                    letter-spacing: 0.02em;
                }
            </style>
        </head>
        <body>
            <div class="loader-wrap" id="loaderWrap">
                <div id="logoTransition" aria-label="Loading animation"></div>
                <p id="status">Finalizing login...</p>
            </div>

            <script>
                const hash = window.location.hash;
                const search = window.location.search;
                const params = new URLSearchParams(search);
                const status = document.getElementById('status');
                const loaderWrap = document.getElementById('loaderWrap');
                let hasRedirected = false;

                if (window.lottie) {
                    window.lottie.loadAnimation({
                        container: document.getElementById('logoTransition'),
                        renderer: 'svg',
                        loop: true,
                        autoplay: true,
                        path: '/static/animations/flow1.json'
                    });
                }

                function proceed(url) {
                    if (hasRedirected) return;
                    hasRedirected = true;
                    loaderWrap.classList.add('exit');
                    setTimeout(() => window.location.replace(url), 800);
                }

                if (hash) {
                    proceed("/auth/session?" + hash.substring(1));
                } else if (params.has('code')) {
                    proceed("/auth/session" + search);
                } else if (params.has('error')) {
                    status.textContent = "Authentication failed. Please try signing in again.";
                } else {
                    status.textContent = "Missing authentication response. Please try signing in again.";
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
            # In implicit flow, we don't get expires_at directly, so we can't refresh.
            # This flow is less common and secure. We'll proceed but without refresh capabilities.
        else:
            return "No valid session data found", 400

        email = user.email

        # 1. VALIDATION: Check for @umak.edu.ph
        if not email.endswith('@umak.edu.ph'):
            # Automatically record as a verification dispute for admin review
            # Using service client to bypass RLS and DNS issues with raw SQL engine
            try:
                if supabase_service:
                    full_name = user.user_metadata.get('full_name', 'Unknown User')
                    
                    # Check for duplicate
                    existing = supabase_service.table('verification_disputes').select("id").eq("email", email).execute()
                    
                    if not existing.data:
                        supabase_service.table('verification_disputes').insert({
                            "email": email,
                            "full_name": full_name,
                            "reason": f"Restricted Domain Attempt: {email}",
                            "status": "auto_rejected"
                        }).execute()
            except Exception as dispute_error:
                logger.error("Failed to record dispute via Supabase API: %s", dispute_error)

            supabase.auth.sign_out()
            return render_template('unauthorized.html', email=email)

        # Store tokens and basic user data in session
        session['access_token'] = access_token
        session['refresh_token'] = refresh_token
        # Store expiry so login_required can proactively refresh
        if 'session_data' in locals() and session_data:
            expires_at = getattr(session_data, 'expires_at', None)
            if expires_at:
                session['expires_at'] = expires_at
        session['temp_user'] = {
            "id": user.id,
            "email": user.email,
            "user_metadata": user.user_metadata
        }

        is_admin_host = is_admin_domain_request()

        # 2. Check if user exists in profiles table
        profile_client = supabase_service or get_public_client()
        profile_check = profile_client.table('profiles').select("id").eq("id", user.id).execute()

        # 3. REDIRECT: New user vs Existing user
        if not profile_check.data:
            # Never onboard fresh users through the admin domain.
            if is_admin_host:
                session.clear()
                supabase.auth.sign_out()
                return render_template('unauthorized.html',
                                       email=email,
                                       admin_restricted=True)
            return redirect(url_for('auth.onboarding'))
        
        # Fetch full profile to get role and other details
        profile_res = profile_client.table('profiles').select("*").eq("id", user.id).single().execute()

        # Admin domain gate: only admin-portal roles can log in on dev.heronshub.social
        if is_admin_host:
            user_role = (profile_res.data.get('role', '') if profile_res.data else '').strip().lower()
            if user_role not in ('admin', 'super_admin', 'superadmin', 'account_manager', 'content_moderator', 'content_manager'):
                session.clear()
                supabase.auth.sign_out()
                return render_template('unauthorized.html',
                                       email=email,
                                       admin_restricted=True)

        # Finalize session and go to post-login transition
        session['user'] = session.pop('temp_user')
        if profile_res.data:
            session['user'].update(profile_res.data)

        # On admin domain, go straight to admin dashboard
        if is_admin_host:
            return redirect(url_for('admin.dashboard'))

        return redirect(url_for('auth.post_login_transition'))
        
    except Exception as e:
        logger.error("Session error: %s", e)
        return "Authentication failed. Please try again.", 500


@auth.route('/onboarding')
def onboarding():
    """
    Shows the onboarding page with multi-step flow:
    1. Terms and Conditions
    2. Profile Setup (College, Course, Bio, etc.)
    """
    if 'temp_user' not in session:
        return redirect(url_for('core.login'))

    # Fetch colleges/institutes for Step 2 dropdown
    profile_client = supabase_service or get_public_client()
    colleges = []
    institutes = []
    try:
        units_res = profile_client.table('colleges_institutes').select("name, full_name, type").order('name').execute()
        colleges = [u for u in units_res.data if u['type'] == 'College']
        institutes = [u for u in units_res.data if u['type'] == 'Institute']
    except Exception as e:
        logger.warning("Could not load academic units for onboarding: %s", e)

    return render_template('onboarding.html', 
                           user=session['temp_user'],
                           colleges=colleges,
                           institutes=institutes)

@auth.route('/auth/post-login')
@login_required
def post_login_transition():
    """Short transition screen before entering the dashboard."""
    return render_template('post_login_transition.html')

@auth.route('/onboarding/complete', methods=['POST'])
def complete_onboarding():
    """
    Finalizes the registration after agreeing to terms and entering profile info.
    """
    if 'temp_user' not in session or 'access_token' not in session:
        return redirect(url_for('core.login'))
    
    user = session['temp_user']
    
    # Extract profile fields from form
    college = request.form.get('college', '').strip()
    course = request.form.get('course', '').strip()
    level = request.form.get('level', '').strip()
    bio = request.form.get('bio', '').strip()
    contact_number = request.form.get('contact_number', '').strip()
    contact_privacy = request.form.get('contact_privacy', 'only_me').strip()

    # Required field validation
    if not all([college, course, level]):
        flash("Please fill in all required academic information.", "error")
        return redirect(url_for('auth.onboarding'))

    # 1. Create the profile in Supabase (using user's token to satisfy RLS)
    try:
        user_client = get_user_client()

        # Handle social links (imported here to avoid circular dependency)
        from .core import normalize_social_links_input
        social_links_raw = []
        social_visibility_raw = []
        for i in range(1, 4):
            url = request.form.get(f'social_link_{i}')
            vis = request.form.get(f'social_link_visibility_{i}')
            if url:
                social_links_raw.append(url)
                social_visibility_raw.append(vis or 'public')
        
        normalized_social_links = normalize_social_links_input(social_links_raw, social_visibility_raw)

        metadata = user.get('user_metadata') or {}
        profile_data = {
            "id": str(user['id']),
            "email": user['email'],
            "full_name": metadata.get('full_name'),
            "avatar_url": metadata.get('avatar_url'),
            "college": college,
            "course": course,
            "level": level,
            "bio": bio,
            "contact_number": contact_number,
            "contact_privacy": contact_privacy
        }

        user_client.table('profiles').upsert(profile_data).execute()

        # 1b. Create social links separately in the correct table
        if normalized_social_links:
            user_client.table('profile_social_links').delete().eq('profile_id', str(user['id'])).execute()
            for link in normalized_social_links:
                user_client.table('profile_social_links').insert({
                    "profile_id": str(user['id']),
                    "platform": link["platform"],
                    "url": link["url"],
                    "visibility": link["visibility"],
                    "position": link["position"],
                }).execute()
        
        # 2. Move from temp_user to full user session
        session['user'] = session.pop('temp_user')

        if is_admin_domain_request():
            profile_res = user_client.table('profiles').select("role").eq("id", user['id']).single().execute()
            role = (profile_res.data.get('role', '') if profile_res.data else '').strip().lower()
            if role in ('admin', 'super_admin', 'superadmin', 'account_manager', 'content_moderator', 'content_manager'):
                return redirect(url_for('admin.dashboard'))

            session.clear()
            supabase.auth.sign_out()
            return render_template('unauthorized.html',
                                   email=user['email'],
                                   admin_restricted=True)

        return redirect(url_for('auth.post_login_transition'))
    except Exception as e:
        logger.error("Onboarding completion error: %s", e)
        flash("Failed to save profile information. Please try again.", "error")
        return redirect(url_for('auth.onboarding'))

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
