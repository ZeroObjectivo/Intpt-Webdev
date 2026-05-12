from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from .auth import (
    apply_supabase_auth_token,
    is_jwt_expired_error,
    login_required,
    refresh_supabase_auth,
)
from services.supabase_client import supabase

core = Blueprint('core', __name__)

@core.route('/')
def home():
    user = session.get('user')
    return render_template('home.html', user=user)

@core.route('/dashboard')
@login_required
def dashboard():
    user_session = session.get('user')
    user_id = user_session.get('id')
    apply_supabase_auth_token()

    try:
        profile, posts = load_dashboard_data(user_id)
    except Exception as e:
        if is_jwt_expired_error(e) and refresh_supabase_auth():
            profile, posts = load_dashboard_data(user_id)
        elif is_jwt_expired_error(e):
            session.clear()
            flash("Your login session expired. Please sign in again.", "error")
            return redirect(url_for('core.login'))
        else:
            raise
    
    return render_template('dashboard.html', user=profile, posts=posts)

def load_dashboard_data(user_id):
    
    # 1. Fetch User Profile from DB
    profile_response = supabase.table('profiles').select("*").eq("id", user_id).single().execute()
    profile = profile_response.data
    
    # 2. Fetch Latest Posts with Profile info
    posts_response = supabase.table('posts').select("*, profiles(full_name, avatar_url)").order("created_at", desc=True).limit(10).execute()
    posts = posts_response.data
    
    return profile, posts

@core.route('/posts/create', methods=['POST'])
@login_required
def create_post():
    user_session = session.get('user')
    user_id = user_session.get('id')
    access_token = session.get('access_token')
    
    content = request.form.get('content')
    category = request.form.get('category', 'General')
    
    if not content:
        flash("Post content cannot be empty!", "error")
        return redirect(url_for('core.dashboard'))

    if not access_token:
        flash("Your login session expired. Please sign in again.", "error")
        return redirect(url_for('core.login'))
    
    try:
        apply_supabase_auth_token()
        insert_post(user_id, content, category)
        flash("Post created successfully!", "success")
    except Exception as e:
        if is_jwt_expired_error(e) and refresh_supabase_auth():
            insert_post(user_id, content, category)
            flash("Post created successfully!", "success")
        elif is_jwt_expired_error(e):
            session.clear()
            flash("Your login session expired. Please sign in again.", "error")
            return redirect(url_for('core.login'))
        else:
            print(f"Error creating post: {e}")
            flash("Something went wrong. Please try again.", "error")
        
    return redirect(url_for('core.dashboard'))

def insert_post(user_id, content, category):
    supabase.table('posts').insert({
            "user_id": user_id,
            "content": content,
            "category": category
    }).execute()

@core.route('/login')
def login():
    return render_template('login.html')
