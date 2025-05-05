#!/usr/bin/env python3
"""
User Management API - Enhanced functionality for the KEMRI Document Management System
This module provides API endpoints and utilities for user management operations.
"""

import sqlite3
import os
import json
import time
import random
import string
from datetime import datetime
from flask import Blueprint, request, jsonify, session, flash, redirect, url_for
from werkzeug.security import generate_password_hash

# Initialize blueprint
user_api = Blueprint('user_api', __name__)

def get_db_connection():
    """Create a connection to the SQLite database"""
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    return conn

def log_activity(user_id, action, details=None):
    """Log user activity in the system"""
    conn = get_db_connection()
    now = datetime.now()
    
    conn.execute(
        'INSERT INTO activity_log (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)',
        (user_id, action, json.dumps(details) if details else None, now)
    )
    conn.commit()
    conn.close()

@user_api.route('/api/users/search', methods=['GET'])
def search_users():
    """Search for users with filters"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    query = request.args.get('query', '')
    role = request.args.get('role', '')
    department = request.args.get('department', '')
    status = request.args.get('status', '')
    
    conn = get_db_connection()
    
    # Build the SQL query with filters
    sql = 'SELECT * FROM user WHERE 1=1'
    params = []
    
    if query:
        sql += ' AND (username LIKE ? OR email LIKE ?)'
        params.extend([f'%{query}%', f'%{query}%'])
    
    if role:
        sql += ' AND role = ?'
        params.append(role)
    
    if department:
        sql += ' AND department = ?'
        params.append(department)
    
    if status:
        is_active = 1 if status == 'active' else 0
        sql += ' AND is_active = ?'
        params.append(is_active)
    
    sql += ' ORDER BY username'
    
    users = conn.execute(sql, params).fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    result = []
    for user in users:
        result.append({
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'phone': user['phone'],
            'department': user['department'],
            'role': user['role'],
            'is_active': bool(user['is_active']),
            'created_at': user['created_at'],
            'last_login': user['last_login']
        })
    
    return jsonify(result)

@user_api.route('/api/users/create', methods=['POST'])
def create_user():
    """Create a new user via API"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Extract user data from request
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'User')
    department = data.get('department')
    phone = data.get('phone')
    
    if not username or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Generate password hash (in a real app)
    # hashed_password = generate_password_hash(password)
    # For debug app, just use plain password
    hashed_password = password
    
    conn = get_db_connection()
    
    # Check if user already exists
    existing = conn.execute(
        'SELECT id FROM user WHERE username = ? OR email = ?', 
        (username, email)
    ).fetchone()
    
    if existing:
        conn.close()
        return jsonify({'error': 'Username or email already exists'}), 409
    
    # Create the user
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user (username, email, password, role, department, phone, created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (username, email, hashed_password, role, department, phone, datetime.now(), True))
    
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    # Log activity
    log_activity(session.get('user_id'), 'create_user', {
        'new_user_id': user_id,
        'username': username,
        'email': email,
        'role': role
    })
    
    return jsonify({
        'id': user_id,
        'username': username,
        'message': 'User created successfully'
    }), 201

@user_api.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user details"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Convert to dictionary
    result = {
        'id': user['id'],
        'username': user['username'],
        'email': user['email'],
        'phone': user['phone'],
        'department': user['department'],
        'role': user['role'],
        'is_active': bool(user['is_active']),
        'created_at': user['created_at'],
        'last_login': user['last_login']
    }
    
    return jsonify(result)

@user_api.route('/api/users/bulk_status', methods=['POST'])
def bulk_update_status():
    """Update status for multiple users"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    user_ids = data.get('user_ids', [])
    is_active = data.get('is_active', True)
    
    if not user_ids:
        return jsonify({'error': 'No users specified'}), 400
    
    # Ensure current user is not deactivating themselves
    if not is_active and session.get('user_id') in user_ids:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400
    
    conn = get_db_connection()
    
    # Update statuses
    for user_id in user_ids:
        conn.execute(
            'UPDATE user SET is_active = ? WHERE id = ?',
            (1 if is_active else 0, user_id)
        )
    
    conn.commit()
    conn.close()
    
    # Log activity
    log_activity(session.get('user_id'), 'bulk_status_update', {
        'user_ids': user_ids,
        'status': 'active' if is_active else 'inactive'
    })
    
    return jsonify({
        'message': f'{len(user_ids)} users {"activated" if is_active else "deactivated"} successfully'
    })

@user_api.route('/api/users/bulk_delete', methods=['POST'])
def bulk_delete_users():
    """Delete multiple users"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    user_ids = data.get('user_ids', [])
    
    if not user_ids:
        return jsonify({'error': 'No users specified'}), 400
    
    # Ensure current user is not deleting themselves
    if session.get('user_id') in user_ids:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    conn = get_db_connection()
    
    # Delete users
    for user_id in user_ids:
        conn.execute('DELETE FROM user WHERE id = ?', (user_id,))
    
    conn.commit()
    conn.close()
    
    # Log activity
    log_activity(session.get('user_id'), 'bulk_delete_users', {
        'user_ids': user_ids
    })
    
    return jsonify({
        'message': f'{len(user_ids)} users deleted successfully'
    })

@user_api.route('/api/users/reset_passwords', methods=['POST'])
def bulk_reset_passwords():
    """Reset passwords for multiple users"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    user_ids = data.get('user_ids', [])
    send_email = data.get('send_email', False)
    
    if not user_ids:
        return jsonify({'error': 'No users specified'}), 400
    
    conn = get_db_connection()
    result = []
    
    # Reset passwords
    for user_id in user_ids:
        # Generate a random password
        new_password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
        
        # In a real app, you'd hash the password
        # hashed_password = generate_password_hash(new_password)
        hashed_password = new_password  # For debug app
        
        # Update the password
        conn.execute(
            'UPDATE user SET password = ? WHERE id = ?',
            (hashed_password, user_id)
        )
        
        # Get user info for the result
        user = conn.execute('SELECT username, email FROM user WHERE id = ?', (user_id,)).fetchone()
        
        if user:
            result.append({
                'id': user_id,
                'username': user['username'],
                'email': user['email'],
                'new_password': new_password,
                'email_sent': send_email
            })
    
    conn.commit()
    conn.close()
    
    # Log activity
    log_activity(session.get('user_id'), 'bulk_reset_passwords', {
        'user_ids': user_ids,
        'send_email': send_email
    })
    
    return jsonify({
        'message': f'Passwords reset for {len(result)} users',
        'users': result
    })

# Route to integrate this blueprint with the main app
def register_user_api(app):
    """Register the user API blueprint with the Flask app"""
    app.register_blueprint(user_api) 