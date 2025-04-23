from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response, Response
import random
from datetime import datetime, timedelta
import os
import json
import string
from io import StringIO
import csv
import argparse
import secrets

app = Flask(__name__)
# Use a more secure secret key for production
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Custom Jinja2 filters
@app.template_filter('number_format')
def number_format_filter(value):
    """Format a number with thousands separators."""
    return "{:,}".format(int(value) if value is not None else 0)

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
    
    # If file doesn't exist, initialize with default users for Render deployment
    default_users = [
        {
            'id': 1,
            'name': 'Admin User',
            'email': 'admin@kemri.org',
            'phone': '+254712345678',
            'department': 'Administration',
            'role': 'Administrator',
            'status': 'active',
            'created_at': datetime.now().replace(tzinfo=None).isoformat(),
            'last_login': (datetime.now() - timedelta(days=2)).replace(tzinfo=None).isoformat(),
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
            'created_at': datetime.now().replace(tzinfo=None).isoformat(),
            'last_login': (datetime.now() - timedelta(hours=5)).replace(tzinfo=None).isoformat(),
            'login_count': 28,
            'password': 'password'  # Default password for demo
        }
    ]
    
    # Save default users to file
    save_users(default_users)
    return default_users

# Helper function to save users to file
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, default=str)  # default=str handles datetime objects

# Home route
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Add the logged_in session variable if not present
    if 'logged_in' not in session:
        session['logged_in'] = True
    return render_template('index.html', active_page='home')

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

@app.route('/track_document', methods=['GET', 'POST'])
def track_document():
    """Route for tracking documents by code. Handles both GET and POST requests."""
    # Check for user login
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Initialize variables
    recent_documents = []
    search_results = []
    is_search = False
    search_params = {}
    qr_code_value = ""
    
    # Handle POST request (direct document tracking)
    if request.method == 'POST':
        document_code = request.form.get('document_code')
        if not document_code:
            flash('Please enter a document code', 'danger')
            return redirect(url_for('track_document'))
        
        # Check for the document in the system
        # In a real system, you would search both DB and JSON sources
        # For demo, we'll check our mock data
        for doc_code in ['DOC-2025-001', 'DOC-2025-002', 'DOC-2025-003']:
            if doc_code == document_code:
                return redirect(url_for('document_details', doc_code=document_code))
        
        # If document not found
        flash(f'Document with code {document_code} not found', 'danger')
        return redirect(url_for('track_document'))
    
    # Handle GET request with code parameter (QR code scan or direct link)
    code_param = request.args.get('code')
    if code_param:
        # Same logic as POST, but from URL parameter
        for doc_code in ['DOC-2025-001', 'DOC-2025-002', 'DOC-2025-003']:
            if doc_code == code_param:
                return redirect(url_for('document_details', doc_code=code_param))
        
        # If not found, set QR code value to pre-populate the form
        qr_code_value = code_param
    
    # Check for search parameters
    sender = request.args.get('sender', '')
    recipient = request.args.get('recipient', '')
    date_range = request.args.get('date_range', '')
    status = request.args.get('status', '')
    
    # If any search parameter is provided, perform search
    if any([sender, recipient, date_range, status != '']):
        is_search = True
        search_params = {
            'sender': sender,
            'recipient': recipient,
            'date_range': date_range,
            'status': status
        }
        
        # Mock document data - in a real system, this would filter based on the search parameters
        current_date = datetime.now()
        mock_docs = [
            {
                'id': 1,
                'code': 'DOC-2025-001',
                'filename': 'Sample Report 1',
                'status': 'Incoming',
                'sender': 'Ministry of Health',
                'recipient': 'KEMRI Director',
                'timestamp': (current_date - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'database'
            },
            {
                'id': 2, 
                'code': 'DOC-2025-002',
                'filename': 'Sample Report 2',
                'status': 'Pending',
                'sender': 'WHO',
                'recipient': 'Research Department',
                'timestamp': (current_date - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'database'
            },
            {
                'id': 3,
                'code': 'DOC-2025-003',
                'filename': 'Research Findings',
                'status': 'Received',
                'sender': 'Partner Lab',
                'recipient': 'Science Department',
                'timestamp': (current_date - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'json'
            }
        ]
        
        # Filter results based on search parameters (simplified for demo)
        search_results = []
        for doc in mock_docs:
            add_doc = True
            
            if sender and sender.lower() not in doc['sender'].lower():
                add_doc = False
            if recipient and recipient.lower() not in doc['recipient'].lower():
                add_doc = False
            if status and status != 'all' and doc['status'] != status:
                add_doc = False
                
            if add_doc:
                search_results.append(doc)
    
    # If no search, get recent documents
    if not is_search:
        # Mock documents data for recent documents
        current_date = datetime.now()
        recent_documents = [
            {
                'id': 1,
                'code': 'DOC-2025-001',
                'filename': 'Sample Report 1',
                'status': 'Incoming',
                'sender': 'Ministry of Health',
                'recipient': 'KEMRI Director',
                'timestamp': (current_date - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'database'
            },
            {
                'id': 2, 
                'code': 'DOC-2025-002',
                'filename': 'Sample Report 2',
                'status': 'Pending',
                'sender': 'WHO',
                'recipient': 'Research Department',
                'timestamp': (current_date - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'database'
            },
            {
                'id': 3,
                'code': 'DOC-2025-003',
                'filename': 'Research Findings',
                'status': 'Received',
                'sender': 'Partner Lab',
                'recipient': 'Science Department',
                'timestamp': (current_date - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'json'
            }
        ]
    
    # Render the template with all necessary data
    return render_template('track_document.html', 
                          recent_documents=recent_documents,
                          search_results=search_results,
                          is_search=is_search,
                          search_params=search_params,
                          qr_code_value=qr_code_value,
                          active_page='track_document')

@app.route('/track_document_details/<document_code>')
def track_document_details(document_code):
    """Route for viewing tracking details of a specific document"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Mock document data with tracking information
    document = {
        'code': document_code,
        'title': f'Document {document_code}',
        'type': 'Research Report',
        'filename': f'{document_code}_report.pdf',
        'date_created': datetime.now() - timedelta(days=10),
        'status': 'In Transit',
        'owner': 'John Researcher',
        'department': 'Research',
        'priority': 'Medium',
        'tracking_id': f'TRK-{document_code}-{random.randint(1000, 9999)}',
        'current_location': 'Document Processing Center',
        'origin': 'Research Department',
        'destination': 'Executive Office',
        'estimated_arrival': datetime.now() + timedelta(days=2),
        'tracking_history': [
            {'location': 'Research Department', 'status': 'Dispatched', 'timestamp': datetime.now() - timedelta(days=3, hours=5), 'handler': 'John Researcher'},
            {'location': 'Document Processing Center', 'status': 'In Transit', 'timestamp': datetime.now() - timedelta(days=2), 'handler': 'Mary Processor'},
            {'location': 'Quality Assurance', 'status': 'Pending Review', 'timestamp': datetime.now() - timedelta(hours=12), 'handler': 'Quality Team'}
        ],
        'notes': 'Priority handling required for this document.'
    }
    
    return render_template('document_details.html', 
                          document=document, 
                          tracking=True,
                          active_page='track_document')

@app.route('/document_details/<doc_code>')
def document_details(doc_code):
    """Route for viewing details of a specific document"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Mock document data
    document = {
        'code': doc_code,
        'title': f'Document {doc_code}',
        'type': 'Research Report',
        'filename': f'{doc_code}_report.pdf',
        'date_created': datetime.now() - timedelta(days=10),
        'status': 'Received',
        'owner': 'John Researcher',
        'department': 'Research',
        'priority': 'Medium',
        'description': 'This is a detailed description of the document. It contains important information about the research conducted.',
        'file_size': '2.4 MB',
        'pages': 24,
        'last_modified': datetime.now() - timedelta(hours=5),
        'related_docs': ['DOC-2023-005', 'DOC-2023-008'],
        'tags': ['research', 'report', 'analysis'],
        'history': [
            {'action': 'Created', 'user': 'John Researcher', 'timestamp': datetime.now() - timedelta(days=10)},
            {'action': 'Submitted', 'user': 'John Researcher', 'timestamp': datetime.now() - timedelta(days=9)},
            {'action': 'Reviewed', 'user': 'Sarah Manager', 'timestamp': datetime.now() - timedelta(days=7)},
            {'action': 'Approved', 'user': 'Robert Director', 'timestamp': datetime.now() - timedelta(days=5)},
            {'action': 'Published', 'user': 'Admin User', 'timestamp': datetime.now() - timedelta(days=2)}
        ]
    }
    
    return render_template('document_details.html', 
                          document=document, 
                          active_page='track_document')

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
    
    # Get documents from session if available
    session_documents = session.get('documents', [])
    
    # Filter documents to show only incoming ones
    incoming_documents = [doc for doc in session_documents if doc.get('status') == 'Incoming']
    
    # Mock document data for initial display
    current_date = datetime.now()
    default_documents = [
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
    
    # Combine the mock and session documents for display
    documents = incoming_documents + default_documents
    
    # Mock filter data
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', 'All')
    priority_filter = request.args.get('priority', 'All')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Mock counts
    priority_counts = {
        'Urgent': len([doc for doc in documents if doc.get('priority') == 'Urgent']),
        'Priority': len([doc for doc in documents if doc.get('priority') == 'Priority']),
        'Normal': len([doc for doc in documents if doc.get('priority') == 'Normal'])
    }
    
    status_counts = {
        'Incoming': len([doc for doc in documents if doc.get('status') == 'Incoming']),
        'Pending': len([doc for doc in documents if doc.get('status') == 'Pending']),
        'Received': len([doc for doc in documents if doc.get('status') == 'Received'])
    }
    
    # Mock pagination
    pagination = {
        'page': 1,
        'per_page': 10,
        'total': len(documents),
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
    
    # Get documents from session if available
    session_documents = session.get('documents', [])
    
    # Filter documents to show only outgoing ones
    outgoing_documents = [doc for doc in session_documents if doc.get('status') == 'Outgoing']
    
    # Mock document data for initial display
    current_date = datetime.now()
    default_documents = [
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
    
    # Combine the mock and session documents for display
    documents = outgoing_documents + default_documents
    
    # Mock filter data
    search_query = request.args.get('search', '')
    priority_filter = request.args.get('priority', 'All')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Apply filter by priority if needed
    if priority_filter != 'All':
        documents = [doc for doc in documents if doc.get('priority') == priority_filter]
        
    # Apply search if provided
    if search_query:
        search_query_lower = search_query.lower()
        filtered_docs = []
        for doc in documents:
            if (search_query_lower in doc.get('code', '').lower() or
                search_query_lower in doc.get('sender', '').lower() or
                search_query_lower in doc.get('details', '').lower() or
                search_query_lower in doc.get('required_action', '').lower()):
                filtered_docs.append(doc)
        documents = filtered_docs
    
    # Apply sorting
    if sort_by == 'date':
        documents.sort(key=lambda x: x.get('date_of_letter') if not isinstance(x.get('date_of_letter'), str) else datetime.now(), reverse=(sort_order == 'desc'))
    elif sort_by == 'priority':
        priority_order = {'Urgent': 0, 'Priority': 1, 'Normal': 2}
        documents.sort(key=lambda x: priority_order.get(x.get('priority'), 3), reverse=(sort_order == 'desc'))
    elif sort_by == 'code':
        documents.sort(key=lambda x: x.get('code', ''), reverse=(sort_order == 'desc'))
    elif sort_by == 'action':
        documents.sort(key=lambda x: x.get('required_action', ''), reverse=(sort_order == 'desc'))
    
    # Mock counts
    priority_counts = {
        'Urgent': len([doc for doc in documents if doc.get('priority') == 'Urgent']),
        'Priority': len([doc for doc in documents if doc.get('priority') == 'Priority']),
        'Normal': len([doc for doc in documents if doc.get('priority') == 'Normal'])
    }
    
    # Mock pagination
    pagination = {
        'page': 1,
        'per_page': 10,
        'total': len(documents),
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

@app.route('/compose', methods=['GET', 'POST'])
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
    
    # Mock workflow templates
    workflow_templates = [
        {'name': 'Standard Review', 'steps': ['Initial Review', 'Department Review', 'Final Approval']},
        {'name': 'Fast Track', 'steps': ['Quick Review', 'Approval']},
        {'name': 'Extended Review', 'steps': ['Initial Check', 'Department Review', 'Management Review', 'Executive Approval', 'Final Filing']}
    ]
    
    # Handle POST submission
    if request.method == 'POST':
        try:
            # In a real application, you would store the document in a database
            # For this demo, we'll store it in the session
            
            # Generate document code if not provided
            tracking_code = request.form.get('preset_tracking_code')
            if not tracking_code:
                timestamp = datetime.now().strftime('%Y%m%d')
                random_hex = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                tracking_code = f"DOC-{timestamp}-{random_hex}"
            
            # Get form data
            document_direction = request.form.get('document_direction', 'incoming')
            document_title = request.form.get('document_title', '')
            sender = request.form.get('sender', user.get('username', 'Unknown'))
            recipient = request.form.get('recipient', '')
            details = request.form.get('details', '')
            required_action = request.form.get('required_action', 'Review')
            priority = request.form.get('priority', 'Normal')
            tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
            is_confidential = request.form.get('is_confidential') == 'on'
            
            # Create document record - ensure datetime is converted to string
            document = {
                'id': random.randint(1000, 9999),
                'tracking_number': tracking_code,
                'title': document_title,
                'status': 'Incoming' if document_direction == 'incoming' else 'Outgoing',
                'priority': priority,
                'sender': sender,
                'recipient': recipient,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'code': tracking_code,
                'details': details,
                'required_action': required_action,
                'date_received': datetime.now().strftime('%Y-%m-%d'),
                'date_of_letter': datetime.now().strftime('%Y-%m-%d'),  # Add this for outgoing documents
                'current_holder': recipient or user.get('username', 'System'),
                'is_confidential': is_confidential,
                'tags': tags
            }
            
            # Store in session
            if 'documents' not in session:
                session['documents'] = []
            
            # Add to session documents list
            documents = session.get('documents', [])
            documents.append(document)
            session['documents'] = documents
            
            # Flash success message
            flash(f'Document uploaded successfully! Tracking code: {tracking_code}', 'success')
            
            # Redirect to appropriate list based on document direction
            if document_direction == 'incoming':
                return redirect(url_for('incoming'))
            else:
                return redirect(url_for('outgoing'))
                
        except Exception as e:
            # If an error occurs, show an error message
            flash(f'Error uploading document: {str(e)}', 'danger')
            # Return to compose page
            return redirect(url_for('compose'))
    
    # Get mock users for recipient dropdown
    users = [
        {'id': 1, 'name': 'John Admin', 'email': 'admin@example.com', 'department': 'Administration'},
        {'id': 2, 'name': 'Jane Manager', 'email': 'jane@example.com', 'department': 'Management'},
        {'id': 3, 'name': 'Bob Researcher', 'email': 'bob@example.com', 'department': 'Research'}
    ]
    
    return render_template('compose.html', 
                          user=user, 
                          is_admin=is_admin, 
                          users=users,
                          workflow_templates=workflow_templates,
                          current_user=user)

@app.route('/reports')
def reports():
    """Route for reports page"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check if user has admin permissions
    if not current_user_has_permission('Administrator'):
        flash('You do not have permission to access the reports page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Mock data for reports
    report_list = [
        {
            'id': 1,
            'name': 'Document Activity Report',
            'description': 'Shows all document activity for a specified time period',
            'last_run': datetime.now() - timedelta(days=1),
            'type': 'activity'
        },
        {
            'id': 2,
            'name': 'User Activity Report',
            'description': 'Shows user login and action history',
            'last_run': datetime.now() - timedelta(days=2),
            'type': 'user'
        },
        {
            'id': 3,
            'name': 'System Performance Report',
            'description': 'Shows system performance metrics',
            'last_run': datetime.now() - timedelta(days=3),
            'type': 'system'
        }
    ]
    
    # Add default filters
    filters = {
        'date_range': 'last-7-days',
        'type': 'all',
        'status': 'all',
        'priority': 'all'
    }
    
    # Mock status data for report table
    status_data = {
        'Incoming': {'total': 12, 'normal': 6, 'priority': 4, 'urgent': 2},
        'Pending': {'total': 8, 'normal': 4, 'priority': 3, 'urgent': 1},
        'Received': {'total': 15, 'normal': 10, 'priority': 3, 'urgent': 2},
        'Outgoing': {'total': 7, 'normal': 5, 'priority': 2, 'urgent': 0},
        'Ended': {'total': 23, 'normal': 18, 'priority': 4, 'urgent': 1}
    }
    
    # Mock average processing times
    avg_times = {
        'Incoming': '1.2 days',
        'Pending': '2.5 days',
        'Received': '0.8 days',
        'Outgoing': '1.5 days',
        'Ended': '4.3 days'
    }
    
    # Calculate total documents
    total_documents = sum(status['total'] for status in status_data.values())
    
    return render_template('reports.html', reports=report_list, filters=filters, 
                           status_data=status_data, avg_times=avg_times, 
                           total_documents=total_documents, active_page='reports')

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
    """Route for maintenance page"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check if user has admin permissions
    if not current_user_has_permission('Administrator'):
        flash('You do not have permission to access the maintenance page.', 'danger')
        return redirect(url_for('dashboard'))
    
    scheduled_tasks = get_scheduled_tasks()
    database_backups = get_database_backups()
    system_health = get_system_health()
    
    # Add missing maintenance_stats
    maintenance_stats = {
        "cpu_usage": f"{random.randint(5, 30)}%",
        "memory_usage": f"{random.randint(20, 60)}%",
        "disk_usage": f"{random.randint(10, 70)}%",
        "system_uptime": "7 days, 14 hours, 23 minutes",
        "active_users": random.randint(1, 10),
        "open_files": random.randint(10, 50),
        "db_size": "324.5 MB",
        "pending_tasks": random.randint(0, 5)
    }
    
    # Add missing performance_data
    performance_data = {
        "response_time": f"{random.randint(80, 150)} ms",
        "queries_per_second": random.randint(10, 50),
        "slow_queries": random.randint(0, 3),
        "cache_hit_ratio": f"{random.randint(75, 95)}%"
    }
    
    # Add last_backup info
    last_backup = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    
    return render_template('maintenance.html', 
                          scheduled_tasks=scheduled_tasks,
                          database_backups=database_backups,
                          system_health=system_health,
                          maintenance_stats=maintenance_stats,
                          performance_data=performance_data,
                          last_backup=last_backup,
                          active_page='maintenance')

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
    
    # Check permission for non-admin users
    if not current_user_has_permission('Administrator'):
        flash('You do not have permission to access user management.', 'danger')
        return redirect(url_for('dashboard'))
    
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
                },
                {
                    'id': 4,
                    'name': 'Read Only User',
                    'email': 'readonly@kemri.org',
                    'phone': '+254745678901',
                    'department': 'Audit',
                    'role': 'Read Only',
                    'status': 'active',
                    'created_at': datetime.now().replace(tzinfo=None),
                    'last_login': (datetime.now() - timedelta(days=5)).replace(tzinfo=None),
                    'login_count': 8,
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
    departments = ['Administration', 'Laboratory', 'Research', 'IT', 'Finance', 'HR', 'Audit']
    roles = ['Administrator', 'Manager', 'Lab Technician', 'Researcher', 'Data Entry', 'User', 'Read Only']
    
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
                           stats=stats,
                           active_page='user_management')

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
    if not current_user_has_permission('Administrator'):
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
    if not current_user_has_permission('Administrator'):
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
    if not current_user_has_permission('Administrator'):
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
    if not current_user_has_permission('Administrator'):
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
    if not current_user_has_permission('Administrator'):
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
    if not current_user_has_permission('Administrator'):
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
    
    # Admin role always has all permissions
    if session.get('user_role') == 'Administrator':
        return True
    
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
    """Add utility functions to the template context."""
    def now():
        # Ensure we always return a timezone-naive datetime
        return datetime.now().replace(tzinfo=None)
    
    # Add is_admin check to all templates
    is_admin = session.get('user_role') == 'Administrator' if 'user_role' in session else False
    
    return {
        'now': now,
        'is_admin': is_admin,
        'timedelta': timedelta
    }

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
    """Route for database management page"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check permission for non-admin users
    if not current_user_has_permission('Administrator'):
        flash('You do not have permission to access database management.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Mock DB stats
    db_stats = {
        'size': '2.4 GB',
        'tables': 42,
        'rows': 157892,
        'indexes': 86,
        'uptime': '18 days, 4 hours',
        'last_backup': '2023-04-11 04:00:00',
        'backup_size': '1.8 GB'
    }
    
    # Mock backup history
    backup_history = [
        {'date': '2023-04-11 04:00:00', 'size': '1.8 GB', 'status': 'Success', 'duration': '23 min'},
        {'date': '2023-04-10 04:00:00', 'size': '1.8 GB', 'status': 'Success', 'duration': '22 min'},
        {'date': '2023-04-09 04:00:00', 'size': '1.7 GB', 'status': 'Success', 'duration': '21 min'},
        {'date': '2023-04-08 04:00:00', 'size': '1.7 GB', 'status': 'Failed', 'duration': '5 min'},
        {'date': '2023-04-07 04:00:00', 'size': '1.7 GB', 'status': 'Success', 'duration': '20 min'}
    ]
    
    return render_template('database_management.html', 
                          db_stats=db_stats, 
                          backup_history=backup_history,
                          active_page='database_management')

@app.route('/database_integrity')
def database_integrity():
    """Route for database integrity check page"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check permission for non-admin users
    if not current_user_has_permission('Administrator'):
        flash('You do not have permission to access database integrity checks.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Mock integrity data
    integrity_checks = [
        {'type': 'Foreign Key', 'table': 'documents', 'status': 'Passed', 'timestamp': datetime.now() - timedelta(hours=1)},
        {'type': 'Index Check', 'table': 'users', 'status': 'Passed', 'timestamp': datetime.now() - timedelta(hours=1)},
        {'type': 'Data Consistency', 'table': 'activities', 'status': 'Passed', 'timestamp': datetime.now() - timedelta(hours=1)}
    ]
    
    return render_template('database_integrity.html', 
                          integrity_checks=integrity_checks,
                          active_page='database_management')

@app.route('/database_logs')
def database_logs():
    """Route for database logs page"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check permission for non-admin users
    if not current_user_has_permission('Administrator'):
        flash('You do not have permission to access database logs.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Mock logs data
    logs = [
        {'type': 'Backup', 'details': 'Full backup completed', 'status': 'Success', 'timestamp': datetime.now() - timedelta(hours=2)},
        {'type': 'Vacuum', 'details': 'Vacuum on users table', 'status': 'Success', 'timestamp': datetime.now() - timedelta(days=1)},
        {'type': 'Schema Update', 'details': 'Added column to documents table', 'status': 'Success', 'timestamp': datetime.now() - timedelta(days=3)}
    ]
    
    return render_template('database_logs.html', 
                          logs=logs,
                          active_page='database_management')

@app.route('/backup_database', methods=['POST'])
def backup_database():
    """Route for backing up the database"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check permission for non-admin users
    if not current_user_has_permission('Administrator'):
        flash('You do not have permission to backup the database.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Mock backup creation
    flash('Database backup created successfully.', 'success')
    return redirect(url_for('database_management'))

@app.route('/restore_database', methods=['POST'])
def restore_database():
    """Route for restoring the database from backup"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check permission for non-admin users
    if not current_user_has_permission('Administrator'):
        flash('You do not have permission to restore the database.', 'danger')
        return redirect(url_for('dashboard'))
    
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

@app.route('/add_document_action/<document_code>', methods=['POST'])
def add_document_action(document_code):
    """Route for adding actions to documents"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Get form data
    action_type = request.form.get('action_type')
    notes = request.form.get('notes', '')
    new_status = request.form.get('new_status', '')
    
    # In a real app, we would save this action to the database or JSON file
    # Mock response for demo purposes
    flash(f'Action "{action_type}" added to document {document_code}', 'success')
    
    # If status was changed, notify the user
    if new_status:
        flash(f'Document status updated to {new_status}', 'info')
    
    return redirect(url_for('document_details', doc_code=document_code))

@app.route('/add_document_comment/<document_code>', methods=['POST'])
def add_document_comment(document_code):
    """Route for adding comments to documents"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Get form data
    comment = request.form.get('comment')
    is_private = request.form.get('is_private') == 'on'
    
    if not comment:
        flash('Comment cannot be empty', 'danger')
        return redirect(url_for('document_details', doc_code=document_code))
    
    # In a real app, we would save this comment to the database or JSON file
    # Mock response for demo purposes
    privacy_note = "private " if is_private else ""
    flash(f'Added {privacy_note}comment to document {document_code}', 'success')
    
    return redirect(url_for('document_details', doc_code=document_code))

@app.route('/set_document_priority/<document_code>', methods=['POST'])
def set_document_priority(document_code):
    """Route for changing document priority"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Get form data
    priority = request.form.get('priority')
    reason = request.form.get('reason', '')
    
    # In a real app, we would update the document in the database or JSON file
    # Mock response for demo purposes
    flash(f'Document priority changed to {priority}', 'success')
    
    return redirect(url_for('document_details', doc_code=document_code))

@app.route('/reassign_document/<document_code>', methods=['POST'])
def reassign_document(document_code):
    """Route for reassigning documents to different users"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Get form data
    new_assignee = request.form.get('new_assignee')
    reason = request.form.get('reason', '')
    
    # In a real app, we would update the document in the database or JSON file
    # Mock response for demo purposes
    flash(f'Document reassigned to {new_assignee}', 'success')
    
    return redirect(url_for('document_details', doc_code=document_code))

@app.route('/attach_related_document/<document_code>', methods=['POST'])
def attach_related_document(document_code):
    """Route for adding related documents"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Get form data
    related_doc_code = request.form.get('related_doc_code')
    relationship = request.form.get('relationship')
    
    # In a real app, we would update the document in the database or JSON file
    # Mock response for demo purposes
    flash(f'Related document {related_doc_code} added with relationship "{relationship}"', 'success')
    
    return redirect(url_for('document_details', doc_code=document_code))

@app.route('/mark_document_ended/<document_code>', methods=['POST'])
def mark_document_ended(document_code):
    """Route for marking documents as ended"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Get form data
    confirmation = request.form.get('confirmation') == 'on'
    reason = request.form.get('reason', '')
    
    if not confirmation:
        flash('You must confirm that you want to mark this document as ended', 'danger')
        return redirect(url_for('document_details', doc_code=document_code))
    
    # In a real app, we would update the document in the database or JSON file
    # Mock response for demo purposes
    flash(f'Document {document_code} marked as Ended', 'success')
    
    return redirect(url_for('document_details', doc_code=document_code))

@app.route('/export_document_history/<document_code>')
def export_document_history(document_code):
    """Route for exporting document history"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    export_format = request.args.get('format', 'json')
    
    # Mock history data
    history = [
        {
            'timestamp': datetime.now() - timedelta(days=10),
            'user': 'John Researcher',
            'action': 'Created',
            'notes': 'Initial document creation'
        },
        {
            'timestamp': datetime.now() - timedelta(days=9),
            'user': 'John Researcher',
            'action': 'Submitted',
            'notes': 'Submitted for review'
        },
        {
            'timestamp': datetime.now() - timedelta(days=7),
            'user': 'Sarah Manager',
            'action': 'Reviewed',
            'notes': 'First review completed'
        },
        {
            'timestamp': datetime.now() - timedelta(days=5),
            'user': 'Robert Director',
            'action': 'Approved',
            'notes': 'Final approval given'
        }
    ]
    
    if export_format == 'json':
        # Convert timestamps to strings for JSON serialization
        for item in history:
            item['timestamp'] = item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
        response = jsonify({
            'document_code': document_code,
            'history': history
        })
        response.headers['Content-Disposition'] = f'attachment; filename=document_{document_code}_history.json'
        return response
    
    elif export_format == 'csv':
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header row
        writer.writerow(['Timestamp', 'User', 'Action', 'Notes'])
        
        # Write data rows
        for item in history:
            writer.writerow([
                item['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                item['user'],
                item['action'],
                item['notes']
            ])
        
        response = Response(output.getvalue(), mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename=document_{document_code}_history.csv'
        return response
    
    else:
        flash('Invalid export format', 'danger')
        return redirect(url_for('document_details', doc_code=document_code))

@app.route('/view_document_file/<document_code>')
def view_document_file(document_code):
    """Route for viewing document files"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # In a real app, we would fetch the file from storage and return it
    # For demo purposes, we'll just redirect back with a message
    flash('File viewing is not available in the demo', 'info')
    return redirect(url_for('document_details', doc_code=document_code))

@app.route('/send_document_notification/<document_code>', methods=['POST'])
def send_document_notification(document_code):
    """Route for sending notifications about documents"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Get form data
    recipient = request.form.get('recipient')
    notification_type = request.form.get('notification_type')
    message = request.form.get('message')
    send_email = request.form.get('send_email') == 'on'
    
    # In a real app, we would send the notification
    # Mock response for demo purposes
    flash(f'Notification sent to {recipient}', 'success')
    
    if send_email:
        flash('Email notification also sent', 'info')
    
    if document_code != '0':  # If called from a document page
        return redirect(url_for('document_details', doc_code=document_code))
    else:
        # If called from somewhere else (like bulk notification)
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Flask application for document tracking and user management')
    parser.add_argument('-p', '--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()
    
    print(f"Starting KEMRI Laboratory System on port {args.port}...")
    app.run(host='0.0.0.0', port=args.port, debug=False)
    print("Application stopped.") 