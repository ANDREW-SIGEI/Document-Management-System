from functools import wraps
from flask import session, redirect, url_for, flash, request, abort
import sqlite3
import time
from datetime import datetime
import json

# Role definitions
ROLES = {
    'Administrator': 100,  # Highest level access
    'Registry': 75,        # Can process documents, approve workflows
    'Supervisor': 50,      # Can approve department documents
    'User': 25             # Basic user access
}

# Permission definitions
PERMISSIONS = {
    # Document management
    'create_document': ['Administrator', 'Registry', 'Supervisor', 'User'],
    'view_any_document': ['Administrator', 'Registry'],
    'view_dept_document': ['Administrator', 'Registry', 'Supervisor'],
    'view_own_document': ['Administrator', 'Registry', 'Supervisor', 'User'],
    'edit_any_document': ['Administrator', 'Registry'],
    'edit_dept_document': ['Administrator', 'Registry', 'Supervisor'],
    'edit_own_document': ['Administrator', 'Registry', 'Supervisor', 'User'],
    'approve_document': ['Administrator', 'Registry', 'Supervisor'],
    'track_document': ['Administrator', 'Registry', 'Supervisor', 'User'],
    
    # User management
    'view_users': ['Administrator'],
    'add_user': ['Administrator'],
    'edit_user': ['Administrator'],
    'delete_user': ['Administrator'],
    'assign_role': ['Administrator'],
    'bulk_user_actions': ['Administrator'],
    
    # System management
    'view_reports': ['Administrator', 'Registry', 'Supervisor'],
    'view_system_reports': ['Administrator'],
    'database_management': ['Administrator'],
    'maintenance': ['Administrator'],
    'system_configuration': ['Administrator'],
    
    # File management
    'file_manager': ['Administrator', 'Registry'],
    
    # Registry specific
    'registry_approval': ['Administrator', 'Registry'],
    'incoming_management': ['Administrator', 'Registry', 'Supervisor'],
    'outgoing_management': ['Administrator', 'Registry', 'Supervisor']
}

# Role-based menu visibility
MENU_PERMISSIONS = {
    'dashboard': ['Administrator', 'Registry', 'Supervisor', 'User'],
    'compose': ['Administrator', 'Registry', 'Supervisor', 'User'],
    'track_document': ['Administrator', 'Registry', 'Supervisor', 'User'],
    'incoming': ['Administrator', 'Registry', 'Supervisor'],
    'outgoing': ['Administrator', 'Registry', 'Supervisor'],
    'reports': ['Administrator', 'Registry', 'Supervisor'],
    'registry_approval': ['Administrator', 'Registry'],
    'database_management': ['Administrator'],
    'maintenance': ['Administrator'],
    'user_management': ['Administrator'],
    'file_manager': ['Administrator', 'Registry']
}

def get_db_connection():
    """Get a database connection with row factory"""
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    return conn

def log_activity(user_id, action, details, status="success"):
    """Log user activity to the database"""
    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO activity_log (user_id, action, details, status, timestamp) VALUES (?, ?, ?, ?, ?)',
            (user_id, action, json.dumps(details), status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging activity: {e}")

def check_session_valid():
    """Check if the current session is valid and not expired"""
    if 'user_id' not in session:
        return False
        
    # Check if session has a last_activity timestamp
    if 'last_activity' in session:
        # Session timeout after 30 minutes of inactivity
        if time.time() - session['last_activity'] > 1800:  # 30 minutes
            session.clear()
            return False
            
    # Update last activity time
    session['last_activity'] = time.time()
    return True

def can_access_menu(menu_item):
    """Check if the current user can access a menu item"""
    if not check_session_valid():
        return False
        
    user_role = session.get('role', None)
    if not user_role:
        return False
        
    if menu_item not in MENU_PERMISSIONS:
        return False
        
    return user_role in MENU_PERMISSIONS[menu_item]

def has_permission(permission):
    """Check if the current user has a specific permission"""
    if not check_session_valid():
        return False
        
    user_role = session.get('role', None)
    if not user_role:
        return False
        
    if permission not in PERMISSIONS:
        return False
        
    return user_role in PERMISSIONS[permission]

def requires_permission(permission):
    """Decorator to require a specific permission for route access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not check_session_valid():
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login', next=request.url))
                
            if not has_permission(permission):
                log_activity(
                    session.get('user_id'), 
                    'unauthorized_access_attempt', 
                    {'route': request.path, 'permission': permission},
                    'error'
                )
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
                
            # Log successful access
            log_activity(
                session.get('user_id'),
                'access_route',
                {'route': request.path, 'permission': permission}
            )
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requires_role(role):
    """Decorator to require a specific role for route access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not check_session_valid():
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login', next=request.url))
                
            user_role = session.get('role', None)
            
            if user_role != role and user_role != 'Administrator':  # Admins can access everything
                log_activity(
                    session.get('user_id'),
                    'unauthorized_role_attempt',
                    {'route': request.path, 'required_role': role, 'user_role': user_role},
                    'error'
                )
                flash(f'Only users with {role} role can access this page.', 'danger')
                return redirect(url_for('dashboard'))
                
            # Log successful access
            log_activity(
                session.get('user_id'),
                'access_route',
                {'route': request.path, 'role': role}
            )
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requires_login(f):
    """Decorator to require user login for route access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_session_valid():
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function 