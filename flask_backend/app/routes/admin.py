from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify
from app.routes.auth import login_required, apply_supabase_auth_token
from services.supabase_client import supabase
from functools import wraps
import datetime

admin = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('role') not in ['admin', 'super_admin', 'superadmin']:
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

@admin.route('/admin/content/<category>')
@login_required
@admin_required
def content_management(category):
    apply_supabase_auth_token()
    query = supabase.table('posts').select("*, profiles(full_name)")
    if category != 'All':
        query = query.eq('category', category)
    res = query.order('created_at', desc=True).execute()
    return render_template('admin/content_manage.html', posts=res.data, category=category, user=session.get('user'))

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
        flash(f"Failed to become admin: {str(e)}", "error")
        return redirect(url_for('core.profile_settings'))

@admin.route('/admin/forbidden-words')
@login_required
@admin_required
def manage_forbidden_words():
    apply_supabase_auth_token()
    res = supabase.table('forbidden_words').select("*").execute()
    return render_template('admin/forbidden_words.html', words=res.data, user=session.get('user'))
