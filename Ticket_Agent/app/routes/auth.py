from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.database import get_connection, User
import logging
from flask import current_app

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
logger = logging.getLogger(__name__)

from flask import current_app

def validate_user_credentials(username, password):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "SELECT id, userName FROM [user] WHERE userName = ? AND password = ?"
        cursor.execute(query, (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {'id': user[0], 'username': user[1]}
        return None
    except Exception as e:
        # Use Flask app logger
        current_app.logger.error(f"Database authentication error: {e}", exc_info=True)
        return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        next_url = request.form.get('next') or url_for('main.index')
        
        user = validate_user_credentials(username, password)
        
        if user:
            user_obj = User(user['id'], user['username'])
            login_user(user_obj)
            session['user_id'] = user['id']
            flash('Login successful!', 'success')
            return redirect(next_url)
        else:
            flash('Invalid credentials. Please try again.', 'danger')
            return render_template('login.html', next_url=next_url)
    
    next_url = request.args.get('next', url_for('main.index'))
    return render_template('login.html', next_url=next_url)

@auth_bp.route('/logout')
# @login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('auth.login'))