from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response
import random
from datetime import datetime, timedelta
import os
import json
import string

app = Flask(__name__)
app.secret_key = 'debug-kemri-secret-key'

# Add application context processor for date functions
@app.context_processor
def inject_now():
    return {'now': datetime.now}

# File to store users
USERS_FILE = 'users.json'

# Helper function to load users from file
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # If file is corrupted, return empty list
            return []
    return []

# Helper function to save users to file
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, default=str)  # default=str handles datetime objects

# Home route
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

# Mock database functions
def get_mock_db_stats():
    return {
        'total_size': '324.5 MB',
        'tables': 12,
        'rows': 24768,
        'indexes': 32,
        'last_backup': datetime.now() - timedelta(days=1),
        'db_version': '5.2.0',
        'uptime': '32 days, 7 hours'
    }

def get_mock_tables():
    return [
        {
            'name': 'users',
            'rows': 156,
            'size': '2.4 MB',
            'last_updated': datetime.now() - timedelta(hours=3)
        },
        {
            'name': 'documents',
            'rows': 12453,
            'size': '156.7 MB',
            'last_updated': datetime.now() - timedelta(minutes=15)
        },
        {
            'name': 'activities',
            'rows': 9876,
            'size': '87.2 MB',
            'last_updated': datetime.now() - timedelta(minutes=5)
        },
        {
            'name': 'settings',
            'rows': 24,
            'size': '0.5 MB',
            'last_updated': datetime.now() - timedelta(days=5)
        },
        {
            'name': 'departments',
            'rows': 12,
            'size': '0.2 MB',
            'last_updated': datetime.now() - timedelta(days=30)
        }
    ]

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Mock user data
    user = {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'email': f"{session.get('username')}@example.com",
        'role': session.get('role', 'user'),
        'phone': '+1234567890',
        'department': 'IT Department',
        'is_active': True,
        'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Check if user is admin
    is_admin = session.get('role') == 'admin'
    
    # Mock dashboard data
    dashboard_data = {
        'total_documents': 1045,
        'pending_documents': 32,
        'completed_documents': 978,
        'recent_activity': [
            {
                'id': 1,
                'type': 'upload',
                'user': 'admin',
                'document': 'Report Q1 2025',
                'timestamp': '2025-04-12 14:30:22'
            },
            {
                'id': 2,
                'type': 'download',
                'user': 'user1',
                'document': 'Meeting Minutes',
                'timestamp': '2025-04-10 09:15:30'
            },
            {
                'id': 3,
                'type': 'share',
                'user': 'admin',
                'document': 'Strategic Plan 2025-2026',
                'timestamp': '2025-04-08 11:45:15'
            }
        ]
    }
    
    return render_template('dashboard.html', user=user, is_admin=is_admin, dashboard=dashboard_data)

@app.route('/track_document')
def track_document():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Mock user data
    user = {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'email': f"{session.get('username')}@example.com",
        'role': session.get('role'),
        'phone': '+1234567890',
        'department': 'IT Department',
        'is_active': True,
        'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Check if user is admin
    is_admin = session.get('role') == 'admin'
    
    # Mock document data
    recent_documents = [
        {
            'id': 1,
            'tracking_number': 'DOC-2025-001',
            'title': 'Sample Report 1',
            'status': 'In Progress',
            'created_at': '2025-04-10 09:15:30',
            'last_updated': '2025-04-12 14:30:22'
        },
        {
            'id': 2,
            'tracking_number': 'DOC-2025-002',
            'title': 'Sample Report 2',
            'status': 'Completed',
            'created_at': '2025-04-08 11:45:15',
            'last_updated': '2025-04-11 10:15:33'
        }
    ]
    
    return render_template('track_document.html', user=user, is_admin=is_admin, recent_documents=recent_documents, documents=recent_documents)

@app.route('/incoming')
def incoming():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Mock user data
    user = {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'email': f"{session.get('username')}@example.com",
        'role': session.get('role'),
        'phone': '+1234567890',
        'department': 'IT Department',
        'is_active': True,
        'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Check if user is admin
    is_admin = session.get('role') == 'admin'
    
    # Mock document data
    current_date = datetime.now()
    documents = [
        {
            'id': 1,
            'tracking_number': 'DOC-2025-001',
            'title': 'Sample Report 1',
            'status': 'Incoming',
            'priority': 'Urgent',
            'sender': 'Ministry of Health',
            'recipient': 'KEMRI Director',
            'created_at': '2025-04-10 09:15:30',
            'last_updated': '2025-04-12 14:30:22',
            'code': 'DOC-2025-001',
            'details': 'Quarterly report on infectious diseases',
            'required_action': 'Review and respond',
            'date_received': current_date - timedelta(days=2),
            'current_holder': 'Dr. Johnson'
        },
        {
            'id': 2,
            'tracking_number': 'DOC-2025-002',
            'title': 'Sample Report 2',
            'status': 'Pending',
            'priority': 'Normal',
            'sender': 'WHO',
            'recipient': 'Research Department',
            'created_at': '2025-04-08 11:45:15',
            'last_updated': '2025-04-11 10:15:33',
            'code': 'DOC-2025-002',
            'details': 'Regional health statistics',
            'required_action': 'File and archive',
            'date_received': current_date - timedelta(days=5),
            'current_holder': 'Dr. Smith'
        },
        {
            'id': 3,
            'tracking_number': 'DOC-2025-003',
            'title': 'Research Findings',
            'status': 'Received',
            'priority': 'Priority',
            'sender': 'Partner Lab',
            'recipient': 'Science Department',
            'created_at': '2025-04-05 14:22:10',
            'last_updated': '2025-04-07 09:45:20',
            'code': 'DOC-2025-003',
            'details': 'Latest findings from the malaria vaccine trial',
            'required_action': 'Urgent review needed',
            'date_received': current_date - timedelta(days=7),
            'current_holder': 'Dr. Williams'
        }
    ]
    
    # Mock filter data
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', 'All')
    priority_filter = request.args.get('priority', 'All')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Mock counts
    priority_counts = {
        'Urgent': 1,
        'Priority': 1,
        'Normal': 1
    }
    
    status_counts = {
        'Incoming': 1,
        'Pending': 1,
        'Received': 1
    }
    
    # Mock pagination
    pagination = {
        'page': 1,
        'per_page': 10,
        'total': 3,
        'pages': 1,
        'has_prev': False,
        'has_next': False,
        'prev_num': None,
        'next_num': None,
        'iter_pages': lambda left_edge=2, right_edge=2, left_current=2, right_current=3: [1]
    }
    
    return render_template('incoming.html', 
                          user=user, 
                          is_admin=is_admin, 
                          documents=documents,
                          search_query=search_query,
                          status_filter=status_filter,
                          priority_filter=priority_filter,
                          sort_by=sort_by,
                          sort_order=sort_order,
                          priority_counts=priority_counts,
                          status_counts=status_counts,
                          pagination=pagination)

@app.route('/outgoing')
def outgoing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Mock user data
    user = {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'email': f"{session.get('username')}@example.com",
        'role': session.get('role'),
        'phone': '+1234567890',
        'department': 'IT Department',
        'is_active': True,
        'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Check if user is admin
    is_admin = session.get('role') == 'admin'
    
    # Mock document data
    current_date = datetime.now()
    documents = [
        {
            'id': 1,
            'tracking_number': 'OUT-2025-001',
            'title': 'Response to Ministry',
            'status': 'Outgoing',
            'priority': 'Urgent',
            'sender': 'KEMRI Director',
            'recipient': 'Ministry of Health',
            'created_at': '2025-04-10 09:15:30',
            'last_updated': '2025-04-12 14:30:22',
            'code': 'OUT-2025-001',
            'details': 'Response to official inquiry',
            'required_action': 'Awaiting acknowledgment',
            'date_of_letter': current_date - timedelta(days=1),
            'current_holder': 'Dr. Johnson'
        },
        {
            'id': 2,
            'tracking_number': 'OUT-2025-002',
            'title': 'Research Proposal',
            'status': 'Sent',
            'priority': 'Normal',
            'sender': 'Research Department',
            'recipient': 'Partner University',
            'created_at': '2025-04-08 11:45:15',
            'last_updated': '2025-04-11 10:15:33',
            'code': 'OUT-2025-002',
            'details': 'Collaboration proposal for vaccine research',
            'required_action': 'Awaiting response',
            'date_of_letter': current_date - timedelta(days=4),
            'current_holder': 'Dr. Smith'
        },
        {
            'id': 3,
            'tracking_number': 'OUT-2025-003',
            'title': 'Quarterly Report',
            'status': 'Received',
            'priority': 'Priority',
            'sender': 'KEMRI Administration',
            'recipient': 'Board of Directors',
            'created_at': '2025-04-05 14:22:10',
            'last_updated': '2025-04-07 09:45:20',
            'code': 'OUT-2025-003',
            'details': 'Q1 2025 operational report',
            'required_action': 'For review and feedback',
            'date_of_letter': current_date - timedelta(days=6),
            'current_holder': 'Dr. Williams'
        }
    ]
    
    # Mock filter data
    search_query = request.args.get('search', '')
    priority_filter = request.args.get('priority', 'All')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Mock counts
    priority_counts = {
        'Urgent': 1,
        'Priority': 1,
        'Normal': 1
    }
    
    # Mock pagination
    pagination = {
        'page': 1,
        'per_page': 10,
        'total': 3,
        'pages': 1,
        'has_prev': False,
        'has_next': False,
        'prev_num': None,
        'next_num': None,
        'iter_pages': lambda left_edge=2, right_edge=2, left_current=2, right_current=3: [1]
    }
    
    return render_template('outgoing.html', 
                          user=user, 
                          is_admin=is_admin, 
                          documents=documents,
                          search_query=search_query,
                          priority_filter=priority_filter,
                          sort_by=sort_by,
                          sort_order=sort_order,
                          priority_counts=priority_counts,
                          pagination=pagination)

@app.route('/compose')
def compose():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Mock user data
    user = {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'email': f"{session.get('username')}@example.com",
        'role': session.get('role'),
        'phone': '+1234567890',
        'department': 'IT Department',
        'is_active': True,
        'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Check if user is admin
    is_admin = session.get('role') == 'admin'
    
    return render_template('compose.html', user=user, is_admin=is_admin, users=[])

@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Mock user data
    user = {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'email': f"{session.get('username')}@example.com",
        'role': session.get('role'),
        'phone': '+1234567890',
        'department': 'IT Department',
        'is_active': True,
        'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Check if user is admin
    is_admin = session.get('role') == 'admin'
    
    # Mock report data
    mock_status_data = {
        'Incoming': {
            'total': 45,
            'normal': 25,
            'priority': 12,
            'urgent': 8
        },
        'Pending': {
            'total': 32,
            'normal': 18,
            'priority': 10,
            'urgent': 4
        },
        'Received': {
            'total': 78,
            'normal': 51,
            'priority': 20,
            'urgent': 7
        },
        'Outgoing': {
            'total': 37,
            'normal': 26,
            'priority': 8,
            'urgent': 3
        },
        'Ended': {
            'total': 52,
            'normal': 38,
            'priority': 11,
            'urgent': 3
        }
    }
    
    # Mock average processing times
    mock_avg_times = {
        'Incoming': '2.5 days',
        'Pending': '4.3 days',
        'Received': '3.7 days',
        'Outgoing': '1.8 days',
        'Ended': '8.2 days'
    }
    
    # Mock chart data (will be used by JavaScript on the client)
    mock_chart_data = {
        'status_labels': ['Incoming', 'Pending', 'Received', 'Outgoing', 'Ended'],
        'status_counts': [45, 32, 78, 37, 52],
        'priority_labels': ['Normal', 'Priority', 'Urgent'],
        'priority_counts': [158, 61, 25]
    }
    
    # Mock activity data for timeline chart
    mock_activity_data = {
        'dates': [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, 0, -1)],
        'incoming_counts': [random.randint(0, 5) for _ in range(30)],
        'outgoing_counts': [random.randint(0, 4) for _ in range(30)]
    }
    
    # Mock user activity data
    mock_user_activity = {
        'users': ['admin', 'john.doe', 'jane.smith', 'mike.jones', 'sarah.brown'],
        'processed_counts': [random.randint(10, 50) for _ in range(5)]
    }
    
    # Mock filter settings
    mock_filters = {
        'date_range': 'last-7-days',
        'type': 'all',
        'status': 'all',
        'priority': 'all'
    }
    
    # Mock document statistics summary
    mock_document_stats = {
        'total_documents': sum(mock_status_data[status]['total'] for status in mock_status_data),
        'documents_added_today': random.randint(3, 8),
        'documents_processed_today': random.randint(5, 12),
        'average_processing_time': '3.5 days'
    }
    
    # Return template with mock data
    return render_template('reports.html',
                          user=user,
                          is_admin=is_admin,
                          status_data=mock_status_data,
                          avg_times=mock_avg_times,
                          chart_data=mock_chart_data,
                          activity_data=mock_activity_data,
                          user_activity=mock_user_activity,
                          filters=mock_filters,
                          stats=mock_document_stats,
                          active_page='reports')

@app.route('/api/reports_data', methods=['GET'])
def reports_data():
    """API endpoint to provide report data for AJAX requests"""
    report_type = request.args.get('type', 'document-summary')
    date_range = request.args.get('date_range', 'last-7-days')
    
    # Mock data based on report type
    if report_type == 'document-summary':
        data = {
            'status_data': {
                'Incoming': {'total': 45, 'normal': 25, 'priority': 12, 'urgent': 8},
                'Pending': {'total': 32, 'normal': 18, 'priority': 10, 'urgent': 4},
                'Received': {'total': 78, 'normal': 51, 'priority': 20, 'urgent': 7},
                'Outgoing': {'total': 37, 'normal': 26, 'priority': 8, 'urgent': 3},
                'Ended': {'total': 52, 'normal': 38, 'priority': 11, 'urgent': 3}
            },
            'chart_data': {
                'status_labels': ['Incoming', 'Pending', 'Received', 'Outgoing', 'Ended'],
                'status_counts': [45, 32, 78, 37, 52],
                'priority_labels': ['Normal', 'Priority', 'Urgent'],
                'priority_counts': [158, 61, 25]
            }
        }
    elif report_type == 'activity-analysis':
        data = {
            'dates': [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, 0, -1)],
            'incoming_counts': [random.randint(0, 5) for _ in range(30)],
            'outgoing_counts': [random.randint(0, 4) for _ in range(30)]
        }
    elif report_type == 'user-activity':
        data = {
            'users': ['admin', 'john.doe', 'jane.smith', 'mike.jones', 'sarah.brown'],
            'processed_counts': [random.randint(10, 50) for _ in range(5)]
        }
    elif report_type == 'status-report':
        data = {
            'status_progression': {
                'Incoming': {'to_pending': 28, 'to_received': 3, 'to_outgoing': 0, 'to_ended': 0},
                'Pending': {'to_received': 22, 'to_outgoing': 5, 'to_ended': 1},
                'Received': {'to_outgoing': 62, 'to_ended': 10},
                'Outgoing': {'to_ended': 31}
            },
            'avg_times': {
                'Incoming': '2.5 days',
                'Pending': '4.3 days',
                'Received': '3.7 days',
                'Outgoing': '1.8 days',
                'Ended': '8.2 days'
            }
        }
    else:
        data = {'error': 'Invalid report type'}
    
    return jsonify(data)

@app.route('/maintenance')
def maintenance():
    # Mock maintenance statistics for the template
    mock_stats = {
        "cpu_usage": f"{random.randint(5, 30)}%",
        "memory_usage": f"{random.randint(20, 60)}%",
        "disk_usage": f"{random.randint(10, 70)}%",
        "system_uptime": "7 days, 14 hours, 23 minutes",
        "active_users": random.randint(1, 10),
        "open_files": random.randint(10, 50)
    }
    
    # Add new mock data for enhanced maintenance page
    mock_users = [
        {"username": "admin", "last_login": "2025-04-12 09:15 AM", "status": "Active"},
        {"username": "john.doe", "last_login": "2025-04-11 14:30 PM", "status": "Active"},
        {"username": "jane.smith", "last_login": "2025-04-12 08:45 AM", "status": "Active"},
        {"username": "guest", "last_login": "2025-04-10 11:20 AM", "status": "Inactive"}
    ]
    
    mock_logs = [
        {"timestamp": "2025-04-12 10:15:23", "level": "INFO", "message": "System backup completed successfully"},
        {"timestamp": "2025-04-12 09:30:45", "level": "WARNING", "message": "High memory usage detected (65%)"},
        {"timestamp": "2025-04-12 08:45:12", "level": "INFO", "message": "User 'admin' logged in"},
        {"timestamp": "2025-04-12 08:30:56", "level": "ERROR", "message": "Failed to connect to email server"},
        {"timestamp": "2025-04-12 07:15:30", "level": "INFO", "message": "Daily maintenance tasks started"}
    ]
    
    mock_storage = {
        "total": "500 GB",
        "used": "125 GB",
        "free": "375 GB",
        "document_storage": "80 GB",
        "system_storage": "30 GB",
        "backup_storage": "15 GB"
    }
    
    mock_performance = {
        "avg_response_time": "120 ms",
        "daily_requests": random.randint(5000, 15000),
        "peak_time": "10:00 AM - 11:00 AM",
        "slow_queries": random.randint(0, 5)
    }
    
    # Get data from our new mock functions
    scheduled_tasks = get_scheduled_tasks()
    database_backups = get_database_backups()
    system_health = get_system_health()
    
    # Include active_page for navigation highlighting
    return render_template('maintenance.html', 
                          active_page='maintenance',
                          maintenance_stats=mock_stats,
                          users=mock_users,
                          system_logs=mock_logs,
                          storage_info=mock_storage,
                          performance_data=mock_performance,
                          scheduled_tasks=scheduled_tasks,
                          database_backups=database_backups,
                          system_health=system_health)

@app.route('/maintenance_action', methods=['POST'])
def maintenance_action():
    action = request.form.get('action')
    
    # Handle various maintenance actions
    if action == 'backup':
        flash('Database backup created successfully!', 'success')
    elif action == 'optimize':
        flash('Database optimization completed successfully!', 'success')
    elif action == 'vacuum_db':
        flash('Database vacuum process completed successfully!', 'success')
    elif action == 'restart':
        flash('System restart initiated. The server will be back online shortly.', 'warning')
    elif action == 'clear_cache':
        flash('Cache cleared successfully!', 'success')
    elif action == 'security_scan':
        flash('Security scan completed. No vulnerabilities found.', 'success')
    elif action == 'check_integrity':
        flash('Database integrity check completed. No issues found.', 'success')
    elif action == 'export_logs':
        flash('System logs exported successfully!', 'success')
    elif action == 'purge_temp':
        flash('Temporary files purged successfully!', 'success')
    elif action == 'run_task':
        task_name = request.form.get('task_name')
        flash(f'Task "{task_name}" executed successfully!', 'success')
    elif action == 'delete_task':
        task_name = request.form.get('task_name')
        flash(f'Task "{task_name}" deleted successfully!', 'success')
    elif action == 'restore_backup':
        backup_name = request.form.get('backup_name')
        flash(f'Database restored from backup "{backup_name}" successfully!', 'success')
    elif action == 'delete_backup':
        backup_name = request.form.get('backup_name')
        flash(f'Backup "{backup_name}" deleted successfully!', 'success')
    else:
        flash('Unknown maintenance action requested.', 'danger')
    
    return redirect(url_for('maintenance'))

@app.route('/user_management')
def user_management():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # For demo purposes, set is_admin to True for all users
    is_admin = True
    
    # Load users from file
    file_users = load_users()
    
    # Initialize session user list if it doesn't exist
    if 'users_list' not in session:
        # Create some mock users if there are none
        if not file_users:
            mock_users = [
                {
                    'id': 1,
                    'name': 'Admin User',
                    'email': 'admin@kemri.org',
                    'phone': '+254712345678',
                    'department': 'Administration',
                    'role': 'Administrator',
                    'status': 'active',
                    'created_at': datetime.now().replace(tzinfo=None),
                    'last_login': (datetime.now() - timedelta(days=2)).replace(tzinfo=None),
                    'login_count': 45,
                    'password': 'admin'  # Default password for demo
                },
                {
                    'id': 2,
                    'name': 'Lab Technician',
                    'email': 'lab.tech@kemri.org',
                    'phone': '+254723456789',
                    'department': 'Laboratory',
                    'role': 'Lab Technician',
                    'status': 'active',
                    'created_at': datetime.now().replace(tzinfo=None),
                    'last_login': (datetime.now() - timedelta(hours=5)).replace(tzinfo=None),
                    'login_count': 28,
                    'password': 'password'  # Default password for demo
                },
                {
                    'id': 3,
                    'name': 'Researcher',
                    'email': 'researcher@kemri.org',
                    'phone': '+254734567890',
                    'department': 'Research',
                    'role': 'Researcher',
                    'status': 'inactive',
                    'created_at': datetime.now().replace(tzinfo=None),
                    'last_login': (datetime.now() - timedelta(days=30)).replace(tzinfo=None),
                    'login_count': 12,
                    'password': 'password'  # Default password for demo
                }
            ]
            session['users_list'] = mock_users
            save_users(mock_users)  # Save initial mock users to file
        else:
            # Make sure all datetime objects are timezone-naive
            for user in file_users:
                if isinstance(user.get('created_at'), datetime):
                    user['created_at'] = user['created_at'].replace(tzinfo=None)
                if isinstance(user.get('last_login'), datetime):
                    user['last_login'] = user['last_login'].replace(tzinfo=None)
            session['users_list'] = file_users
    
    # Get users from session
    users = session.get('users_list', [])
    
    # Define available departments and roles for dropdowns
    departments = ['Administration', 'Laboratory', 'Research', 'IT', 'Finance', 'HR']
    roles = ['Administrator', 'Manager', 'Lab Technician', 'Researcher', 'Data Entry', 'User']
    
    # Calculate user statistics
    stats = {
        'total': len(users),
        'active': sum(1 for user in users if user.get('status') == 'active'),
        'inactive': sum(1 for user in users if user.get('status') == 'inactive'),
        'admin': sum(1 for user in users if user.get('role') == 'Administrator')
    }
    
    return render_template('user_management.html', 
                           users=users, 
                           departments=departments, 
                           roles=roles, 
                           is_admin=is_admin,
                           stats=stats)

@app.route('/add_user', methods=['POST'])
def add_user():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # For demo purposes, allow all users to add new users
    
    # Get form data
    name = request.form.get('fullName')
    email = request.form.get('email')
    phone = request.form.get('phone', '')
    department = request.form.get('department')
    role = request.form.get('role')
    status = 'active' if request.form.get('status') == 'on' else 'inactive'
    password = request.form.get('password')
    send_email = request.form.get('sendWelcome') == 'on'
    
    # Validate required fields
    if not all([name, email, department, role, password]):
        flash('All required fields must be filled out', 'danger')
        return redirect(url_for('user_management'))
    
    # Load existing users
    users = session.get('users_list', [])
    
    # Check if email already exists
    if any(user['email'] == email for user in users):
        flash('A user with this email already exists', 'danger')
        return redirect(url_for('user_management'))
    
    # Create new user with timezone-naive datetime
    new_user = {
        'id': max([user.get('id', 0) for user in users], default=0) + 1,
        'name': name,
        'email': email,
        'phone': phone,
        'department': department,
        'role': role,
        'status': status,
        'created_at': datetime.now().replace(tzinfo=None),
        'last_login': None,
        'login_count': 0,
        'password': password  # Store password for demo purposes
    }
    
    # Add user to list
    users.append(new_user)
    
    # Update session
    session['users_list'] = users
    
    # Save to file
    save_users(users)
    
    # In a real app, you would hash the password and potentially send a welcome email
    if send_email:
        # Simulate email sending
        print(f"Sending welcome email to {email}")
    
    flash('User added successfully', 'success')
    return redirect(url_for('user_management'))

@app.route('/quick_add_user', methods=['POST'])
def quick_add_user():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check permission
    if not current_user_has_permission('admin'):
        flash('You do not have permission to add users.', 'danger')
        return redirect(url_for('user_management'))
    
    # Get form data
    name = request.form.get('name')
    email = request.form.get('email')
    department = request.form.get('department')
    password = request.form.get('password')
    
    # Validate required fields
    if not all([name, email, department, password]):
        flash('All required fields must be filled out', 'danger')
        return redirect(url_for('user_management'))
    
    # Load existing users
    users = session.get('users_list', [])
    
    # Check if email already exists
    if any(user['email'] == email for user in users):
        flash('A user with this email already exists', 'danger')
        return redirect(url_for('user_management'))
    
    # Create new user with default values
    new_user = {
        'id': max([user.get('id', 0) for user in users], default=0) + 1,
        'name': name,
        'email': email,
        'phone': '',
        'department': department,
        'role': 'User',  # Default role
        'status': 'active',
        'created_at': datetime.now().replace(tzinfo=None),
        'last_login': None,
        'login_count': 0,
        'password': password  # Store password for demo purposes
    }
    
    # Add user to list
    users.append(new_user)
    
    # Update session
    session['users_list'] = users
    
    # Save to file
    save_users(users)
    
    flash('User added successfully', 'success')
    return redirect(url_for('user_management'))

@app.route('/edit_user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check permission
    if not current_user_has_permission('admin'):
        flash('You do not have permission to edit users.', 'danger')
        return redirect(url_for('user_management'))
    
    # Get form data
    name = request.form.get('fullName')
    email = request.form.get('email')
    phone = request.form.get('phone', '')
    department = request.form.get('department')
    role = request.form.get('role')
    status = 'active' if request.form.get('status') == 'on' else 'inactive'
    notify_user = request.form.get('notifyUser') == 'on'
    
    # Validate required fields
    if not all([name, email, department, role]):
        flash('All required fields must be filled out', 'danger')
        return redirect(url_for('user_management'))
    
    # Load existing users
    users = session.get('users_list', [])
    
    # Find user by ID
    user_found = False
    for user in users:
        if user.get('id') == user_id:
            # Check if email already exists (but not for this user)
            if email != user['email'] and any(u['email'] == email for u in users):
                flash('A user with this email already exists', 'danger')
                return redirect(url_for('user_management'))
            
            # Update user
            user['name'] = name
            user['email'] = email
            user['phone'] = phone
            user['department'] = department
            user['role'] = role
            user['status'] = status
            user_found = True
            break
    
    if not user_found:
        flash('User not found', 'danger')
        return redirect(url_for('user_management'))
    
    # Update session
    session['users_list'] = users
    
    # Save to file
    save_users(users)
    
    # Notify user if requested
    if notify_user:
        # Simulate notification
        print(f"Sending update notification to {email}")
    
    flash('User updated successfully', 'success')
    return redirect(url_for('user_management'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # For demo purposes, allow all users to delete users
    
    # Load existing users
    users = session.get('users_list', [])
    
    # Find and delete user
    for i, user in enumerate(users):
        if user.get('id') == user_id:
            del users[i]
            break
    
    # Update session
    session['users_list'] = users
    
    # Save to file
    save_users(users)
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('user_management'))

@app.route('/reset_password/<int:user_id>', methods=['POST'])
def reset_password(user_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check permission
    if not current_user_has_permission('admin'):
        flash('You do not have permission to reset passwords.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Load existing users
    users = session.get('users_list', [])
    
    # Find user
    user_email = None
    for user in users:
        if user.get('id') == user_id:
            user_email = user.get('email')
            break
    
    if not user_email:
        flash('User not found', 'danger')
        return redirect(url_for('user_management'))
    
    # In a real app, you would generate a secure reset link and send it to the user
    # For this demo, we'll just simulate the process
    
    flash('Password reset link has been sent to the user', 'success')
    return redirect(url_for('user_management'))

@app.route('/toggle_user_status/<int:user_id>', methods=['POST'])
def toggle_user_status(user_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check permission
    if not current_user_has_permission('admin'):
        flash('You do not have permission to change user status.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Load existing users
    users = session.get('users_list', [])
    
    # Find user and toggle status
    for user in users:
        if user.get('id') == user_id:
            user['status'] = 'inactive' if user.get('status') == 'active' else 'active'
            new_status = user['status']
            break
    
    # Update session
    session['users_list'] = users
    
    # Save to file
    save_users(users)
    
    flash(f'User status changed to {new_status}', 'success')
    return redirect(url_for('user_management'))

@app.route('/bulk_user_action', methods=['POST'])
def bulk_user_action():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # For demo purposes, allow all users to perform bulk actions
    
    # Get action type and user IDs
    action = request.form.get('action')
    user_ids_str = request.form.get('user_ids', '')
    
    # Parse user IDs
    try:
        user_ids = [int(id) for id in user_ids_str.split(',') if id]
    except ValueError:
        flash('Invalid user IDs', 'danger')
        return redirect(url_for('user_management'))
    
    if not user_ids:
        flash('No users selected', 'warning')
        return redirect(url_for('user_management'))
    
    # Load existing users
    users = session.get('users_list', [])
    
    # Process based on action
    if action == 'activate':
        # Activate users
        for user in users:
            if user.get('id') in user_ids:
                user['status'] = 'active'
        flash(f'{len(user_ids)} users activated', 'success')
    
    elif action == 'deactivate':
        # Deactivate users
        for user in users:
            if user.get('id') in user_ids:
                user['status'] = 'inactive'
        flash(f'{len(user_ids)} users deactivated', 'success')
    
    elif action == 'delete':
        # Delete users
        users = [user for user in users if user.get('id') not in user_ids]
        flash(f'{len(user_ids)} users deleted', 'success')
    
    elif action == 'assign-role':
        # Assign role
        role = request.form.get('role')
        notify = request.form.get('notify_users') == 'on'
        
        if not role:
            flash('No role selected', 'danger')
            return redirect(url_for('user_management'))
        
        for user in users:
            if user.get('id') in user_ids:
                user['role'] = role
                if notify:
                    # Simulate notification
                    print(f"Sending role update notification to {user['email']}")
        
        flash(f'{len(user_ids)} users assigned to role: {role}', 'success')
    
    elif action == 'assign-department':
        # Assign department
        department = request.form.get('department')
        notify = request.form.get('notify_users') == 'on'
        
        if not department:
            flash('No department selected', 'danger')
            return redirect(url_for('user_management'))
        
        for user in users:
            if user.get('id') in user_ids:
                user['department'] = department
                if notify:
                    # Simulate notification
                    print(f"Sending department update notification to {user['email']}")
        
        flash(f'{len(user_ids)} users assigned to department: {department}', 'success')
    
    else:
        flash('Invalid action', 'danger')
        return redirect(url_for('user_management'))
    
    # Update session
    session['users_list'] = users
    
    # Save to file
    save_users(users)
    
    return redirect(url_for('user_management'))

@app.route('/send_notification/<int:user_id>', methods=['POST'])
def send_notification(user_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check permission
    if not current_user_has_permission('admin'):
        flash('You do not have permission to send notifications.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get form data
    notification_type = request.form.get('notification_type')
    message = request.form.get('message')
    send_email = request.form.get('send_email') == 'on'
    
    if not all([notification_type, message]):
        flash('Type and message are required', 'danger')
        return redirect(url_for('user_management'))
    
    # Load existing users
    users = session.get('users_list', [])
    
    # For bulk notifications
    if user_id == 0:
        user_ids_str = request.form.get('user_ids', '')
        try:
            user_ids = [int(id) for id in user_ids_str.split(',') if id]
        except ValueError:
            flash('Invalid user IDs', 'danger')
            return redirect(url_for('user_management'))
        
        if not user_ids:
            flash('No users selected', 'warning')
            return redirect(url_for('user_management'))
        
        # Get list of emails for selected users
        target_users = [user for user in users if user.get('id') in user_ids]
        
        # Simulate sending notifications
        for user in target_users:
            print(f"Sending {notification_type} notification to {user['email']}: {message}")
        
        flash(f'Notification sent to {len(target_users)} users', 'success')
    
    # For single user notification
    else:
        user_found = False
        for user in users:
            if user.get('id') == user_id:
                print(f"Sending {notification_type} notification to {user['email']}: {message}")
                user_found = True
                break
        
        if not user_found:
            flash('User not found', 'danger')
            return redirect(url_for('user_management'))
        
        flash('Notification sent', 'success')
    
    return redirect(url_for('user_management'))

@app.route('/export_users', methods=['POST'])
def export_users():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check permission
    if not current_user_has_permission('admin'):
        flash('You do not have permission to export users.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get user IDs if provided (for bulk export)
    user_ids_str = request.form.get('user_ids', '')
    
    # Load users
    users = session.get('users_list', [])
    
    # Filter users if IDs provided
    if user_ids_str:
        try:
            user_ids = [int(id) for id in user_ids_str.split(',') if id]
            users = [user for user in users if user.get('id') in user_ids]
        except ValueError:
            flash('Invalid user IDs', 'danger')
            return redirect(url_for('user_management'))
    
    # Create CSV data
    csv_data = "Name,Email,Department,Role,Status,Phone,Created Date,Last Login\n"
    
    for user in users:
        created_at = user.get('created_at', '')
        if isinstance(created_at, datetime):
            created_at = created_at.strftime('%Y-%m-%d')
        
        last_login = user.get('last_login', '')
        if isinstance(last_login, datetime):
            last_login = last_login.strftime('%Y-%m-%d %H:%M')
        elif last_login is None:
            last_login = 'Never'
        
        csv_data += f"{user.get('name', '')},{user.get('email', '')},{user.get('department', '')},"
        csv_data += f"{user.get('role', '')},{user.get('status', '')},{user.get('phone', '')},"
        csv_data += f"{created_at},{last_login}\n"
    
    # Create response
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=users_export.csv"
    response.headers["Content-Type"] = "text/csv"
    
    return response

@app.route('/import_users', methods=['POST'])
def import_users():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check permission
    if not current_user_has_permission('admin'):
        flash('You do not have permission to import users.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if file was uploaded
    if 'csvFile' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('user_management'))
    
    file = request.files['csvFile']
    
    # Check if file is empty
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('user_management'))
    
    # Check file extension
    if not file.filename.endswith('.csv'):
        flash('File must be a CSV', 'danger')
        return redirect(url_for('user_management'))
    
    # Get other form data
    skip_header = request.form.get('skipHeader') == 'on'
    send_email = request.form.get('sendWelcome') == 'on'
    
    try:
        # Read file content
        content = file.read().decode('utf-8')
        lines = content.splitlines()
        
        # Skip header if requested
        if skip_header and lines:
            lines = lines[1:]
        
        # Load existing users
        users = session.get('users_list', [])
        next_id = max([user.get('id', 0) for user in users], default=0) + 1
        
        # Process each line
        imported_count = 0
        skipped_count = 0
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Parse CSV line
            parts = line.split(',')
            
            # Check minimum required fields
            if len(parts) < 3:
                skipped_count += 1
                continue
            
            name = parts[0].strip()
            email = parts[1].strip()
            department = parts[2].strip()
            
            # Skip if missing required fields
            if not all([name, email, department]):
                skipped_count += 1
                continue
            
            # Check if email already exists
            if any(user['email'] == email for user in users):
                skipped_count += 1
                continue
            
            # Get optional fields
            role = parts[3].strip() if len(parts) > 3 else 'User'
            status = parts[4].strip() if len(parts) > 4 else 'active'
            phone = parts[5].strip() if len(parts) > 5 else ''
            password = parts[6].strip() if len(parts) > 6 else 'password123'  # Default password
            
            # Validate status
            if status not in ['active', 'inactive']:
                status = 'active'
            
            # Create new user
            new_user = {
                'id': next_id,
                'name': name,
                'email': email,
                'department': department,
                'role': role,
                'status': status,
                'phone': phone,
                'created_at': datetime.now().replace(tzinfo=None),
                'last_login': None,
                'login_count': 0,
                'password': password
            }
            
            # Add user
            users.append(new_user)
            next_id += 1
            imported_count += 1
            
            # Send welcome email if requested
            if send_email:
                # Simulate email sending
                print(f"Sending welcome email to {email}")
        
        # Update session
        session['users_list'] = users
        
        # Save to file
        save_users(users)
        
        flash(f'Successfully imported {imported_count} users. Skipped {skipped_count} entries.', 'success')
    
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'danger')
    
    return redirect(url_for('user_management'))

# Helper function to check user permissions
def current_user_has_permission(required_role=None):
    """Check if the current user has the required role/permission."""
    # In a real app, this would check against the user's actual role
    if 'user_role' not in session:
        return False
    
    # For admin role checks
    if required_role == 'admin':
        return session.get('user_role') == 'Administrator'
    
    # For specific role checks
    if required_role and session.get('user_role') != required_role:
        return False
    
    return True

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check for admin credentials first (for demo)
        if username == 'admin' and password == 'admin':
            session['logged_in'] = True
            session['username'] = 'Admin User'
            session['user_id'] = 1
            session['user_role'] = 'Administrator'
            flash('Welcome, Admin!', 'success')
            return redirect(url_for('dashboard'))
        
        # Check for normal user login
        users = load_users()
        for user in users:
            if user.get('email') == username:
                # In a real app, you would hash and check the password properly
                # For demo purposes, we'll just check the raw password
                if 'password' in user and user['password'] == password:
                    session['logged_in'] = True
                    session['username'] = user.get('name')
                    session['user_id'] = user.get('id')
                    session['user_role'] = user.get('role', 'User')
                    
                    # Update last login time
                    user['last_login'] = datetime.now().replace(tzinfo=None)
                    user['login_count'] = user.get('login_count', 0) + 1
                    save_users(users)
                    
                    flash(f'Welcome, {user.get("name")}!', 'success')
                    return redirect(url_for('dashboard'))
        
        flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout the current user"""
    # Clear session
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.context_processor
def utility_processor():
    def now():
        # Ensure we always return a timezone-naive datetime
        return datetime.now().replace(tzinfo=None)
    return dict(now=now)

@app.route('/incoming_bulk_action', methods=['POST'])
def incoming_bulk_action():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get form data
    bulk_action = request.form.get('bulk_action', '')
    document_ids = request.form.getlist('document_ids[]')
    
    # Process the bulk action (this is just a mock)
    if bulk_action == 'mark_pending':
        flash(f'Marked {len(document_ids)} documents as Pending', 'success')
    elif bulk_action == 'mark_received':
        flash(f'Marked {len(document_ids)} documents as Received', 'success')
    elif bulk_action == 'print':
        flash(f'Prepared {len(document_ids)} documents for printing', 'info')
    
    return redirect(url_for('incoming'))

@app.route('/update_incoming_status/<doc_code>', methods=['POST'])
def update_incoming_status(doc_code):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get the new status from form
    new_status = request.form.get('status', '')
    
    # Process the status update (this is just a mock)
    status_messages = {
        'Pending': 'Document marked as Pending',
        'Received': 'Document marked as Received',
        'Outgoing': 'Document moved to Outgoing',
        'Ended': 'Document marked as Ended'
    }
    
    if new_status in status_messages:
        flash(f"{status_messages[new_status]}: {doc_code}", 'success')
    
    return redirect(url_for('incoming'))

@app.route('/outgoing_bulk_action', methods=['POST'])
def outgoing_bulk_action():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get form data
    bulk_action = request.form.get('bulk_action', '')
    document_ids = request.form.getlist('document_ids[]')
    
    # Process the bulk action (this is just a mock)
    if bulk_action == 'mark_sent':
        flash(f'Marked {len(document_ids)} documents as Sent', 'success')
    elif bulk_action == 'mark_received':
        flash(f'Marked {len(document_ids)} documents as Received', 'success')
    elif bulk_action == 'print':
        flash(f'Prepared {len(document_ids)} documents for printing', 'info')
    
    return redirect(url_for('outgoing'))

@app.route('/update_outgoing_status/<doc_code>', methods=['POST'])
def update_outgoing_status(doc_code):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get the new status from form
    new_status = request.form.get('status', '')
    
    # Process the status update (this is just a mock)
    status_messages = {
        'Sent': 'Document marked as Sent',
        'Received': 'Document marked as Received',
        'Ended': 'Document marked as Ended'
    }
    
    if new_status in status_messages:
        flash(f"{status_messages[new_status]}: {doc_code}", 'success')
    
    return redirect(url_for('outgoing'))

# Mock data for maintenance page
def get_scheduled_tasks():
    return [
        {
            "name": "Database Backup",
            "schedule": "Daily at 01:00 AM",
            "last_run": "2025-04-11 01:00 AM",
            "status": "Completed"
        },
        {
            "name": "System Log Rotation",
            "schedule": "Daily at 02:00 AM",
            "last_run": "2025-04-11 02:00 AM",
            "status": "Completed"
        },
        {
            "name": "Storage Cleanup",
            "schedule": "Weekly on Sunday",
            "last_run": "2025-04-07 03:00 AM",
            "status": "Completed"
        },
        {
            "name": "Performance Optimization",
            "schedule": "Monthly on 1st",
            "last_run": "2025-04-01 04:00 AM",
            "status": "Completed"
        }
    ]

def get_database_backups():
    return [
        {
            "filename": "backup_2025-04-11.db",
            "date": "2025-04-11 01:00 AM",
            "size": "12.5 MB",
            "user": "System"
        },
        {
            "filename": "backup_2025-04-10.db",
            "date": "2025-04-10 01:00 AM",
            "size": "12.3 MB",
            "user": "System"
        },
        {
            "filename": "manual_backup_2025-04-09.db",
            "date": "2025-04-09 15:32 PM",
            "size": "12.2 MB",
            "user": "admin"
        },
        {
            "filename": "backup_2025-04-08.db",
            "date": "2025-04-08 01:00 AM",
            "size": "11.8 MB",
            "user": "System"
        }
    ]

def get_system_health():
    return {
        "cpu_usage": f"{random.randint(10, 40)}%",
        "memory_usage": f"{random.randint(30, 70)}%",
        "disk_usage": f"{random.randint(20, 80)}%",
        "uptime": "7 days, 12 hours",
        "last_reboot": (datetime.now() - timedelta(days=7, hours=12)).strftime("%Y-%m-%d %H:%M")
    }

# Database management routes
@app.route('/database_management')
def database_management():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # For demo purposes, allow all users
    
    # Get mock database stats and tables
    db_stats = get_mock_db_stats()
    tables = get_mock_tables()
    
    return render_template('database_management.html', 
                          db_stats=db_stats, 
                          tables=tables)

@app.route('/database_integrity')
def database_integrity():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # For demo purposes, allow all users
    
    # Mock integrity data
    integrity_checks = [
        {'type': 'Foreign Key', 'table': 'documents', 'status': 'Passed', 'timestamp': datetime.now() - timedelta(hours=1)},
        {'type': 'Index Check', 'table': 'users', 'status': 'Passed', 'timestamp': datetime.now() - timedelta(hours=1)},
        {'type': 'Data Consistency', 'table': 'activities', 'status': 'Passed', 'timestamp': datetime.now() - timedelta(hours=1)}
    ]
    
    return render_template('database_integrity.html', 
                          integrity_checks=integrity_checks)

@app.route('/database_logs')
def database_logs():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # For demo purposes, allow all users
    
    # Mock logs data
    logs = [
        {'type': 'Backup', 'details': 'Full backup completed', 'status': 'Success', 'timestamp': datetime.now() - timedelta(hours=2)},
        {'type': 'Vacuum', 'details': 'Vacuum on users table', 'status': 'Success', 'timestamp': datetime.now() - timedelta(days=1)},
        {'type': 'Schema Update', 'details': 'Added column to documents table', 'status': 'Success', 'timestamp': datetime.now() - timedelta(days=3)}
    ]
    
    return render_template('database_logs.html', 
                          logs=logs)

@app.route('/backup_database', methods=['POST'])
def backup_database():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # For demo purposes, allow all users
    
    # Mock backup creation
    flash('Database backup created successfully.', 'success')
    return redirect(url_for('database_management'))

@app.route('/restore_database', methods=['POST'])
def restore_database():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # For demo purposes, allow all users
    
    # Mock database restoration
    flash('Database restored successfully from backup.', 'success')
    return redirect(url_for('database_management'))

@app.route('/my_account')
def my_account():
    """Route for user account page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get current user info
    user_id = session.get('user_id')
    
    # Mock user data - in a real app, fetch from database
    if user_id == 1:
        user = {
            'id': 1, 
            'name': 'John Admin', 
            'email': 'admin@example.com',
            'role': 'Administrator',
            'department': 'IT Department',
            'created_at': datetime.now() - timedelta(days=80),
            'last_login': datetime.now() - timedelta(hours=1),
            'status': 'active',
            'phone': '+254123456789',
            'login_count': 42,
            'profile_image': '/static/img/avatars/admin.jpg',
            'bio': 'System administrator responsible for managing the laboratory system.',
            'joined_date': datetime.now() - timedelta(days=80),
            'permissions': ['full_access', 'admin_panel', 'user_management', 'system_configuration']
        }
    else:
        # Generic user profile for any other ID
        user = {
            'id': user_id, 
            'name': f'User {user_id}', 
            'email': f'user{user_id}@example.com',
            'role': 'Lab Technician' if user_id % 2 == 0 else 'Researcher',
            'department': 'Research' if user_id % 2 == 0 else 'Lab Operations',
            'created_at': datetime.now() - timedelta(days=user_id * 10),
            'last_login': datetime.now() - timedelta(hours=user_id * 2),
            'status': 'active',
            'phone': f'+2541234{user_id:05d}',
            'login_count': user_id * 5,
            'profile_image': f'/static/img/avatars/user{user_id % 5 + 1}.jpg',
            'bio': f'User with ID {user_id} - mock biography information.',
            'joined_date': datetime.now() - timedelta(days=user_id * 10),
            'permissions': ['view_reports', 'edit_profile']
        }
    
    # Mock login history
    login_history = [
        {'timestamp': datetime.now() - timedelta(hours=1), 'ip': '192.168.1.100', 'device': 'Chrome on Windows'},
        {'timestamp': datetime.now() - timedelta(days=1), 'ip': '192.168.1.101', 'device': 'Safari on macOS'},
        {'timestamp': datetime.now() - timedelta(days=2), 'ip': '192.168.1.102', 'device': 'Firefox on Linux'},
        {'timestamp': datetime.now() - timedelta(days=3), 'ip': '192.168.1.103', 'device': 'Chrome on Android'},
    ]
    
    # Mock recent activity
    recent_activity = [
        {'timestamp': datetime.now() - timedelta(minutes=30), 'action': 'Logged in', 'details': 'Successful login from 192.168.1.100'},
        {'timestamp': datetime.now() - timedelta(hours=2), 'action': 'Updated profile', 'details': 'Changed phone number'},
        {'timestamp': datetime.now() - timedelta(hours=5), 'action': 'Ran report', 'details': 'Generated monthly activity report'},
        {'timestamp': datetime.now() - timedelta(days=1), 'action': 'Created document', 'details': 'Added new research protocol'},
    ]
    
    return render_template('user_profile.html', 
                          user=user, 
                          login_history=login_history,
                          recent_activity=recent_activity)

@app.route('/reset_password_request', methods=['POST'])
def reset_password_request():
    """Handle password reset requests"""
    # This is a mock implementation for demonstration purposes
    if request.is_xhr or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX request
        email = request.form.get('email')
        if email:
            # In a real application, you would:
            # 1. Check if the email exists in the database
            # 2. Generate a reset token
            # 3. Send an email with a reset link
            
            # For this demo, we'll just pretend it worked
            if '@' in email:  # Simple validation
                return jsonify({
                    'success': True,
                    'message': 'Password reset link has been sent to your email.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Invalid email address.'
                })
        else:
            return jsonify({
                'success': False,
                'message': 'Email is required.'
            })
    
    # Regular form submission
    email = request.form.get('email')
    if email:
        flash('Password reset link has been sent to your email.', 'success')
    else:
        flash('Email is required.', 'danger')
    
    return redirect(url_for('login'))

@app.route('/user_profile/<int:user_id>')
def user_profile(user_id):
    """Route for viewing a user's profile"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Load users from file
    users = session.get('users_list', [])
    
    # Find the user with the given ID
    user = None
    for u in users:
        if u.get('id') == user_id:
            user = u
            break
    
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('user_management'))
    
    # Mock login history for the user
    login_history = [
        {'timestamp': datetime.now().replace(tzinfo=None) - timedelta(hours=1), 'ip': '192.168.1.100', 'device': 'Chrome on Windows'},
        {'timestamp': datetime.now().replace(tzinfo=None) - timedelta(days=1), 'ip': '192.168.1.101', 'device': 'Safari on macOS'},
        {'timestamp': datetime.now().replace(tzinfo=None) - timedelta(days=2), 'ip': '192.168.1.102', 'device': 'Firefox on Linux'},
        {'timestamp': datetime.now().replace(tzinfo=None) - timedelta(days=3), 'ip': '192.168.1.103', 'device': 'Chrome on Android'},
    ]
    
    # Mock recent activity for the user
    recent_activity = [
        {'timestamp': datetime.now().replace(tzinfo=None) - timedelta(minutes=30), 'action': 'Logged in', 'details': 'Successful login from 192.168.1.100'},
        {'timestamp': datetime.now().replace(tzinfo=None) - timedelta(hours=2), 'action': 'Updated profile', 'details': 'Changed phone number'},
        {'timestamp': datetime.now().replace(tzinfo=None) - timedelta(hours=5), 'action': 'Ran report', 'details': 'Generated monthly activity report'},
        {'timestamp': datetime.now().replace(tzinfo=None) - timedelta(days=1), 'action': 'Created document', 'details': 'Added new research protocol'},
    ]
    
    return render_template('user_profile.html', 
                           user=user, 
                           login_history=login_history,
                           recent_activity=recent_activity)

if __name__ == '__main__':
    print("Starting enhanced Flask application with database management...")
    app.run(host='0.0.0.0', debug=True)
    print("Application stopped.") 