import logging
import os
import math
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request
from app.routes.auth import login_required
from services.supabase_client import supabase, supabase_service, get_user_client, engine
from sqlalchemy import text
from app.utils.post_archive import archive_post_snapshot, maybe_purge_expired_archived_posts, purge_expired_archived_posts
from functools import wraps
import datetime
import uuid

logger = logging.getLogger(__name__)

admin = Blueprint('admin', __name__)

ROLE_ALIASES = {
    "superadmin": "super_admin",
    "content_manager": "content_moderator",
}

SUPER_ADMIN_ROLES = {'super_admin', 'superadmin'}
ADMIN_ROLES = {'admin'}
ACCOUNT_MANAGER_ROLES = {'account_manager'}
CONTENT_MODERATOR_ROLES = {'content_moderator'}

ADMIN_PORTAL_ROLES = SUPER_ADMIN_ROLES | ADMIN_ROLES | ACCOUNT_MANAGER_ROLES | CONTENT_MODERATOR_ROLES
ACCOUNT_ACCESS_ROLES = SUPER_ADMIN_ROLES | ADMIN_ROLES | ACCOUNT_MANAGER_ROLES
CONTENT_ACCESS_ROLES = SUPER_ADMIN_ROLES | ADMIN_ROLES | CONTENT_MODERATOR_ROLES
CATALOG_MANAGE_ROLES = SUPER_ADMIN_ROLES | ADMIN_ROLES
ALLOWED_CATALOG_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}

def get_service_client():
    """
    Helper to get a service role client that bypasses RLS.
    Used for administrative actions that standard users shouldn't have permissions for.
    """
    if supabase_service:
        return supabase_service
    logger.warning(
        "SUPABASE service-role client is not configured; "
        "falling back to user-scoped admin client (RLS still applies)."
    )
    return get_user_client()


def get_admin_read_client():
    """
    Read-only admin pages should not hard-crash when service key is absent.
    Fallback to per-user client for graceful behavior.
    """
    return get_service_client()

def format_size(size_bytes):
    if size_bytes == 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])

def normalize_role(role):
    value = (role or '').strip().lower()
    return ROLE_ALIASES.get(value, value)


def can_manage_target_role(actor_role, target_role):
    actor = normalize_role(actor_role)
    target = normalize_role(target_role)

    if actor in SUPER_ADMIN_ROLES:
        return True
    if target in SUPER_ADMIN_ROLES:
        return False
    if actor in ADMIN_ROLES:
        return target not in ADMIN_ROLES
    if actor in ACCOUNT_MANAGER_ROLES:
        return target not in (ADMIN_ROLES | SUPER_ADMIN_ROLES)
    return False


def chunked(values, size=100):
    for idx in range(0, len(values), size):
        yield values[idx:idx + size]


def delete_comment_thread(admin_client, root_comment_id):
    pending = [(root_comment_id, 0)]
    seen = set()
    collected = []

    while pending:
        current, depth = pending.pop(0)
        if not current or current in seen:
            continue
        seen.add(current)
        collected.append((current, depth))

        children = admin_client.table('comments').select('id').eq('parent_id', current).execute()
        for child in (children.data or []):
            child_id = child.get('id')
            if child_id and child_id not in seen:
                pending.append((child_id, depth + 1))

    if not collected:
        return

    # Delete deepest children first to satisfy self-referential FK constraints.
    ordered_ids = [comment_id for comment_id, _ in sorted(collected, key=lambda row: row[1], reverse=True)]
    for batch in chunked(ordered_ids, size=100):
        admin_client.table('comments').delete().in_('id', batch).execute()


def delete_post_dependencies(admin_client, post_id):
    # Clear references before removing the post in schemas without ON DELETE CASCADE.
    admin_client.table('comments').delete().eq('post_id', post_id).execute()
    admin_client.table('likes').delete().eq('post_id', post_id).execute()
    admin_client.table('reports').delete().eq('post_id', post_id).execute()
    admin_client.table('warnings').update({"post_id": None}).eq('post_id', post_id).execute()

def get_current_role():
    user = session.get('user')
    if not user:
        return None

    current_role = normalize_role(user.get('role'))

    # Check database for latest role using service client (bypasses RLS)
    try:
        admin_client = get_service_client()
        profile_res = admin_client.table('profiles').select("role").eq("id", user.get('id')).single().execute()
        db_role = normalize_role(profile_res.data.get('role') if profile_res.data else current_role)

        # Sync session role if changed
        if db_role and db_role != current_role:
            user['role'] = db_role
            session['user'] = user
            session.modified = True
        return db_role or current_role
    except Exception as e:
        logger.error("Error verifying admin role: %s", e)
        return current_role

def wants_json_response():
    if request.is_json:
        return True
    accept = (request.headers.get('Accept') or '').lower()
    if 'application/json' in accept:
        return True
    requested_with = (request.headers.get('X-Requested-With') or '').lower()
    return requested_with == 'xmlhttprequest'

def require_admin_service_client(action_label="Admin action"):
    """
    Enforce service-role usage for privileged writes.
    Without service credentials, many actions will fail under RLS.
    """
    if supabase_service:
        return supabase_service, None

    message = "Admin service credentials are missing. Configure SUPABASE_SERVICE_ROLE_KEY."
    logger.error("%s blocked: %s", action_label, message)

    if wants_json_response():
        return None, (jsonify({"status": "error", "message": message}), 500)

    flash(message, "error")
    return None, redirect(request.referrer or url_for('admin.dashboard'))


def get_delete_reason_payload():
    data = request.get_json(silent=True) if request.is_json else None
    data = data or request.form.to_dict() or {}
    reason = (data.get("reason") or "").strip()
    note = (data.get("note") or "").strip()
    if not reason:
        reason = "Violation of community guidelines"
    return reason, note

def role_block_response(message):
    if wants_json_response():
        return jsonify({"status": "error", "message": message}), 403

    flash(message, "error")
    current_role = normalize_role(session.get('user', {}).get('role'))
    if current_role in ADMIN_PORTAL_ROLES:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('core.dashboard'))

def role_required(allowed_roles, denied_message):
    allowed_roles = {normalize_role(r) for r in allowed_roles}

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = session.get('user')
            if not user:
                if wants_json_response():
                    return jsonify({"status": "error", "message": "Session expired"}), 401
                return redirect(url_for('core.login'))

            current_role = get_current_role()
            if current_role not in allowed_roles:
                return role_block_response(denied_message)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

admin_required = role_required(
    ADMIN_PORTAL_ROLES,
    "Admin portal access required.",
)

account_access_required = role_required(
    ACCOUNT_ACCESS_ROLES,
    "Only account managers or higher can access account tools.",
)

content_access_required = role_required(
    CONTENT_ACCESS_ROLES,
    "Only content moderators or higher can access content tools.",
)

warning_access_required = role_required(
    ADMIN_PORTAL_ROLES,
    "Only authorized moderators can issue warnings.",
)

catalog_manage_required = role_required(
    CATALOG_MANAGE_ROLES,
    "Only Admin or Super Admin can manage Scholarship and UMak Coop catalogs.",
)

def build_admin_permissions(role):
    current = normalize_role(role)
    is_super_admin = current in SUPER_ADMIN_ROLES
    is_admin = current in ADMIN_ROLES
    is_account_manager = current in ACCOUNT_MANAGER_ROLES
    is_content_moderator = current in CONTENT_MODERATOR_ROLES

    return {
        "role": current,
        "is_super_admin": is_super_admin,
        "is_admin": is_admin,
        "is_account_manager": is_account_manager,
        "is_content_moderator": is_content_moderator,
        "can_access_accounts": current in ACCOUNT_ACCESS_ROLES,
        "can_access_content": current in CONTENT_ACCESS_ROLES,
        "can_manage_catalog": current in CATALOG_MANAGE_ROLES,
        "can_assign_admin": is_super_admin,
        "can_modify_admin_accounts": is_super_admin,
    }

def push_notification(client, user_id, *, title, message, notif_type="system", reference_id=None, actor_id=None):
    if not user_id:
        return
    sender_client = supabase_service or client
    try:
        # 1. Implement Like Merging logic
        if notif_type == "interaction" and reference_id and "like" in title.lower():
            try:
                # Fetch recent likers for this post
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
                            "message": "",
                            "actor_id": actor_id,
                            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                        }).eq("id", existing.data[0]['id']).execute()
                        return
                    
                    title = new_title
                    message = ""
            except Exception as e:
                logger.warning("Like merging failed in admin: %s", e)

        # 2. Prevent spamming for other interactions
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

def fetch_comprehensive_stats(client):
    """
    Unified helper to fetch all admin dashboard metrics.
    Handles SQL blocking and API limitations gracefully.
    """
    stats = {
        "total_users": 0,
        "total_posts": 0,
        "total_comments": 0,
        "total_likes": 0,
        "total_photos": 0,
        "total_notifications": 0,
        "pending_approvals": 0,
        "reported_count": 0,
        "open_tickets_count": 0,
        "banned_accounts": 0,
        "user_list": [],
        "reports_list": [],
        "posts_by_category": [],
        "recent_activities": [],
        "disputes_count": 0,
        "college_breakdown": [],
    }

    try:
        # 1. Primary Metrics (via standard API - always works)
        # Use a single query for profiles if possible, or separate for counts
        profiles_res = client.table('profiles').select("id, college, status, full_name, avatar_url, role").execute()
        stats["user_list"] = profiles_res.data
        stats["total_users"] = len(profiles_res.data)
        stats["banned_accounts"] = len([p for p in profiles_res.data if p.get('status') == 'banned'])

        # College Breakdown for Chart
        college_counts = {}
        for p in profiles_res.data:
            college = p.get('college') or 'Unknown'
            college_counts[college] = college_counts.get(college, 0) + 1
        
        # Sort by count descending
        sorted_colleges = sorted(college_counts.items(), key=lambda x: x[1], reverse=True)
        
        colors = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#64748B']
        breakdown = []
        total_users_count = stats["total_users"] or 1
        current_angle = 0
        
        for i, (label, count) in enumerate(sorted_colleges):
            percentage = round((count / total_users_count) * 100, 1)
            angle = (count / total_users_count) * 360
            breakdown.append({
                "label": label,
                "count": count,
                "percentage": percentage,
                "color": colors[i % len(colors)],
                "start_angle": current_angle,
                "end_angle": current_angle + angle
            })
            current_angle += angle
        
        stats["college_breakdown"] = breakdown

        posts_res = client.table('posts').select("id, category, status").execute()
        stats["total_posts"] = len(posts_res.data)
        cat_counts = {}
        pending_count = 0
        for p in posts_res.data:
            cat = p.get('category', 'General')
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            if p.get('status') == 'pending': pending_count += 1
        stats["posts_by_category"] = [{"category": k, "count": v} for k, v in cat_counts.items()]
        stats["pending_approvals"] = pending_count

        # Counts for other major tables
        for table in ['comments', 'likes', 'notifications', 'reports', 'support_tickets']:
            try:
                res = client.table(table).select("id", count="exact").limit(0).execute()
                count = res.count if hasattr(res, 'count') else len(res.data)
                stats[f"total_{table if table != 'reports' else 'reported_count'}"] = count
                if table == 'reports': stats["reported_count"] = count
            except: pass

        # 2. Photos count
        try:
            storage_client = (supabase_service or client).storage
            buckets = storage_client.list_buckets()
            total_photos = 0
            for b in buckets:
                files = storage_client.from_(b.id).list()
                total_photos += len(files)
            stats["total_photos"] = total_photos
        except: pass

    except Exception as e:
        logger.error("Error in fetch_comprehensive_stats: %s", e)

    return stats

@admin.route('/admin/dashboard')
@login_required
@admin_required
def dashboard():
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)

    if supabase_service:
        try:
            maybe_purge_expired_archived_posts(supabase_service)
        except Exception as cleanup_e:
            logger.warning("Admin dashboard archive cleanup skipped: %s", cleanup_e)
    
    stats = fetch_comprehensive_stats(client)
    
    try:
        # Fetch additional data needed specifically for dashboard view
        pending_res = client.table('posts').select("*, profiles(full_name)").eq('status', 'pending').order("created_at", desc=True).limit(5).execute()
        stats["pending_list"] = pending_res.data

        reports_res = client.table('reports').select("*, posts(content), profiles!reports_reporter_id_fkey(full_name)").order("created_at", desc=True).execute()
        stats["reports_list"] = reports_res.data
        
        now = datetime.datetime.now(datetime.timezone.utc)
        day_ago = now - datetime.timedelta(hours=24)
        stats["new_reports_count"] = len([r for r in reports_res.data if datetime.datetime.fromisoformat(r['created_at'].replace('Z', '+00:00')) > day_ago])

        logs_res = client.table('admin_logs').select("*, profiles!admin_logs_admin_id_fkey(full_name)").order("created_at", desc=True).limit(20).execute()
        stats["recent_activities"] = logs_res.data

        disputes_res = client.table('verification_disputes').select("id", count="exact").eq("status", "pending").execute()
        stats["disputes_count"] = disputes_res.count if hasattr(disputes_res, 'count') else len(disputes_res.data)
            
    except Exception as e:
        logger.error("Error fetching dashboard-specific data: %s", e)

    return render_template('admin/dashboard.html', stats=stats, user=session.get('user'), permissions=permissions)

@admin.route('/admin/support')
@login_required
@admin_required
def manage_support():
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    
    status_filter = request.args.get('status', 'open')
    
    query = client.table('support_tickets').select("*, profiles(full_name, avatar_url, email)")
    if status_filter != 'all':
        query = query.eq('status', status_filter)
        
    res = query.order('created_at', desc=True).execute()
    
    return render_template('admin/support_inbox.html', 
                           tickets=res.data, 
                           status_filter=status_filter,
                           user=session.get('user'), 
                           permissions=permissions)

@admin.route('/admin/support/<ticket_id>/update', methods=['POST'])
@login_required
@admin_required
def update_ticket(ticket_id):
    status = request.form.get('status')
    notes = request.form.get('admin_notes', '').strip()
    
    try:
        admin_client = get_service_client()
        admin_client.table('support_tickets').update({
            "status": status,
            "admin_notes": notes,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }).eq("id", ticket_id).execute()
        
        flash("Ticket updated successfully.", "success")
    except Exception as e:
        logger.error("Error updating ticket: %s", e)
        flash("Failed to update ticket.", "error")
        
    return redirect(url_for('admin.manage_support'))

@admin.route('/admin/users')
@login_required
@account_access_required
def manage_users():
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    search = request.args.get('search', '')
    
    query = client.table('profiles').select("*")
    if search:
        query = query.or_(f"full_name.ilike.%{search}%,email.ilike.%{search}%")
    
    res = query.order('full_name').execute()
    users = res.data or []

    if wants_json_response():
        return jsonify({"status": "ok", "users": users})
        
    return render_template('admin/users.html', users=users, user=session.get('user'), search=search, permissions=permissions)

@admin.route('/admin/users/<user_id>/manage')
@login_required
@account_access_required
def user_management(user_id):
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    profile_res = client.table('profiles').select("*").eq("id", user_id).single().execute()
    
    # Include profiles in the select for the modal to have names
    posts_res = client.table('posts').select("*, profiles(full_name, avatar_url)").eq("user_id", user_id).order('created_at', desc=True).limit(50).execute()
    comments_res = client.table('comments').select("*, posts(content, category), profiles(full_name, avatar_url)").eq("user_id", user_id).order('created_at', desc=True).limit(50).execute()
    
    warnings_res = client.table('warnings').select("*").eq("user_id", user_id).execute()
    return render_template('admin/user_manage.html',
                           target_user=profile_res.data,
                           posts=posts_res.data,
                           comments=comments_res.data,
                           warnings=warnings_res.data,
                           user=session.get('user'),
                           permissions=permissions)
@admin.route('/admin/users/<user_id>/update-role', methods=['POST'])
@login_required
@account_access_required
def update_user_role(user_id):
    new_role = normalize_role(request.form.get('role'))
    actor_role = get_current_role()

    valid_roles = {'student', 'content_moderator', 'content_manager', 'account_manager', 'admin', 'super_admin', 'superadmin'}
    if new_role not in valid_roles:
        flash("Invalid role selected.", "error")
        return redirect(url_for('admin.user_management', user_id=user_id))

    # Canonicalize alias
    if new_role == 'superadmin':
        new_role = 'super_admin'
    
    try:
        admin_client, service_error = require_admin_service_client("Update role")
        if service_error:
            return service_error

        target_profile_res = admin_client.table('profiles').select("id, role, full_name").eq("id", user_id).single().execute()
        target_name = target_profile_res.data.get('full_name', 'Unknown User') if target_profile_res.data else 'Unknown User'
        target_role = normalize_role(target_profile_res.data.get('role') if target_profile_res.data else '')
        if target_role == 'superadmin':
            target_role = 'super_admin'

        # Permission checks
        if actor_role in ACCOUNT_MANAGER_ROLES:
            flash("Account managers can manage account data but cannot change user roles.", "error")
            return redirect(url_for('admin.user_management', user_id=user_id))

        if actor_role in ADMIN_ROLES:
            if target_role in ADMIN_ROLES or target_role in SUPER_ADMIN_ROLES:
                flash("Admins cannot modify Admin or Super Admin accounts.", "error")
                return redirect(url_for('admin.user_management', user_id=user_id))
            if new_role in ADMIN_ROLES or new_role in SUPER_ADMIN_ROLES:
                flash("Only Super Admin can assign Admin or Super Admin roles.", "error")
                return redirect(url_for('admin.user_management', user_id=user_id))

        if actor_role not in SUPER_ADMIN_ROLES and new_role in SUPER_ADMIN_ROLES:
            flash("Only Super Admin can assign Super Admin role.", "error")
            return redirect(url_for('admin.user_management', user_id=user_id))

        if actor_role not in SUPER_ADMIN_ROLES and new_role in ADMIN_ROLES:
            flash("Only Super Admin can assign Admin role.", "error")
            return redirect(url_for('admin.user_management', user_id=user_id))

        # Super admins can modify any role; admins only lower-level roles (validated above).
        update_res = admin_client.table('profiles').update({"role": new_role}).eq("id", user_id).execute()
        
        # Check if update was successful
        if not update_res.data:
            flash(f"Database update failed. Please check system logs.", "error")
            return redirect(url_for('admin.user_management', user_id=user_id))

        # 2. Sync session if updating current user
        if user_id == session['user']['id']:
            session['user']['role'] = new_role
            session.modified = True
        
        # 3. Attempt to log the action (also using service client)
        try:
            admin_id = session['user']['id']
            admin_client.table('admin_logs').insert({
                "admin_id": admin_id,
                "action_type": "update_role",
                "target_id": user_id,
                "details": f"Updated role to {new_role}"
            }).execute()
        except Exception as log_e:
            logger.error("Audit log error: %s", log_e)
        
        flash(f"User role updated successfully to {new_role.replace('_', ' ').title()}.", "success")
    except Exception as e:
        flash("Error updating user role.", "error")
        
    return redirect(url_for('admin.user_management', user_id=user_id))

@admin.route('/admin/users/<user_id>/lift-suspension', methods=['POST'])
@login_required
@account_access_required
def lift_user_suspension(user_id):
    try:
        admin_client, service_error = require_admin_service_client("Lift suspension")
        if service_error:
            return service_error
        actor_role = get_current_role()
        target_res = admin_client.table('profiles').select("role, full_name").eq("id", user_id).single().execute()
        target_name = target_res.data.get('full_name', 'Unknown User') if target_res.data else 'Unknown User'
        target_role = normalize_role(target_res.data.get('role') if target_res.data else '')
        if not can_manage_target_role(actor_role, target_role):
            flash("You cannot override this account level.", "error")
            return redirect(url_for('admin.user_management', user_id=user_id))

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        admin_client.table('profiles').update({
            "status": "active",
            "ban_reason": None,
            "suspended_until": None,
            "profanity_count": 0,
            "profanity_warning_sent": False,
            "profanity_counter_started_at": now_iso
        }).eq("id", user_id).execute()

        try:
            admin_client.table('admin_logs').insert({
                "admin_id": session.get('user', {}).get('id'),
                "action_type": "lift_suspension_override",
                "target_id": user_id,
                "details": "Manual override: lifted moderation suspension and reset profanity counters."
            }).execute()
        except Exception as log_error:
            logger.error("Admin log insert failed (lift suspension): %s", log_error)

        flash("Suspension lifted and moderation counter reset.", "success")
    except Exception as e:
        logger.error("Error lifting suspension: %s", e)
        flash("Failed to lift suspension.", "error")

    return redirect(url_for('admin.user_management', user_id=user_id))

@admin.route('/admin/content/<category>')
@login_required
@content_access_required
def content_management(category):
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    
    view_filter = request.args.get('view', 'approved') # 'pending', 'approved'
    sort_method = request.args.get('sort', 'recent') # 'recent', 'oldest'
    search = request.args.get('search', '')
    
    query = client.table('posts').select("*, profiles(full_name, avatar_url, college, course, level)")
    
    # 1. Filter by Status
    if view_filter == 'pending':
        query = query.eq('status', 'pending')
    else:
        # Default to showing approved/flagged but not pending
        query = query.neq('status', 'pending')

    # 2. Filter by Category
    if category != 'All':
        query = query.eq('category', category)

    # 3. Filter by Search
    if search:
        query = query.ilike('content', f'%{search}%')
        
    # 4. Execution & Sorting
    desc_order = (sort_method == 'recent')
    res = query.order('created_at', desc=desc_order).execute()
    
    # 4. Fetch Pending Count for the indicator
    pending_count = 0
    try:
        pending_res = client.table('posts').select("id", count='exact').eq('status', 'pending').limit(1).execute()
        pending_count = int(pending_res.count or 0)
    except: pass
    
    return render_template('admin/content_manage.html', 
                           posts=res.data, 
                           category=category, 
                           view_filter=view_filter,
                           sort=sort_method,
                           pending_count=pending_count,
                           user=session.get('user'), 
                           permissions=permissions)

@admin.route('/admin/reports')
@admin.route('/admin/reports/<category>')
@login_required
@content_access_required
def reports_queue(category='All'):
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    
    report_type = request.args.get('type', 'posts') # 'posts' or 'accounts'
    sort_method = request.args.get('sort', 'recent_reports')
    search = request.args.get('search', '')
    
    if report_type == 'accounts':
        # 1. Fetch all pending user reports
        reports_res = client.table('reports').select("reported_user_id, created_at").eq('status', 'pending').not_.is_('reported_user_id', 'null').execute()
        pending_reports = reports_res.data or []
        
        if not pending_reports:
            return render_template('admin/reports_queue.html', accounts=[], category=category, sort=sort_method, report_type=report_type, user=session.get('user'), permissions=permissions)

        # 2. Group reports by user_id
        report_stats = {}
        for r in pending_reports:
            uid = r['reported_user_id']
            if uid not in report_stats:
                report_stats[uid] = {"total": 0, "latest_report": r['created_at'], "earliest_report": r['created_at']}
            report_stats[uid]["total"] += 1
            if r['created_at'] > report_stats[uid]["latest_report"]:
                report_stats[uid]["latest_report"] = r['created_at']
            if r['created_at'] < report_stats[uid]["earliest_report"]:
                report_stats[uid]["earliest_report"] = r['created_at']

        # 3. Fetch details for these users
        user_ids = list(report_stats.keys())
        res = client.table('profiles').select("*").in_('id', user_ids).execute()
        accounts = res.data or []

        # 4. Filter by Search
        if search:
            search_lower = search.lower()
            accounts = [a for a in accounts if search_lower in (a.get('full_name') or '').lower() or search_lower in (a.get('email') or '').lower()]

        # 5. Attach stats and Sort
        for a in accounts:
            stats = report_stats.get(a['id'], {"total": 0, "latest_report": "", "earliest_report": ""})
            a['report_count'] = stats["total"]
            a['latest_report_at'] = stats["latest_report"]
            a['earliest_report_at'] = stats["earliest_report"]

        if sort_method == 'most_reports':
            accounts.sort(key=lambda x: x.get('report_count', 0), reverse=True)
        elif sort_method == 'oldest_reports':
            accounts.sort(key=lambda x: x.get('earliest_report_at', ''))
        else:
            accounts.sort(key=lambda x: x.get('latest_report_at', ''), reverse=True)

        return render_template('admin/reports_queue.html', accounts=accounts, category=category, sort=sort_method, report_type=report_type, user=session.get('user'), permissions=permissions)

    else: # report_type == 'posts' (Reported Posts)
        # 1. Fetch all pending post reports
        reports_res = client.table('reports').select("post_id, created_at").eq('status', 'pending').not_.is_('post_id', 'null').execute()
        pending_reports = reports_res.data or []
        
        if not pending_reports:
            return render_template('admin/reports_queue.html', posts=[], category=category, sort=sort_method, report_type=report_type, user=session.get('user'), permissions=permissions)

        # 2. Group reports by post_id
        report_stats = {}
        for r in pending_reports:
            pid = r['post_id']
            if pid not in report_stats:
                report_stats[pid] = {"total": 0, "latest_report": r['created_at'], "earliest_report": r['created_at']}
            report_stats[pid]["total"] += 1
            if r['created_at'] > report_stats[pid]["latest_report"]:
                report_stats[pid]["latest_report"] = r['created_at']
            if r['created_at'] < report_stats[pid]["earliest_report"]:
                report_stats[pid]["earliest_report"] = r['created_at']

        # 3. Fetch details for these posts
        post_ids = list(report_stats.keys())
        query = client.table('posts').select("*, profiles(full_name, avatar_url, college, course, level)").in_('id', post_ids)
        if category != 'All':
            query = query.eq('category', category)
        res = query.execute()
        posts = res.data or []

        # 4. Filter by Search
        if search:
            search_lower = search.lower()
            posts = [p for p in posts if search_lower in (p.get('content') or '').lower()]

        # 5. Attach stats and Sort
        for p in posts:
            stats = report_stats.get(p['id'], {"total": 0, "latest_report": "", "earliest_report": ""})
            p['report_count'] = stats["total"]
            p['latest_report_at'] = stats["latest_report"]
            p['earliest_report_at'] = stats["earliest_report"]

        if sort_method == 'most_reports':
            posts.sort(key=lambda x: x.get('report_count', 0), reverse=True)
        elif sort_method == 'oldest_reports':
            posts.sort(key=lambda x: x.get('earliest_report_at', ''))
        else:
            posts.sort(key=lambda x: x.get('latest_report_at', ''), reverse=True)

        return render_template('admin/reports_queue.html', posts=posts, category=category, sort=sort_method, report_type=report_type, user=session.get('user'), permissions=permissions)


@admin.route('/admin/posts/bulk-approve', methods=['POST'])
@login_required
@content_access_required
def bulk_approve_posts():
    data = request.get_json() or {}
    post_ids = data.get('ids', [])
    
    if not post_ids:
        return jsonify({"status": "error", "message": "No posts selected"}), 400
        
    try:
        admin_client = get_service_client()
        
        # 1. Update status
        admin_client.table('posts').update({"status": "approved"}).in_("id", post_ids).execute()
        
        # 2. Notify all owners (simplified for bulk)
        posts_res = admin_client.table('posts').select("user_id").in_("id", post_ids).execute()
        owner_ids = list(set(p['user_id'] for p in posts_res.data if p.get('user_id')))
        
        admin_id = session.get('user', {}).get('id')
        for owner_id in owner_ids:
            push_notification(
                admin_client, owner_id,
                title="Post Approved!",
                message="One or more of your posts have been approved by moderators.",
                notif_type="system",
                actor_id=admin_id
            )
            
        # 3. Log action
        admin_client.table('admin_logs').insert({
            "admin_id": admin_id,
            "action_type": "bulk_approve_posts",
            "details": f"Bulk approved {len(post_ids)} posts."
        }).execute()
        
        return jsonify({"status": "success", "count": len(post_ids)})
    except Exception as e:
        logger.error("Bulk approval failed: %s", e)
        return jsonify({"status": "error", "message": "Bulk action failed"}), 500

@admin.route('/admin/posts/bulk-reject', methods=['POST'])
@login_required
@content_access_required
def bulk_reject_posts():
    data = request.get_json() or {}
    post_ids = data.get('ids', [])
    reason = data.get('reason', 'Media policy violation')
    
    if not post_ids:
        return jsonify({"status": "error", "message": "No posts selected"}), 400
        
    try:
        admin_client = get_service_client()
        admin_client.table('posts').update({"status": "rejected"}).in_("id", post_ids).execute()
        
        admin_id = session.get('user', {}).get('id')
        # 3. Notify owners
        posts_res = admin_client.table('posts').select("user_id").in_("id", post_ids).execute()
        owner_ids = list(set(p['user_id'] for p in posts_res.data if p.get('user_id')))
        for owner_id in owner_ids:
            push_notification(
                admin_client, owner_id,
                title="Post Rejected",
                message=f"One or more posts were rejected. Reason: {reason}",
                notif_type="warning",
                actor_id=admin_id
            )
            
        admin_client.table('admin_logs').insert({
            "admin_id": session.get('user', {}).get('id'),
            "action_type": "bulk_reject_posts",
            "details": f"Bulk rejected {len(post_ids)} posts. Reason: {reason}"
        }).execute()
        
        return jsonify({"status": "success", "count": len(post_ids)})
    except Exception as e:
        logger.error("Bulk rejection failed: %s", e)
        return jsonify({"status": "error", "message": "Bulk action failed"}), 500

@admin.route('/admin/posts/bulk-delete', methods=['POST'])
@login_required
@content_access_required
def bulk_delete_posts():
    data = request.get_json() or {}
    post_ids = data.get('ids', [])
    reason = data.get('reason', 'Policy violation')
    
    if not post_ids:
        return jsonify({"status": "error", "message": "No posts selected"}), 400
        
    try:
        admin_client = get_service_client()
        
        # 1. Fetch info for notifications
        posts_res = admin_client.table('posts').select("id, user_id").in_("id", post_ids).execute()
        
        for p in posts_res.data:
            pid = p['id']
            owner_id = p.get('user_id')
            
            # Archive and cleanup
            archive_post_snapshot(admin_client, pid, deleted_by=session['user']['id'], deleted_by_role='admin', source='bulk_admin', reason=reason)
            delete_post_dependencies(admin_client, pid)
            admin_client.table('posts').delete().eq("id", pid).execute()
            
            if owner_id:
                push_notification(admin_client, owner_id, title="Post Removed", message=f"Your post was removed during bulk moderation. Reason: {reason}", notif_type="warning", actor_id=session.get('user', {}).get('id'))

        admin_client.table('admin_logs').insert({
            "admin_id": session.get('user', {}).get('id'),
            "action_type": "bulk_delete_posts",
            "details": f"Bulk removed {len(post_ids)} posts. Reason: {reason}"
        }).execute()
        
        return jsonify({"status": "success", "count": len(post_ids)})
    except Exception as e:
        logger.error("Bulk deletion failed: %s", e)
        return jsonify({"status": "error", "message": "Bulk action failed"}), 500

@admin.route('/admin/reports/bulk-dismiss', methods=['POST'])
@login_required
@content_access_required
def bulk_dismiss_reports():
    data = request.get_json() or {}
    post_ids = data.get('post_ids', [])
    user_ids = data.get('user_ids', [])
    
    try:
        admin_client = get_service_client()
        count = 0
        
        if post_ids:
            admin_client.table('reports').update({"status": "resolved"}).in_("post_id", post_ids).eq("status", "pending").execute()
            count += len(post_ids)
            
        if user_ids:
            admin_client.table('reports').update({"status": "resolved"}).in_("reported_user_id", user_ids).eq("status", "pending").execute()
            count += len(user_ids)

        admin_client.table('admin_logs').insert({
            "admin_id": session.get('user', {}).get('id'),
            "action_type": "bulk_dismiss_reports",
            "details": f"Bulk dismissed flags for {len(post_ids)} posts and {len(user_ids)} accounts."
        }).execute()
        
        return jsonify({"status": "success", "count": count})
    except Exception as e:
        logger.error("Bulk dismissal failed: %s", e)
        return jsonify({"status": "error", "message": "Bulk action failed"}), 500

@admin.route('/admin/posts/<post_id>/approve', methods=['POST'])
@login_required
@content_access_required
def approve_post(post_id):
    try:
        admin_client = get_service_client()
        
        # 1. Fetch post and author info
        post_res = admin_client.table('posts').select("*, profiles(full_name)").eq("id", post_id).single().execute()
        if not post_res.data:
            return jsonify({"status": "error", "message": "Post not found"}), 404
            
        post = post_res.data
        owner_id = post.get('user_id')
        author_name = post.get('profiles', {}).get('full_name', 'Unknown User')
        
        # 2. Update post status
        admin_client.table('posts').update({"status": "approved"}).eq("id", post_id).execute()
        
        # 3. Notify user
        if owner_id:
            push_notification(
                admin_client, owner_id,
                title="Post Approved!",
                message="Your post has been reviewed and is now visible to the community.",
                notif_type="system",
                reference_id=post_id
            )
            
        # 4. Log action
        admin_client.table('admin_logs').insert({
            "admin_id": session.get('user', {}).get('id'),
            "action_type": "approve_post",
            "target_id": post_id,
            "details": f"Approved post from {author_name}."
        }).execute()
        
        return jsonify({"status": "success", "message": "Post approved."})
    except Exception as e:
        logger.error("Error approving post: %s", e)
        return jsonify({"status": "error", "message": "Failed to approve post."}), 500

@admin.route('/admin/posts/<post_id>/reject', methods=['POST'])
@login_required
@content_access_required
def reject_post(post_id):
    reason = request.form.get('reason', 'Content violates media policy')
    try:
        admin_client = get_service_client()
        
        # 1. Fetch post and author info
        post_res = admin_client.table('posts').select("*, profiles(full_name)").eq("id", post_id).single().execute()
        if not post_res.data:
            return jsonify({"status": "error", "message": "Post not found"}), 404
            
        post = post_res.data
        owner_id = post.get('user_id')
        author_name = post.get('profiles', {}).get('full_name', 'Unknown User')

        # 2. Update status to rejected
        admin_client.table('posts').update({"status": "rejected"}).eq("id", post_id).execute()
        
        # 3. Notify user
        if owner_id:
            push_notification(
                admin_client, owner_id,
                title="Post Rejected",
                message=f"Your post was rejected by moderation. Reason: {reason}",
                notif_type="warning",
                reference_id=post_id
            )
            
        # 4. Log action
        admin_client.table('admin_logs').insert({
            "admin_id": session.get('user', {}).get('id'),
            "action_type": "reject_post",
            "target_id": post_id,
            "details": f"Rejected post from {author_name}. Reason: {reason}"
        }).execute()
        
        return jsonify({"status": "success", "message": "Post rejected."})
    except Exception as e:
        logger.error("Error rejecting post: %s", e)
        return jsonify({"status": "error", "message": "Failed to reject post."}), 500

@admin.route('/admin/posts/<post_id>/details')
@login_required
@content_access_required
def admin_get_post_details(post_id):
    client = get_admin_read_client()
    try:
        # Fetch post with author profile
        res = client.table('posts').select("*, profiles(full_name, avatar_url, college, course, level)").eq("id", post_id).single().execute()
        if not res.data:
            return jsonify({"status": "error", "message": "Post not found"}), 404
            
        post = res.data
        # Ensure likes/comments counts are current
        # (Though we trust the DB columns for now, we can calculate if needed)
        
        return jsonify({"post": post})
    except Exception as e:
        logger.error("Error fetching post details for admin: %s", e)
        return jsonify({"status": "error", "message": "Failed to load post details"}), 500

@admin.route('/admin/posts/<post_id>/likers')
@login_required
@content_access_required
def get_post_likers(post_id):
    client = get_admin_read_client()
    res = client.table('likes').select("profiles(id, full_name, avatar_url)").eq('post_id', post_id).execute()
    likers = [item['profiles'] for item in res.data if item.get('profiles')]
    return jsonify({"likers": likers})

@admin.route('/admin/posts/<post_id>/comments')
@login_required
@content_access_required
def admin_get_post_comments(post_id):
    client = get_admin_read_client()
    try:
        comments_response = client.table('comments')\
            .select("*, profiles(full_name, avatar_url, college, course, level)")\
            .eq("post_id", post_id)\
            .order("created_at", desc=False)\
            .execute()
        return jsonify({"comments": comments_response.data or []})
    except Exception as e:
        logger.error("Error fetching comments for admin view: %s", e)
        return jsonify({"error": "Failed to load comments."}), 500

@admin.route('/admin/posts/<post_id>/flag', methods=['POST'])
@login_required
@content_access_required
def flag_post(post_id):
    client, service_error = require_admin_service_client("Flag post")
    if service_error:
        return service_error
    try:
        post_res = client.table('posts').select("id, user_id").eq("id", post_id).single().execute()
        post = post_res.data or {}
        client.table('posts').update({"is_flagged": True}).eq("id", post_id).execute()
        owner_id = post.get("user_id")
        if owner_id:
            push_notification(
                client, owner_id,
                title="Post flagged for review",
                message="Your post was flagged by moderation and is under review.",
                notif_type="warning",
                reference_id=post_id,
                actor_id=session.get('user', {}).get('id')
            )
        return jsonify({"status": "success", "message": "Post flagged."})
    except Exception as e:
        logger.error("Error flagging post %s: %s", post_id, e)
        return jsonify({"status": "error", "message": "An error occurred."}), 500

@admin.route('/admin/comments/<comment_id>/flag', methods=['POST'])
@login_required
@content_access_required
def flag_comment(comment_id):
    client, service_error = require_admin_service_client("Flag comment")
    if service_error:
        return service_error
    try:
        comment_res = client.table('comments').select("id, user_id, post_id").eq("id", comment_id).single().execute()
        comment = comment_res.data or {}
        client.table('comments').update({"is_flagged": True}).eq("id", comment_id).execute()
        owner_id = comment.get("user_id")
        if owner_id:
            push_notification(
                client, owner_id,
                title="Comment flagged for review",
                message="One of your comments was flagged by moderation and is under review.",
                notif_type="warning",
                reference_id=comment_id,
                actor_id=session.get('user', {}).get('id')
            )
        return jsonify({"status": "success", "message": "Comment flagged."})
    except Exception as e:
        logger.error("Error flagging comment %s: %s", comment_id, e)
        return jsonify({"status": "error", "message": "An error occurred."}), 500

@admin.route('/admin/warn-user', methods=['POST'])
@login_required
@warning_access_required
def warn_user():
    data = request.get_json(silent=True) or {}
    if not data:
        data = request.form.to_dict()
    user_id = data.get('user_id')
    post_id = data.get('post_id') or None
    reason = data.get('reason')
    message = data.get('message')

    is_json = wants_json_response()

    if not all([user_id, reason, message]):
        if is_json:
            return jsonify({"status": "error", "message": "Missing required fields."}), 400
        flash("Missing required fields for warning.", "error")
        return redirect(request.referrer or url_for('admin.dashboard'))

    try:
        admin_client, service_error = require_admin_service_client("Warn user")
        if service_error:
            return service_error

        # Get target name for logging
        target_res = admin_client.table('profiles').select("full_name").eq("id", user_id).single().execute()
        target_name = target_res.data.get('full_name', 'Unknown User') if target_res.data else 'Unknown User'

        # 1. Insert into warnings table
        admin_client.table('warnings').insert({
            "user_id": user_id,
            "admin_id": session['user']['id'],
            "reason": reason,
            "message": message,
            "post_id": post_id
        }).execute()

        # 2. Insert into notifications table
        push_notification(
            admin_client, user_id,
            title=f"Community Warning: {reason}",
            message=message,
            notif_type="warning",
            actor_id=session['user']['id']
        )

        # 3. Log action
        try:
            admin_client.table('admin_logs').insert({
                "admin_id": session.get('user', {}).get('id'),
                "action_type": "issue_warning",
                "target_id": user_id,
                "details": f"Issued warning to {target_name}. Reason: {reason}"
            }).execute()
        except Exception as log_e:
            logger.error("Audit log error (warn user): %s", log_e)

        if is_json:
            return jsonify({"status": "success", "message": "Warning sent successfully."})
        flash("Warning sent successfully.", "success")
        return redirect(request.referrer or url_for('admin.dashboard'))
    except Exception as e:
        logger.error("CRITICAL error in warn_user: %s", e, exc_info=True)
        if is_json:
            return jsonify({"status": "error", "message": "An error occurred."}), 500
        flash("Failed to send warning.", "error")
        return redirect(request.referrer or url_for('admin.dashboard'))

@admin.route('/admin/disputes')
@login_required
@account_access_required
def manage_disputes():
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    res = client.table('verification_disputes').select("*").order('created_at', desc=True).execute()
    return render_template('admin/disputes.html', disputes=res.data, user=session.get('user'), permissions=permissions)

# /admin/become-admin route removed — was a temporary testing endpoint.

@admin.route('/admin/users/<user_id>/suspend', methods=['POST'])
@login_required
@account_access_required
def suspend_user(user_id):
    reason = request.form.get('reason', '').strip() or 'Suspended by admin'
    try:
        days = int(request.form.get('days', 3))
    except (TypeError, ValueError):
        days = 3
    days = max(1, min(days, 365))

    try:
        admin_client, service_error = require_admin_service_client("Suspend user")
        if service_error:
            return service_error
        actor_role = get_current_role()
        target_res = admin_client.table('profiles').select("role, full_name").eq("id", user_id).single().execute()
        target_name = target_res.data.get('full_name', 'Unknown User') if target_res.data else 'Unknown User'
        target_role = normalize_role(target_res.data.get('role') if target_res.data else '')
        if not can_manage_target_role(actor_role, target_role):
            flash("You cannot suspend this account level.", "error")
            return redirect(url_for('admin.user_management', user_id=user_id))

        suspended_until = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).isoformat()
        admin_client.table('profiles').update({
            "status": "suspended",
            "ban_reason": reason,
            "suspended_until": suspended_until
        }).eq("id", user_id).execute()

        # Notify user
        push_notification(
            admin_client, user_id,
            title="Account Suspended",
            message=f"Your account has been suspended for {days} day(s). Reason: {reason}",
            notif_type="warning",
            actor_id=session.get('user', {}).get('id')
        )

        try:
            admin_client.table('admin_logs').insert({
                "admin_id": session.get('user', {}).get('id'),
                "action_type": "suspend",
                "target_id": user_id,
                "details": f"Suspended {target_name} for {days} day(s). Reason: {reason}"
            }).execute()
        except Exception as log_e:
            logger.error("Audit log error (suspend): %s", log_e)

        flash(f"User suspended for {days} day(s).", "success")
    except Exception as e:
        logger.error("Error suspending user: %s", e)
        flash("Failed to suspend user.", "error")

    return redirect(url_for('admin.user_management', user_id=user_id))

@admin.route('/admin/users/<user_id>/ban', methods=['POST'])
@login_required
@account_access_required
def ban_user(user_id):
    reason = request.form.get('reason', '').strip() or 'Banned by admin'

    try:
        admin_client, service_error = require_admin_service_client("Ban user")
        if service_error:
            return service_error
        actor_role = get_current_role()
        target_res = admin_client.table('profiles').select("role, full_name").eq("id", user_id).single().execute()
        target_name = target_res.data.get('full_name', 'Unknown User') if target_res.data else 'Unknown User'
        target_role = normalize_role(target_res.data.get('role') if target_res.data else '')
        if not can_manage_target_role(actor_role, target_role):
            flash("You cannot ban this account level.", "error")
            return redirect(url_for('admin.user_management', user_id=user_id))

        admin_client.table('profiles').update({
            "status": "banned",
            "ban_reason": reason,
            "suspended_until": None
        }).eq("id", user_id).execute()

        # Notify user
        push_notification(
            admin_client, user_id,
            title="Account Banned",
            message=f"Your account has been permanently banned. Reason: {reason}",
            notif_type="warning",
            actor_id=session.get('user', {}).get('id')
        )

        try:
            admin_client.table('admin_logs').insert({
                "admin_id": session.get('user', {}).get('id'),
                "action_type": "ban",
                "target_id": user_id,
                "details": f"Banned {target_name}. Reason: {reason}"
            }).execute()
        except Exception as log_e:
            logger.error("Audit log error (ban): %s", log_e)

        flash("User has been banned.", "success")
    except Exception as e:
        logger.error("Error banning user: %s", e)
        flash("Failed to ban user.", "error")

    return redirect(url_for('admin.user_management', user_id=user_id))

@admin.route('/admin/posts/<post_id>/delete', methods=['POST'])
@login_required
@content_access_required
def admin_delete_post(post_id):
    try:
        admin_client, service_error = require_admin_service_client("Delete post")
        if service_error:
            return service_error

        delete_reason, delete_note = get_delete_reason_payload()
        actor = session.get('user', {})
        actor_id = actor.get('id')
        actor_role = normalize_role(actor.get('role'))

        purge_expired_archived_posts(admin_client)

        archived_post = None
        archived_ok = False
        author_name = 'Unknown User'

        try:
            # Try to fetch author name first for logging
            post_res = admin_client.table('posts').select("profiles(full_name)").eq("id", post_id).single().execute()
            if post_res.data and post_res.data.get('profiles'):
                author_name = post_res.data['profiles'].get('full_name', 'Unknown User')

            archived_post = archive_post_snapshot(
                admin_client,
                post_id,
                deleted_by=actor_id,
                deleted_by_role=actor_role,
                source="admin",
                reason=delete_reason,
                note=delete_note or None,
            )
            archived_ok = bool(archived_post)
        except Exception as archive_error:
            logger.warning("Archive snapshot skipped for post %s: %s", post_id, archive_error)
            # Fallback if archiving failed but post exists
            post_res = admin_client.table('posts').select("*").eq("id", post_id).limit(1).execute()
            rows = post_res.data or []
            archived_post = rows[0] if rows else None

        if not archived_post:
            if wants_json_response():
                return jsonify({"status": "error", "message": "Post not found."}), 404
            flash("Post not found.", "error")
            return redirect(request.referrer or url_for('admin.dashboard'))

        delete_post_dependencies(admin_client, post_id)
        admin_client.table('posts').delete().eq("id", post_id).execute()

        owner_id = archived_post.get("user_id")
        if owner_id:
            try:
                preview = (archived_post.get("content") or "").strip()
                if len(preview) > 120:
                    preview = f"{preview[:117]}..."
                
                push_notification(
                    admin_client, owner_id,
                    title="Post removed by moderation",
                    message=f"Your post was removed. Reason: {delete_reason}" + (f" | \"{preview}\"" if preview else ""),
                    notif_type="warning",
                    reference_id=post_id,
                    actor_id=actor_id
                )
            except Exception as notif_e:
                logger.warning("Could not notify post owner for deleted post %s: %s", post_id, notif_e)

        try:
            admin_client.table('admin_logs').insert({
                "admin_id": actor_id,
                "action_type": "remove_post",
                "target_id": post_id,
                "details": f"Removed post from {author_name}. Reason: {delete_reason}" + (f" | Note: {delete_note}" if delete_note else ""),
            }).execute()
        except Exception as log_e:
            logger.error("Audit log error (delete post): %s", log_e)

        if wants_json_response():
            if archived_ok:
                return jsonify({"status": "deleted", "message": "Post removed and archived."})
            return jsonify({"status": "deleted", "message": "Post removed."})
        flash("Post removed and archived." if archived_ok else "Post removed.", "success")
    except Exception as e:
        logger.error("Error deleting post (admin): %s", e)
        if wants_json_response():
            return jsonify({
                "status": "error",
                "message": "Failed to remove post.",
                "details": str(e),
            }), 500
        flash("Failed to remove post.", "error")

    return redirect(request.referrer or url_for('admin.dashboard'))

@admin.route('/admin/comments/<comment_id>/delete', methods=['POST'])
@login_required
@content_access_required
def admin_delete_comment(comment_id):
    try:
        admin_client, service_error = require_admin_service_client("Delete comment")
        if service_error:
            return service_error
        comment_res = admin_client.table('comments').select("id, user_id, post_id, profiles(full_name)").eq("id", comment_id).single().execute()
        comment = comment_res.data or {}
        author_name = comment.get('profiles', {}).get('full_name', 'Unknown User') if comment.get('profiles') else 'Unknown User'
        
        delete_comment_thread(admin_client, comment_id)
        owner_id = comment.get("user_id")
        post_id = comment.get("post_id")
        
        if owner_id:
            try:
                push_notification(
                    admin_client, owner_id,
                    title="Comment removed by moderation",
                    message="One of your comments was removed by moderation due to policy enforcement.",
                    notif_type="warning",
                    reference_id=post_id,
                    actor_id=session.get('user', {}).get('id')
                )
            except Exception as notif_e:
                logger.warning("Could not notify comment owner for deleted comment %s: %s", comment_id, notif_e)

        # Log action
        try:
            admin_client.table('admin_logs').insert({
                "admin_id": session.get('user', {}).get('id'),
                "action_type": "remove_comment",
                "target_id": comment_id,
                "details": f"Removed comment from {author_name}."
            }).execute()
        except Exception as log_e:
            logger.error("Audit log error (delete comment): %s", log_e)

        return jsonify({"status": "deleted"})
    except Exception as e:
        logger.error("Error deleting comment (admin): %s", e)
        return jsonify({"status": "error", "message": "Failed to remove comment."}), 500

@admin.route('/admin/disputes/<dispute_id>/resolve', methods=['POST'])
@login_required
@account_access_required
def resolve_dispute(dispute_id):
    action = request.form.get('action', '').strip().lower()
    if action not in ('approved', 'rejected'):
        flash("Invalid action.", "error")
        return redirect(url_for('admin.manage_disputes'))

    try:
        admin_client = get_service_client()
        dispute_res = admin_client.table('verification_disputes').select("full_name, email").eq("id", dispute_id).single().execute()
        dispute = dispute_res.data or {}
        target_info = dispute.get('full_name') or dispute.get('email') or 'Unknown'

        admin_client.table('verification_disputes').update({
            "status": action
        }).eq("id", dispute_id).execute()

        try:
            admin_client.table('admin_logs').insert({
                "admin_id": session.get('user', {}).get('id'),
                "action_type": f"dispute_{action}",
                "target_id": dispute_id,
                "details": f"Resolved verification dispute for {target_info} as {action}."
            }).execute()
        except Exception as log_e:
            logger.error("Audit log error (dispute): %s", log_e)

        flash(f"Dispute {action}.", "success")
    except Exception as e:
        logger.error("Error resolving dispute: %s", e)
        flash("Failed to resolve dispute.", "error")

    return redirect(url_for('admin.manage_disputes'))

@admin.route('/admin/warnings/<warning_id>/delete', methods=['POST'])
@login_required
@account_access_required
def delete_warning(warning_id):
    try:
        admin_client = get_service_client()
        admin_client.table('warnings').delete().eq("id", warning_id).execute()
        flash("Warning removed.", "success")
    except Exception as e:
        logger.error("Error deleting warning: %s", e)
        flash("Failed to remove warning.", "error")
    return redirect(request.referrer or url_for('admin.dashboard'))

@admin.route('/admin/forbidden-words')
@login_required
@content_access_required
def manage_forbidden_words():
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    res = client.table('forbidden_words').select("*").order('word').execute()
    return render_template('admin/forbidden_words.html', words=res.data, user=session.get('user'), permissions=permissions)

@admin.route('/admin/forbidden-words/add', methods=['POST'])
@login_required
@content_access_required
def add_forbidden_word():
    client = get_admin_read_client()
    word = request.form.get('word', '').strip().lower()
    if not word:
        flash("Word cannot be empty.", "error")
        return redirect(url_for('admin.manage_forbidden_words'))
    
    try:
        client.table('forbidden_words').insert({"word": word}).execute()
        # Invalidate profanity cache so new word takes effect immediately
        from .core import _PROFANITY_TERM_CACHE
        _PROFANITY_TERM_CACHE["terms"] = []
        _PROFANITY_TERM_CACHE["fetched_at"] = 0
        flash(f"Added '{word}' to forbidden words.", "success")
    except Exception as e:
        flash("Error adding word.", "error")

    return redirect(url_for('admin.manage_forbidden_words'))

@admin.route('/admin/forbidden-words/<word>/delete', methods=['POST'])
@login_required
@content_access_required
def delete_forbidden_word(word):
    client = get_admin_read_client()
    try:
        client.table('forbidden_words').delete().eq('word', word).execute()
        # Invalidate profanity cache so removal takes effect immediately
        from .core import _PROFANITY_TERM_CACHE
        _PROFANITY_TERM_CACHE["terms"] = []
        _PROFANITY_TERM_CACHE["fetched_at"] = 0
        flash(f"Removed '{word}' from forbidden words.", "success")
    except Exception as e:
        flash("Error removing word.", "error")

    return redirect(url_for('admin.manage_forbidden_words'))

def _parse_catalog_price(raw_value):
    if raw_value is None:
        return None
    cleaned = str(raw_value).strip().replace(',', '')
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None

def _upload_catalog_image(image_file, uploader_id):
    if not image_file or not getattr(image_file, 'filename', ''):
        return None

    filename = image_file.filename.strip()
    if '.' not in filename:
        raise ValueError("Image must have a valid extension.")

    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_CATALOG_IMAGE_EXTENSIONS:
        raise ValueError("Unsupported image type. Use JPG, PNG, WEBP, or GIF.")

    timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    object_path = f"catalog/{uploader_id}/{timestamp}_{uuid.uuid4().hex}.{ext}"
    bucket_name = (os.getenv('CATALOG_IMAGE_BUCKET') or 'post-images').strip() or 'post-images'
    content_type = image_file.mimetype or image_file.content_type or f"image/{ext}"

    image_file.seek(0)
    file_bytes = image_file.read()
    if not file_bytes:
        raise ValueError("Uploaded image is empty.")

    admin_client = get_service_client()
    admin_client.storage.from_(bucket_name).upload(
        path=object_path,
        file=file_bytes,
        file_options={"content-type": content_type}
    )
    return admin_client.storage.from_(bucket_name).get_public_url(object_path)

@admin.route('/admin/logs')
@login_required
@admin_required
def view_logs():
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    
    search = request.args.get('search', '')
    action_filter = request.args.get('action', '')
    
    query = client.table('admin_logs').select("*, profiles!admin_logs_admin_id_fkey(full_name, role)")
    
    if search:
        query = query.ilike('details', f'%{search}%')
    if action_filter:
        query = query.eq('action_type', action_filter)
        
    res = query.order('created_at', desc=True).limit(100).execute()
    
    # Get unique action types for filter dropdown
    actions_res = client.table('admin_logs').select("action_type").execute()
    action_types = sorted(list(set(item['action_type'] for item in actions_res.data)))
    
    return render_template('admin/logs.html', 
                           logs=res.data, 
                           user=session.get('user'), 
                           permissions=permissions,
                           search=search,
                           action_filter=action_filter,
                           action_types=action_types)

@admin.route('/admin/search/global')
@login_required
@admin_required
def global_search():
    query_text = (request.args.get('q') or '').strip().lower()
    if not query_text:
        return jsonify({"status": "ok", "profiles": [], "posts": [], "nav": []})

    client = get_admin_read_client()
    
    # Smart Navigation Mapping
    navigation_items = [
        {"title": "User Management", "url": "/admin/users", "keywords": ["users", "accounts", "profiles", "manage users", "members"], "icon": "users"},
        {"title": "Verification Disputes", "url": "/admin/disputes", "keywords": ["disputes", "verification", "id verify", "appeals"], "icon": "shield"},
        {"title": "Reports Queue", "url": "/admin/reports", "keywords": ["reports", "flagged", "reported", "moderation", "violations"], "icon": "flag"},
        {"title": "Content Management", "url": "/admin/content/All", "keywords": ["posts", "content", "feed", "manage posts"], "icon": "document"},
        {"title": "Scholarship Catalog", "url": "/admin/catalog/scholarship", "keywords": ["scholarships", "grants", "scholarship cards"], "icon": "academic"},
        {"title": "UMak Coop Catalog", "url": "/admin/catalog/umak-coop", "keywords": ["coop", "items", "products", "store", "shop"], "icon": "shopping"},
        {"title": "Colleges & Institutes", "url": "/admin/colleges", "keywords": ["colleges", "institutes", "academic units", "departments"], "icon": "office"},
        {"title": "Profanity Filter", "url": "/admin/forbidden-words", "keywords": ["profanity", "forbidden", "filter", "words", "banned words"], "icon": "chat"},
        {"title": "Support Inbox", "url": "/admin/support", "keywords": ["support", "inbox", "tickets", "help", "messages"], "icon": "mail"},
        {"title": "System Logs", "url": "/admin/logs", "keywords": ["logs", "audit", "history", "activity"], "icon": "clipboard"}
    ]

    matched_nav = []
    for item in navigation_items:
        if any(kw in query_text for kw in item['keywords']) or query_text in item['title'].lower():
            matched_nav.append(item)

    try:
        # Search Dynamic Entities (Profiles and Posts)
        profiles_res = client.table('profiles').select("id, full_name, avatar_url, role, email")\
            .or_(f"full_name.ilike.%{query_text}%,email.ilike.%{query_text}%")\
            .limit(5).execute()
        
        posts_res = client.table('posts').select("id, content, status, profiles(full_name)")\
            .ilike('content', f'%{query_text}%')\
            .limit(5).execute()
        
        return jsonify({
            "status": "ok",
            "profiles": profiles_res.data or [],
            "posts": posts_res.data or [],
            "nav": matched_nav
        })
    except Exception as e:
        logger.error("Global admin search failed: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@admin.route('/admin/colleges')
@login_required
@admin_required
def manage_colleges():
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    
    res = client.table('colleges_institutes').select("*").order('type').order('name').execute()
    
    colleges = [item for item in res.data if item['type'] == 'College']
    institutes = [item for item in res.data if item['type'] == 'Institute']
    
    return render_template('admin/colleges_manage.html', 
                           colleges=colleges, 
                           institutes=institutes,
                           user=session.get('user'), 
                           permissions=permissions)

@admin.route('/admin/colleges/add', methods=['POST'])
@login_required
@admin_required
def add_college():
    name = request.form.get('name', '').strip().upper()
    full_name = request.form.get('full_name', '').strip()
    unit_type = request.form.get('type', 'College')
    
    if not name:
        flash("Unit abbreviation (name) is required.", "error")
        return redirect(url_for('admin.manage_colleges'))
    
    try:
        admin_client = get_service_client()
        admin_client.table('colleges_institutes').insert({
            "name": name,
            "full_name": full_name,
            "type": unit_type
        }).execute()
        
        # Log action
        admin_client.table('admin_logs').insert({
            "admin_id": session.get('user', {}).get('id'),
            "action_type": "add_academic_unit",
            "details": f"Added {unit_type}: {name} ({full_name})"
        }).execute()
        
        flash(f"Successfully added {name}.", "success")
    except Exception as e:
        logger.error("Error adding academic unit: %s", e)
        flash("Error adding unit. It might already exist.", "error")
    
    return redirect(url_for('admin.manage_colleges'))

@admin.route('/admin/colleges/<unit_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_college(unit_id):
    try:
        admin_client = get_service_client()
        
        # Get info for logging before delete
        unit_res = admin_client.table('colleges_institutes').select("name, type").eq("id", unit_id).single().execute()
        unit_info = unit_res.data
        
        admin_client.table('colleges_institutes').delete().eq("id", unit_id).execute()
        
        # Log action
        if unit_info:
            admin_client.table('admin_logs').insert({
                "admin_id": session.get('user', {}).get('id'),
                "action_type": "delete_academic_unit",
                "details": f"Deleted {unit_info['type']}: {unit_info['name']}"
            }).execute()
            
        flash("Academic unit removed.", "success")
    except Exception as e:
        logger.error("Error deleting academic unit: %s", e)
        flash("Failed to remove academic unit.", "error")
    
    return redirect(url_for('admin.manage_colleges'))

@admin.route('/admin/catalog/scholarship')
@login_required
@content_access_required
def manage_scholarship_catalog():
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    res = client.table('scholarship_catalog')\
        .select("id, scholarship_type, name, details, qualifications, requirements, created_at")\
        .order('created_at', desc=True).execute()
    return render_template(
        'admin/catalog_manage.html',
        catalog_type='scholarship',
        items=res.data or [],
        user=session.get('user'),
        permissions=permissions
    )

@admin.route('/admin/catalog/scholarship/create', methods=['POST'])
@login_required
@catalog_manage_required
def create_scholarship_catalog_item():
    scholarship_type = request.form.get('scholarship_type', '').strip()
    name = request.form.get('name', '').strip()
    details = request.form.get('details', '').strip()
    qualifications = request.form.get('qualifications', '').strip()
    requirements = request.form.get('requirements', '').strip()

    if not scholarship_type or not name or not details:
        flash("Scholarship type, name, and details are required.", "error")
        return redirect(url_for('admin.manage_scholarship_catalog'))

    try:
        admin_client = get_service_client()
        admin_client.table('scholarship_catalog').insert({
            "scholarship_type": scholarship_type,
            "name": name,
            "details": details,
            "qualifications": qualifications,
            "requirements": requirements,
            "created_by": session.get('user', {}).get('id')
        }).execute()
        flash("Scholarship card created.", "success")
    except Exception as e:
        logger.error("Error creating scholarship catalog item: %s", e)
        flash("Failed to create scholarship card.", "error")
    return redirect(url_for('admin.manage_scholarship_catalog'))

@admin.route('/admin/catalog/scholarship/<item_id>/update', methods=['POST'])
@login_required
@catalog_manage_required
def update_scholarship_catalog_item(item_id):
    scholarship_type = request.form.get('scholarship_type', '').strip()
    name = request.form.get('name', '').strip()
    details = request.form.get('details', '').strip()
    qualifications = request.form.get('qualifications', '').strip()
    requirements = request.form.get('requirements', '').strip()

    if not scholarship_type or not name or not details:
        flash("Scholarship type, name, and details are required.", "error")
        return redirect(url_for('admin.manage_scholarship_catalog'))

    try:
        admin_client = get_service_client()
        admin_client.table('scholarship_catalog').update({
            "scholarship_type": scholarship_type,
            "name": name,
            "details": details,
            "qualifications": qualifications,
            "requirements": requirements,
        }).eq('id', item_id).execute()
        flash("Scholarship card updated.", "success")
    except Exception as e:
        logger.error("Error updating scholarship catalog item: %s", e)
        flash("Failed to update scholarship card.", "error")
    return redirect(url_for('admin.manage_scholarship_catalog'))

@admin.route('/admin/catalog/scholarship/<item_id>/delete', methods=['POST'])
@login_required
@catalog_manage_required
def delete_scholarship_catalog_item(item_id):
    try:
        admin_client = get_service_client()
        admin_client.table('scholarship_catalog').delete().eq('id', item_id).execute()
        flash("Scholarship card deleted.", "success")
    except Exception as e:
        logger.error("Error deleting scholarship catalog item: %s", e)
        flash("Failed to delete scholarship card.", "error")
    return redirect(url_for('admin.manage_scholarship_catalog'))

@admin.route('/admin/catalog/umak-coop')
@login_required
@content_access_required
def manage_umak_coop_catalog():
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    
    search = request.args.get('search', '').strip()
    category = request.args.get('category', 'All').strip()
    availability = request.args.get('availability', 'All').strip()
    sort = request.args.get('sort', 'recent').strip()

    query = client.table('umak_coop_items').select("id, name, details, price, availability, image_url, created_at, category")
    
    if search:
        query = query.ilike('name', f'%{search}%')
    
    if category != 'All':
        query = query.eq('category', category)
        
    if availability != 'All':
        query = query.eq('availability', availability)

    if sort == 'price_high':
        query = query.order('price', desc=True)
    elif sort == 'price_low':
        query = query.order('price', desc=False)
    elif sort == 'az':
        query = query.order('name', desc=False)
    elif sort == 'za':
        query = query.order('name', desc=True)
    else:
        query = query.order('created_at', desc=True)

    res = query.execute()
    return render_template(
        'admin/catalog_manage.html',
        catalog_type='umak_coop',
        items=res.data or [],
        user=session.get('user'),
        permissions=permissions,
        search=search,
        category=category,
        availability=availability,
        sort=sort
    )

@admin.route('/admin/catalog/umak-coop/create', methods=['POST'])
@login_required
@catalog_manage_required
def create_umak_coop_item():
    name = request.form.get('name', '').strip()
    details = request.form.get('details', '').strip()
    category = request.form.get('category', 'Other').strip() or 'Other'
    availability = request.form.get('availability', 'Available').strip() or 'Available'
    image_url = request.form.get('image_url', '').strip()
    image_file = request.files.get('image_file')
    
    try:
        price_raw = request.form.get('price', '0')
        price_val = float(price_raw) if price_raw else 0.0
        if price_val <= 0:
            flash("Price must be greater than 0.", "error")
            return redirect(url_for('admin.manage_umak_coop_catalog'))
        price = price_val
    except (ValueError, TypeError):
        flash("A valid numeric price is required.", "error")
        return redirect(url_for('admin.manage_umak_coop_catalog'))

    if not name or not details:
        flash("Item name and details are required.", "error")
        return redirect(url_for('admin.manage_umak_coop_catalog'))

    try:
        admin_client = get_service_client()
        if image_file and getattr(image_file, 'filename', '').strip():
            uploaded_url = _upload_catalog_image(image_file, session.get('user', {}).get('id', 'admin'))
            if uploaded_url:
                image_url = uploaded_url

        admin_client.table('umak_coop_items').insert({
            "name": name,
            "details": details,
            "category": category,
            "availability": availability,
            "price": price,
            "image_url": image_url,
            "created_by": session.get('user', {}).get('id')
        }).execute()
        flash("UMak Coop item created.", "success")
    except Exception as e:
        logger.error("Error creating UMak Coop item: %s", e)
        flash("Failed to create UMak Coop item.", "error")
    return redirect(url_for('admin.manage_umak_coop_catalog'))

@admin.route('/admin/catalog/umak-coop/<item_id>/update', methods=['POST'])
@login_required
@catalog_manage_required
def update_umak_coop_item(item_id):
    name = request.form.get('name', '').strip()
    details = request.form.get('details', '').strip()
    category = request.form.get('category', 'Other').strip() or 'Other'
    availability = request.form.get('availability', 'Available').strip() or 'Available'
    image_url = request.form.get('image_url', '').strip()
    image_file = request.files.get('image_file')
    
    try:
        price_raw = request.form.get('price', '0')
        price_val = float(price_raw) if price_raw else 0.0
        if price_val <= 0:
            flash("Price must be greater than 0.", "error")
            return redirect(url_for('admin.manage_umak_coop_catalog'))
        price = price_val
    except (ValueError, TypeError):
        flash("A valid numeric price is required.", "error")
        return redirect(url_for('admin.manage_umak_coop_catalog'))

    if not name or not details:
        flash("Item name and details are required.", "error")
        return redirect(url_for('admin.manage_umak_coop_catalog'))

    try:
        admin_client = get_service_client()
        if image_file and getattr(image_file, 'filename', '').strip():
            uploaded_url = _upload_catalog_image(image_file, session.get('user', {}).get('id', 'admin'))
            if uploaded_url:
                image_url = uploaded_url

        admin_client.table('umak_coop_items').update({
            "name": name,
            "details": details,
            "category": category,
            "availability": availability,
            "price": price,
            "image_url": image_url
        }).eq('id', item_id).execute()
        flash("UMak Coop item updated.", "success")
    except Exception as e:
        logger.error("Error updating UMak Coop item: %s", e)
        flash("Failed to update UMak Coop item.", "error")
    return redirect(url_for('admin.manage_umak_coop_catalog'))

@admin.route('/admin/catalog/umak-coop/<item_id>/delete', methods=['POST'])
@login_required
@catalog_manage_required
def delete_umak_coop_item(item_id):
    try:
        admin_client = get_service_client()
        admin_client.table('umak_coop_items').delete().eq('id', item_id).execute()
        flash("UMak Coop item deleted.", "success")
    except Exception as e:
        logger.error("Error deleting UMak Coop item: %s", e)
        flash("Failed to delete UMak Coop item.", "error")
    return redirect(url_for('admin.manage_umak_coop_catalog'))
