import logging
import os
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request
from app.routes.auth import login_required
from services.supabase_client import supabase, supabase_service, get_user_client
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
    pending = [root_comment_id]
    seen = set()
    collected = []

    while pending:
        current = pending.pop(0)
        if not current or current in seen:
            continue
        seen.add(current)
        collected.append(current)

        children = admin_client.table('comments').select('id').eq('parent_id', current).execute()
        for child in (children.data or []):
            child_id = child.get('id')
            if child_id and child_id not in seen:
                pending.append(child_id)

    if not collected:
        return

    # Delete leaf+parent ids in one grouped delete per batch.
    for batch in chunked(collected, size=100):
        admin_client.table('comments').delete().in_('id', batch).execute()


def delete_post_dependencies(admin_client, post_id):
    # Clear references before removing the post in schemas without ON DELETE CASCADE.
    admin_client.table('likes').delete().eq('post_id', post_id).execute()
    admin_client.table('reports').delete().eq('post_id', post_id).execute()
    admin_client.table('warnings').update({"post_id": None}).eq('post_id', post_id).execute()
    admin_client.table('comments').delete().eq('post_id', post_id).execute()

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

def role_block_response(message):
    if request.is_json:
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
                if request.is_json:
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

@admin.route('/admin/dashboard')
@login_required
@admin_required
def dashboard():
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    
    stats = {
        "total_users": 0,
        "total_posts": 0,
        "reported_posts": 0,
        "banned_accounts": 0,
        "user_list": [],
        "reports_list": [],
        "posts_by_category": [],
        "recent_activities": [],
        "disputes_count": 0
    }
    
    try:
        # Fetch all profiles
        users_res = client.table('profiles').select("*").execute()
        stats["total_users"] = len(users_res.data)
        stats["user_list"] = users_res.data
        
        # Fetch all posts for category counts
        posts_res = client.table('posts').select("id, category").execute()
        stats["total_posts"] = len(posts_res.data)
        
        cat_counts = {}
        for p in posts_res.data:
            cat = p.get('category', 'General')
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        stats["posts_by_category"] = [{"category": k, "count": v} for k, v in cat_counts.items()]

        # Fetch reports
        reports_res = client.table('reports').select("*, posts(content), profiles!reports_reporter_id_fkey(full_name)").order("created_at", desc=True).execute()
        stats["reported_posts"] = len(reports_res.data)
        stats["reports_list"] = reports_res.data
        
        # Banned accounts
        banned_res = client.table('profiles').select("id").eq("status", "banned").execute()
        stats["banned_accounts"] = len(banned_res.data)

        # Recent Activities (Admin Logs)
        logs_res = client.table('admin_logs').select("*, profiles!admin_logs_admin_id_fkey(full_name)").order("created_at", desc=True).limit(5).execute()
        stats["recent_activities"] = logs_res.data

        # Verification Disputes Count
        disputes_res = client.table('verification_disputes').select("id", count="exact").eq("status", "pending").execute()
        stats["disputes_count"] = disputes_res.count if hasattr(disputes_res, 'count') else len(disputes_res.data)
            
    except Exception as e:
        logger.error("Error fetching admin stats: %s", e)

    return render_template('admin/dashboard.html', stats=stats, user=session.get('user'), permissions=permissions)

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
        query = query.ilike('full_name', f'%{search}%')
    res = query.order('full_name').execute()
    return render_template('admin/users.html', users=res.data, user=session.get('user'), search=search, permissions=permissions)

@admin.route('/admin/users/<user_id>/manage')
@login_required
@account_access_required
def user_management(user_id):
    client = get_admin_read_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    profile_res = client.table('profiles').select("*").eq("id", user_id).single().execute()
    posts_res = client.table('posts').select("*").eq("user_id", user_id).execute()
    warnings_res = client.table('warnings').select("*").eq("user_id", user_id).execute()
    return render_template('admin/user_manage.html', 
                           target_user=profile_res.data, 
                           posts=posts_res.data, 
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
        admin_client = get_service_client()

        target_profile_res = admin_client.table('profiles').select("id, role").eq("id", user_id).single().execute()
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
        admin_client = get_service_client()
        actor_role = get_current_role()
        target_res = admin_client.table('profiles').select("role").eq("id", user_id).single().execute()
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
    query = client.table('posts').select("*, profiles(full_name, avatar_url)")
    if category != 'All':
        query = query.eq('category', category)
    res = query.order('created_at', desc=True).execute()
    return render_template('admin/content_manage.html', posts=res.data, category=category, user=session.get('user'), permissions=permissions)

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
            .select("*, profiles(full_name, avatar_url)")\
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
    client = get_admin_read_client()
    try:
        client.table('posts').update({"is_flagged": True}).eq("id", post_id).execute()
        return jsonify({"status": "success", "message": "Post flagged."})
    except Exception as e:
        return jsonify({"status": "error", "message": "An error occurred."}), 500

@admin.route('/admin/comments/<comment_id>/flag', methods=['POST'])
@login_required
@content_access_required
def flag_comment(comment_id):
    client = get_admin_read_client()
    try:
        client.table('comments').update({"is_flagged": True}).eq("id", comment_id).execute()
        return jsonify({"status": "success", "message": "Comment flagged."})
    except Exception as e:
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

    is_json = request.is_json

    if not all([user_id, reason, message]):
        if is_json:
            return jsonify({"status": "error", "message": "Missing required fields."}), 400
        flash("Missing required fields for warning.", "error")
        return redirect(request.referrer or url_for('admin.dashboard'))

    try:
        admin_client = get_service_client()

        # 1. Insert into warnings table
        admin_client.table('warnings').insert({
            "user_id": user_id,
            "admin_id": session['user']['id'],
            "reason": reason,
            "post_id": post_id
        }).execute()

        # 2. Insert into notifications table
        admin_client.table('notifications').insert({
            "user_id": user_id,
            "title": f"Community Warning: {reason}",
            "message": message,
            "type": "warning"
        }).execute()

        if is_json:
            return jsonify({"status": "success", "message": "Warning sent successfully."})
        flash("Warning sent successfully.", "success")
        return redirect(request.referrer or url_for('admin.dashboard'))
    except Exception as e:
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
        admin_client = get_service_client()
        actor_role = get_current_role()
        target_res = admin_client.table('profiles').select("role").eq("id", user_id).single().execute()
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

        admin_client.table('notifications').insert({
            "user_id": user_id,
            "title": "Account Suspended",
            "message": f"Your account has been suspended for {days} day(s). Reason: {reason}",
            "type": "warning"
        }).execute()

        try:
            admin_client.table('admin_logs').insert({
                "admin_id": session.get('user', {}).get('id'),
                "action_type": "suspend",
                "target_id": user_id,
                "details": f"Suspended for {days} day(s). Reason: {reason}"
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
        admin_client = get_service_client()
        actor_role = get_current_role()
        target_res = admin_client.table('profiles').select("role").eq("id", user_id).single().execute()
        target_role = normalize_role(target_res.data.get('role') if target_res.data else '')
        if not can_manage_target_role(actor_role, target_role):
            flash("You cannot ban this account level.", "error")
            return redirect(url_for('admin.user_management', user_id=user_id))

        admin_client.table('profiles').update({
            "status": "banned",
            "ban_reason": reason,
            "suspended_until": None
        }).eq("id", user_id).execute()

        admin_client.table('notifications').insert({
            "user_id": user_id,
            "title": "Account Banned",
            "message": f"Your account has been permanently banned. Reason: {reason}",
            "type": "warning"
        }).execute()

        try:
            admin_client.table('admin_logs').insert({
                "admin_id": session.get('user', {}).get('id'),
                "action_type": "ban",
                "target_id": user_id,
                "details": f"Banned. Reason: {reason}"
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
        admin_client = get_service_client()
        delete_post_dependencies(admin_client, post_id)
        admin_client.table('posts').delete().eq("id", post_id).execute()

        try:
            admin_client.table('admin_logs').insert({
                "admin_id": session.get('user', {}).get('id'),
                "action_type": "remove_post",
                "target_id": post_id,
                "details": "Post removed by admin."
            }).execute()
        except Exception as log_e:
            logger.error("Audit log error (delete post): %s", log_e)

        if request.is_json:
            return jsonify({"status": "deleted"})
        flash("Post removed.", "success")
    except Exception as e:
        logger.error("Error deleting post (admin): %s", e)
        if request.is_json:
            return jsonify({"status": "error", "message": "Failed to remove post."}), 500
        flash("Failed to remove post.", "error")

    return redirect(request.referrer or url_for('admin.dashboard'))

@admin.route('/admin/comments/<comment_id>/delete', methods=['POST'])
@login_required
@content_access_required
def admin_delete_comment(comment_id):
    try:
        admin_client = get_service_client()
        delete_comment_thread(admin_client, comment_id)
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
        admin_client.table('verification_disputes').update({
            "status": action
        }).eq("id", dispute_id).execute()

        try:
            admin_client.table('admin_logs').insert({
                "admin_id": session.get('user', {}).get('id'),
                "action_type": f"dispute_{action}",
                "target_id": dispute_id,
                "details": f"Verification dispute {action}."
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
    res = client.table('umak_coop_items')\
        .select("id, name, details, price, availability, image_url, created_at")\
        .order('created_at', desc=True).execute()
    return render_template(
        'admin/catalog_manage.html',
        catalog_type='umak_coop',
        items=res.data or [],
        user=session.get('user'),
        permissions=permissions
    )

@admin.route('/admin/catalog/umak-coop/create', methods=['POST'])
@login_required
@catalog_manage_required
def create_umak_coop_item():
    name = request.form.get('name', '').strip()
    details = request.form.get('details', '').strip()
    availability = request.form.get('availability', 'Available').strip() or 'Available'
    image_url = request.form.get('image_url', '').strip()
    image_file = request.files.get('image_file')
    price = _parse_catalog_price(request.form.get('price'))

    if not name or not details:
        flash("Item name and details are required.", "error")
        return redirect(url_for('admin.manage_umak_coop_catalog'))
    if price is None:
        flash("A valid item price is required.", "error")
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
            "availability": availability,
            "price": price,
            "image_url": image_url,
            "created_by": session.get('user', {}).get('id')
        }).execute()
        flash("UMak Coop item created.", "success")
    except ValueError as ve:
        flash(str(ve), "error")
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
    availability = request.form.get('availability', 'Available').strip() or 'Available'
    image_url = request.form.get('image_url', '').strip()
    image_file = request.files.get('image_file')
    price = _parse_catalog_price(request.form.get('price'))

    if not name or not details:
        flash("Item name and details are required.", "error")
        return redirect(url_for('admin.manage_umak_coop_catalog'))
    if price is None:
        flash("A valid item price is required.", "error")
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
            "availability": availability,
            "price": price,
            "image_url": image_url
        }).eq('id', item_id).execute()
        flash("UMak Coop item updated.", "success")
    except ValueError as ve:
        flash(str(ve), "error")
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
