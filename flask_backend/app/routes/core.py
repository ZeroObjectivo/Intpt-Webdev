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
from zoneinfo import ZoneInfo

core = Blueprint('core', __name__)

DISPLAY_TIMEZONE = ZoneInfo("Asia/Manila")

def parse_post_datetime(value):
    if not value:
        return None

    if isinstance(value, datetime.datetime):
        created_at = value
    else:
        raw_value = str(value).strip()
        if raw_value.endswith("Z"):
            raw_value = f"{raw_value[:-1]}+00:00"
        created_at = datetime.datetime.fromisoformat(raw_value)

    if created_at.tzinfo is None:
        return created_at.replace(tzinfo=datetime.timezone.utc)

    return created_at.astimezone(datetime.timezone.utc)

def format_relative_time(created_at, now=None):
    created_at = parse_post_datetime(created_at)
    if created_at is None:
        return ""

    now = now or datetime.datetime.now(datetime.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    else:
        now = now.astimezone(datetime.timezone.utc)

    delta = now - created_at
    seconds = max(int(delta.total_seconds()), 0)

    if seconds < 60:
        return "Just now"
    if seconds < 3600:
        minutes = seconds // 60
        unit = "min" if minutes == 1 else "mins"
        return f"{minutes} {unit} ago"
    if seconds < 86400:
        hours = seconds // 3600
        unit = "hr" if hours == 1 else "hrs"
        return f"{hours} {unit} ago"

    created_local = created_at.astimezone(DISPLAY_TIMEZONE)
    now_local = now.astimezone(DISPLAY_TIMEZONE)
    if created_local.date() == now_local.date() - datetime.timedelta(days=1):
        return f"Yesterday at {created_local.strftime('%I:%M %p').lstrip('0')}"

    if created_local.year == now_local.year:
        return created_local.strftime("%b %d").replace(" 0", " ")

    return created_local.strftime("%b %d, %Y").replace(" 0", " ")

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
        profile, posts, trending, upcoming_events = load_dashboard_data(user_id, category)
    except Exception as e:
        if is_jwt_expired_error(e) and refresh_supabase_auth():
            profile, posts, trending, upcoming_events = load_dashboard_data(user_id, category)
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
                           events=upcoming_events,
                           now=datetime.datetime.utcnow())

@core.route('/profile/<target_user_id>')
@login_required
def view_profile(target_user_id):
    current_user_id = session.get('user').get('id')
    apply_supabase_auth_token()
    
    try:
        profile, posts, activity = load_profile_data(target_user_id, viewer_id=current_user_id)
        # Check if the viewer owns this profile
        is_own_profile = (current_user_id == target_user_id)
        
        return render_template('profile_settings.html', 
                               user=profile, 
                               posts=posts, 
                               activity=activity,
                               is_own_profile=is_own_profile,
                               now=datetime.datetime.utcnow())
    except Exception as e:
        print(f"Error loading profile: {e}")
        flash("Profile not found.", "error")
        return redirect(url_for('core.dashboard'))

@core.route('/settings/profile')
@login_required
def profile_settings():
    return redirect(url_for('core.view_profile', target_user_id=session.get('user').get('id')))

def load_profile_data(user_id, viewer_id=None):
    # 1. Fetch User Profile
    profile_response = supabase.table('profiles').select("*").eq("id", user_id).single().execute()
    profile = profile_response.data
    
    # 2. Fetch User's Own Posts
    posts_response = supabase.table('posts')\
        .select("*, profiles(full_name, avatar_url)")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True).execute()
    posts = posts_response.data
    
    # Optimize: Fetch all likes by viewer for these posts in one query
    liked_post_ids = set()
    if viewer_id:
        post_ids = [p['id'] for p in posts]
        if post_ids:
            likes_res = supabase.table('likes').select("post_id").eq("user_id", viewer_id).in_("post_id", post_ids).execute()
            liked_post_ids = {l['post_id'] for l in likes_res.data}

    # Ensure counts and user_has_liked
    for post in posts:
        post['user_has_liked'] = post['id'] in liked_post_ids
        post['likes_count'] = post.get('likes_count') or 0
        post['comments_count'] = post.get('comments_count') or 0
        post['relative_created_at'] = format_relative_time(post.get('created_at'))

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

    # 3. Fetch likes for all posts in one go to avoid N+1
    post_ids = [p['id'] for p in posts]
    liked_post_ids = set()
    if post_ids:
        likes_res = supabase.table('likes').select("post_id").eq("user_id", user_id).in_("post_id", post_ids).execute()
        liked_post_ids = {l['post_id'] for l in likes_res.data}

    for post in posts:
        post['user_has_liked'] = post['id'] in liked_post_ids
        # Ensure counts are initialized if null
        post['likes_count'] = post.get('likes_count') or 0
        post['comments_count'] = post.get('comments_count') or 0
        post['relative_created_at'] = format_relative_time(post.get('created_at'))

    # 4. Fetch Trending Posts (Top 3 by likes_count, must have at least 1 like)
    trending_response = supabase.table('posts')\
        .select("*, profiles(full_name, avatar_url)")\
        .gt("likes_count", 0)\
        .order("likes_count", desc=True)\
        .limit(3).execute()
    trending = trending_response.data

    trending_ids = [p['id'] for p in trending]
    trending_liked_ids = set()
    if trending_ids:
        t_likes_res = supabase.table('likes').select("post_id").eq("user_id", user_id).in_("post_id", trending_ids).execute()
        trending_liked_ids = {l['post_id'] for l in t_likes_res.data}

    for t_post in trending:
        t_post['user_has_liked'] = t_post['id'] in trending_liked_ids
        t_post['likes_count'] = t_post.get('likes_count') or 0
        t_post['comments_count'] = t_post.get('comments_count') or 0
        t_post['relative_created_at'] = format_relative_time(t_post.get('created_at'))
    
    # 5. Fetch Upcoming & Ongoing Events (Top 3 that haven't ended yet)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Fetch events where (event_date >= now) OR (event_end_date >= now)
    events_response = supabase.table('posts')\
        .select("*, profiles(full_name, avatar_url)")\
        .eq("category", "Events")\
        .or_(f"event_date.gte.{now_iso},event_end_date.gte.{now_iso}")\
        .order("event_date", desc=False)\
        .limit(3).execute()
    upcoming_events = []
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    for event in events_response.data:
        try:
            # Parse times
            start_dt = parse_post_datetime(event['event_date'])
            end_dt = parse_post_datetime(event.get('event_end_date'))
            
            # Format display
            display_dt = start_dt.astimezone(DISPLAY_TIMEZONE)
            event['day'] = display_dt.strftime('%d')
            event['month'] = display_dt.strftime('%b')
            event['time_display'] = display_dt.strftime('%I:%M %p').lstrip('0')
            
            if end_dt:
                display_edt = end_dt.astimezone(DISPLAY_TIMEZONE)
                event['time_display'] += f" - {display_edt.strftime('%I:%M %p').lstrip('0')}"
            
            # Determine status
            if start_dt <= now_utc:
                if not end_dt or end_dt >= now_utc:
                    event['status'] = 'Ongoing'
                else:
                    continue # Already ended, skip (redundant check due to query but safe)
            else:
                event['status'] = 'Upcoming'
                
            upcoming_events.append(event)
        except Exception as e:
            print(f"Error formatting event: {e}")

    return profile, posts, trending, upcoming_events[:3]

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
            # Unlike: Remove from DB. Trigger handles decrement.
            supabase.table('likes').delete().eq("post_id", post_id).eq("user_id", user_id).execute()
            return {"status": "unliked", "post_id": post_id}
        else:
            # Like: Insert into DB. Trigger handles increment.
            try:
                supabase.table('likes').insert({"post_id": post_id, "user_id": user_id}).execute()
                return {"status": "liked", "post_id": post_id}
            except Exception as e:
                # If it failed (e.g. unique constraint), it might already be liked
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
        # Insert comment. Trigger handles increment.
        comment_data = {
            "post_id": post_id,
            "user_id": user_id,
            "content": content
        }
        if parent_id:
            comment_data["parent_id"] = parent_id
            
        comment_response = supabase.table('comments').insert(comment_data).execute()
        
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
    event_title = request.form.get('event_title')
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
        if event_title is not None: update_data["event_title"] = event_title.strip()
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
    event_title = request.form.get('event_title')
    price = request.form.get('price')
    location = request.form.get('location')
    status = request.form.get('status')
    event_date = request.form.get('event_date')
    event_end_date = request.form.get('event_end_date')
    
    # Clean empty values
    price = float(price) if price and price.strip() else None
    location = location.strip() if location and location.strip() else None
    status = status.strip() if status and status.strip() else None
    
    # Handle timezone for event dates (assume Manila time from browser)
    if event_date and 'T' in event_date and '+' not in event_date and 'Z' not in event_date:
        event_date = f"{event_date}:00+08:00"
    if event_end_date and 'T' in event_end_date and '+' not in event_end_date and 'Z' not in event_end_date:
        event_end_date = f"{event_end_date}:00+08:00"

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
            "event_title": event_title,
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

@core.route('/notifications/<notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    apply_supabase_auth_token()
    try:
        supabase.table('notifications').update({"is_read": True}).eq("id", notification_id).execute()
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}, 500

@core.route('/login')
def login():
    return render_template('login.html')
