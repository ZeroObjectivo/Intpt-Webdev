from flask import Blueprint, render_template

core = Blueprint('core', __name__)

@core.route('/')
def home():
    return render_template('home.html')

@core.route('/login')
def login():
    return render_template('login.html')
