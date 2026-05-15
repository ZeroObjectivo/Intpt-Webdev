from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify, make_response
from .auth import (
    is_jwt_error,
    login_required,
    refresh_supabase_auth,
)
from services.supabase_client import get_user_client, supabase_service
import datetime
import time
import os
import re
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

core = Blueprint('core', __name__)

DISPLAY_TIMEZONE = ZoneInfo("Asia/Manila")
HERON_BUSINESS_CATEGORIES = ['Heron Business', 'Buy & Sell']
EMBED_URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)
YOUTUBE_ID_RE = re.compile(r'^[A-Za-z0-9_-]{6,}$')
LOOM_ID_RE = re.compile(r'^[A-Za-z0-9]+$')
VIMEO_ID_RE = re.compile(r'^\d+$')
DAILYMOTION_ID_RE = re.compile(r'^[A-Za-z0-9]+$')
TIKTOK_ID_RE = re.compile(r'^\d{8,}$')
PROFANITY_WARNING_THRESHOLD = 5
PROFANITY_SUSPEND_THRESHOLD = 10
PROFANITY_WEEK_RESET_DAYS = 7
PROFANITY_SUSPEND_DAYS = 3
PROFANITY_TERM_CACHE_SECONDS = 300
_PROFANITY_TERM_CACHE = {"fetched_at": 0.0, "terms": []}

DEFAULT_FORBIDDEN_TERMS = [
    "putang ina", "putangina", "tang ina", "tangina", "puta ka", "anak ka ng puta",
    "gago", "gaga", "ulol", "tanga", "bobo", "pakshet", "punyeta", "kantot", "burat", "bayag", "jakol",
    "fuck", "fucking", "shit", "bitch", "asshole", "motherfucker", "bastard", "dick", "pussy", "cunt", "slut", "whore", "bullshit",
    "puta", "hijo de puta", "coño", "mierda", "cabron",
    "madarchod", "behenchod", "chutiya", "randi", "gandu",
    "شرموطة", "قحبة", "كس", "طيز", "زب"
]

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

def normalize_text_for_moderation(text):
    lowered = (text or "").lower()
    collapsed = re.sub(r"[^\w]+", " ", lowered, flags=re.UNICODE)
    return re.sub(r"\s+", " ", collapsed).strip()

def load_forbidden_terms():
    now_ts = time.time()
    if _PROFANITY_TERM_CACHE["terms"] and (now_ts - float(_PROFANITY_TERM_CACHE["fetched_at"] or 0) < PROFANITY_TERM_CACHE_SECONDS):
        return _PROFANITY_TERM_CACHE["terms"]

    terms = set(DEFAULT_FORBIDDEN_TERMS)
    client = supabase_service or get_user_client()
    try:
        res = client.table('forbidden_words').select("word").execute()
        for row in (res.data or []):
            word = (row.get("word") or "").strip().lower()
            if word:
                terms.add(word)
    except Exception as e:
        print(f"Warning: failed loading forbidden words from DB, using defaults ({e})")

    normalized_terms = sorted({normalize_text_for_moderation(term) for term in terms if term})
    _PROFANITY_TERM_CACHE["fetched_at"] = now_ts
    _PROFANITY_TERM_CACHE["terms"] = normalized_terms
    return normalized_terms

def find_profanity_match(content):
    normalized_text = normalize_text_for_moderation(content)
    if not normalized_text:
        return None
    padded_text = f" {normalized_text} "
    for term in load_forbidden_terms():
        if not term:
            continue
        token = f" {term} "
        if token in padded_text:
            return term
    return None

def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def _upsert_policy_warning_notification(client, user_id, title, message, warn_reason=None):
    try:
        client.table('notifications').insert({
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": "warning"
        }).execute()
    except Exception as e:
        print(f"Failed to create policy notification: {e}")

    if not warn_reason:
        return

    try:
        client.table('warnings').insert({
            "user_id": user_id,
            "admin_id": None,
            "reason": warn_reason
        }).execute()
    except Exception as e:
        print(f"Failed to create automated warning row: {e}")

def evaluate_submission_policy(user_id, content, submission_type):
    now = datetime.datetime.now(datetime.timezone.utc)
    moderation_client = supabase_service or get_user_client()
    profile_res = moderation_client.table('profiles')\
        .select("id, status, ban_reason, suspended_until, profanity_count, profanity_counter_started_at, profanity_warning_sent")\
        .eq("id", user_id).single().execute()
    profile = profile_res.data or {}

    status = (profile.get("status") or "active").strip().lower()
    ban_reason = profile.get("ban_reason") or ""
    suspended_until = parse_post_datetime(profile.get("suspended_until"))
    counter_started = parse_post_datetime(profile.get("profanity_counter_started_at"))
    profanity_count = _safe_int(profile.get("profanity_count"), 0)
    warning_sent = bool(profile.get("profanity_warning_sent"))
    profile_updates = {}

    if counter_started is None:
        counter_started = now
        profile_updates["profanity_counter_started_at"] = now.isoformat()

    if counter_started and now - counter_started >= datetime.timedelta(days=PROFANITY_WEEK_RESET_DAYS):
        profanity_count = 0
        warning_sent = False
        counter_started = now
        profile_updates.update({
            "profanity_count": 0,
            "profanity_warning_sent": False,
            "profanity_counter_started_at": now.isoformat()
        })

    if status == "suspended":
        if suspended_until and suspended_until <= now:
            status = "active"
            ban_reason = ""
            suspended_until = None
            profanity_count = 0
            warning_sent = False
            counter_started = now
            profile_updates.update({
                "status": "active",
                "ban_reason": None,
                "suspended_until": None,
                "profanity_count": 0,
                "profanity_warning_sent": False,
                "profanity_counter_started_at": now.isoformat()
            })
        else:
            if profile_updates:
                moderation_client.table('profiles').update(profile_updates).eq("id", user_id).execute()
            remaining = "temporarily suspended"
            if suspended_until:
                remaining = f"suspended until {suspended_until.astimezone(DISPLAY_TIMEZONE).strftime('%b %d, %Y %I:%M %p')}"
            return {
                "allowed": False,
                "reason": "suspended",
                "message": f"Your account is {remaining}. Posting and commenting are disabled.",
                "count": profanity_count,
                "threshold_warning": PROFANITY_WARNING_THRESHOLD,
                "threshold_suspend": PROFANITY_SUSPEND_THRESHOLD
            }

    if status == "banned":
        if profile_updates:
            moderation_client.table('profiles').update(profile_updates).eq("id", user_id).execute()
        reason_text = f" Reason: {ban_reason}" if ban_reason else ""
        return {
            "allowed": False,
            "reason": "banned",
            "message": f"Your account is banned and cannot create posts or comments.{reason_text}",
            "count": profanity_count,
            "threshold_warning": PROFANITY_WARNING_THRESHOLD,
            "threshold_suspend": PROFANITY_SUSPEND_THRESHOLD
        }

    matched_term = find_profanity_match(content)
    if matched_term:
        profanity_count += 1
        profile_updates.update({
            "profanity_count": profanity_count,
            "profanity_counter_started_at": (counter_started or now).isoformat()
        })

        auto_action = None
        if profanity_count >= PROFANITY_SUSPEND_THRESHOLD:
            suspended_until = now + datetime.timedelta(days=PROFANITY_SUSPEND_DAYS)
            profile_updates.update({
                "status": "suspended",
                "suspended_until": suspended_until.isoformat(),
                "ban_reason": "Automatic moderation suspension due to repeated blocked language.",
                "profanity_warning_sent": True
            })
            auto_action = "suspended"
            _upsert_policy_warning_notification(
                moderation_client,
                user_id,
                "Account Suspended (Policy)",
                f"Your account has been suspended for {PROFANITY_SUSPEND_DAYS} days due to repeated blocked language.",
                warn_reason=f"Automatic suspension ({profanity_count}/{PROFANITY_SUSPEND_THRESHOLD}) for blocked language."
            )
        elif profanity_count >= PROFANITY_WARNING_THRESHOLD and not warning_sent:
            profile_updates["profanity_warning_sent"] = True
            auto_action = "warned"
            _upsert_policy_warning_notification(
                moderation_client,
                user_id,
                "Content Warning (Policy)",
                f"You have reached {profanity_count} blocked-language violations. At {PROFANITY_SUSPEND_THRESHOLD}, your account will be suspended.",
                warn_reason=f"Automatic profanity warning ({profanity_count}/{PROFANITY_SUSPEND_THRESHOLD})."
            )

        moderation_client.table('profiles').update(profile_updates).eq("id", user_id).execute()

        if auto_action == "suspended":
            return {
                "allowed": False,
                "reason": "suspended",
                "message": f"Blocked language detected. Your account is suspended for {PROFANITY_SUSPEND_DAYS} days.",
                "count": profanity_count,
                "threshold_warning": PROFANITY_WARNING_THRESHOLD,
                "threshold_suspend": PROFANITY_SUSPEND_THRESHOLD
            }

        return {
            "allowed": False,
            "reason": "profanity",
            "message": (
                f"Blocked language detected in your {submission_type}. "
                f"Strike {profanity_count}/{PROFANITY_SUSPEND_THRESHOLD}. "
                f"At {PROFANITY_WARNING_THRESHOLD} you receive a warning, at {PROFANITY_SUSPEND_THRESHOLD} you are suspended."
            ),
            "count": profanity_count,
            "threshold_warning": PROFANITY_WARNING_THRESHOLD,
            "threshold_suspend": PROFANITY_SUSPEND_THRESHOLD
        }

    if profile_updates:
        moderation_client.table('profiles').update(profile_updates).eq("id", user_id).execute()

    return {
        "allowed": True,
        "reason": None,
        "message": None,
        "count": profanity_count,
        "threshold_warning": PROFANITY_WARNING_THRESHOLD,
        "threshold_suspend": PROFANITY_SUSPEND_THRESHOLD
    }

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

def parse_embed_timestamp(value):
    if not value:
        return None

    raw = str(value).strip().lower()
    if not raw:
        return None

    if raw.isdigit():
        return int(raw)

    match = re.fullmatch(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?', raw)
    if not match:
        return None

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    total = hours * 3600 + minutes * 60 + seconds
    return total or None

def extract_embed_from_content(content):
    if not content:
        return None

    for match in EMBED_URL_RE.finditer(str(content)):
        source_url = match.group(0).rstrip('.,!?;:')
        while source_url.endswith(')') and source_url.count('(') < source_url.count(')'):
            source_url = source_url[:-1]

        embed = extract_embed_from_url(source_url)
        if embed:
            return embed

    return None

def extract_embed_from_url(source_url):
    try:
        parsed = urlparse(source_url)
    except ValueError:
        return None

    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return None

    host = parsed.netloc.lower().split(':')[0]
    path_parts = [segment for segment in parsed.path.split('/') if segment]
    query = parse_qs(parsed.query)

    provider = None
    embed_url = None

    if host in {'youtu.be', 'www.youtu.be', 'youtube.com', 'www.youtube.com', 'm.youtube.com'}:
        video_id = None
        if host.endswith('youtu.be') and path_parts:
            video_id = path_parts[0]
        elif path_parts and path_parts[0] == 'watch':
            video_id = (query.get('v') or [None])[0]
        elif len(path_parts) >= 2 and path_parts[0] in {'shorts', 'embed'}:
            video_id = path_parts[1]

        if video_id and YOUTUBE_ID_RE.fullmatch(video_id):
            provider = 'youtube'
            embed_url = f"https://www.youtube.com/embed/{video_id}"
            start_seconds = parse_embed_timestamp((query.get('t') or [None])[0]) or parse_embed_timestamp((query.get('start') or [None])[0])
            if start_seconds:
                embed_url = f"{embed_url}?start={start_seconds}"

    elif host.endswith('loom.com') and len(path_parts) >= 2 and path_parts[0] in {'share', 'embed'}:
        video_id = path_parts[1]
        if LOOM_ID_RE.fullmatch(video_id):
            provider = 'loom'
            embed_url = f"https://www.loom.com/embed/{video_id}"

    elif host in {'vimeo.com', 'www.vimeo.com', 'player.vimeo.com'}:
        video_id = None
        if host == 'player.vimeo.com' and len(path_parts) >= 2 and path_parts[0] == 'video':
            video_id = path_parts[1]
        else:
            numeric_segments = [part for part in path_parts if VIMEO_ID_RE.fullmatch(part)]
            if numeric_segments:
                video_id = numeric_segments[-1]

        if video_id and VIMEO_ID_RE.fullmatch(video_id):
            provider = 'vimeo'
            embed_url = f"https://player.vimeo.com/video/{video_id}"

    elif host in {'dailymotion.com', 'www.dailymotion.com', 'dai.ly'}:
        video_id = None
        if host == 'dai.ly' and path_parts:
            video_id = path_parts[0]
        elif len(path_parts) >= 2 and path_parts[0] in {'video', 'embed'}:
            if path_parts[0] == 'video':
                video_id = path_parts[1]
            elif len(path_parts) >= 3 and path_parts[1] == 'video':
                video_id = path_parts[2]

        if video_id:
            video_id = video_id.split('_')[0]

        if video_id and DAILYMOTION_ID_RE.fullmatch(video_id):
            provider = 'dailymotion'
            embed_url = f"https://www.dailymotion.com/embed/video/{video_id}"

    elif host.endswith('tiktok.com'):
        video_id = None

        if len(path_parts) >= 3 and path_parts[0].startswith('@') and path_parts[1] == 'video':
            video_id = path_parts[2]
        elif len(path_parts) >= 3 and path_parts[0] == 'embed' and path_parts[1] == 'v2':
            video_id = path_parts[2]
        elif len(path_parts) >= 3 and path_parts[0] == 'player' and path_parts[1] == 'v1':
            video_id = path_parts[2]

        if video_id and TIKTOK_ID_RE.fullmatch(video_id):
            provider = 'tiktok'
            embed_url = f"https://www.tiktok.com/player/v1/{video_id}"

    if not embed_url:
        return None

    return {
        "provider": provider,
        "embed_url": embed_url,
        "source_url": source_url
    }

def attach_embed_metadata(post):
    if not isinstance(post, dict):
        return
    post['embed'] = extract_embed_from_content(post.get('content'))

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

def parse_catalog_multiline(value):
    if not value:
        return []
    lines = [line.strip(" \t-•") for line in str(value).splitlines()]
    return [line for line in lines if line]

def load_catalog_page_data(user_id, catalog_kind):
    client = get_user_client()
    profile_res = client.table('profiles').select("*").eq("id", user_id).single().execute()
    profile = profile_res.data

    if catalog_kind == 'scholarship':
        cards_res = client.table('scholarship_catalog')\
            .select("id, scholarship_type, name, details, qualifications, requirements, created_at")\
            .order("created_at", desc=True)\
            .limit(60).execute()
        cards = cards_res.data or []
        for card in cards:
            card['relative_created_at'] = format_relative_time(card.get('created_at'))
            card['qualification_items'] = parse_catalog_multiline(card.get('qualifications'))
            card['requirement_items'] = parse_catalog_multiline(card.get('requirements'))
        return profile, cards

    cards_res = client.table('umak_coop_items')\
        .select("id, name, details, price, availability, image_url, created_at")\
        .order("created_at", desc=True)\
        .limit(60).execute()
    cards = cards_res.data or []
    for card in cards:
        card['relative_created_at'] = format_relative_time(card.get('created_at'))
        try:
            numeric_price = float(card.get('price')) if card.get('price') is not None else None
        except (TypeError, ValueError):
            numeric_price = None
        card['price_label'] = f"PHP {numeric_price:,.2f}" if numeric_price is not None else "N/A"
    return profile, cards

def build_comment_count_map(client, post_ids):
    if not post_ids:
        return {}

    unique_post_ids = list(dict.fromkeys(post_ids))
    count_map = {pid: 0 for pid in unique_post_ids}

    comments_res = client.table('comments')\
        .select("post_id")\
        .in_("post_id", unique_post_ids).execute()

    for row in (comments_res.data or []):
        post_id = row.get('post_id')
        if post_id in count_map:
            count_map[post_id] += 1

    return count_map

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

    try:
        profile, posts, trending, upcoming_events = load_dashboard_data(user_id, category)
    except Exception as e:
        if is_jwt_error(e) and refresh_supabase_auth():
            profile, posts, trending, upcoming_events = load_dashboard_data(user_id, category)
        elif is_jwt_error(e):
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

@core.route('/scholarship')
@login_required
def scholarship():
    user_session = session.get('user')
    user_id = user_session.get('id')

    try:
        profile, cards = load_catalog_page_data(user_id, 'scholarship')
    except Exception as e:
        if is_jwt_error(e) and refresh_supabase_auth():
            profile, cards = load_catalog_page_data(user_id, 'scholarship')
        elif is_jwt_error(e):
            session.clear()
            flash("Your login session expired. Please sign in again.", "error")
            return redirect(url_for('core.login'))
        else:
            print(f"Error loading scholarship catalog: {e}")
            profile = user_session or {}
            cards = []

    response = make_response(render_template(
        'scholarship.html',
        user=profile,
        cards=cards
    ))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@core.route('/umak-coop')
@login_required
def umak_coop():
    user_session = session.get('user')
    user_id = user_session.get('id')

    try:
        profile, cards = load_catalog_page_data(user_id, 'umak_coop')
    except Exception as e:
        if is_jwt_error(e) and refresh_supabase_auth():
            profile, cards = load_catalog_page_data(user_id, 'umak_coop')
        elif is_jwt_error(e):
            session.clear()
            flash("Your login session expired. Please sign in again.", "error")
            return redirect(url_for('core.login'))
        else:
            print(f"Error loading UMak Coop catalog: {e}")
            profile = user_session or {}
            cards = []

    response = make_response(render_template(
        'umak_coop.html',
        user=profile,
        cards=cards
    ))
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
        if is_jwt_error(e) and refresh_supabase_auth():
            profile, posts, activity = load_profile_data(target_user_id, viewer_id=current_user_id)
            is_own_profile = (current_user_id == target_user_id)
            return render_template('profile_settings.html',
                                   user=profile, posts=posts, activity=activity,
                                   is_own_profile=is_own_profile,
                                   now=datetime.datetime.now(datetime.timezone.utc))
        elif is_jwt_error(e):
            session.clear()
            flash("Your session expired. Please sign in again.", "error")
            return redirect(url_for('core.login'))
        print(f"Error loading profile: {e}")
        flash("Profile not found.", "error")
        return redirect(url_for('core.dashboard'))

@core.route('/settings/profile')
@login_required
def profile_settings():
    return redirect(url_for('core.view_profile', target_user_id=session.get('user').get('id')))

@core.route('/search/users')
@login_required
def search_users():
    query_text = (request.args.get('q') or '').strip()
    if not query_text:
        return jsonify({"status": "ok", "users": []})

    limit_raw = request.args.get('limit', '8')
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 8
    limit = max(1, min(limit, 20))

    current_user_id = session.get('user', {}).get('id')

    def run_search():
        client = get_user_client()
        query = client.table('profiles')\
            .select("id, full_name, avatar_url, college, course")\
            .ilike('full_name', f'%{query_text}%')

        if current_user_id:
            query = query.neq('id', current_user_id)

        res = query.order('full_name').limit(limit).execute()
        users = []

        for row in (res.data or []):
            full_name = (row.get('full_name') or '').strip()
            if not full_name:
                continue
            users.append({
                "id": row.get('id'),
                "full_name": full_name,
                "avatar_url": row.get('avatar_url'),
                "college": row.get('college') or '',
                "course": row.get('course') or '',
            })

        return users

    try:
        users = run_search()
        return jsonify({"status": "ok", "users": users})
    except Exception as e:
        if is_jwt_error(e) and refresh_supabase_auth():
            try:
                users = run_search()
                return jsonify({"status": "ok", "users": users})
            except Exception:
                return jsonify({"status": "error", "reason": "search_failed"}), 500
        if is_jwt_error(e):
            return jsonify({"status": "error", "reason": "session_expired"}), 401
        return jsonify({"status": "error", "reason": "search_failed"}), 500

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

    comments_count_map = build_comment_count_map(client, [p['id'] for p in posts])

    for post in posts:
        post['user_has_liked'] = post['id'] in liked_post_ids
        post['likes_count'] = post.get('likes_count') or 0
        post['comments_count'] = comments_count_map.get(post['id'], 0)
        post['relative_created_at'] = format_relative_time(post.get('created_at'))
        attach_embed_metadata(post)

    activity = []
    is_own_profile = str(viewer_id) == str(user_id)
    if is_own_profile:
        likes_activity = client.table('likes')\
            .select("created_at, posts(id, content, category)")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True).limit(10).execute()

        comments_activity = client.table('comments')\
            .select("id, created_at, content, post_id, posts(id, content, category)")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True).limit(10).execute()

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

    comments_count_map = build_comment_count_map(client, post_ids)

    for post in posts:
        post['user_has_liked'] = post['id'] in liked_post_ids
        post['likes_count'] = post.get('likes_count') or 0
        post['comments_count'] = comments_count_map.get(post['id'], 0)
        post['relative_created_at'] = format_relative_time(post.get('created_at'))
        attach_embed_metadata(post)

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

    trending_comments_map = build_comment_count_map(client, trending_ids)

    for t_post in trending:
        t_post['user_has_liked'] = t_post['id'] in trending_liked_ids
        t_post['likes_count'] = t_post.get('likes_count') or 0
        t_post['comments_count'] = trending_comments_map.get(t_post['id'], 0)
        t_post['relative_created_at'] = format_relative_time(t_post.get('created_at'))
        attach_embed_metadata(t_post)

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

            attach_embed_metadata(event)
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
    try:
        unread_res = client.table('notifications')\
            .select("id", count='exact', head=True)\
            .eq('user_id', user_id)\
            .eq('is_read', False)\
            .execute()
        unread_count = int(unread_res.count or 0)
    except Exception:
        unread_count = len([n for n in items if not n.get('is_read')])

    return {
        "items": items,
        "unread_count": unread_count,
    }

def build_interactions_payload(client, user_id, post_ids):
    if not post_ids:
        return []

    posts_res = client.table('posts')\
        .select("id, likes_count")\
        .in_("id", post_ids).execute()
    posts = posts_res.data or []

    comments_count_map = build_comment_count_map(client, post_ids)

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
            "comments_count": comments_count_map.get(row['id'], 0),
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
    try:
        client = get_user_client()
        state = build_dashboard_sync_state(client, category=category)
    except Exception as e:
        if is_jwt_error(e) and refresh_supabase_auth():
            client = get_user_client()
            state = build_dashboard_sync_state(client, category=category)
        elif is_jwt_error(e):
            return jsonify({"status": "error", "reason": "session_expired"}), 401
        else:
            return jsonify({"status": "error", "reason": "sync_failed"}), 500

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

    try:
        client = get_user_client()
        state = build_dashboard_sync_state(client, category=category)
        notifications = build_notification_payload(client, user_id)
        interactions = {
            "posts": build_interactions_payload(client, user_id, post_ids)
        }
    except Exception as e:
        if is_jwt_error(e) and refresh_supabase_auth():
            client = get_user_client()
            state = build_dashboard_sync_state(client, category=category)
            notifications = build_notification_payload(client, user_id)
            interactions = {
                "posts": build_interactions_payload(client, user_id, post_ids)
            }
        elif is_jwt_error(e):
            return jsonify({"status": "error", "reason": "session_expired"}), 401
        else:
            return jsonify({"status": "error", "reason": "sync_failed"}), 500

    payload = {
        "status": "ok",
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "state": state,
        "notifications": notifications,
        "interactions": interactions,
    }

    admin_domain = normalize_domain(os.getenv('ADMIN_DOMAIN', ''))
    current_host = normalize_domain(request.host)
    is_admin_domain = bool(admin_domain and current_host == admin_domain)

    if is_admin_domain and role in ['admin', 'super_admin', 'superadmin', 'content_manager', 'content_moderator', 'account_manager']:
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
    data = request.get_json(silent=True) or {}
    content = data.get('content')
    parent_id = data.get('parent_id')

    if not content:
        return {"error": "Comment cannot be empty"}, 400

    try:
        moderation = evaluate_submission_policy(user_id, content, "comment")
    except Exception as e:
        print(f"Moderation policy check failed for comment: {e}")
        return {"error": "Unable to validate content policy right now."}, 500

    if not moderation.get("allowed"):
        return {
            "status": "blocked",
            "error": moderation.get("message") or "Your comment violates content policy.",
            "policy": moderation
        }, 403

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

@core.route('/posts/<post_id>/report', methods=['POST'])
@login_required
def report_post(post_id):
    user_session = session.get('user')
    reporter_id = user_session.get('id')
    data = request.get_json(silent=True) or {}
    reason = (data.get('reason') or '').strip()

    if not reason:
        return {"error": "Report reason is required."}, 400

    client = get_user_client()

    try:
        post_res = client.table('posts').select("id, user_id").eq("id", post_id).single().execute()
        post = post_res.data or {}
        if not post:
            return {"error": "Post not found."}, 404

        if post.get('user_id') == reporter_id:
            return {"error": "You cannot report your own post."}, 400

        existing_res = client.table('reports')\
            .select("id, status")\
            .eq("post_id", post_id)\
            .eq("reporter_id", reporter_id)\
            .eq("status", "pending")\
            .limit(1).execute()

        if existing_res.data:
            return {"status": "already_reported"}

        client.table('reports').insert({
            "post_id": post_id,
            "reporter_id": reporter_id,
            "reason": reason
        }).execute()

        return {"status": "reported"}
    except Exception as e:
        print(f"Error reporting post: {e}")
        return {"error": "Failed to report post."}, 500

@core.route('/comments/<comment_id>/update', methods=['POST'])
@login_required
def update_comment(comment_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    data = request.get_json(silent=True) or {}
    content = data.get('content')

    if not content:
        return {"error": "Comment cannot be empty"}, 400

    try:
        moderation = evaluate_submission_policy(user_id, content, "comment")
    except Exception as e:
        print(f"Moderation policy check failed for comment update: {e}")
        return {"error": "Unable to validate content policy right now."}, 500

    if not moderation.get("allowed"):
        return {
            "status": "blocked",
            "error": moderation.get("message") or "Your comment violates content policy.",
            "policy": moderation
        }, 403

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

    try:
        moderation = evaluate_submission_policy(user_id, content or "", "post")
    except Exception as e:
        print(f"Moderation policy check failed for post: {e}")
        flash("Unable to validate content policy right now. Please try again.", "error")
        return redirect(url_for('core.dashboard'))

    if not moderation.get("allowed"):
        policy_message = moderation.get("message") or "Your post violates content policy."
        if not policy_message.startswith("⚠"):
            policy_message = f"⚠ {policy_message}"
        flash(policy_message, "error")
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
    def _apply_mark_read():
        user_id = session.get('user', {}).get('id')
        client = get_user_client()
        client.table('notifications')\
            .update({"is_read": True})\
            .eq("id", notification_id)\
            .eq("user_id", user_id)\
            .execute()

    try:
        _apply_mark_read()
        return jsonify({"status": "success"})
    except Exception as e:
        if is_jwt_error(e) and refresh_supabase_auth():
            try:
                _apply_mark_read()
                return jsonify({"status": "success"})
            except Exception as retry_error:
                if is_jwt_error(retry_error):
                    return jsonify({"status": "error", "reason": "session_expired"}), 401
                return jsonify({"status": "error", "reason": "mark_read_failed"}), 500
        if is_jwt_error(e):
            return jsonify({"status": "error", "reason": "session_expired"}), 401
        return jsonify({"status": "error", "reason": "mark_read_failed"}), 500

@core.route('/login')
def login():
    admin_domain = normalize_domain(os.getenv('ADMIN_DOMAIN', ''))
    host = normalize_domain(request.host)
    is_admin_login = bool(admin_domain and host == admin_domain)

    return render_template(
        'login.html',
        is_admin_login=is_admin_login,
    )
