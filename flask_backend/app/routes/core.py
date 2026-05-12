from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from .auth import login_required
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
    
    # 1. Fetch User Profile from DB
    profile_response = supabase.table('profiles').select("*").eq("id", user_id).single().execute()
    profile = profile_response.data
    
    # 2. Fetch Latest Posts with Profile info
    posts_response = supabase.table('posts').select("*, profiles(full_name, avatar_url)").order("created_at", desc=True).limit(10).execute()
    posts = posts_response.data
    
    return render_template('dashboard.html', user=profile, posts=posts)

@core.route('/posts/create', methods=['POST'])
@login_required
def create_post():
    user_session = session.get('user')
    user_id = user_session.get('id')
    
    content = request.form.get('content')
    category = request.form.get('category', 'General')
    
    if not content:
        flash("Post content cannot be empty!", "error")
        return redirect(url_for('core.dashboard'))
    
    try:
        supabase.table('posts').insert({
            "user_id": user_id,
            "content": content,
            "category": category
        }).execute()
        flash("Post created successfully!", "success")
    except Exception as e:
        print(f"Error creating post: {e}")
        flash("Something went wrong. Please try again.", "error")
        
    return redirect(url_for('core.dashboard'))

@core.route('/login')
def login():
    return render_template('login.html')
