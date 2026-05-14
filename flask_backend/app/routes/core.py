from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify, make_response
from .auth import (
    is_jwt_expired_error,
    login_required,
    refresh_supabase_auth,
)
from services.supabase_client import get_user_client
import datetime
import time
from zoneinfo import ZoneInfo

core = Blueprint('core', __name__)

DISPLAY_TIMEZONE = ZoneInfo("Asia/Manila")
HERON_BUSINESS_CATEGORIES = ['Heron Business', 'Buy & Sell']

def normalize_dashboard_category(category):
    if category == 'Buy & Sell':
        return 'Heron Business'
    return category

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
    category = normalize_dashboard_category(request.args.get('category'))
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

    response = make_response(render_template('dashboard.html',
                           user=profile,
                           posts=posts,
                           active_category=category,
                           trending=trending,
                           events=upcoming_events,
                           now=datetime.datetime.now(datetime.timezone.utc)))
    # Prevent stale dashboard snapshots from cache/CDN.
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@core.route('/profile/<target_user_id>')
@login_required
def view_profile(target_user_id):
    current_user_id = session.get('user').get('id')

    try:
        profile, posts, activity = load_profile_data(target_user_id, viewer_id=current_user_id)
        is_own_profile = (current_user_id == target_user_id)

        return render_template('profile_settings.html',
                               user=profile,
                               posts=posts,
                               activity=activity,
                               is_own_profile=is_own_profile,
                               now=datetime.datetime.now(datetime.timezone.utc))
    except Exception as e:
        print(f"Error loading profile: {e}")
        flash("Profile not found.", "error")
        return redirect(url_for('core.dashboard'))

@core.route('/settings/profile')
@login_required
def profile_settings():
    return redirect(url_for('core.view_profile', target_user_id=session.get('user').get('id')))

def load_profile_data(user_id, viewer_id=None):
    client = get_user_client()

    profile_response = client.table('profiles').select("*").eq("id", user_id).single().execute()
    profile = profile_response.data

    posts_response = client.table('posts')\
        .select("*, profiles(full_name, avatar_url)")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True).execute()
    posts = posts_response.data

    liked_post_ids = set()
    if viewer_id:
        post_ids = [p['id'] for p in posts]
        if post_ids:
            likes_res = client.table('likes').select("post_id").eq("user_id", viewer_id).in_("post_id", post_ids).execute()
            liked_post_ids = {l['post_id'] for l in likes_res.data}

    for post in posts:
        post['user_has_liked'] = post['id'] in liked_post_ids
        post['likes_count'] = post.get('likes_count') or 0
        post['comments_count'] = post.get('comments_count') or 0
        post['relative_created_at'] = format_relative_time(post.get('created_at'))

    likes_activity = client.table('likes')\
        .select("created_at, posts(id, content, category)")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True).limit(10).execute()

    comments_activity = client.table('comments')\
        .select("id, created_at, content, post_id, posts(id, content, category)")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True).limit(10).execute()

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

    contact_number = request.form.get('contact_number')
    contact_privacy = request.form.get('contact_privacy', 'public')
    college = request.form.get('college')
    course = request.form.get('course')
    level = request.form.get('level')
    bio = request.form.get('bio')

    client = get_user_client()

    try:
        update_data = {
            "contact_number": contact_number,
            "contact_privacy": contact_privacy,
            "college": college,
            "course": course,
            "level": level,
            "bio": bio,
        }

        client.table('profiles').update(update_data).eq("id", user_id).execute()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('core.profile_settings'))
    except Exception as e:
        flash("Error updating profile. Please try again.", "error")
        return redirect(url_for('core.profile_settings'))

def load_dashboard_data(user_id, category=None):
    client = get_user_client()

    profile_response = client.table('profiles').select("*").eq("id", user_id).single().execute()
    profile = profile_response.data

    query = client.table('posts').select("*, profiles(full_name, avatar_url)")

    if category:
        if category == 'Heron Business':
            query = query.in_('category', HERON_BUSINESS_CATEGORIES)
        else:
            query = query.eq('category', category)

    posts_response = query.order("created_at", desc=True).limit(20).execute()
    posts = posts_response.data

    post_ids = [p['id'] for p in posts]
    liked_post_ids = set()
    if post_ids:
        likes_res = client.table('likes').select("post_id").eq("user_id", user_id).in_("post_id", post_ids).execute()
        liked_post_ids = {l['post_id'] for l in likes_res.data}

    for post in posts:
        post['user_has_liked'] = post['id'] in liked_post_ids
        post['likes_count'] = post.get('likes_count') or 0
        post['comments_count'] = post.get('comments_count') or 0
        post['relative_created_at'] = format_relative_time(post.get('created_at'))

    trending_response = client.table('posts')\
        .select("*, profiles(full_name, avatar_url)")\
        .gt("likes_count", 0)\
        .order("likes_count", desc=True)\
        .limit(3).execute()
    trending = trending_response.data

    trending_ids = [p['id'] for p in trending]
    trending_liked_ids = set()
    if trending_ids:
        t_likes_res = client.table('likes').select("post_id").eq("user_id", user_id).in_("post_id", trending_ids).execute()
        trending_liked_ids = {l['post_id'] for l in t_likes_res.data}

    for t_post in trending:
        t_post['user_has_liked'] = t_post['id'] in trending_liked_ids
        t_post['likes_count'] = t_post.get('likes_count') or 0
        t_post['comments_count'] = t_post.get('comments_count') or 0
        t_post['relative_created_at'] = format_relative_time(t_post.get('created_at'))

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    events_response = client.table('posts')\
        .select("*, profiles(full_name, avatar_url)")\
        .eq("category", "Events")\
        .or_(f"event_date.gte.{now_iso},event_end_date.gte.{now_iso}")\
        .order("event_date", desc=False)\
        .limit(3).execute()
    upcoming_events = []

    now_utc = datetime.datetime.now(datetime.timezone.utc)

    for event in events_response.data:
        try:
            start_dt = parse_post_datetime(event['event_date'])
            end_dt = parse_post_datetime(event.get('event_end_date'))

            display_dt = start_dt.astimezone(DISPLAY_TIMEZONE)
            event['day'] = display_dt.strftime('%d')
            event['month'] = display_dt.strftime('%b')
            event['time_display'] = display_dt.strftime('%I:%M %p').lstrip('0')

            if end_dt:
                display_edt = end_dt.astimezone(DISPLAY_TIMEZONE)
                event['time_display'] += f" - {display_edt.strftime('%I:%M %p').lstrip('0')}"

            if start_dt <= now_utc:
                if not end_dt or end_dt >= now_utc:
                    event['status'] = 'Ongoing'
                else:
                    continue
            else:
                event['status'] = 'Upcoming'

            upcoming_events.append(event)
        except Exception as e:
            print(f"Error formatting event: {e}")

    return profile, posts, trending, upcoming_events[:3]

def parse_sync_post_ids(raw_ids):
    if not raw_ids:
        return []

    parsed = []
    for token in raw_ids.split(','):
        value = token.strip()
        if not value or len(value) > 64:
            continue
        if all(ch.isalnum() or ch == '-' for ch in value):
            parsed.append(value)

    # Keep payload small and bounded.
    return parsed[:50]

def build_dashboard_sync_state(client, category=None):
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    latest_query = client.table('posts').select("id, created_at")
    if category:
        latest_query = latest_query.eq('category', category)
    latest_post_res = latest_query.order("created_at", desc=True).limit(1).execute()
    latest_post = latest_post_res.data[0] if latest_post_res.data else {}

    trending_res = client.table('posts')\
        .select("id")\
        .gt("likes_count", 0)\
        .order("likes_count", desc=True)\
        .order("created_at", desc=True)\
        .limit(3).execute()
    trending_ids = [row['id'] for row in (trending_res.data or [])]

    events_res = client.table('posts')\
        .select("id")\
        .eq("category", "Events")\
        .or_(f"event_date.gte.{now_iso},event_end_date.gte.{now_iso}")\
        .order("event_date", desc=False)\
        .limit(3).execute()
    event_ids = [row['id'] for row in (events_res.data or [])]

    state = {
        "latest_post_id": latest_post.get('id'),
        "latest_post_created_at": latest_post.get('created_at'),
        "trending_ids": trending_ids,
        "event_ids": event_ids,
    }
    state["version"] = "|".join([
        str(state["latest_post_id"] or ""),
        str(state["latest_post_created_at"] or ""),
        ",".join(state["trending_ids"]),
        ",".join(state["event_ids"]),
    ])
    return state

def build_notification_payload(client, user_id):
    notifications_res = client.table('notifications')\
        .select("id, title, message, type, is_read, created_at")\
        .eq('user_id', user_id)\
        .order('created_at', desc=True)\
        .limit(5).execute()

    items = notifications_res.data or []
    unread_count = len([n for n in items if not n.get('is_read')])

    return {
        "items": items,
        "unread_count": unread_count,
    }

def build_interactions_payload(client, user_id, post_ids):
    if not post_ids:
        return []

    posts_res = client.table('posts')\
        .select("id, likes_count, comments_count")\
        .in_("id", post_ids).execute()
    posts = posts_res.data or []

    liked_res = client.table('likes')\
        .select("post_id")\
        .eq("user_id", user_id)\
        .in_("post_id", post_ids).execute()
    liked_post_ids = {row['post_id'] for row in (liked_res.data or [])}

    row_map = {}
    for row in posts:
        row_map[row['id']] = {
            "id": row['id'],
            "likes_count": row.get('likes_count') or 0,
            "comments_count": row.get('comments_count') or 0,
            "user_has_liked": row['id'] in liked_post_ids,
        }

    # Preserve front-end order.
    ordered = []
    for pid in post_ids:
        if pid in row_map:
            ordered.append(row_map[pid])
    return ordered

def build_admin_activity_payload(client):
    try:
        latest_report = client.table('reports').select("id, created_at").order('created_at', desc=True).limit(1).execute()
        latest_warning = client.table('warnings').select("id, created_at").order('created_at', desc=True).limit(1).execute()
        latest_dispute = client.table('verification_disputes').select("id, created_at, status").eq('status', 'pending').order('created_at', desc=True).limit(1).execute()

        report_row = latest_report.data[0] if latest_report.data else {}
        warning_row = latest_warning.data[0] if latest_warning.data else {}
        dispute_row = latest_dispute.data[0] if latest_dispute.data else {}

        version = "|".join([
            str(report_row.get('id') or ""),
            str(report_row.get('created_at') or ""),
            str(warning_row.get('id') or ""),
            str(warning_row.get('created_at') or ""),
            str(dispute_row.get('id') or ""),
            str(dispute_row.get('created_at') or ""),
        ])

        return {
            "version": version,
            "latest_report_id": report_row.get('id'),
            "latest_warning_id": warning_row.get('id'),
            "latest_dispute_id": dispute_row.get('id'),
        }
    except Exception as e:
        print(f"Error building admin activity payload: {e}")
        return {"version": ""}

@core.route('/sync/dashboard/load', methods=['GET'])
@login_required
def sync_dashboard_load():
    category = request.args.get('category')
    client = get_user_client()

    state = build_dashboard_sync_state(client, category=category)

    response = jsonify({
        "status": "ok",
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "state": state,
    })
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@core.route('/sync/realtime', methods=['GET'])
@login_required
def sync_realtime():
    category = request.args.get('category')
    raw_post_ids = request.args.get('post_ids', '')
    post_ids = parse_sync_post_ids(raw_post_ids)
    user = session.get('user', {})
    user_id = user.get('id')
    role = (user.get('role') or '').lower()

    client = get_user_client()

    state = build_dashboard_sync_state(client, category=category)
    notifications = build_notification_payload(client, user_id)
    interactions = {
        "posts": build_interactions_payload(client, user_id, post_ids)
    }

    payload = {
        "status": "ok",
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "state": state,
        "notifications": notifications,
        "interactions": interactions,
    }

    if role in ['admin', 'super_admin', 'superadmin', 'content_moderator', 'account_manager']:
        payload["admin"] = build_admin_activity_payload(client)

    response = jsonify(payload)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@core.route('/posts/<post_id>/like', methods=['POST'])
@login_required
def toggle_like(post_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    client = get_user_client()

    try:
        existing = client.table('likes').select("id").eq("post_id", post_id).eq("user_id", user_id).execute()

        if len(existing.data) > 0:
            client.table('likes').delete().eq("post_id", post_id).eq("user_id", user_id).execute()
            return {"status": "unliked", "post_id": post_id}
        else:
            try:
                client.table('likes').insert({"post_id": post_id, "user_id": user_id}).execute()
                return {"status": "liked", "post_id": post_id}
            except Exception:
                return {"status": "liked", "post_id": post_id}

    except Exception as e:
        print(f"Error toggling like: {e}")
        return {"error": "Failed to toggle like."}, 500

@core.route('/posts/<post_id>/comments', methods=['GET'])
@login_required
def get_comments(post_id):
    client = get_user_client()
    try:
        comments_response = client.table('comments')\
            .select("*, profiles(full_name, avatar_url)")\
            .eq("post_id", post_id)\
            .order("created_at", desc=False)\
            .execute()
        return {"comments": comments_response.data}
    except Exception as e:
        print(f"Error fetching comments: {e}")
        return {"error": "Failed to load comments."}, 500

@core.route('/posts/<post_id>/comments', methods=['POST'])
@login_required
def add_comment(post_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    content = request.json.get('content')
    parent_id = request.json.get('parent_id')

    if not content:
        return {"error": "Comment cannot be empty"}, 400

    client = get_user_client()
    try:
        comment_data = {
            "post_id": post_id,
            "user_id": user_id,
            "content": content
        }
        if parent_id:
            comment_data["parent_id"] = parent_id

        comment_response = client.table('comments').insert(comment_data).execute()

        new_comment = client.table('comments')\
            .select("*, profiles(full_name, avatar_url)")\
            .eq("id", comment_response.data[0]['id'])\
            .single().execute()

        return {"comment": new_comment.data}
    except Exception as e:
        print(f"Error adding comment: {e}")
        return {"error": "Failed to add comment."}, 500

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

    client = get_user_client()

    try:
        update_data = {
            "content": content,
            "category": category,
        }

        if price is not None: update_data["price"] = float(price) if price.strip() else None
        if event_title is not None: update_data["event_title"] = event_title.strip()
        if location is not None: update_data["location"] = location.strip()
        if status is not None: update_data["status"] = status.strip()
        if event_date is not None: update_data["event_date"] = event_date if event_date.strip() else None
        if event_end_date is not None: update_data["event_end_date"] = event_end_date if event_end_date.strip() else None

        result = client.table('posts').update(update_data).eq("id", post_id).eq("user_id", user_id).execute()

        if not result.data:
            return {"error": "Unauthorized or post not found"}, 403

        flash("Post updated successfully!", "success")
        return redirect(url_for('core.dashboard'))
    except Exception as e:
        print(f"Error updating post: {e}")
        flash("Error updating post. Please try again.", "error")
        return redirect(url_for('core.dashboard'))

@core.route('/posts/<post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    client = get_user_client()

    try:
        result = client.table('posts').delete().eq("id", post_id).eq("user_id", user_id).execute()

        if not result.data:
            return {"error": "Unauthorized or post not found"}, 403

        flash("Post deleted successfully!", "success")
        return {"status": "deleted"}
    except Exception as e:
        print(f"Error deleting post: {e}")
        return {"error": "Failed to delete post."}, 500

@core.route('/comments/<comment_id>/update', methods=['POST'])
@login_required
def update_comment(comment_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    content = request.json.get('content')

    if not content:
        return {"error": "Comment cannot be empty"}, 400

    client = get_user_client()
    try:
        result = client.table('comments').update({
            "content": content,
        }).eq("id", comment_id).eq("user_id", user_id).execute()

        if not result.data:
            return {"error": "Unauthorized or comment not found"}, 403

        return {"comment": result.data[0]}
    except Exception as e:
        print(f"Error updating comment: {e}")
        return {"error": "Failed to update comment."}, 500

@core.route('/comments/<comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    client = get_user_client()

    try:
        comment = client.table('comments').select("post_id").eq("id", comment_id).eq("user_id", user_id).single().execute()

        if not comment.data:
            return {"error": "Unauthorized or comment not found"}, 403

        post_id = comment.data['post_id']

        client.table('comments').delete().eq("id", comment_id).eq("user_id", user_id).execute()

        return {"status": "deleted", "post_id": post_id}
    except Exception as e:
        print(f"Error deleting comment: {e}")
        return {"error": "Failed to delete comment."}, 500

@core.route('/posts/create', methods=['POST'])
@login_required
def create_post():
    user_session = session.get('user')
    user_id = user_session.get('id')

    current_time = time.time()
    last_post_time = session.get('last_post_time', 0)
    if current_time - last_post_time < 30:
        flash("You are posting too fast! Please wait a moment.", "warning")
        return redirect(url_for('core.dashboard'))

    access_token = session.get('access_token')

    content = request.form.get('content')
    category = request.form.get('category', 'General')
    image_files = request.files.getlist('image')

    event_title = request.form.get('event_title')
    price = request.form.get('price')
    location = request.form.get('location')
    status = request.form.get('status')
    event_date = request.form.get('event_date')
    event_end_date = request.form.get('event_end_date')

    price = float(price) if price and price.strip() else None
    location = location.strip() if location and location.strip() else None
    status = status.strip() if status and status.strip() else None
    if category != 'Lost & Found' and status == 'Lost':
        status = None

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

    client = get_user_client()

    image_urls = []
    if image_files:
        for img_file in image_files:
            if img_file.filename:
                try:
                    img_url = upload_single_image(client, img_file, user_id)
                    if img_url:
                        image_urls.append(img_url)
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
        client.table('posts').insert(post_data).execute()

        session['last_post_time'] = current_time

        flash("Post created successfully!", "success")
    except Exception as e:
        print(f"CRITICAL: Post insertion failed: {str(e)}")
        flash("Something went wrong. Please try again.", "error")

    return redirect(url_for('core.dashboard'))

def upload_single_image(client, file, user_id):
    import uuid

    file_ext = file.filename.split('.')[-1]
    timestamp = int(time.time())
    filename = f"{user_id}/{timestamp}_{uuid.uuid4().hex}.{file_ext}"
    bucket_name = 'post-images'

    file.seek(0)
    file_data = file.read()

    client.storage.from_(bucket_name).upload(
        path=filename,
        file=file_data,
        file_options={"content-type": file.content_type}
    )
    return client.storage.from_(bucket_name).get_public_url(filename)

@core.route('/notifications/<notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    try:
        user_id = session.get('user', {}).get('id')
        client = get_user_client()
        client.table('notifications')\
            .update({"is_read": True})\
            .eq("id", notification_id)\
            .eq("user_id", user_id)\
            .execute()
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}, 500

@core.route('/login')
def login():
    return render_template('login.html')
