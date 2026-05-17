import logging
from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify, make_response
from .auth import (
    is_jwt_error,
    login_required,
    refresh_supabase_auth,
)
from services.supabase_client import get_user_client, supabase_service
from app.utils.post_archive import archive_post_snapshot, maybe_purge_expired_archived_posts, purge_expired_archived_posts
import datetime
import time
import os
import re
import calendar as month_calendar

logger = logging.getLogger(__name__)
from urllib.parse import parse_qs, quote, urlparse, urlunparse
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
INSTAGRAM_CODE_RE = re.compile(r'^[A-Za-z0-9_-]+$')
PH_MOBILE_REGEX = re.compile(r'^(?:\+639\d{9}|09\d{9})$')
PH_MOBILE_PREFIX_REGEX = re.compile(
    r'^(?:\+639(?:05|06|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36|37|38|39|45|46|47|48|49|50|51|53|54|55|56|57|58|59|60|61|62|63|64|65|66|67|68|69|70|73|74|75|76|77|78|79|81|90|91|92|93|94|95|96|97|98|99)\d{7}|09(?:05|06|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36|37|38|39|45|46|47|48|49|50|51|53|54|55|56|57|58|59|60|61|62|63|64|65|66|67|68|69|70|73|74|75|76|77|78|79|81|90|91|92|93|94|95|96|97|98|99)\d{7})$'
)
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
        logger.warning("Failed loading forbidden words from DB, using defaults: %s", e)

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


ADMIN_NOTIFICATION_ROLES = {'super_admin', 'superadmin', 'admin', 'content_moderator', 'account_manager'}

def push_notification(client, user_id, *, title, message, notif_type="system", reference_id=None, actor_id=None):
    if not user_id:
        return
    sender_client = supabase_service or client
    try:
        # 1. Implement Like Merging logic
        if notif_type == "interaction" and reference_id and "like" in title.lower():
            try:
                # Fetch recent likers for this post to build merged message
                likes_res = sender_client.table('likes')\
                    .select("user_id, profiles(full_name)")\
                    .eq("post_id", reference_id)\
                    .order("created_at", desc=True)\
                    .limit(3).execute()
                
                total_likes_res = sender_client.table('likes')\
                    .select("id", count="exact")\
                    .eq("post_id", reference_id).execute()
                
                total_count = total_likes_res.count or 0
                likers = likes_res.data or []
                
                if total_count > 0 and likers:
                    # Extract first names
                    names = []
                    for l in likers:
                        full_name = (l.get('profiles') or {}).get('full_name') or "A user"
                        names.append(full_name.split()[0])
                    
                    if total_count == 1:
                        new_title = f"{names[0]} liked your post."
                    elif total_count == 2:
                        new_title = f"{names[0]} and {names[1]} liked your post."
                    else:
                        others_count = total_count - 2
                        new_title = f"{names[0]}, {names[1]} and {others_count} others liked your post."
                    
                    # Check for existing unread like notif to update instead of insert
                    existing = sender_client.table('notifications')\
                        .select("id")\
                        .eq("user_id", user_id)\
                        .eq("type", "interaction")\
                        .eq("reference_id", reference_id)\
                        .ilike("title", "%liked your post%")\
                        .eq("is_read", False)\
                        .limit(1).execute()
                    
                    if existing.data:
                        sender_client.table('notifications').update({
                            "title": new_title,
                            "message": "", # Content moved to title
                            "actor_id": actor_id, # Latest actor for photo
                            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                        }).eq("id", existing.data[0]['id']).execute()
                        return
                    
                    # No existing unread notif, use the merged title for the new insert
                    title = new_title
                    message = ""
            except Exception as e:
                logger.warning("Like merging failed: %s", e)

        # 2. Prevent spamming for non-like interactions (e.g. comment notifications)
        elif notif_type == "interaction" and reference_id:
             existing = sender_client.table('notifications')\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("type", "interaction")\
                .eq("reference_id", reference_id)\
                .eq("title", title)\
                .eq("is_read", False)\
                .limit(1).execute()
             
             if existing.data:
                sender_client.table('notifications').update({
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "actor_id": actor_id
                }).eq("id", existing.data[0]['id']).execute()
                return

        # 3. Standard insert
        sender_client.table('notifications').insert({
            "user_id": user_id,
            "type": notif_type,
            "reference_id": reference_id,
            "actor_id": actor_id,
            "title": title,
            "message": message,
        }).execute()
    except Exception as e:
        logger.warning("Notification insert skipped for user %s: %s", user_id, e)


def push_admin_notification(*, title, message, notif_type="admin", reference_id=None):
    """Send a notification to all users with admin-level roles."""
    sender_client = supabase_service
    if not sender_client:
        logger.warning("No service client available for admin notifications")
        return
    try:
        admins_res = sender_client.table('profiles')\
            .select("id, role")\
            .in_("role", list(ADMIN_NOTIFICATION_ROLES))\
            .execute()
        admin_ids = [a['id'] for a in (admins_res.data or [])]
        if not admin_ids:
            return
        rows = [
            {
                "user_id": uid,
                "type": notif_type,
                "reference_id": reference_id,
                "title": title,
                "message": message,
            }
            for uid in admin_ids
        ]
        sender_client.table('notifications').insert(rows).execute()
    except Exception as e:
        logger.warning("Admin notification broadcast failed: %s", e)

def _upsert_policy_warning_notification(client, user_id, title, message, warn_reason=None):
    try:
        client.table('notifications').insert({
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": "warning"
        }).execute()
    except Exception as e:
        logger.error("Failed to create policy notification: %s", e)

    if not warn_reason:
        return

    try:
        client.table('warnings').insert({
            "user_id": user_id,
            "admin_id": None,
            "reason": warn_reason
        }).execute()
    except Exception as e:
        logger.error("Failed to create automated warning row: %s", e)

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

    # --- YouTube ---
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
            params = ['rel=0', 'modestbranding=1']
            start_seconds = parse_embed_timestamp((query.get('t') or [None])[0]) or parse_embed_timestamp((query.get('start') or [None])[0])
            if start_seconds:
                params.append(f"start={start_seconds}")
            embed_url = f"https://www.youtube.com/embed/{video_id}?{'&'.join(params)}"

    # --- Loom ---
    elif host.endswith('loom.com') and len(path_parts) >= 2 and path_parts[0] in {'share', 'embed'}:
        video_id = path_parts[1]
        if LOOM_ID_RE.fullmatch(video_id):
            provider = 'loom'
            embed_url = f"https://www.loom.com/embed/{video_id}?hide_share=true&hideEmbedTopBar=true"

    # --- Vimeo ---
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
            embed_url = f"https://player.vimeo.com/video/{video_id}?dnt=1"

    # --- DailyMotion ---
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
            embed_url = f"https://www.dailymotion.com/embed/video/{video_id}?endscreen-enable=false&queue-enable=false&sharing-enable=false"

    # --- TikTok ---
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
            embed_url = f"https://www.tiktok.com/player/v1/{video_id}?rel=0"

    # --- Facebook ---
    elif host in {'facebook.com', 'www.facebook.com', 'web.facebook.com', 'm.facebook.com', 'fb.watch'}:
        if host == 'fb.watch':
            provider = 'facebook'
            embed_url = f"https://www.facebook.com/plugins/video.php?href={quote(source_url, safe='')}&show_text=false"
        elif path_parts:
            is_video = 'videos' in path_parts or 'video' in path_parts or 'watch' in path_parts or 'reel' in path_parts
            if is_video:
                provider = 'facebook'
                embed_url = f"https://www.facebook.com/plugins/video.php?href={quote(source_url, safe='')}&show_text=false"
            elif 'posts' in path_parts or 'photos' in path_parts or 'permalink' in path_parts:
                provider = 'facebook'
                embed_url = f"https://www.facebook.com/plugins/post.php?href={quote(source_url, safe='')}&show_text=true"

    # --- Instagram ---
    elif host in {'instagram.com', 'www.instagram.com'}:
        shortcode = None
        if len(path_parts) >= 2 and path_parts[0] in {'p', 'reel', 'reels', 'tv'}:
            shortcode = path_parts[1]

        if shortcode and INSTAGRAM_CODE_RE.fullmatch(shortcode):
            provider = 'instagram'
            embed_url = f"https://www.instagram.com/{path_parts[0]}/{shortcode}/embed/"

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
    created_local = created_at.astimezone(DISPLAY_TIMEZONE)
    now_local = now.astimezone(DISPLAY_TIMEZONE)

    # Within 24 hours: Use relative time (mins/hrs)
    if seconds < 86400:
        if seconds < 60:
            return "Just now"
        if seconds < 3600:
            minutes = seconds // 60
            unit = "min" if minutes == 1 else "mins"
            return f"{minutes} {unit} ago"
        
        hours = seconds // 3600
        unit = "hr" if hours == 1 else "hrs"
        return f"{hours} {unit} ago"

    # Previous local calendar day: use "Yesterday at ..." copy.
    if created_local.date() == (now_local.date() - datetime.timedelta(days=1)):
        return created_local.strftime("Yesterday at %I:%M %p").replace(" 0", " ")

    # Older posts: use descriptive date with year and time
    return created_local.strftime("%B %d, %Y at %I:%M %p").replace(" 0", " ")

def format_profile_date(value):
    parsed = parse_post_datetime(value)
    if parsed is None:
        return ""
    return parsed.astimezone(DISPLAY_TIMEZONE).strftime("%b %d, %Y").replace(" 0", " ")

def normalize_philippine_mobile_number(raw_value):
    candidate = (raw_value or "").strip()
    if not candidate:
        return ""
    if re.search(r'[A-Za-z]', candidate):
        raise ValueError("Invalid phone number.")
    if ' ' in candidate:
        raise ValueError("Invalid phone number.")
    if candidate.startswith('+'):
        if not candidate.startswith('+639'):
            raise ValueError("Phone number must start with 09.")
        if not candidate[1:].isdigit():
            raise ValueError("Invalid phone number.")
        if len(candidate) != 13:
            raise ValueError("Phone number must contain exactly 13 characters.")
    else:
        if not candidate.startswith('09'):
            raise ValueError("Phone number must start with 09.")
        if not candidate.isdigit():
            raise ValueError("Invalid phone number.")
        if len(candidate) != 11:
            raise ValueError("Phone number must contain exactly 11 digits.")

    if not PH_MOBILE_REGEX.fullmatch(candidate):
        raise ValueError("Invalid phone number.")
    if not PH_MOBILE_PREFIX_REGEX.fullmatch(candidate):
        raise ValueError("Invalid phone number.")

    if candidate.startswith('09'):
        return f"+639{candidate[2:]}"
    return candidate

SOCIAL_HOST_PLATFORM_MAP = {
    "facebook.com": "facebook",
    "www.facebook.com": "facebook",
    "m.facebook.com": "facebook",
    "instagram.com": "instagram",
    "www.instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "www.tiktok.com": "tiktok",
    "linkedin.com": "linkedin",
    "www.linkedin.com": "linkedin",
    "discord.com": "discord",
    "www.discord.com": "discord",
}

SOCIAL_PLATFORM_LABELS = {
    "facebook": "Facebook",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "linkedin": "LinkedIn",
    "discord": "Discord",
}

VALID_SOCIAL_VISIBILITIES = {"public", "only_me"}

def normalize_social_url(raw_url):
    candidate = (raw_url or "").strip()
    if not candidate:
        return None

    if "://" not in candidate:
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    host = (parsed.netloc or "").strip().lower()
    path = (parsed.path or "").strip()
    normalized_path = path.rstrip("/")

    if not host or not normalized_path:
        raise ValueError("Please enter valid social profile URLs.")

    platform = SOCIAL_HOST_PLATFORM_MAP.get(host)
    if not platform:
        raise ValueError("Only supported social media links can be saved right now.")

    normalized_url = urlunparse(("https", host, normalized_path, "", "", ""))
    return platform, normalized_url

def normalize_social_links_input(raw_links, raw_visibilities=None):
    raw_links = list(raw_links or [])
    raw_visibilities = list(raw_visibilities or [])
    values = [(value or "").strip() for value in raw_links if (value or "").strip()]
    if len(values) > 3:
        raise ValueError("You can save up to 3 social links only.")

    results = []
    seen_urls = set()
    compact_index = 0
    for index, value in enumerate(raw_links):
        value = (value or "").strip()
        if not value:
            continue
        compact_index += 1
        normalized = normalize_social_url(value)
        if normalized is None:
            continue
        platform, normalized_url = normalized
        if normalized_url in seen_urls:
            raise ValueError("Duplicate social links are not allowed.")
        visibility = (raw_visibilities[index] if index < len(raw_visibilities) else "public") or "public"
        visibility = visibility.strip().lower()
        if visibility not in VALID_SOCIAL_VISIBILITIES:
            raise ValueError("Please choose a valid visibility setting for each social link.")
        seen_urls.add(normalized_url)
        results.append({
            "platform": platform,
            "url": normalized_url,
            "visibility": visibility,
            "position": compact_index,
        })
    return results

def load_profile_social_links(client, user_id):
    response = client.table('profile_social_links')\
        .select("platform, url, visibility, position")\
        .eq("profile_id", user_id)\
        .order("position")\
        .execute()

    return [
        {
            "platform": row.get("platform"),
            "url": row.get("url"),
            "label": SOCIAL_PLATFORM_LABELS.get(row.get("platform"), (row.get("platform") or "").title()),
            "visibility": row.get("visibility") or "public",
            "position": row.get("position"),
        }
        for row in (response.data or [])
        if row.get("url")
    ]

def load_college_institute_options():
    client = supabase_service or get_user_client()
    try:
        response = client.table('colleges_institutes')\
            .select("name, full_name, type")\
            .order("type")\
            .order("name")\
            .execute()
    except Exception as exc:
        logger.warning("Unable to load colleges_institutes options: %s", exc)
        return []

    options = []
    seen = set()
    for row in (response.data or []):
        code = (row.get('name') or '').strip()
        if not code or code in seen:
            continue
        seen.add(code)
        option_type = (row.get('type') or '').strip()
        group_label = "Colleges" if option_type.lower() == "college" else "Institutes"
        options.append({
            "value": code,
            "label": code,
            "full_name": (row.get('full_name') or '').strip(),
            "type": option_type,
            "group": group_label,
        })
    return options

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

def normalize_calendar_month(month_param):
    now_local = datetime.datetime.now(DISPLAY_TIMEZONE)
    month_anchor = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    raw_month = (month_param or '').strip()
    if not raw_month:
        return month_anchor

    try:
        parsed = datetime.datetime.strptime(raw_month, "%Y-%m")
        safe_year = max(2000, min(parsed.year, 2100))
        return month_anchor.replace(year=safe_year, month=parsed.month)
    except ValueError:
        return month_anchor

def shift_calendar_month(month_anchor, delta):
    month_index = (month_anchor.year * 12 + (month_anchor.month - 1)) + delta
    year = month_index // 12
    month = (month_index % 12) + 1
    return month_anchor.replace(year=year, month=month, day=1)

def format_calendar_time_range(start_local, end_local):
    start_label = start_local.strftime('%I:%M %p').lstrip('0')
    if not end_local or end_local == start_local:
        return start_label
    if end_local.date() == start_local.date():
        end_label = end_local.strftime('%I:%M %p').lstrip('0')
        return f"{start_label} - {end_label}"
    start_full = start_local.strftime('%b %d %I:%M %p')
    end_full = end_local.strftime('%b %d %I:%M %p')
    return f"{start_full} - {end_full}"

def load_event_calendar_page_data(user_id, month_param=None):
    client = get_user_client()
    profile_res = client.table('profiles').select("*").eq("id", user_id).single().execute()
    profile = profile_res.data or {}

    month_anchor = normalize_calendar_month(month_param)
    month_start_local = month_anchor
    month_end_local = shift_calendar_month(month_anchor, 1)
    month_start_date = month_start_local.date()
    month_last_date = (month_end_local - datetime.timedelta(days=1)).date()

    window_start_utc = (month_start_local - datetime.timedelta(days=31)).astimezone(datetime.timezone.utc).isoformat()
    window_end_utc = (month_end_local + datetime.timedelta(days=31)).astimezone(datetime.timezone.utc).isoformat()

    events_res = client.table('posts')\
        .select("id, content, event_title, event_date, event_end_date, location")\
        .eq("category", "Events")\
        .gte("event_date", window_start_utc)\
        .lt("event_date", window_end_utc)\
        .order("event_date", desc=False)\
        .limit(400).execute()

    now_local = datetime.datetime.now(DISPLAY_TIMEZONE)
    events_by_day = {}
    month_events = []

    for event in (events_res.data or []):
        try:
            start_dt = parse_post_datetime(event.get('event_date'))
            if not start_dt:
                continue

            end_dt = parse_post_datetime(event.get('event_end_date')) or start_dt
            start_local = start_dt.astimezone(DISPLAY_TIMEZONE)
            end_local = end_dt.astimezone(DISPLAY_TIMEZONE)
            if end_local < start_local:
                end_local = start_local

            if end_local < month_start_local or start_local >= month_end_local:
                continue

            if start_local <= now_local <= end_local:
                status = "Ongoing"
            elif start_local > now_local:
                status = "Upcoming"
            else:
                status = "Ended"

            title = (event.get('event_title') or '').strip() or (event.get('content') or 'Untitled Event').strip() or 'Untitled Event'
            location = (event.get('location') or 'UMak Campus').strip() or 'UMak Campus'

            event_item = {
                "id": event.get('id'),
                "title": title,
                "location": location,
                "status": status,
                "time_display": format_calendar_time_range(start_local, end_local),
                "day_label": start_local.strftime('%b %d'),
                "start_iso": start_local.isoformat(),
            }
            month_events.append(event_item)

            span_start = max(start_local.date(), month_start_date)
            span_end = min(end_local.date(), month_last_date)
            cursor_date = span_start
            while cursor_date <= span_end:
                events_by_day.setdefault(cursor_date.day, []).append(event_item)
                cursor_date += datetime.timedelta(days=1)
        except Exception as e:
            logger.warning("Skipping malformed calendar event row: %s", e)

    for day in events_by_day:
        events_by_day[day].sort(key=lambda item: item.get('start_iso') or '')
    month_events.sort(key=lambda item: item.get('start_iso') or '')

    weekday_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    first_weekday, days_in_month = month_calendar.monthrange(month_anchor.year, month_anchor.month)
    today_local = now_local.date()
    calendar_cells = []

    for _ in range(first_weekday):
        calendar_cells.append(None)

    for day in range(1, days_in_month + 1):
        day_events = events_by_day.get(day, [])
        cell_date = datetime.date(month_anchor.year, month_anchor.month, day)
        calendar_cells.append({
            "day": day,
            "event_count": len(day_events),
            "events": day_events[:2],
            "is_today": cell_date == today_local,
        })

    while len(calendar_cells) % 7 != 0:
        calendar_cells.append(None)

    prev_month = shift_calendar_month(month_anchor, -1).strftime('%Y-%m')
    next_month = shift_calendar_month(month_anchor, 1).strftime('%Y-%m')

    return profile, {
        "month_label": month_anchor.strftime('%B %Y'),
        "month_key": month_anchor.strftime('%Y-%m'),
        "prev_month": prev_month,
        "next_month": next_month,
        "weekday_labels": weekday_labels,
        "calendar_cells": calendar_cells,
        "month_events": month_events,
    }

def build_comment_count_map(client, post_ids):
    if not post_ids:
        return {}

    unique_post_ids = list(dict.fromkeys(post_ids))
    count_map = {pid: 0 for pid in unique_post_ids}

    comments_res = client.table('comments')\
        .select("post_id")\
        .in_("post_id", unique_post_ids)\
        .is_("parent_id", "null").execute()

    for row in (comments_res.data or []):
        post_id = row.get('post_id')
        if post_id in count_map:
            count_map[post_id] += 1

    return count_map

def _safe_exact_count(response):
    try:
        return int(response.count or 0)
    except Exception:
        return 0

def load_home_metrics():
    metrics = {
        "members_count": 0,
        "posts_count": 0,
        "upcoming_events_count": 0,
        "scholarship_count": 0,
        "coop_count": 0,
        "catalog_count": 0,
    }

    client = supabase_service or get_user_client()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        metrics["members_count"] = _safe_exact_count(
            client.table('profiles').select("id", count='exact', head=True).execute()
        )
    except Exception as e:
        logger.warning("Home metrics: profiles count unavailable: %s", e)

    try:
        metrics["posts_count"] = _safe_exact_count(
            client.table('posts').select("id", count='exact', head=True).execute()
        )
    except Exception as e:
        logger.warning("Home metrics: posts count unavailable: %s", e)

    try:
        metrics["upcoming_events_count"] = _safe_exact_count(
            client.table('posts')
                .select("id", count='exact', head=True)
                .eq("category", "Events")
                .or_(f"event_date.gte.{now_iso},event_end_date.gte.{now_iso}")
                .execute()
        )
    except Exception as e:
        logger.warning("Home metrics: events count unavailable: %s", e)

    try:
        metrics["scholarship_count"] = _safe_exact_count(
            client.table('scholarship_catalog').select("id", count='exact', head=True).execute()
        )
    except Exception as e:
        logger.warning("Home metrics: scholarship count unavailable: %s", e)

    try:
        metrics["coop_count"] = _safe_exact_count(
            client.table('umak_coop_items').select("id", count='exact', head=True).execute()
        )
    except Exception as e:
        logger.warning("Home metrics: coop count unavailable: %s", e)

    metrics["catalog_count"] = metrics["scholarship_count"] + metrics["coop_count"]
    return metrics

@core.route('/')
def home():
    user = session.get('user')
    metrics = load_home_metrics()
    return render_template('home.html', user=user, metrics=metrics)

@core.route('/dashboard')
@login_required
def dashboard():
    user_session = session.get('user')
    user_id = user_session.get('id')
    category = normalize_dashboard_category(request.args.get('category'))

    if supabase_service:
        try:
            maybe_purge_expired_archived_posts(supabase_service)
        except Exception as cleanup_e:
            logger.warning("Dashboard archive cleanup skipped: %s", cleanup_e)

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

    # Fetch colleges/institutes for the Create Post modal
    client = get_user_client()
    units_res = client.table('colleges_institutes').select("name, full_name, type").order('name').execute()
    colleges = [u for u in units_res.data if u['type'] == 'College']
    institutes = [u for u in units_res.data if u['type'] == 'Institute']

    response = make_response(render_template('dashboard.html',
                           user=profile,
                           posts=posts,
                           active_category=category,
                           trending=trending,
                           events=upcoming_events,
                           colleges=colleges,
                           institutes=institutes,
                           DISPLAY_TIMEZONE=DISPLAY_TIMEZONE,
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
            logger.error("Error loading scholarship catalog: %s", e)
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
            logger.error("Error loading UMak Coop catalog: %s", e)
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

@core.route('/event-calendar')
@login_required
def event_calendar():
    user_session = session.get('user')
    user_id = user_session.get('id')
    month_param = request.args.get('month')

    try:
        profile, calendar_payload = load_event_calendar_page_data(user_id, month_param)
    except Exception as e:
        if is_jwt_error(e) and refresh_supabase_auth():
            profile, calendar_payload = load_event_calendar_page_data(user_id, month_param)
        elif is_jwt_error(e):
            session.clear()
            flash("Your login session expired. Please sign in again.", "error")
            return redirect(url_for('core.login'))
        else:
            logger.error("Error loading event calendar: %s", e)
            profile = user_session or {}
            month_anchor = normalize_calendar_month(month_param)
            calendar_payload = {
                "month_label": month_anchor.strftime('%B %Y'),
                "month_key": month_anchor.strftime('%Y-%m'),
                "prev_month": shift_calendar_month(month_anchor, -1).strftime('%Y-%m'),
                "next_month": shift_calendar_month(month_anchor, 1).strftime('%Y-%m'),
                "weekday_labels": ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                "calendar_cells": [],
                "month_events": [],
            }

    response = make_response(render_template(
        'event_calendar.html',
        user=profile,
        **calendar_payload
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
        profile, posts, pending_posts, interactions, college_options, social_links, public_social_links = load_profile_data(target_user_id, viewer_id=current_user_id)
        is_own_profile = (current_user_id == target_user_id)

        # Fetch colleges/institutes for settings dropdown
        client = get_user_client()
        units_res = client.table('colleges_institutes').select("name, full_name, type").order('name').execute()
        colleges = [u for u in units_res.data if u['type'] == 'College']
        institutes = [u for u in units_res.data if u['type'] == 'Institute']

        return render_template('profile_settings.html',
                               user=profile,
                               posts=posts,
                               pending_posts=pending_posts,
                               interactions=interactions,
                               college_options=college_options,
                               social_links=social_links,
                               public_social_links=public_social_links,
                               is_own_profile=is_own_profile,
                               colleges=colleges,
                               institutes=institutes,
                               now=datetime.datetime.now(datetime.timezone.utc))
    except Exception as e:
        if is_jwt_error(e) and refresh_supabase_auth():
            profile, posts, pending_posts, interactions, college_options, social_links, public_social_links = load_profile_data(target_user_id, viewer_id=current_user_id)
            is_own_profile = (current_user_id == target_user_id)
            client = get_user_client()
            units_res = client.table('colleges_institutes').select("name, full_name, type").order('name').execute()
            colleges = [u for u in units_res.data if u['type'] == 'College']
            institutes = [u for u in units_res.data if u['type'] == 'Institute']
            return render_template('profile_settings.html',
                                   user=profile, posts=posts, pending_posts=pending_posts, interactions=interactions, college_options=college_options, social_links=social_links, public_social_links=public_social_links,
                                   is_own_profile=is_own_profile,
                                   colleges=colleges,
                                   institutes=institutes,
                                   now=datetime.datetime.now(datetime.timezone.utc))
        elif is_jwt_error(e):
            session.clear()
            flash("Your session expired. Please sign in again.", "error")
            return redirect(url_for('core.login'))
        logger.error("Error loading profile: %s", e)
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
    target_id = request.args.get('id')
    
    limit_raw = request.args.get('limit', '8')
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 8
    limit = max(1, min(limit, 20))

    current_user_id = session.get('user', {}).get('id')

    def run_search():
        client = get_user_client()
        
        if target_id:
            res = client.table('profiles')\
                .select("id, full_name, avatar_url, college, course")\
                .eq('id', target_id).execute()
            return res.data or []

        if not query_text:
            return []

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
    college_options = load_college_institute_options()
    social_links = load_profile_social_links(client, user_id)
    public_social_links = [link for link in social_links if link.get("visibility") == "public"]

    profile_response = client.table('profiles').select("*").eq("id", user_id).single().execute()
    profile = profile_response.data

    activity_timestamps = []
    if profile:
        profile_created_at = profile.get('created_at')
        profile['joined_label'] = format_profile_date(profile_created_at)
        if profile_created_at:
            activity_timestamps.append(profile_created_at)

    # Enforce contact privacy: hide contact_number from non-owners
    if profile and str(viewer_id) != str(user_id):
        if profile.get('contact_privacy') == 'only_me':
            profile['contact_number'] = None

    posts_query = client.table('posts')\
        .select("*, profiles(full_name, avatar_url, college, course, level)")\
        .eq("user_id", user_id)\
        .eq('status', 'approved')
    
    posts_response = posts_query.order("created_at", desc=True).execute()
    posts = posts_response.data
    pending_posts = []

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
        if post.get('created_at'):
            activity_timestamps.append(post.get('created_at'))

    likes_count_res = client.table('likes').select("post_id", count="exact").eq("user_id", user_id).execute()
    comments_count_res = client.table('comments').select("id", count="exact").eq("user_id", user_id).execute()

    interactions = {
        "stats": {
            "posts_count": len(posts),
            "likes_count": likes_count_res.count or 0,
            "comments_count": comments_count_res.count or 0,
        },
        "likes": [],
        "comments": [],
    }
    is_own_profile = str(viewer_id) == str(user_id)
    if is_own_profile:
        pending_posts_res = client.table('posts')\
            .select("*, profiles(full_name, avatar_url, college, course, level)")\
            .eq("user_id", user_id)\
            .eq('status', 'pending')\
            .order("created_at", desc=True).execute()
        pending_posts = pending_posts_res.data or []

        pending_comments_count_map = build_comment_count_map(client, [p['id'] for p in pending_posts])
        for post in pending_posts:
            post['user_has_liked'] = False
            post['likes_count'] = post.get('likes_count') or 0
            post['comments_count'] = pending_comments_count_map.get(post['id'], 0)
            post['relative_created_at'] = format_relative_time(post.get('created_at'))
            attach_embed_metadata(post)
            if post.get('created_at'):
                activity_timestamps.append(post.get('created_at'))

        likes_activity = client.table('likes')\
            .select("created_at, posts(id, content, category)")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True).limit(12).execute()

        comments_activity = client.table('comments')\
            .select("id, created_at, content, post_id, posts(id, content, category)")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True).limit(12).execute()

        for l in likes_activity.data:
            if l.get('posts'):
                activity_timestamps.append(l.get('created_at'))
                interactions["likes"].append({
                    "created_at": l['created_at'],
                    "post_id": l['posts']['id'],
                    "post_content": l['posts']['content'],
                    "category": l['posts']['category'],
                    "relative_created_at": format_relative_time(l.get('created_at')),
                })

        for c in comments_activity.data:
            if c.get('posts'):
                activity_timestamps.append(c.get('created_at'))
                interactions["comments"].append({
                    "created_at": c['created_at'],
                    "content": c['content'],
                    "post_id": c['posts']['id'],
                    "post_content": c['posts']['content'],
                    "category": c['posts']['category'],
                    "relative_created_at": format_relative_time(c.get('created_at')),
                })

    if profile:
        last_seen_source = max(
            (parse_post_datetime(value) for value in activity_timestamps if value),
            default=None,
        )
        profile['last_seen_label'] = format_relative_time(last_seen_source) if last_seen_source else ""

        current_college = (profile.get('college') or '').strip()
        if current_college and all(option["value"] != current_college for option in college_options):
            college_options.insert(0, {
                "value": current_college,
                "label": current_college,
                "full_name": current_college,
                "type": "",
                "group": "Colleges",
            })

    return profile, posts, pending_posts, interactions, college_options, social_links, public_social_links

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
    social_links_raw = [
        request.form.get('social_link_1', ''),
        request.form.get('social_link_2', ''),
        request.form.get('social_link_3', ''),
    ]
    social_visibility_raw = [
        request.form.get('social_link_visibility_1', 'public'),
        request.form.get('social_link_visibility_2', 'public'),
        request.form.get('social_link_visibility_3', 'public'),
    ]

    client = get_user_client()

    try:
        normalized_contact_number = normalize_philippine_mobile_number(contact_number)
        normalized_social_links = normalize_social_links_input(social_links_raw, social_visibility_raw)
        update_data = {
            "contact_number": normalized_contact_number or None,
            "contact_privacy": contact_privacy,
            "college": college,
            "course": course,
            "level": level,
            "bio": bio,
        }

        client.table('profiles').update(update_data).eq("id", user_id).execute()
        client.table('profile_social_links').delete().eq('profile_id', user_id).execute()
        for link in normalized_social_links:
            client.table('profile_social_links').insert({
                "profile_id": user_id,
                "platform": link["platform"],
                "url": link["url"],
                "visibility": link["visibility"],
                "position": link["position"],
            }).execute()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('core.profile_settings'))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for('core.profile_settings'))
    except Exception as e:
        flash("Error updating profile. Please try again.", "error")
        return redirect(url_for('core.profile_settings'))

def load_dashboard_data(user_id, category=None, before_timestamp=None):
    client = get_user_client()

    profile_response = client.table('profiles').select("*").eq("id", user_id).single().execute()
    profile = profile_response.data

    query = client.table('posts')\
        .select("*, profiles(full_name, avatar_url, college, course, level)")\
        .eq('status', 'approved')

    if category:
        if category == 'Heron Business':
            query = query.in_('category', HERON_BUSINESS_CATEGORIES)
        else:
            query = query.eq('category', category)

    if before_timestamp:
        query = query.lt('created_at', before_timestamp)

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
        .select("*, profiles(full_name, avatar_url, college, course, level)")\
        .eq('status', 'approved')\
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
        .select("*, profiles(full_name, avatar_url, college, course, level)")\
        .eq("category", "Events")\
        .eq('status', 'approved')\
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
            logger.error("Error formatting event: %s", e)

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

    latest_query = client.table('posts').select("id, created_at").eq('status', 'approved')
    if category:
        latest_query = latest_query.eq('category', category)
    latest_post_res = latest_query.order("created_at", desc=True).limit(1).execute()
    latest_post = latest_post_res.data[0] if latest_post_res.data else {}

    trending_res = client.table('posts')\
        .select("id")\
        .eq('status', 'approved')\
        .gt("likes_count", 0)\
        .order("likes_count", desc=True)\
        .order("created_at", desc=True)\
        .limit(3).execute()
    trending_ids = [row['id'] for row in (trending_res.data or [])]

    events_res = client.table('posts')\
        .select("id")\
        .eq('status', 'approved')\
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
    # Fetch notifications with actor profile info
    notifications_res = client.table('notifications')\
        .select("id, title, message, type, is_read, created_at, reference_id, actor_id, actor:profiles(full_name, avatar_url)")\
        .eq('user_id', user_id)\
        .order('created_at', desc=True)\
        .limit(15).execute()

    items = notifications_res.data or []
    for n in items:
        # Add relative time
        n['relative_time'] = format_relative_time(n.get('created_at'))
        # Flatten actor details
        actor = n.get('actor')
        if actor:
            n['actor_name'] = actor.get('full_name')
            n['actor_avatar'] = actor.get('avatar_url')
        else:
            n['actor_name'] = "System"
            n['actor_avatar'] = None
        # Cleanup
        if 'actor' in n: del n['actor']

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
        logger.error("Error building admin activity payload: %s", e)
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

    is_admin_domain = is_admin_domain_request()

    if is_admin_domain and role in ['admin', 'super_admin', 'superadmin', 'content_manager', 'content_moderator', 'account_manager']:
        payload["admin"] = build_admin_activity_payload(client)

    response = jsonify(payload)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@core.route('/posts/<post_id>')
@login_required
def get_post_details(post_id):
    client = get_user_client()
    user_id = session.get('user', {}).get('id')
    try:
        post_res = client.table('posts')\
            .select("*, profiles(full_name, avatar_url, college, course, level)")\
            .eq("id", post_id)\
            .single().execute()
        
        post = post_res.data
        if not post:
            return jsonify({"error": "Post not found"}), 404
            
        # Add interaction state
        like_check = client.table('likes').select("id").eq("post_id", post_id).eq("user_id", user_id).execute()
        post['user_has_liked'] = len(like_check.data) > 0
        
        count_map = build_comment_count_map(client, [post_id])
        post['comments_count'] = count_map.get(post_id, 0)
        post['relative_created_at'] = format_relative_time(post.get('created_at'))
        attach_embed_metadata(post)
        
        return jsonify({"post": post})
    except Exception as e:
        logger.error("Error fetching post details: %s", e)
        return jsonify({"error": "Failed to load post"}), 500

@core.route('/posts/fetch')
@login_required
def fetch_posts():
    user_session = session.get('user')
    user_id = user_session.get('id')
    category = normalize_dashboard_category(request.args.get('category'))
    before_timestamp = request.args.get('before')

    try:
        profile, posts, trending, upcoming_events = load_dashboard_data(user_id, category, before_timestamp)
    except Exception as e:
        if is_jwt_error(e) and refresh_supabase_auth():
            profile, posts, trending, upcoming_events = load_dashboard_data(user_id, category, before_timestamp)
        elif is_jwt_error(e):
            return jsonify({"status": "error", "reason": "session_expired"}), 401
        else:
            logger.error("Error fetching posts: %s", e)
            return jsonify({"status": "error", "reason": "fetch_failed"}), 500

    html_posts = []
    for post in posts:
        html = render_template('includes/post_card.html', post=post, user=profile, DISPLAY_TIMEZONE=DISPLAY_TIMEZONE)
        html_posts.append(html)

    return jsonify({
        "status": "ok",
        "posts": html_posts,
        "raw_posts": posts,
        "has_more": len(posts) == 20,
        "last_timestamp": posts[-1]['created_at'] if posts else None
    })

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
                try:
                    post_res = client.table('posts').select("id, user_id").eq("id", post_id).single().execute()
                    post_owner_id = (post_res.data or {}).get("user_id")
                    if post_owner_id and post_owner_id != user_id:
                        liker_name = (
                            ((user_session.get('user_metadata') or {}).get('full_name'))
                            or user_session.get('full_name')
                            or "A user"
                        )
                        push_notification(
                            client,
                            post_owner_id,
                            title="New like on your post",
                            message=f"{liker_name} liked your post.",
                            notif_type="interaction",
                            reference_id=post_id,
                            actor_id=user_id,
                        )
                except Exception as notif_e:
                    logger.warning("Like notification skipped for post %s: %s", post_id, notif_e)
                return {"status": "liked", "post_id": post_id}
            except Exception:
                return {"status": "liked", "post_id": post_id}

    except Exception as e:
        logger.error("Error toggling like: %s", e)
        return {"error": "Failed to toggle like."}, 500

@core.route('/posts/<post_id>/comments', methods=['GET'])
@login_required
def get_comments(post_id):
    client = get_user_client()
    try:
        comments_response = client.table('comments')\
            .select("*, profiles(full_name, avatar_url, college, course, level)")\
            .eq("post_id", post_id)\
            .order("created_at", desc=False)\
            .execute()
        return {"comments": comments_response.data}
    except Exception as e:
        logger.error("Error fetching comments: %s", e)
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
        logger.error("Moderation policy check failed for comment: %s", e)
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
            .select("*, profiles(full_name, avatar_url, college, course, level)")\
            .eq("id", comment_response.data[0]['id'])\
            .single().execute()

        commenter_name = (
            ((user_session.get('user_metadata') or {}).get('full_name'))
            or user_session.get('full_name')
            or "A user"
        )
        try:
            post_owner_res = client.table('posts').select("user_id").eq("id", post_id).single().execute()
            post_owner_id = (post_owner_res.data or {}).get("user_id")
            if post_owner_id and post_owner_id != user_id:
                push_notification(
                    client,
                    post_owner_id,
                    title="New comment on your post",
                    message=f"{commenter_name} commented on your post.",
                    notif_type="interaction",
                    reference_id=post_id,
                    actor_id=user_id,
                )
        except Exception as notif_e:
            logger.warning("Post owner comment notification skipped for post %s: %s", post_id, notif_e)

        if parent_id:
            try:
                parent_res = client.table('comments').select("user_id").eq("id", parent_id).single().execute()
                parent_owner_id = (parent_res.data or {}).get("user_id")
                if parent_owner_id and parent_owner_id not in (user_id,):
                    push_notification(
                        client,
                        parent_owner_id,
                        title="New reply to your comment",
                        message=f"{commenter_name} replied to your comment.",
                        notif_type="interaction",
                        reference_id=post_id,
                        actor_id=user_id,
                    )
            except Exception as notif_e:
                logger.warning("Reply notification skipped for parent comment %s: %s", parent_id, notif_e)

        return {"comment": new_comment.data}
    except Exception as e:
        logger.error("Error adding comment: %s", e)
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

    # Profanity / moderation check on updated content
    if content:
        try:
            moderation = evaluate_submission_policy(user_id, content, "post")
        except Exception as e:
            logger.error("Moderation policy check failed for post update: %s", e)
            flash("Unable to validate content policy right now. Please try again.", "error")
            return redirect(url_for('core.dashboard'))

        if not moderation.get("allowed"):
            policy_message = moderation.get("message") or "Your update violates content policy."
            if not policy_message.startswith("\u26a0"):
                policy_message = f"\u26a0 {policy_message}"
            flash(policy_message, "warning")
            return redirect(url_for('core.dashboard'))

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
        logger.error("Error updating post: %s", e)
        flash("Error updating post. Please try again.", "error")
        return redirect(url_for('core.dashboard'))

@core.route('/posts/<post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    user_session = session.get('user')
    user_id = user_session.get('id')
    client = get_user_client()
    delete_reason = (request.form.get('reason') or request.args.get('reason') or "Deleted by post author").strip()
    if not delete_reason:
        delete_reason = "Deleted by post author"

    try:
        post_check = client.table('posts').select("id").eq("id", post_id).eq("user_id", user_id).limit(1).execute()
        if not (post_check.data or []):
            return {"error": "Unauthorized or post not found"}, 403

        if supabase_service:
            try:
                purge_expired_archived_posts(supabase_service)
                archive_post_snapshot(
                    supabase_service,
                    post_id,
                    deleted_by=user_id,
                    deleted_by_role=(user_session.get('role') or 'student'),
                    source="user",
                    reason=delete_reason,
                )
            except Exception as archive_e:
                logger.warning("User delete archive skipped for post %s: %s", post_id, archive_e)

        result = client.table('posts').delete().eq("id", post_id).eq("user_id", user_id).execute()

        if not result.data:
            return {"error": "Unauthorized or post not found"}, 403

        flash("Post deleted successfully!", "success")
        return {"status": "deleted"}
    except Exception as e:
        logger.error("Error deleting post: %s", e)
        return {"error": "Failed to delete post."}, 500

@core.route('/support/ticket/create', methods=['POST'])
@login_required
def create_support_ticket():
    user_id = session.get('user', {}).get('id')
    data = request.get_json(silent=True) or {}
    subject = data.get('subject', '').strip()
    message = data.get('message', '').strip()

    if not subject or not message:
        return {"error": "Subject and message are required."}, 400

    try:
        client = get_user_client()
        client.table('support_tickets').insert({
            "user_id": user_id,
            "subject": subject,
            "message": message
        }).execute()

        user_name = session.get('user', {}).get('full_name', 'A user')
        push_admin_notification(
            title="New Support Ticket",
            message=f"{user_name} submitted a support ticket: {subject}",
            notif_type="admin",
        )

        return {"status": "created"}
    except Exception as e:
        logger.error("Error creating support ticket: %s", e)
        return {"error": "Failed to send message."}, 500

@core.route('/profiles/<target_user_id>/report', methods=['POST'])
@login_required
def report_user(target_user_id):
    user_session = session.get('user')
    reporter_id = user_session.get('id')
    data = request.get_json(silent=True) or {}
    reason = (data.get('reason') or '').strip()

    if not reason:
        return {"error": "Report reason is required."}, 400
    
    if reporter_id == target_user_id:
        return {"error": "You cannot report yourself."}, 400

    client = get_user_client()

    try:
        # Verify user exists
        profile_res = client.table('profiles').select("id").eq("id", target_user_id).single().execute()
        if not profile_res.data:
            return {"error": "Target user not found."}, 404

        # Check for duplicate pending report
        existing = client.table('reports').select("id").eq("reporter_id", reporter_id).eq("reported_user_id", target_user_id).eq("status", "pending").execute()
        if existing.data:
            return {"status": "already_reported"}

        # Insert report
        client.table('reports').insert({
            "reporter_id": reporter_id,
            "reported_user_id": target_user_id,
            "reason": reason
        }).execute()

        reporter_name = user_session.get('full_name', 'A user')
        push_admin_notification(
            title="New User Report",
            message=f"{reporter_name} reported a user account. Reason: {reason[:100]}",
            notif_type="admin",
        )

        return {"status": "reported"}
    except Exception as e:
        logger.error("Error reporting user: %s", e)
        return {"error": "Failed to submit report."}, 500

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

        reporter_name = user_session.get('full_name', 'A user')
        push_admin_notification(
            title="New Post Report",
            message=f"{reporter_name} reported a post. Reason: {reason[:100]}",
            notif_type="admin",
            reference_id=post_id,
        )

        return {"status": "reported"}
    except Exception as e:
        logger.error("Error reporting post: %s", e)
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
        logger.error("Moderation policy check failed for comment update: %s", e)
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
        logger.error("Error updating comment: %s", e)
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
        logger.error("Error deleting comment: %s", e)
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
        logger.error("Moderation policy check failed for post: %s", e)
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
                    logger.error("Error uploading image %s: %s", img_file.filename, e)
                    flash(f"Failed to upload image {img_file.filename}.", "warning")

    try:
        # Determine Approval Status
        # Rule: Posts with images OR 'Events' category REQUIRE admin approval.
        # Text-only non-event posts are approved by default.
        post_status = 'pending' if (image_urls or category == 'Events') else 'approved'

        post_data = {
            "user_id": user_id,
            "content": content,
            "category": category,
            "event_title": event_title,
            "price": price,
            "location": location,
            "status": post_status,
            "event_date": event_date,
            "event_end_date": event_end_date,
            "image_url": image_urls[0] if image_urls else None,
            "image_urls": image_urls
        }
        client.table('posts').insert(post_data).execute()

        session['last_post_time'] = current_time

        if post_status == 'pending':
            if category == 'Events':
                flash("Event post submitted! It will be visible after admin approval.", "success")
            else:
                flash("Post submitted! Since it contains media, it will be visible after admin approval.", "success")
            poster_name = session.get('user', {}).get('full_name', 'A user')
            push_admin_notification(
                title="Post Pending Approval",
                message=f"{poster_name} submitted a post with media that needs approval.",
                notif_type="admin",
            )
        else:
            flash("Post created successfully!", "success")
    except Exception as e:
        logger.critical("Post insertion failed: %s", e)
        flash("Something went wrong. Please try again.", "error")

    return redirect(url_for('core.dashboard'))

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}

def upload_single_image(client, file, user_id):
    import uuid

    if not file.filename or '.' not in file.filename:
        raise ValueError("File must have a valid extension.")

    file_ext = file.filename.rsplit('.', 1)[1].lower()
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f"File type '.{file_ext}' not allowed. Accepted: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}")

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

@core.route('/notifications')
@login_required
def notifications_page():
    user_id = session.get('user', {}).get('id')
    try:
        client = get_user_client()
        res = client.table('notifications')\
            .select("id, title, message, type, is_read, created_at, reference_id")\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .limit(50).execute()
        notifications = res.data or []
    except Exception as e:
        if is_jwt_error(e) and refresh_supabase_auth():
            client = get_user_client()
            res = client.table('notifications')\
                .select("id, title, message, type, is_read, created_at, reference_id")\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(50).execute()
            notifications = res.data or []
        else:
            notifications = []
    return render_template('notifications.html', notifications=notifications)

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

@core.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    user_id = session.get('user', {}).get('id')
    client = get_user_client()
    try:
        client.table('notifications')\
            .update({"is_read": True})\
            .eq("user_id", user_id)\
            .execute()
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error("Failed to mark all notifications as read: %s", e)
        return jsonify({"status": "error"}), 500

@core.route('/notifications/clear-all', methods=['POST'])
@login_required
def clear_all_notifications():
    user_id = session.get('user', {}).get('id')
    client = get_user_client()
    try:
        client.table('notifications')\
            .delete()\
            .eq("user_id", user_id)\
            .execute()
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error("Failed to clear all notifications: %s", e)
        return jsonify({"status": "error"}), 500

@core.route('/login')
def login():
    is_admin_login = is_admin_domain_request()

    return render_template(
        'login.html',
        is_admin_login=is_admin_login,
    )
