from flask import Blueprint, render_template, session
from .auth import login_required

core = Blueprint('core', __name__)

@core.route('/')
def home():
    user = session.get('user')
    return render_template('home.html', user=user)

@core.route('/dashboard')
@login_required
def dashboard():
    user = session.get('user')
    return render_template('dashboard.html', user=user)

@core.route('/login')
def login():
    return render_template('login.html')
