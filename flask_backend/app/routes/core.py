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
    
    # Extra fields
    price = request.form.get('price')
    location = request.form.get('location')
    status = request.form.get('status')
    event_date = request.form.get('event_date')
    
    # Clean empty values
    price = float(price) if price and price.strip() else None
    location = location.strip() if location and location.strip() else None
    status = status.strip() if status and status.strip() else None
    event_date = event_date if event_date and event_date.strip() else None
    
    if not content:
        flash("Post content cannot be empty!", "error")
        return redirect(url_for('core.dashboard'))
    
    try:
        supabase.table('posts').insert({
            "user_id": user_id,
            "content": content,
            "category": category,
            "price": price,
            "location": location,
            "status": status,
            "event_date": event_date
        }).execute()
        flash("Post created successfully!", "success")
    except Exception as e:
        print(f"Error creating post: {e}")
        flash("Something went wrong. Please try again.", "error")
        
    return redirect(url_for('core.dashboard'))

@core.route('/login')
def login():
    return render_template('login.html')
