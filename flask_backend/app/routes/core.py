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
    category = request.args.get('category')
    apply_supabase_auth_token()

    try:
        profile, posts = load_dashboard_data(user_id, category)
    except Exception as e:
        if is_jwt_expired_error(e) and refresh_supabase_auth():
            profile, posts = load_dashboard_data(user_id, category)
        elif is_jwt_expired_error(e):
            session.clear()
            flash("Your login session expired. Please sign in again.", "error")
            return redirect(url_for('core.login'))
        else:
            raise
    
    return render_template('dashboard.html', user=profile, posts=posts, active_category=category)

def load_dashboard_data(user_id, category=None):
    
    # 1. Fetch User Profile from DB
    profile_response = supabase.table('profiles').select("*").eq("id", user_id).single().execute()
    profile = profile_response.data
    
    # 2. Fetch Latest Posts with Profile info
    query = supabase.table('posts').select("*, profiles(full_name, avatar_url)")
    
    if category:
        query = query.eq('category', category)
        
    posts_response = query.order("created_at", desc=True).limit(20).execute()
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
    image_files = request.files.getlist('image')
    
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
    
    if not content and (not image_files or not image_files[0].filename):
        flash("Post content cannot be empty!", "error")
        return redirect(url_for('core.dashboard'))

    if not access_token:
        flash("Your login session expired. Please sign in again.", "error")
        return redirect(url_for('core.login'))
    
    image_urls = []
    if image_files:
        # Limit to 5 images
        for file in image_files[:5]:
            if file and file.filename:
                try:
                    url = upload_single_image(file, user_id)
                    image_urls.append(url)
                except Exception as e:
                    print(f"Error uploading image {file.filename}: {e}")
                    flash(f"Failed to upload image {file.filename}.", "warning")

    try:
        post_data = {
            "user_id": user_id,
            "content": content,
            "category": category,
            "price": price,
            "location": location,
            "status": status,
            "event_date": event_date,
            "image_urls": image_urls
        }
        print(f"DEBUG: Attempting to insert post for user {user_id}: {post_data}")
        response = supabase.table('posts').insert(post_data).execute()
        print(f"DEBUG: Insert successful: {response.data}")
        flash("Post created successfully!", "success")
    except Exception as e:
        print(f"CRITICAL: Post insertion failed: {str(e)}")
        if is_jwt_expired_error(e) and refresh_supabase_auth():
            insert_post_multi(user_id, content, category, price, location, status, event_date, image_urls)
            flash("Post created successfully!", "success")
        elif is_jwt_expired_error(e):
            session.clear()
            flash("Your login session expired. Please sign in again.", "error")
            return redirect(url_for('core.login'))
        else:
            flash("Something went wrong. Please try again.", "error")
        
    return redirect(url_for('core.dashboard'))

def upload_single_image(file, user_id):
    import uuid
    import time
    
    try:
        file_ext = file.filename.split('.')[-1]
        timestamp = int(time.time())
        filename = f"{user_id}/{timestamp}_{uuid.uuid4().hex}.{file_ext}"
        bucket_name = 'post-images'
        
        file.seek(0)
        file_data = file.read()
        
        # Try uploading
        res = supabase.storage.from_(bucket_name).upload(
            path=filename,
            file=file_data,
            file_options={"content-type": file.content_type}
        )
        return supabase.storage.from_(bucket_name).get_public_url(filename)
    except Exception as e:
        print(f"CRITICAL: Supabase storage upload failed: {str(e)}")
        raise e

def insert_post_multi(user_id, content, category, price=None, location=None, status=None, event_date=None, image_urls=None):
    post_data = {
        "user_id": user_id,
        "content": content,
        "category": category,
        "price": price,
        "location": location,
        "status": status,
        "event_date": event_date,
        "image_urls": image_urls if image_urls else []
    }
    supabase.table('posts').insert(post_data).execute()

def upload_post_image(file, user_id):
    # Legacy helper for single image upload
    return upload_single_image(file, user_id)

def insert_post(user_id, content, category, price=None, location=None, status=None, event_date=None, image_url=None):
    # Legacy helper for single image insert
    image_urls = [image_url] if image_url else []
    insert_post_multi(user_id, content, category, price, location, status, event_date, image_urls)

@core.route('/login')
def login():
    return render_template('login.html')
