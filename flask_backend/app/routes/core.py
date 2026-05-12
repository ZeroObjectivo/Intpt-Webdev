from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from .auth import (
    apply_supabase_auth_token,
    is_jwt_expired_error,
    login_required,
    refresh_supabase_auth,
)
from services.supabase_client import supabase
import datetime
import time

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
        profile, posts, trending = load_dashboard_data(user_id, category)
    except Exception as e:
        if is_jwt_expired_error(e) and refresh_supabase_auth():
            profile, posts, trending = load_dashboard_data(user_id, category)
        elif is_jwt_expired_error(e):
            session.clear()
            flash("Your login session expired. Please sign in again.", "error")
            return redirect(url_for('core.login'))
        else:
            raise
    
    return render_template('dashboard.html', 
                           user=profile, 
                           posts=posts, 
                           active_category=category, 
                           trending=trending,
                           now=datetime.datetime.utcnow())

@core.route('/settings/profile')
@login_required
def profile_settings():
    user_session = session.get('user')
    user_id = user_session.get('id')
    apply_supabase_auth_token()
    
    try:
        profile, posts, activity = load_profile_data(user_id)
        return render_template('profile_settings.html', 
                               user=profile, 
                               posts=posts, 
                               activity=activity,
                               now=datetime.datetime.utcnow())
    except Exception as e:
        print(f"Error loading profile dashboard: {e}")
        flash(f"Error loading profile: {str(e)}", "error")
        return redirect(url_for('core.dashboard'))

def load_profile_data(user_id):
    # 1. Fetch User Profile
    profile_response = supabase.table('profiles').select("*").eq("id", user_id).single().execute()
    profile = profile_response.data
    
    # 2. Fetch User's Own Posts
    posts_response = supabase.table('posts')\
        .select("*, profiles(full_name, avatar_url)")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True).execute()
    posts = posts_response.data
    
    # Ensure counts and user_has_liked for own posts
    for post in posts:
        post['user_has_liked'] = True # If it's my post, I can see it, but I still need to check likes table if I actually liked it
        # Actually, let's do a real check for likes
        like_check = supabase.table('likes').select("id").eq("post_id", post['id']).eq("user_id", user_id).execute()
        post['user_has_liked'] = len(like_check.data) > 0
        post['likes_count'] = post.get('likes_count') or 0
        post['comments_count'] = post.get('comments_count') or 0

    # 3. Fetch Activity Log (Recent Likes and Comments by the user)
    # Get recent likes on other people's posts
    likes_activity = supabase.table('likes')\
        .select("created_at, posts(id, content, category)")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True).limit(10).execute()
    
    # Get recent comments by the user
    comments_activity = supabase.table('comments')\
        .select("id, created_at, content, post_id, posts(id, content, category)")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True).limit(10).execute()
    
    # Combine and sort activity
    activity = []
    for l in likes_activity.data:
        if l.get('posts'):
            activity.append({
                "type": "like",
                "created_at": l['created_at'],
                "post_id": l['posts']['id'],
                "post_content": l['posts']['content'],
                "category": l['posts']['category']
            })
    
    for c in comments_activity.data:
        if c.get('posts'):
            activity.append({
                "type": "comment",
                "created_at": c['created_at'],
                "content": c['content'],
                "post_id": c['posts']['id'],
                "post_content": c['posts']['content'],
                "category": c['posts']['category']
            })
            
    activity.sort(key=lambda x: x['created_at'], reverse=True)
    
    return profile, posts, activity[:20]

@core.route('/settings/profile', methods=['POST'])
@login_required
def update_profile():
    user_session = session.get('user')
    user_id = user_session.get('id')
    
    # Get form data
    contact_number = request.form.get('contact_number')
    contact_privacy = request.form.get('contact_privacy', 'public')
    college = request.form.get('college')
    course = request.form.get('course')
    level = request.form.get('level')
    bio = request.form.get('bio')
    
    apply_supabase_auth_token()
    
    try:
        update_data = {
            "contact_number": contact_number,
            "contact_privacy": contact_privacy,
            "college": college,
            "course": course,
            "level": level,
            "bio": bio,
            "updated_at": "now()"
        }
        
        supabase.table('profiles').update(update_data).eq("id", user_id).execute()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('core.profile_settings'))
    except Exception as e:
        flash(f"Error updating profile: {str(e)}", "error")
        return redirect(url_for('core.profile_settings'))

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

    # 4. Fetch Trending Posts (Top 3 by likes_count)
    trending_response = supabase.table('posts').select("content, category, likes_count").order("likes_count", desc=True).limit(3).execute()
    trending = trending_response.data
    
    return profile, posts, trending

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

@core.route('/posts/<post_id>/update', methods=['POST'])
@login_required
def update_post(post_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    
    content = request.form.get('content')
    category = request.form.get('category')
    price = request.form.get('price')
    location = request.form.get('location')
    status = request.form.get('status')
    event_date = request.form.get('event_date')
    event_end_date = request.form.get('event_end_date')
    
    apply_supabase_auth_token()
    
    try:
        # RLS will prevent unauthorized updates, but we'll check user_id too
        update_data = {
            "content": content,
            "category": category,
            "updated_at": "now()"
        }
        
        if price is not None: update_data["price"] = float(price) if price.strip() else None
        if location is not None: update_data["location"] = location.strip()
        if status is not None: update_data["status"] = status.strip()
        if event_date is not None: update_data["event_date"] = event_date if event_date.strip() else None
        if event_end_date is not None: update_data["event_end_date"] = event_end_date if event_end_date.strip() else None

        result = supabase.table('posts').update(update_data).eq("id", post_id).eq("user_id", user_id).execute()
        
        if not result.data:
            return {"error": "Unauthorized or post not found"}, 403
            
        flash("Post updated successfully!", "success")
        return redirect(url_for('core.dashboard'))
    except Exception as e:
        print(f"Error updating post: {e}")
        flash(f"Error updating post: {str(e)}", "error")
        return redirect(url_for('core.dashboard'))

@core.route('/posts/<post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    
    apply_supabase_auth_token()
    
    try:
        result = supabase.table('posts').delete().eq("id", post_id).eq("user_id", user_id).execute()
        
        if not result.data:
            return {"error": "Unauthorized or post not found"}, 403
            
        flash("Post deleted successfully!", "success")
        return {"status": "deleted"}
    except Exception as e:
        print(f"Error deleting post: {e}")
        return {"error": str(e)}, 500

@core.route('/comments/<comment_id>/update', methods=['POST'])
@login_required
def update_comment(comment_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    content = request.json.get('content')
    
    if not content:
        return {"error": "Comment cannot be empty"}, 400
        
    apply_supabase_auth_token()
    try:
        result = supabase.table('comments').update({
            "content": content,
            "updated_at": "now()"
        }).eq("id", comment_id).eq("user_id", user_id).execute()
        
        if not result.data:
            return {"error": "Unauthorized or comment not found"}, 403
            
        return {"comment": result.data[0]}
    except Exception as e:
        print(f"Error updating comment: {e}")
        return {"error": str(e)}, 500

@core.route('/comments/<comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    
    apply_supabase_auth_token()
    try:
        # Get the post_id before deleting so we can decrement count
        comment = supabase.table('comments').select("post_id").eq("id", comment_id).eq("user_id", user_id).single().execute()
        
        if not comment.data:
            return {"error": "Unauthorized or comment not found"}, 403
            
        post_id = comment.data['post_id']
        
        supabase.table('comments').delete().eq("id", comment_id).eq("user_id", user_id).execute()
        
        # Decrement comments_count
        supabase.rpc('decrement_comments_count', {'row_id': post_id}).execute()
        
        return {"status": "deleted", "post_id": post_id}
    except Exception as e:
        print(f"Error deleting comment: {e}")
        return {"error": str(e)}, 500

@core.route('/posts/create', methods=['POST'])
@login_required
def create_post():
    user_session = session.get('user')
    user_id = user_session.get('id')
    
    # --- Rate Limiting (Spam Protection) ---
    current_time = time.time()
    last_post_time = session.get('last_post_time', 0)
    if current_time - last_post_time < 30:  # 30 seconds limit
        flash("You are posting too fast! Please wait a moment.", "warning")
        return redirect(url_for('core.dashboard'))
    
    access_token = session.get('access_token')
    
    content = request.form.get('content')
    category = request.form.get('category', 'General')
    image_files = request.files.getlist('image')
    
    # Extra fields
    price = request.form.get('price')
    location = request.form.get('location')
    status = request.form.get('status')
    event_date = request.form.get('event_date')
    event_end_date = request.form.get('event_end_date')
    
    # Clean empty values
    price = float(price) if price and price.strip() else None
    location = location.strip() if location and location.strip() else None
    status = status.strip() if status and status.strip() else None
    event_date = event_date if event_date and event_date.strip() else None
    event_end_date = event_end_date if event_end_date and event_end_date.strip() else None
    
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
            "event_end_date": event_end_date,
            "image_url": image_urls[0] if image_urls else None,
            "image_urls": image_urls
        }
        supabase.table('posts').insert(post_data).execute()
        
        # Update rate limit timestamp
        session['last_post_time'] = current_time
        
        flash("Post created successfully!", "success")
    except Exception as e:
        print(f"CRITICAL: Post insertion failed: {str(e)}")
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

@core.route('/login')
def login():
    return render_template('login.html')
