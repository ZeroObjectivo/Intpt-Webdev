import os
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request
from app.routes.auth import login_required
from services.supabase_client import supabase, supabase_service, get_user_client
from functools import wraps
import datetime

admin = Blueprint('admin', __name__)

SUPER_ADMIN_ROLES = {'super_admin', 'superadmin'}
ADMIN_ROLES = {'admin'}
ACCOUNT_MANAGER_ROLES = {'account_manager'}
CONTENT_MODERATOR_ROLES = {'content_moderator'}

ADMIN_PORTAL_ROLES = SUPER_ADMIN_ROLES | ADMIN_ROLES | ACCOUNT_MANAGER_ROLES | CONTENT_MODERATOR_ROLES
ACCOUNT_ACCESS_ROLES = SUPER_ADMIN_ROLES | ADMIN_ROLES | ACCOUNT_MANAGER_ROLES
CONTENT_ACCESS_ROLES = SUPER_ADMIN_ROLES | ADMIN_ROLES | CONTENT_MODERATOR_ROLES
CATALOG_MANAGE_ROLES = SUPER_ADMIN_ROLES | ADMIN_ROLES

def get_service_client():
    """
    Helper to get a service role client that bypasses RLS.
    Used for administrative actions that standard users shouldn't have permissions for.
    """
    if not supabase_service:
        # Fallback to standard client if service key isn't configured
        return supabase
    return supabase_service

def normalize_role(role):
    return (role or '').strip().lower()

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
        print(f"Error verifying admin role: {e}")
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
    client = get_user_client()
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
        print(f"Error fetching admin stats: {e}")

    return render_template('admin/dashboard.html', stats=stats, user=session.get('user'), permissions=permissions)

@admin.route('/admin/users')
@login_required
@account_access_required
def manage_users():
    client = get_user_client()
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
    client = get_user_client()
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

    valid_roles = {'student', 'content_moderator', 'account_manager', 'admin', 'super_admin', 'superadmin'}
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
            print(f"Audit Log Error: {str(log_e)}")
        
        flash(f"User role updated successfully to {new_role.replace('_', ' ').title()}.", "success")
    except Exception as e:
        flash("Error updating user role.", "error")
        
    return redirect(url_for('admin.user_management', user_id=user_id))

@admin.route('/admin/content/<category>')
@login_required
@content_access_required
def content_management(category):
    client = get_user_client()
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
    client = get_user_client()
    res = client.table('likes').select("profiles(id, full_name, avatar_url)").eq('post_id', post_id).execute()
    likers = [item['profiles'] for item in res.data if item.get('profiles')]
    return jsonify({"likers": likers})

@admin.route('/admin/posts/<post_id>/flag', methods=['POST'])
@login_required
@content_access_required
def flag_post(post_id):
    client = get_user_client()
    try:
        client.table('posts').update({"is_flagged": True}).eq("id", post_id).execute()
        return jsonify({"status": "success", "message": "Post flagged."})
    except Exception as e:
        return jsonify({"status": "error", "message": "An error occurred."}), 500

@admin.route('/admin/comments/<comment_id>/flag', methods=['POST'])
@login_required
@content_access_required
def flag_comment(comment_id):
    client = get_user_client()
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
    user_id = data.get('user_id')
    post_id = data.get('post_id')
    reason = data.get('reason')
    message = data.get('message')

    if not all([user_id, reason, message]):
        return jsonify({"status": "error", "message": "Missing required fields."}), 400

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

        return jsonify({"status": "success", "message": "Warning sent successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": "An error occurred."}), 500

@admin.route('/admin/disputes')
@login_required
@account_access_required
def manage_disputes():
    client = get_user_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    res = client.table('verification_disputes').select("*").order('created_at', desc=True).execute()
    return render_template('admin/disputes.html', disputes=res.data, user=session.get('user'), permissions=permissions)

@admin.route('/admin/become-admin', methods=['POST'])
@login_required
@role_required(SUPER_ADMIN_ROLES, "Only Super Admin can access this action.")
def become_admin():
    """Temporary route for testing to promote current user to super_admin."""
    user_id = session['user']['id']
    client = get_user_client()
    
    try:
        # 1. Update in database
        client.table('profiles').update({"role": "super_admin"}).eq("id", user_id).execute()
        
        # 2. Re-fetch profile to ensure session is perfectly synced
        profile_res = client.table('profiles').select("*").eq("id", user_id).single().execute()
        profile = profile_res.data
        
        # 3. Update the full user object in session
        # We preserve the user_metadata from the auth session but update the profile info
        session['user'].update(profile)
        session.modified = True
        
        flash("You are now a Super Admin!", "success")
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        flash("Failed to become admin.", "error")
        return redirect(url_for('core.profile_settings'))

@admin.route('/admin/forbidden-words')
@login_required
@content_access_required
def manage_forbidden_words():
    client = get_user_client()
    current_role = get_current_role()
    permissions = build_admin_permissions(current_role)
    res = client.table('forbidden_words').select("*").order('word').execute()
    return render_template('admin/forbidden_words.html', words=res.data, user=session.get('user'), permissions=permissions)

@admin.route('/admin/forbidden-words/add', methods=['POST'])
@login_required
@content_access_required
def add_forbidden_word():
    client = get_user_client()
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
    client = get_user_client()
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

@admin.route('/admin/catalog/scholarship')
@login_required
@content_access_required
def manage_scholarship_catalog():
    client = get_user_client()
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
        print(f"Error creating scholarship catalog item: {e}")
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
        print(f"Error updating scholarship catalog item: {e}")
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
        print(f"Error deleting scholarship catalog item: {e}")
        flash("Failed to delete scholarship card.", "error")
    return redirect(url_for('admin.manage_scholarship_catalog'))

@admin.route('/admin/catalog/umak-coop')
@login_required
@content_access_required
def manage_umak_coop_catalog():
    client = get_user_client()
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
    price = _parse_catalog_price(request.form.get('price'))

    if not name or not details:
        flash("Item name and details are required.", "error")
        return redirect(url_for('admin.manage_umak_coop_catalog'))
    if price is None:
        flash("A valid item price is required.", "error")
        return redirect(url_for('admin.manage_umak_coop_catalog'))

    try:
        admin_client = get_service_client()
        admin_client.table('umak_coop_items').insert({
            "name": name,
            "details": details,
            "availability": availability,
            "price": price,
            "image_url": image_url,
            "created_by": session.get('user', {}).get('id')
        }).execute()
        flash("UMak Coop item created.", "success")
    except Exception as e:
        print(f"Error creating UMak Coop item: {e}")
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
    price = _parse_catalog_price(request.form.get('price'))

    if not name or not details:
        flash("Item name and details are required.", "error")
        return redirect(url_for('admin.manage_umak_coop_catalog'))
    if price is None:
        flash("A valid item price is required.", "error")
        return redirect(url_for('admin.manage_umak_coop_catalog'))

    try:
        admin_client = get_service_client()
        admin_client.table('umak_coop_items').update({
            "name": name,
            "details": details,
            "availability": availability,
            "price": price,
            "image_url": image_url
        }).eq('id', item_id).execute()
        flash("UMak Coop item updated.", "success")
    except Exception as e:
        print(f"Error updating UMak Coop item: {e}")
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
        print(f"Error deleting UMak Coop item: {e}")
        flash("Failed to delete UMak Coop item.", "error")
    return redirect(url_for('admin.manage_umak_coop_catalog'))
