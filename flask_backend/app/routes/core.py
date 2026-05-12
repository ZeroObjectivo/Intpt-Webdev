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
    
    import datetime
    return render_template('dashboard.html', 
                           user=profile, 
                           posts=posts, 
                           active_category=category,
                           now=datetime.datetime.utcnow())

def load_dashboard_data(user_id, category=None):
    
    # 1. Fetch User Profile from DB
    profile_response = supabase.table('profiles').select("*").eq("id", user_id).single().execute()
    profile = profile_response.data
    
    # 2. Fetch Latest Posts with Profile info and Likes/Comments counts
    query = supabase.table('posts').select("*, profiles(full_name, avatar_url)")
    
    if category:
        query = query.eq('category', category)
        
    posts_response = query.order("created_at", desc=True).limit(20).execute()
    posts = posts_response.data
    
    # 3. For each post, check if the current user has liked it
    # and ensure counts are present
    for post in posts:
        # Check if current user liked this post
        like_check = supabase.table('likes').select("id").eq("post_id", post['id']).eq("user_id", user_id).execute()
        post['user_has_liked'] = len(like_check.data) > 0
        
        # Ensure counts are initialized if null
        post['likes_count'] = post.get('likes_count') or 0
        post['comments_count'] = post.get('comments_count') or 0
    
    return profile, posts

@core.route('/posts/<post_id>/like', methods=['POST'])
@login_required
def toggle_like(post_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    apply_supabase_auth_token()
    
    try:
        # Check if already liked
        existing = supabase.table('likes').select("id").eq("post_id", post_id).eq("user_id", user_id).execute()
        
        if len(existing.data) > 0:
            # Unlike
            supabase.table('likes').delete().eq("post_id", post_id).eq("user_id", user_id).execute()
            # Decrement likes_count
            supabase.rpc('decrement_likes_count', {'row_id': post_id}).execute()
            return {"status": "unliked", "post_id": post_id}
        else:
            # Like
            supabase.table('likes').insert({"post_id": post_id, "user_id": user_id}).execute()
            # Increment likes_count
            supabase.rpc('increment_likes_count', {'row_id': post_id}).execute()
            return {"status": "liked", "post_id": post_id}
            
    except Exception as e:
        print(f"Error toggling like: {e}")
        return {"error": str(e)}, 500

@core.route('/posts/<post_id>/comments', methods=['GET'])
@login_required
def get_comments(post_id):
    apply_supabase_auth_token()
    try:
        comments_response = supabase.table('comments')\
            .select("*, profiles(full_name, avatar_url)")\
            .eq("post_id", post_id)\
            .order("created_at", desc=False)\
            .execute()
        return {"comments": comments_response.data}
    except Exception as e:
        return {"error": str(e)}, 500

@core.route('/posts/<post_id>/comments', methods=['POST'])
@login_required
def add_comment(post_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    content = request.json.get('content')
    parent_id = request.json.get('parent_id') # Optional parent_id for replies
    
    if not content:
        return {"error": "Comment cannot be empty"}, 400
        
    apply_supabase_auth_token()
    try:
        # Insert comment
        comment_data = {
            "post_id": post_id,
            "user_id": user_id,
            "content": content
        }
        if parent_id:
            comment_data["parent_id"] = parent_id
            
        comment_response = supabase.table('comments').insert(comment_data).execute()
        
        # Increment comments_count
        supabase.rpc('increment_comments_count', {'row_id': post_id}).execute()
        
        # Fetch the inserted comment with profile info
        new_comment = supabase.table('comments')\
            .select("*, profiles(full_name, avatar_url)")\
            .eq("id", comment_response.data[0]['id'])\
            .single().execute()
            
        return {"comment": new_comment.data}
    except Exception as e:
        print(f"Error adding comment: {e}")
        return {"error": str(e)}, 500

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
    
    # Authenticate the supabase client with the user's token
    apply_supabase_auth_token()
    
    image_urls = []
    if image_files:
        for img_file in image_files:
            if img_file.filename:
                try:
                    url = upload_single_image(img_file, user_id)
                    if url:
                        image_urls.append(url)
                except Exception as e:
                    print(f"Error uploading image {img_file.filename}: {e}")
                    flash(f"Failed to upload image {img_file.filename}.", "warning")

    try:
        post_data = {
            "user_id": user_id,
            "content": content,
            "category": category,
            "price": price,
            "location": location,
            "status": status,
            "event_date": event_date,
            "image_url": image_urls[0] if image_urls else None,
            "image_urls": image_urls
        }
        print(f"DEBUG: Attempting standard insert for user {user_id}: {post_data}")
        supabase.table('posts').insert(post_data).execute()
        flash("Post created successfully!", "success")
    except Exception as e:
        print(f"CRITICAL: Standard post insertion failed: {str(e)}")
        flash(f"Something went wrong: {str(e)}", "error")
        
    return redirect(url_for('core.dashboard'))

def upload_single_image(file, user_id):
    import uuid
    import time
    
    try:
        print(f"DEBUG: File received: {file.filename}, Content-Type: {file.content_type}")
        
        file_ext = file.filename.split('.')[-1]
        timestamp = int(time.time())
        filename = f"{user_id}/{timestamp}_{uuid.uuid4().hex}.{file_ext}"
        bucket_name = 'post-images'
        
        file.seek(0)
        file_data = file.read()
        print(f"DEBUG: Read {len(file_data)} bytes from file.")
        
        # Try uploading
        res = supabase.storage.from_(bucket_name).upload(
            path=filename,
            file=file_data,
            file_options={"content-type": file.content_type}
        )
        print(f"DEBUG: Supabase upload response: {res}")
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
