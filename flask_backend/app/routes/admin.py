import os
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request
from app.routes.auth import login_required, apply_supabase_auth_token
from services.supabase_client import supabase, supabase_service
from supabase import create_client, Client
from functools import wraps
import datetime

admin = Blueprint('admin', __name__)

def get_service_client():
    """
    Helper to get a service role client that bypasses RLS.
    Used for administrative actions that standard users shouldn't have permissions for.
    """
    if not supabase_service:
        # Fallback to standard client if service key isn't configured
        return supabase
    return supabase_service

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user:
            return redirect(url_for('core.login'))
        
        # Check database for latest role to avoid stale session issues
        try:
            profile_res = supabase.table('profiles').select("role").eq("id", user.get('id')).single().execute()
            current_role = profile_res.data.get('role') if profile_res.data else user.get('role')
            
            # Update session role if it changed
            if current_role != user.get('role'):
                user['role'] = current_role
                session['user'] = user
                session.modified = True
        except Exception as e:
            print(f"Error verifying admin role: {e}")
            current_role = user.get('role')

        if current_role not in ['admin', 'super_admin', 'superadmin']:
            flash("Unauthorized access. Admin privileges required.", "error")
            return redirect(url_for('core.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/admin/dashboard')
@login_required
@admin_required
def dashboard():
    apply_supabase_auth_token()
    
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
        users_res = supabase.table('profiles').select("*").execute()
        stats["total_users"] = len(users_res.data)
        stats["user_list"] = users_res.data
        
        # Fetch all posts for category counts
        posts_res = supabase.table('posts').select("id, category").execute()
        stats["total_posts"] = len(posts_res.data)
        
        cat_counts = {}
        for p in posts_res.data:
            cat = p.get('category', 'General')
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        stats["posts_by_category"] = [{"category": k, "count": v} for k, v in cat_counts.items()]

        # Fetch reports
        reports_res = supabase.table('reports').select("*, posts(content), profiles!reports_reporter_id_fkey(full_name)").order("created_at", desc=True).execute()
        stats["reported_posts"] = len(reports_res.data)
        stats["reports_list"] = reports_res.data
        
        # Banned accounts
        banned_res = supabase.table('profiles').select("id").eq("status", "banned").execute()
        stats["banned_accounts"] = len(banned_res.data)

        # Recent Activities (Admin Logs)
        logs_res = supabase.table('admin_logs').select("*, profiles!admin_logs_admin_id_fkey(full_name)").order("created_at", desc=True).limit(5).execute()
        stats["recent_activities"] = logs_res.data

        # Verification Disputes Count
        disputes_res = supabase.table('verification_disputes').select("id", count="exact").eq("status", "pending").execute()
        stats["disputes_count"] = disputes_res.count if hasattr(disputes_res, 'count') else len(disputes_res.data)
            
    except Exception as e:
        print(f"Error fetching admin stats: {e}")

    return render_template('admin/dashboard.html', stats=stats, user=session.get('user'))

@admin.route('/admin/users')
@login_required
@admin_required
def manage_users():
    apply_supabase_auth_token()
    search = request.args.get('search', '')
    query = supabase.table('profiles').select("*")
    if search:
        query = query.ilike('full_name', f'%{search}%')
    res = query.order('full_name').execute()
    return render_template('admin/users.html', users=res.data, user=session.get('user'), search=search)

@admin.route('/admin/users/<user_id>/manage')
@login_required
@admin_required
def user_management(user_id):
    apply_supabase_auth_token()
    profile_res = supabase.table('profiles').select("*").eq("id", user_id).single().execute()
    posts_res = supabase.table('posts').select("*").eq("user_id", user_id).execute()
    warnings_res = supabase.table('warnings').select("*").eq("user_id", user_id).execute()
    return render_template('admin/user_manage.html', 
                           target_user=profile_res.data, 
                           posts=posts_res.data, 
                           warnings=warnings_res.data,
                           user=session.get('user'))

@admin.route('/admin/users/<user_id>/update-role', methods=['POST'])
@login_required
@admin_required
def update_user_role(user_id):
    apply_supabase_auth_token()
    new_role = request.form.get('role')
    
    valid_roles = ['student', 'content_moderator', 'account_manager', 'admin', 'super_admin']
    if new_role not in valid_roles:
        flash("Invalid role selected.", "error")
        return redirect(url_for('admin.user_management', user_id=user_id))
    
    try:
        # 1. Use the service client to bypass RLS policies for profile updates
        admin_client = get_service_client()
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
@admin_required
def content_management(category):
    apply_supabase_auth_token()
    query = supabase.table('posts').select("*, profiles(full_name, avatar_url)")
    if category != 'All':
        query = query.eq('category', category)
    res = query.order('created_at', desc=True).execute()
    return render_template('admin/content_manage.html', posts=res.data, category=category, user=session.get('user'))

@admin.route('/admin/posts/<post_id>/likers')
@login_required
@admin_required
def get_post_likers(post_id):
    apply_supabase_auth_token()
    res = supabase.table('likes').select("profiles(id, full_name, avatar_url)").eq('post_id', post_id).execute()
    likers = [item['profiles'] for item in res.data if item.get('profiles')]
    return jsonify({"likers": likers})

@admin.route('/admin/posts/<post_id>/flag', methods=['POST'])
@login_required
@admin_required
def flag_post(post_id):
    apply_supabase_auth_token()
    try:
        supabase.table('posts').update({"is_flagged": True}).eq("id", post_id).execute()
        return jsonify({"status": "success", "message": "Post flagged."})
    except Exception as e:
        return jsonify({"status": "error", "message": "An error occurred."}), 500

@admin.route('/admin/comments/<comment_id>/flag', methods=['POST'])
@login_required
@admin_required
def flag_comment(comment_id):
    apply_supabase_auth_token()
    try:
        supabase.table('comments').update({"is_flagged": True}).eq("id", comment_id).execute()
        return jsonify({"status": "success", "message": "Comment flagged."})
    except Exception as e:
        return jsonify({"status": "error", "message": "An error occurred."}), 500

@admin.route('/admin/warn-user', methods=['POST'])
@login_required
@admin_required
def warn_user():
    apply_supabase_auth_token()
    data = request.json
    user_id = data.get('user_id')
    post_id = data.get('post_id')
    reason = data.get('reason')
    message = data.get('message')

    if not all([user_id, reason, message]):
        return jsonify({"status": "error", "message": "Missing required fields."}), 400

    try:
        # 1. Insert into warnings table
        supabase.table('warnings').insert({
            "user_id": user_id,
            "admin_id": session['user']['id'],
            "reason": reason,
            "post_id": post_id
        }).execute()

        # 2. Insert into notifications table
        supabase.table('notifications').insert({
            "user_id": user_id,
            "title": "Community Warning",
            "message": message,
            "type": "warning"
        }).execute()

        return jsonify({"status": "success", "message": "Warning sent successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": "An error occurred."}), 500

@admin.route('/admin/disputes')
@login_required
@admin_required
def manage_disputes():
    apply_supabase_auth_token()
    res = supabase.table('verification_disputes').select("*").order('created_at', desc=True).execute()
    return render_template('admin/disputes.html', disputes=res.data, user=session.get('user'))

@admin.route('/admin/become-admin', methods=['POST'])
@login_required
def become_admin():
    """Temporary route for testing to promote current user to super_admin."""
    user_id = session['user']['id']
    apply_supabase_auth_token()
    
    try:
        # 1. Update in database
        supabase.table('profiles').update({"role": "super_admin"}).eq("id", user_id).execute()
        
        # 2. Re-fetch profile to ensure session is perfectly synced
        profile_res = supabase.table('profiles').select("*").eq("id", user_id).single().execute()
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
@admin_required
def manage_forbidden_words():
    apply_supabase_auth_token()
    res = supabase.table('forbidden_words').select("*").order('word').execute()
    return render_template('admin/forbidden_words.html', words=res.data, user=session.get('user'))

@admin.route('/admin/forbidden-words/add', methods=['POST'])
@login_required
@admin_required
def add_forbidden_word():
    apply_supabase_auth_token()
    word = request.form.get('word', '').strip().lower()
    if not word:
        flash("Word cannot be empty.", "error")
        return redirect(url_for('admin.manage_forbidden_words'))
    
    try:
        supabase.table('forbidden_words').insert({"word": word}).execute()
        flash(f"Added '{word}' to forbidden words.", "success")
    except Exception as e:
        flash("Error adding word.", "error")
    
    return redirect(url_for('admin.manage_forbidden_words'))

@admin.route('/admin/forbidden-words/<word>/delete', methods=['POST'])
@login_required
@admin_required
def delete_forbidden_word(word):
    apply_supabase_auth_token()
    try:
        supabase.table('forbidden_words').delete().eq('word', word).execute()
        flash(f"Removed '{word}' from forbidden words.", "success")
    except Exception as e:
        flash("Error removing word.", "error")
    
    return redirect(url_for('admin.manage_forbidden_words'))
