"""Render dashboard pages via test client and save HTML for screenshots."""
import os, sys, datetime, logging
os.environ.setdefault('SECRET_KEY', 'screenshot-dev-key')
os.environ.setdefault('FLASK_ENV', 'development')

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, session, render_template
from services.supabase_client import supabase_service

logging.basicConfig(level=logging.WARNING)

app = Flask(__name__, template_folder='app/templates', static_folder='app/static', static_url_path='/static')
app.config['SECRET_KEY'] = 'screenshot-dev-key'
app.config['SERVER_NAME'] = '127.0.0.1:5099'
app.config['WTF_CSRF_ENABLED'] = False

from flask_wtf.csrf import CSRFProtect
CSRFProtect(app)

# Register blueprints so url_for() works in templates
from app.routes.core import core
from app.routes.auth import auth
from app.routes.admin import admin
app.register_blueprint(core)
app.register_blueprint(auth)
app.register_blueprint(admin)

@app.template_filter('datetime_obj')
def datetime_obj(value):
    ts = value.replace('Z', '').split('.')[0]
    try:
        return datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return datetime.datetime.strptime(value.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')

@app.context_processor
def inject_globals():
    return {
        'now': datetime.datetime.now(datetime.timezone.utc),
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_ANON_KEY': os.getenv('SUPABASE_KEY'),
        'notifications': [],
        'unread_notifications_count': 0,
    }

# Fetch real users
admin_user = regular_user = None
if supabase_service:
    try:
        r = supabase_service.table('profiles').select('*').in_('role', ['admin','super_admin','superadmin']).limit(1).execute()
        if r.data: admin_user = r.data[0]
    except: pass
    try:
        r = supabase_service.table('profiles').select('*').limit(1).execute()
        if r.data: regular_user = r.data[0]
    except: pass

user_data = regular_user or admin_user or {'id':'0','email':'demo@umak.edu.ph','full_name':'Demo','role':'student'}
admin_data = admin_user or user_data
print(f"User: {user_data.get('full_name')} | Admin: {admin_data.get('full_name')}")

OUT = 'C:/Users/USER/screenshots'

with app.app_context():
    # --- User Dashboard ---
    print("Rendering user dashboard...")
    posts = trending = events = []
    try:
        posts = (supabase_service.table('posts').select('*, profiles(full_name, avatar_url, role)').order('created_at', desc=True).limit(20).execute()).data or []
        trending = (supabase_service.table('posts').select('*, profiles(full_name, avatar_url, role)').order('likes_count', desc=True).limit(5).execute()).data or []
        events = (supabase_service.table('posts').select('*, profiles(full_name, avatar_url, role)').eq('category', 'Events').order('created_at', desc=True).limit(5).execute()).data or []
    except Exception as e:
        print(f"  posts fetch: {e}")

    with app.test_request_context('/dashboard'):
        session['user'] = user_data
        session['access_token'] = 'fake'
        html = render_template('dashboard.html', user=user_data, posts=posts, active_category='all', trending=trending, events=events, now=datetime.datetime.now(datetime.timezone.utc))
    with open(f'{OUT}/user_dashboard.html', 'w', encoding='utf-8') as f:
        # Rewrite static paths to absolute file paths for local rendering
        html = html.replace('/static/', 'http://127.0.0.1:5000/static/')
        f.write(html)
    print(f"  Saved {OUT}/user_dashboard.html")

    # --- Admin Dashboard ---
    print("Rendering admin dashboard...")
    sys.path.insert(0, os.getcwd())
    from app.routes.admin import build_admin_permissions
    permissions = build_admin_permissions(admin_data.get('role', 'admin'))
    stats = {"total_users":0,"total_posts":0,"reported_posts":0,"banned_accounts":0,"user_list":[],"reports_list":[],"posts_by_category":[],"recent_activities":[],"disputes_count":0}
    try:
        u = supabase_service.table('profiles').select("*").execute()
        stats["total_users"]=len(u.data); stats["user_list"]=u.data
        p = supabase_service.table('posts').select("id, category").execute()
        stats["total_posts"]=len(p.data)
        cc={}
        for x in p.data: c=x.get('category','General'); cc[c]=cc.get(c,0)+1
        stats["posts_by_category"]=[{"category":k,"count":v} for k,v in cc.items()]
        rr=supabase_service.table('reports').select("*, posts(content), profiles!reports_reporter_id_fkey(full_name)").order("created_at",desc=True).execute()
        stats["reported_posts"]=len(rr.data); stats["reports_list"]=rr.data
        b=supabase_service.table('profiles').select("id").eq("status","banned").execute()
        stats["banned_accounts"]=len(b.data)
        l=supabase_service.table('admin_logs').select("*, profiles!admin_logs_admin_id_fkey(full_name)").order("created_at",desc=True).limit(5).execute()
        stats["recent_activities"]=l.data
        d=supabase_service.table('verification_disputes').select("id",count="exact").eq("status","pending").execute()
        stats["disputes_count"]=d.count if hasattr(d,'count') else len(d.data)
    except Exception as e:
        print(f"  admin stats: {e}")

    with app.test_request_context('/admin/dashboard'):
        session['user'] = admin_data
        session['access_token'] = 'fake'
        html = render_template('admin/dashboard.html', stats=stats, user=admin_data, permissions=permissions)
    with open(f'{OUT}/admin_dashboard.html', 'w', encoding='utf-8') as f:
        html = html.replace('/static/', 'http://127.0.0.1:5000/static/')
        f.write(html)
    print(f"  Saved {OUT}/admin_dashboard.html")

print("\nDone! Now screenshot the HTML files.")
