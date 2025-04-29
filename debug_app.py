from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify, send_from_directory
import sqlite3
import os
from werkzeug.routing.exceptions import BuildError
from datetime import datetime, timedelta
import json
import random
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'kemri_secret_key'  # Required for flash messages
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False

# Disable auto-setting of session cookies on responses
app.config['SESSION_USE_SIGNER'] = True

# File Upload Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'txt'}

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Function to check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Function to handle file upload
def handle_file_upload(file, document_id=None):
    """
    Handle file upload, save to disk, and return the saved filename
    
    Args:
        file: The file object from request.files
        document_id: Optional document ID to associate with the file
        
    Returns:
        dict: Information about the saved file or None if file upload failed
    """
    if not file or file.filename == '':
        return None
        
    if not allowed_file(file.filename):
        return None
        
    # Secure the filename to prevent security issues
    original_filename = secure_filename(file.filename)
    
    # Generate a unique filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    doc_prefix = f"{document_id}_" if document_id else ""
    filename = f"{doc_prefix}{timestamp}_{original_filename}"
    
    # Save the file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    # Get file size
    file_size = os.path.getsize(file_path)
    
    # Determine file type
    file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    
    # Create file info dict
    file_info = {
        'original_filename': original_filename,
        'saved_filename': filename,
        'file_path': file_path,
        'file_size': file_size,
        'file_type': file_ext,
        'upload_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return file_info

# Function to get human-readable file size
def get_human_readable_size(size_bytes):
    """Convert file size in bytes to human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

# Custom Pagination class for templates that expect SQLAlchemy pagination
class Pagination:
    def __init__(self, page, per_page, total_items):
        self.page = page
        self.per_page = per_page
        self.total = total_items
        self.items = []
        
    @property
    def pages(self):
        """The total number of pages"""
        return max(1, self.total // self.per_page + (1 if self.total % self.per_page > 0 else 0))
        
    @property
    def has_prev(self):
        """True if a previous page exists"""
        return self.page > 1
        
    @property
    def has_next(self):
        """True if a next page exists"""
        return self.page < self.pages
        
    @property
    def prev_num(self):
        """Number of the previous page"""
        return self.page - 1 if self.has_prev else None
        
    @property
    def next_num(self):
        """Number of the next page"""
        return self.page + 1 if self.has_next else None
        
    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        """Iterates over the page numbers in the pagination.
        
        This implementation is similar to Flask-SQLAlchemy's Pagination.iter_pages method.
        """
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge or
                (num > self.page - left_current - 1 and num < self.page + right_current) or
                num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num

# Add has_endpoint function to Jinja environment
def has_endpoint(endpoint):
    """Check if the endpoint exists in the application"""
    try:
        return app.url_map._rules_by_endpoint.get(endpoint) is not None
    except:
        return False

app.jinja_env.globals['has_endpoint'] = has_endpoint

# Add now() function to Jinja environment
app.jinja_env.globals['now'] = datetime.now

# Database path
DB_PATH = 'app.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    """Home page route"""
    # Always show the standalone home page
    return render_template('index_standalone.html')

@app.route('/index')
def index():
    """Render the index page"""
    # Explicitly clear any session
    session.clear()
    return render_template('index_standalone.html')

@app.route('/session_status')
def session_status():
    """Debug route to check session state"""
    if 'user_id' in session:
        return f"Session active: user_id={session.get('user_id')}, username={session.get('username')}"
    else:
        return "No active session"

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Clear any existing session first
    if 'user_id' in session:
        session.clear()
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple connection to check if user exists
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user:
            # For simplicity, we're bypassing password check
            session.clear()  # Ensure we start with a clean session
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role'] 
            flash('You have been logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', current_year=2025)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard', 'warning')
        return redirect(url_for('login'))
    
    # Get basic counts for dashboard
    conn = get_db_connection()
    
    # Count users
    user_count = conn.execute('SELECT COUNT(*) as count FROM user').fetchone()['count']
    
    # Count documents by status
    status_counts = {}
    statuses = ['Incoming', 'Pending', 'Received', 'Outgoing', 'Ended']
    for status in statuses:
        count = conn.execute('SELECT COUNT(*) as count FROM document WHERE status = ?', 
                            (status,)).fetchone()['count']
        status_counts[status] = count
    
    # Get recent logs
    recent_logs = conn.execute('''
        SELECT * FROM system_log ORDER BY timestamp DESC LIMIT 10
    ''').fetchall()
    
    # Get urgent documents
    urgent_docs = conn.execute('''
        SELECT * FROM document 
        WHERE priority = 'Urgent' 
        ORDER BY created_at DESC LIMIT 5
    ''').fetchall()
    
    # Count total documents
    total_documents = conn.execute('SELECT COUNT(*) as count FROM document').fetchone()['count']
    
    conn.close()
    
    # Add registry pending approvals for staff with registry role
    # In a real app, check if user has registry role
    is_registry_staff = session.get('role') in ['Registry', 'Administrator']
    pending_registry_count = 7  # Simulated count for demo
    
    # Get pending registry documents (simple sample data)
    registry_documents = []
    if is_registry_staff:
        for i in range(1, 4):
            doc_date = datetime.now() - timedelta(days=i % 3)
            tracking_code = f"KEMRI-{doc_date.strftime('%Y%m%d')}-{1000+i}"
            
            document = {
                'id': i,
                'tracking_code': tracking_code,
                'title': f"Document {i} requiring approval",
                'sender': f"Department {i % 5 + 1}",
                'recipient': f"Recipient {i % 3 + 1}",
                'date_submitted': doc_date.strftime('%Y-%m-%d %H:%M'),
                'priority': ['Normal', 'Priority', 'Urgent'][i % 3],
                'document_type': ['Letter', 'Report', 'Requisition'][i % 3],
                'status': 'Pending Registry Approval'
            }
            registry_documents.append(document)
    
    return render_template(
        'dashboard_new.html', 
        status_counts=status_counts,
        recent_logs=recent_logs,
        urgent_docs=urgent_docs,
        total_documents=total_documents,
        total_users=user_count,
        is_registry_staff=is_registry_staff,
        pending_registry_count=pending_registry_count,
        registry_documents=registry_documents
    )

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/user-management')
def user_management():
    if 'user_id' not in session:
        flash('Please log in to access user management', 'warning')
        return redirect(url_for('login'))
    
    if session['role'] != 'Administrator':
        flash('You do not have permission to access user management', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM user').fetchall()
    conn.close()
    
    # Available roles for user creation
    roles = ['Administrator', 'Registry', 'User', 'Supervisor']
    
    # Sample departments for user creation
    departments = [
        'Administration',
        'Research',
        'Laboratory',
        'Finance',
        'IT',
        'Registry',
        'Operations'
    ]
    
    return render_template('user_management.html', 
                           users=users, 
                           roles=roles, 
                           departments=departments)

@app.errorhandler(BuildError)
def handle_build_error(error):
    print(f"BuildError: {error}")
    flash("Some navigation links may not be available in debug mode", "warning")
    return redirect(url_for('dashboard'))

@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors with a custom page"""
    return render_template('error.html', error=error), 500

@app.errorhandler(404)
def page_not_found(e):
    flash("The page you requested was not found", "warning")
    return redirect(url_for('dashboard'))

@app.route('/track_document', methods=['GET', 'POST'])
def track_document():
    if 'user_id' not in session:
        flash('Please log in to access this page', 'warning')
        return redirect(url_for('login'))

    search_results = None
    recent_documents = None
    error_message = None

    if request.method == 'POST':
        tracking_code = request.form.get('tracking_code')
        if tracking_code:
            # Dummy data for demonstration - replace with actual database query
            search_results = [{
                'tracking_code': tracking_code,
                'title': 'Sample Document',
                'sender': 'John Doe',
                'recipient': 'Jane Smith',
                'status': 'In Progress',
                'date_created': datetime.now().strftime('%Y-%m-%d'),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }]
    else:
        # Handle GET request with search parameters
        sender = request.args.get('sender', '')
        recipient = request.args.get('recipient', '')
        status = request.args.get('status', '')
        date_range = request.args.get('date_range', 'all')

        if any([sender, recipient, status, date_range != 'all']):
            # Dummy search results - replace with actual database query
            search_results = [{
                'tracking_code': 'DOC123',
                'title': 'Research Report',
                'sender': sender or 'John Doe',
                'recipient': recipient or 'Jane Smith',
                'status': status or 'Pending',
                'date_created': datetime.now().strftime('%Y-%m-%d'),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }]
        else:
            # Show recent documents on initial page load
            recent_documents = [{
                'tracking_code': f'DOC{i}',
                'title': f'Document {i}',
                'sender': f'Sender {i}',
                'recipient': f'Recipient {i}',
                'status': ['Pending', 'In Progress', 'Completed'][i % 3],
                'date_created': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            } for i in range(1, 6)]

    return render_template('track_document.html',
                         search_results=search_results,
                         recent_documents=recent_documents,
                         error_message=error_message)

@app.route('/document_details/<doc_code>')
def document_details(doc_code):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # In a real app, you would fetch document data from database
    document = {
        'code': doc_code,
        'title': f'Document {doc_code}',
        'filename': f'file_{doc_code}.pdf',
                'status': 'Pending',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'sender': 'John Doe',
        'recipient': 'Jane Smith',
        'description': 'Sample document for testing purposes'
    }
    history = [
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': 'Document Created',
            'user': 'System Admin',
            'details': f'Document {doc_code} was created'
        },
        {
            'timestamp': (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
            'action': 'Status Changed',
            'user': 'John Doe',
            'details': 'Document status updated to Pending'
        }
    ]
    return render_template('document_details.html', document=document, history=history, active_page='track_document')

@app.route('/track_document_details/<document_code>')
def track_document_details(document_code):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # In a real app, you would fetch document data from JSON or external tracking system
    document = {
        'code': document_code,
        'filename': f'external_{document_code}.pdf',
        'status': 'Received',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'sender': 'External Dept',
        'recipient': 'KEMRI Lab',
        'description': 'External document for testing'
    }
    actions = [
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': 'Document Received',
            'user': 'System',
            'details': 'Document was received from external system'
        }
    ]
    comments = [
        {
            'user': 'System Admin',
            'date': 'Feb 20, 2023',
            'content': 'I\'ve adjusted the Q3 projections down by 6% and recalculated the annual totals accordingly.'
        }
    ]
    return render_template('document_details.html', document=document, actions=actions, comments=comments, tracking_code=document_code, active_page='track_document')

@app.route('/compose', methods=['GET', 'POST'])
def compose():
    if 'user_id' not in session:
        flash('Please log in to compose documents', 'warning')
        return redirect(url_for('login'))
    
    # Initialize errors dictionary to store validation errors
    errors = {}
    form_data = {}
    
    if request.method == 'POST':
        # Extract form data
        doc_type = request.form.get('doc_type', 'Outgoing')
        title = request.form.get('title', '').strip()
        date_of_letter = request.form.get('date_of_letter', '').strip()
        sender = request.form.get('sender', '').strip()
        recipient = request.form.get('recipient', '').strip()
        details = request.form.get('details', '').strip()
        required_action = request.form.get('required_action', '').strip()
        priority = request.form.get('priority', 'Normal')
        
        # Store form data for redisplaying the form in case of errors
        form_data = {
            'doc_type': doc_type,
            'title': title,
            'date_of_letter': date_of_letter,
            'sender': sender,
            'recipient': recipient,
            'details': details,
            'required_action': required_action,
            'priority': priority
        }
        
        # Validate required fields
        if not title:
            errors['title'] = 'Document title is required'
            
        if not sender:
            errors['sender'] = 'Sender is required'
            
        if not recipient:
            errors['recipient'] = 'Recipient is required'
            
        # Validate date format if provided
        if date_of_letter:
            try:
                datetime.strptime(date_of_letter, '%Y-%m-%d')
            except ValueError:
                errors['date_of_letter'] = 'Invalid date format. Please use YYYY-MM-DD'
        
        # Validate document type
        if doc_type not in ['Incoming', 'Outgoing', 'Internal']:
            errors['doc_type'] = 'Invalid document type'
            
        # Validate priority
        if priority not in ['Urgent', 'Priority', 'Normal']:
            errors['priority'] = 'Invalid priority'
        
        # Handle file upload if present
        file = request.files.get('document_file')
        uploaded_file_info = None
        
        if file and file.filename:
            # Check if file extension is allowed
            if not allowed_file(file.filename):
                allowed_ext_list = ', '.join(app.config['ALLOWED_EXTENSIONS'])
                errors['document_file'] = f'Invalid file type. Allowed types: {allowed_ext_list}'
            
            # Check file size
            if request.content_length and request.content_length > app.config['MAX_CONTENT_LENGTH']:
                max_size_readable = get_human_readable_size(app.config['MAX_CONTENT_LENGTH'])
                errors['document_file'] = f'File size exceeds maximum limit of {max_size_readable}'
        
        # Process if no validation errors
        if not errors:
            # Generate a unique tracking code
            # Format: KEMRI-YYYYMMDD-XXXX where XXXX is a random 4-digit number
            today = datetime.now().strftime('%Y%m%d')
            random_digits = random.randint(1000, 9999)
            tracking_code = f"KEMRI-{today}-{random_digits}"
            
            # Handle file upload after generating tracking code
            if file and file.filename:
                uploaded_file_info = handle_file_upload(file, tracking_code)
                if not uploaded_file_info:
                    flash('File upload failed', 'danger')
                    return render_template('compose.html', active_page='compose', errors=errors, form_data=form_data)
            
            # In a real app, save document data to database including file info
            
            # Set initial status to "Pending Registry Approval"
            initial_status = "Pending Registry Approval"
            
            # For demo purposes, flash success messages
            flash(f'Document "{title}" successfully submitted with tracking code: {tracking_code}', 'success')
            flash(f'Document is now awaiting Registry approval', 'info')
            
            if uploaded_file_info:
                file_name = uploaded_file_info['original_filename']
                file_size = get_human_readable_size(uploaded_file_info['file_size'])
                flash(f'File "{file_name}" ({file_size}) uploaded successfully', 'success')
            
            # Store tracking code in session for immediate use
            session['last_tracking_code'] = tracking_code
            
            # Always redirect to dashboard after document submission
            return redirect(url_for('dashboard'))
        else:
            # If there are validation errors, flash a message
            flash('Please correct the errors in the form', 'danger')
    
    return render_template('compose.html', active_page='compose', errors=errors, form_data=form_data)

@app.route('/my_account')
def my_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Get user data from database (using dummy data for now)
    user = {
        'id': session['user_id'],
        'username': 'admin',
        'email': 'admin@example.com',
        'role': 'Administrator',
        'department': 'IT',
        'date_joined': '2024-01-01',
        'last_login': '2024-03-15'
    }
    
    # Convert date strings to datetime objects
    user['date_joined'] = datetime.strptime(user['date_joined'], '%Y-%m-%d')
    user['last_login'] = datetime.strptime(user['last_login'], '%Y-%m-%d')
    
    # Dummy login activities
    login_activities = [
        {'date': '2024-03-15 09:00:00', 'ip': '192.168.1.100', 'status': 'Success'},
        {'date': '2024-03-14 14:30:00', 'ip': '192.168.1.100', 'status': 'Success'},
        {'date': '2024-03-13 11:15:00', 'ip': '192.168.1.101', 'status': 'Failed'}
    ]
    
    return render_template('my_account_simple.html', 
                         user=user,
                         login_activities=login_activities,
                         active_page='my_account')

@app.route('/incoming')
def incoming():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get filter parameters
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'All')
    date_range = request.args.get('date_range', 'all')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    page = request.args.get('page', 1, type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Add dummy data for status counts
    status_counts = {
        'Incoming': 5,
        'Pending': 3, 
        'Received': 15
    }
    
    # Add dummy data for priority counts
    priority_counts = {
        'Urgent': 3,
        'Priority': 8,
        'Normal': 12
    }
    
    # Generate sample documents for display
    documents = []
    total_items = 23  # Total number of documents (for pagination)
    
    # Date logic for filtering
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = datetime.now().replace(day=1).date()
    
    # Generate sample documents
    for i in range(1, 15):
        # Create a sample date, biased toward more recent dates
        days_ago = i if i < 5 else i * 2
        doc_date = datetime.now() - timedelta(days=days_ago)
        doc_date_str = doc_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine status in rotation
        if i % 3 == 0:
            status = 'Incoming'
        elif i % 3 == 1:
            status = 'Pending'
        else:
            status = 'Received'
        
        # Determine priority in rotation
        if i % 5 == 0:
            priority = 'Urgent'
        elif i % 5 == 2 or i % 5 == 4:
            priority = 'Priority'
        else:
            priority = 'Normal'
        
        document = {
            'id': i,
            'code': f'DOC-{2025}-{i:03d}',
            'title': f'Sample Document {i}',
            'sender': f'Department {i % 5 + 1}',
            'recipient': 'KEMRI Laboratory',
            'details': f'This is a sample document {i} for testing purposes.',
            'required_action': ['Review', 'Approve', 'Forward', 'File', 'Comment'][i % 5],
            'date_received': doc_date_str,
            'date_received_obj': doc_date,
            'status': status,
            'priority': priority,
            'current_holder': f'User {i % 3 + 1}'
        }
        
        # Apply filters
        include_document = True
        
        # Status filter
        if status_filter != 'all' and document['status'] != status_filter:
            include_document = False
            
        # Priority filter
        if priority_filter != 'All' and document['priority'] != priority_filter:
            include_document = False
            
        # Search query
        if search_query and search_query.lower() not in document['title'].lower() and search_query.lower() not in document['sender'].lower():
            include_document = False
            
        # Date range filter
        doc_date = document['date_received_obj'].date()
        if date_range == 'today' and doc_date != today:
            include_document = False
        elif date_range == 'week' and doc_date < week_start:
            include_document = False
        elif date_range == 'month' and doc_date < month_start:
            include_document = False
        elif date_range == 'custom' and start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            if doc_date < start or doc_date > end:
                include_document = False
        
        if include_document:
            documents.append(document)
    
    # Sort documents
    if sort_by == 'date':
        documents.sort(key=lambda x: x['date_received_obj'], reverse=(sort_order == 'desc'))
    elif sort_by == 'priority':
        priority_order = {'Urgent': 0, 'Priority': 1, 'Normal': 2}
        documents.sort(key=lambda x: priority_order[x['priority']], reverse=(sort_order != 'desc'))
    elif sort_by == 'sender':
        documents.sort(key=lambda x: x['sender'], reverse=(sort_order == 'desc'))
    
    # Create pagination object
    per_page = 10
    total_filtered = len(documents)
    
    # Get the documents for the current page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_filtered)
    page_documents = documents[start_idx:end_idx] if documents else []
    
    # Create Pagination instance
    pagination = Pagination(page=page, per_page=per_page, total_items=total_filtered)
    pagination.items = page_documents
    
    return render_template('incoming.html', 
                          active_page='incoming',
                          status_counts=status_counts,
                          priority_counts=priority_counts,
                          documents=page_documents,
                          search_query=search_query,
                          status_filter=status_filter,
                          priority_filter=priority_filter,
                          date_range=date_range,
                          start_date=start_date,
                          end_date=end_date,
                          sort_by=sort_by,
                          sort_order=sort_order,
                          pagination=pagination)

@app.route('/outgoing')
def outgoing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Add dummy data for priority counts to fix the template error
    priority_counts = {
        'Urgent': 2,
        'Priority': 5,
        'Normal': 10
    }
    
    # Add other variables needed by the template
    documents = []
    search_query = request.args.get('search', '')
    priority_filter = request.args.get('priority', 'All')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    page = request.args.get('page', 1, type=int)
    
    # Create pagination object with proper iter_pages method
    pagination = Pagination(page=page, per_page=10, total_items=17)
    
    return render_template('outgoing.html', 
                          active_page='outgoing',
                          priority_counts=priority_counts,
                          documents=documents,
                          search_query=search_query,
                          priority_filter=priority_filter,
                          sort_by=sort_by,
                          sort_order=sort_order,
                          pagination=pagination)

@app.route('/database_management')
def database_management():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if session.get('role') != 'Administrator':
        flash('You do not have permission to access database management', 'danger')
        return redirect(url_for('dashboard'))
    
    # Add statistics data needed for the database_management template
    stats = {
        'total_documents': 127,
        'total_users': 15,
        'total_logs': 450,
        'total_attachments': 83,
        'db_size': '7.2 MB',
        'health_percentage': 98
    }
    
    # Add sample backups for the template
    backups = [
        {
            'filename': 'backup_20250427_120000.db',
            'date': 'Apr 27, 2025 12:00',
            'size': '6.8 MB'
        },
        {
            'filename': 'backup_20250426_120000.db',
            'date': 'Apr 26, 2025 12:00',
            'size': '6.7 MB'
        },
        {
            'filename': 'backup_20250425_120000.db',
            'date': 'Apr 25, 2025 12:00',
            'size': '6.5 MB'
        }
    ]
    
    # Add sample logs
    recent_logs = [
        {
            'timestamp': datetime.now() - timedelta(hours=1),
            'action': 'Backup',
            'log_type': 'Success',
            'user': 'admin',
            'details': 'Database backup completed successfully'
        },
        {
            'timestamp': datetime.now() - timedelta(hours=2),
            'action': 'Optimize',
            'log_type': 'Success',
            'user': 'admin',
            'details': 'Database optimization completed'
        },
        {
            'timestamp': datetime.now() - timedelta(hours=6),
            'action': 'Vacuum',
            'log_type': 'Success',
            'user': 'admin',
            'details': 'Database vacuum process completed'
        }
    ]
    
    # Add performance metrics
    performance = {
        'response_time': 115,
        'queries_per_second': 13.2,
        'slow_queries': 0,
        'cache_hit_ratio': 96
    }
    
    return render_template('database_management.html', 
                          active_page='database_management',
                          stats=stats,
                          backups=backups,
                          recent_logs=recent_logs,
                          performance=performance,
                          now=datetime.now)

@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Add dummy filters data for the reports template
    filters = {
        'date_range': request.args.get('date_range', 'last-30-days'),
        'status': request.args.get('status', 'all'),
        'priority': request.args.get('priority', 'all'),
        'department': request.args.get('department', 'all')
    }
    
    # Add dummy report data
    report_data = {
        'total_documents': 127,
        'incoming_count': 45,
        'outgoing_count': 82,
        'by_priority': {
            'Urgent': 18,
            'Priority': 53,
            'Normal': 56
        },
        'by_status': {
            'Incoming': 23,
            'Pending': 14,
            'Received': 35,
            'Outgoing': 39,
            'Ended': 16
        }
    }
    
    # Create chart data
    chart_data = {
        'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'datasets': {
            'incoming': [12, 19, 8, 15, 10, 14],
            'outgoing': [8, 15, 12, 9, 16, 11]
        }
    }
    
    # Create status data required by the template
    status_data = {
        'Incoming': {
            'total': 23,
            'normal': 8,
            'priority': 10,
            'urgent': 5,
            'percent': 18,
            'trend': 'up'
        },
        'Pending': {
            'total': 14,
            'normal': 5,
            'priority': 6,
            'urgent': 3,
            'percent': 11,
            'trend': 'down'
        },
        'Received': {
            'total': 35,
            'normal': 15,
            'priority': 12,
            'urgent': 8,
            'percent': 28,
            'trend': 'up'
        },
        'Outgoing': {
            'total': 39,
            'normal': 18,
            'priority': 16,
            'urgent': 5,
            'percent': 31,
            'trend': 'up'
        },
        'Ended': {
            'total': 16,
            'normal': 10,
            'priority': 4,
            'urgent': 2,
            'percent': 12,
            'trend': 'down'
        }
    }
    
    # Add average times data
    avg_times = {
        'Incoming': '1.5 days',
        'Pending': '3.2 days',
        'Received': '2.8 days',
        'Outgoing': '1.7 days',
        'Ended': '4.5 days'
    }
    
    # Prepare JSON data for charts
    status_chart_data = json.dumps([
        {'name': 'Incoming', 'value': 23, 'color': '#2196F3'},
        {'name': 'Pending', 'value': 14, 'color': '#FFC107'},
        {'name': 'Received', 'value': 35, 'color': '#4CAF50'},
        {'name': 'Outgoing', 'value': 39, 'color': '#9C27B0'},
        {'name': 'Ended', 'value': 16, 'color': '#F44336'}
    ])
    
    priority_chart_data = json.dumps([
        {'name': 'Normal', 'value': 56, 'color': '#4CAF50'},
        {'name': 'Priority', 'value': 53, 'color': '#FFC107'},
        {'name': 'Urgent', 'value': 18, 'color': '#F44336'}
    ])
    
    return render_template('reports.html', 
                          active_page='reports',
                          filters=filters,
                          report_data=report_data,
                          chart_data=chart_data,
                          status_data=status_data,
                          avg_times=avg_times,
                          total_documents=127,
                          status_chart_data=status_chart_data,
                          priority_chart_data=priority_chart_data)

@app.route('/maintenance')
def maintenance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # In debug mode, allow all users to access maintenance
    # if session.get('role') != 'Administrator':
    #     flash('You do not have permission to access maintenance', 'danger')
    #     return redirect(url_for('dashboard'))
    
    # Add dummy data needed for the maintenance template
    maintenance_stats = {
        'database_size': '5.2 MB',
        'last_backup': datetime.now() - timedelta(days=2),
        'logs_size': '1.8 MB',
        'system_uptime': '23 days, 7 hours',
        'users_active': 14,
        'documents_total': 257
    }
    
    # Add performance data for the template
    performance_data = {
        'response_time': '120 ms',
        'cpu_usage': '24%',
        'memory_usage': '512 MB',
        'disk_io': '3.2 MB/s',
        'network_io': '1.8 MB/s',
        'average_load': '0.42'
    }
    
    # Add recent logs
    recent_logs = [
        {
            'timestamp': datetime.now() - timedelta(hours=1),
            'action': 'Backup',
            'log_type': 'Success',
            'user': 'admin',
            'details': 'Database backup completed successfully'
        },
        {
            'timestamp': datetime.now() - timedelta(hours=2),
            'action': 'Optimize',
            'log_type': 'Success',
            'user': 'admin',
            'details': 'Database optimization completed'
        },
        {
            'timestamp': datetime.now() - timedelta(hours=6),
            'action': 'Vacuum',
            'log_type': 'Success',
            'user': 'admin',
            'details': 'Database vacuum process completed'
        }
    ]
    
    return render_template('maintenance_dashboard.html', 
                          active_page='maintenance',
                          maintenance_stats=maintenance_stats,
                          performance_data=performance_data,
                          recent_logs=recent_logs)

@app.route('/maintenance_action', methods=['POST'])
def maintenance_action():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    action = request.form.get('action', '')
    
    # Handle different maintenance actions
    if action == 'backup':
        flash('Database backup created successfully', 'success')
    elif action == 'cleanup':
        flash('Temporary files have been cleaned up', 'success')
    elif action == 'optimize':
        flash('Database optimization completed', 'success')
    elif action == 'logs':
        flash('System logs have been cleared', 'success')
    else:
        flash(f'Unknown maintenance action: {action}', 'warning')
    
    return redirect(url_for('maintenance'))

@app.route('/incoming_bulk_action', methods=['POST'])
def incoming_bulk_action():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # In debug mode, just flash a message and redirect back
    flash('Bulk action performed on incoming documents', 'success')
    return redirect(url_for('incoming'))

@app.route('/outgoing_bulk_action', methods=['POST'])
def outgoing_bulk_action():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # In debug mode, just flash a message and redirect back
    flash('Bulk action performed on outgoing documents', 'success')
    return redirect(url_for('outgoing'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # In debug mode, just flash a message and redirect back
    flash('Profile updated successfully', 'success')
    return redirect(url_for('my_account'))

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # In debug mode, just flash a message and redirect back
    flash('Password changed successfully', 'success')
    return redirect(url_for('my_account'))

@app.route('/toggle_2fa', methods=['POST'])
def toggle_2fa():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # In debug mode, just flash a message and redirect back
    flash('Two-factor authentication settings updated', 'success')
    return redirect(url_for('my_account'))

@app.route('/debug_login')
def debug_login():
    """Debug route to bypass login for development
    In production, this should be removed
    """
    # Clear any existing session
    session.clear()
    
    # Set session variables for testing
    role = request.args.get('role', 'Administrator')
    
    if role not in ['Administrator', 'User', 'Registry', 'Supervisor']:
        role = 'Administrator'  # Default to Administrator if invalid role
        
    session['user_id'] = 1
    session['username'] = f'{role.lower()}_user'
    session['role'] = role
    
    flash(f'You are now logged in as a {role}', 'success')
    return redirect(url_for('dashboard'))

@app.route('/track/code/<tracking_code>')
def track_by_code(tracking_code):
    if 'user_id' not in session:
        flash('Please log in to track documents.', 'warning')
        return redirect(url_for('login'))
    
    document = None
    error_message = None
    
    # Sample data for demo purposes
    if tracking_code == 'KMR-2023-001':
        document = {
            'tracking_code': 'KMR-2023-001',
            'title': 'Research Proposal: Malaria Prevention Study',
            'document_type': 'Research Proposal',
            'status': 'Processing',
            'date_created': 'March 15, 2023',
            'last_updated': 'April 2, 2023',
            'sender': 'Dr. Jane Smith',
            'sender_department': 'Research',
            'recipient': 'Ethics Committee',
            'recipient_department': 'Administration',
            'current_department': 'Ethics Review',
            'process_time': '18 days',
            'priority': 'Priority',
            'confidentiality': 'Confidential',
            'timeline': [
                {
                    'title': 'Document Created',
                    'time': 'March 15, 2023 - 09:30 AM',
                    'user': 'Dr. Jane Smith',
                    'status': 'Completed',
                    'description': 'Research proposal document was created and submitted for review.'
                },
                {
                    'title': 'Received by Registry',
                    'time': 'March 16, 2023 - 10:15 AM',
                    'user': 'John Doe',
                    'status': 'Completed',
                    'description': 'Document received and validated by registry department.'
                },
                {
                    'title': 'Sent to Ethics Review',
                    'time': 'March 20, 2023 - 02:45 PM',
                    'user': 'John Doe',
                    'status': 'Completed',
                    'description': 'Document forwarded to Ethics Committee for review and approval.',
                    'comments': 'Priority review requested due to funding deadlines.'
                },
                {
                    'title': 'Under Review',
                    'time': 'April 2, 2023 - 11:30 AM',
                    'user': 'Ethics Committee',
                    'status': 'Processing',
                    'description': 'Document is currently being reviewed by the Ethics Committee.'
                }
            ],
            'attachments': [
                {
                    'name': 'Research_Proposal_v1.pdf',
                    'type': 'pdf',
                    'size': '2.4 MB',
                    'date': 'March 15, 2023'
                },
                {
                    'name': 'Budget_Breakdown.xlsx',
                    'type': 'xlsx',
                    'size': '1.2 MB',
                    'date': 'March 15, 2023'
                },
                {
                    'name': 'Participant_Consent_Form.docx',
                    'type': 'docx',
                    'size': '350 KB',
                    'date': 'March 17, 2023'
                }
            ],
            'comments': [
                {
                    'user': 'Dr. Jane Smith',
                    'date': 'March 15, 2023',
                    'content': 'Initial submission of the research proposal for review.'
                },
                {
                    'user': 'John Doe',
                    'date': 'March 16, 2023',
                    'content': 'Document received and processed. Forwarded to management for initial review.'
                },
                {
                    'user': 'Robert Johnson',
                    'date': 'March 20, 2023',
                    'content': 'Please prioritize this review as there are funding deadlines approaching.'
                }
            ]
        }
    elif tracking_code == 'KMR-2023-002':
        document = {
            'tracking_code': 'KMR-2023-002',
            'title': 'Annual Budget Report 2023',
            'document_type': 'Financial Report',
            'status': 'Awaiting Approval',
            'date_created': 'February 10, 2023',
            'last_updated': 'March 25, 2023',
            'sender': 'Finance Department',
            'sender_department': 'Finance',
            'recipient': 'Board of Directors',
            'recipient_department': 'Management',
            'current_department': 'Management',
            'process_time': '43 days',
            'priority': 'Urgent',
            'confidentiality': 'Strictly Confidential',
            'timeline': [
                {
                    'title': 'Document Created',
                    'time': 'February 10, 2023 - 11:45 AM',
                    'user': 'Finance Team',
                    'status': 'Completed',
                    'description': 'Annual budget report was compiled and submitted.'
                },
                {
                    'title': 'Initial Review',
                    'time': 'February 15, 2023 - 09:30 AM',
                    'user': 'CFO Office',
                    'status': 'Completed',
                    'description': 'Initial review completed by the CFO office.',
                    'comments': 'Some revisions needed in Q3 projections.'
                },
                {
                    'title': 'Revisions Made',
                    'time': 'March 5, 2023 - 02:15 PM',
                    'user': 'Finance Team',
                    'status': 'Completed',
                    'description': 'Revisions completed based on CFO recommendations.'
                },
                {
                    'title': 'Forwarded to Board',
                    'time': 'March 10, 2023 - 10:00 AM',
                    'user': 'CFO Office',
                    'status': 'Completed',
                    'description': 'Final report forwarded to Board of Directors for approval.'
                },
                {
                    'title': 'Board Review',
                    'time': 'March 25, 2023 - 03:30 PM',
                    'user': 'Board Secretary',
                    'status': 'Awaiting Approval',
                    'description': 'Document is awaiting final approval from the Board of Directors.'
                }
            ],
            'attachments': [
                {
                    'name': 'Annual_Budget_2023.pdf',
                    'type': 'pdf',
                    'size': '4.8 MB',
                    'date': 'February 10, 2023'
                },
                {
                    'name': 'Financial_Projections.xlsx',
                    'type': 'xlsx',
                    'size': '2.7 MB',
                    'date': 'February 10, 2023'
                },
                {
                    'name': 'Budget_Presentation.pptx',
                    'type': 'ppt',
                    'size': '5.2 MB',
                    'date': 'March 5, 2023'
                },
                {
                    'name': 'Revision_Summary.pdf',
                    'type': 'pdf',
                    'size': '1.3 MB',
                    'date': 'March 5, 2023'
                }
            ],
            'comments': [
                {
                    'user': 'Finance Team',
                    'date': 'February 10, 2023',
                    'content': 'Final version of the annual budget submitted for review and approval.'
                },
                {
                    'user': 'CFO',
                    'date': 'February 15, 2023',
                    'content': 'Please revise the Q3 projections based on the updated forecast data.'
                },
                {
                    'user': 'Finance Team',
                    'date': 'March 5, 2023',
                    'content': 'Revisions completed as requested. All projections now align with the latest forecast models.'
                },
                {
                    'user': 'Board Secretary',
                    'date': 'March 25, 2023',
                    'content': 'Document received by the Board. Will be reviewed in the upcoming meeting on April 5.'
                }
            ]
        }
    else:
        error_message = f"No document found with tracking code: {tracking_code}"
    
    return render_template('track_by_code.html', document=document, error_message=error_message)

@app.route('/api/document/notify', methods=['POST'])
def document_notify():
    """API endpoint to notify external stakeholders when document status changes.
    
    This would integrate with email, SMS, or mobile push notifications
    to keep all parties informed about document status changes.
    """
    if request.method == 'POST':
        data = request.json
        if not data or 'tracking_code' not in data:
            return jsonify({'error': 'Missing tracking_code parameter'}), 400
            
        tracking_code = data.get('tracking_code')
        notify_method = data.get('method', 'email')  # email, sms, push
        recipients = data.get('recipients', [])
        
        # In a real implementation, this would:
        # 1. Validate the tracking code exists
        # 2. Send notifications to the recipients via the specified method
        # 3. Log the notification for audit purposes
        
        # For demo purposes, just return success
        return jsonify({
            'success': True,
            'message': f'Notification about document {tracking_code} would be sent to {len(recipients)} recipients via {notify_method}',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    return jsonify({'error': 'Method not allowed'}), 405

@app.route('/update_document_status/<tracking_code>', methods=['POST'])
def update_document_status(tracking_code):
    """Update a document's status and create an audit trail entry"""
    if 'user_id' not in session:
        flash('Please log in to update document status', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_status = request.form.get('status')
        comments = request.form.get('comments', '')
        department = request.form.get('department', '')
        
        # In a real app, we would update the database
        # For demo purposes, just flash a message and redirect
        
        flash(f'Document {tracking_code} status updated to {new_status}', 'success')
        
        # In a real implementation, we would also:
        # 1. Add an entry to the document history/audit trail
        # 2. Send notifications to interested parties
        # 3. Update the document's location/holder information
        
        # Redirect back to the document tracking page
        return redirect(url_for('track_by_code', tracking_code=tracking_code))
    
    # This should never be reached since we only accept POST requests
    return redirect(url_for('track_document'))

@app.route('/registry_approval', methods=['GET'])
def registry_approval():
    """Registry page to approve or reject documents"""
    if 'user_id' not in session:
        flash('Please log in to access registry approval', 'warning')
        return redirect(url_for('login'))
    
    # In a real implementation, check if user has registry privileges
    # For demo purposes, assume the user can access if they are an Administrator
    if session.get('role') not in ['Administrator', 'Registry']:
        flash('You do not have permission to access the registry workflow', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get pending documents from the database
    # For demo, generate sample data
    pending_approvals = []
    
    for i in range(1, 8):
        # Create demo document
        doc_date = datetime.now() - timedelta(days=i % 3)
        tracking_code = f"KEMRI-{doc_date.strftime('%Y%m%d')}-{1000+i}"
        
        document = {
            'id': i,
            'tracking_code': tracking_code,
            'title': f"Document {i} requiring approval",
            'sender': f"Department {i % 5 + 1}",
            'recipient': f"Recipient {i % 3 + 1}",
            'date_submitted': doc_date.strftime('%Y-%m-%d %H:%M'),
            'priority': ['Normal', 'Priority', 'Urgent'][i % 3],
            'document_type': ['Letter', 'Report', 'Requisition', 'Application', 'Memo'][i % 5],
            'status': 'Pending Registry Approval'
        }
        pending_approvals.append(document)
    
    # Calculate stats for the page
    approved_today = 3  # Simulated count for demo
    rejected_today = 1  # Simulated count for demo
    avg_time = '1.5h'   # Simulated average processing time
    
    return render_template(
        'registry_workflow.html', 
        pending_approvals=pending_approvals,
        approved_today=approved_today,
        rejected_today=rejected_today,
        avg_time=avg_time,
        active_page='registry_approval'
    )

@app.route('/registry_decision/<tracking_code>', methods=['POST'])
def registry_decision(tracking_code):
    """Handle registry decision on a document"""
    if 'user_id' not in session:
        flash('Please log in to make registry decisions', 'warning')
        return redirect(url_for('login'))
    
    decision = request.form.get('decision')
    comments = request.form.get('comments', '')
    next_department = request.form.get('department', '')
    
    # In a real implementation, update the database with the decision
    # For demo, just flash a message
    if decision == 'approve':
        flash(f'Document {tracking_code} has been approved and forwarded to {next_department}', 'success')
    elif decision == 'reject':
        flash(f'Document {tracking_code} has been rejected with comments: {comments}', 'warning')
    else:
        flash(f'Document {tracking_code} has been put on hold with comments: {comments}', 'info')
    
    # Redirect back to approval page
    return redirect(url_for('registry_approval'))

@app.route('/update_incoming_status/<doc_code>', methods=['POST'])
def update_incoming_status(doc_code):
    """Update the status of an incoming document"""
    if 'user_id' not in session:
        flash('Please log in to update document status', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_status = request.form.get('status')
        
        # In a real app, update the database with the new status
        # For demo purposes, just flash a message
        flash(f'Document {doc_code} status updated to {new_status}', 'success')
        
        # Log the status change in the document history
        # This would be done in a real implementation
        
        return redirect(url_for('document_details', doc_code=doc_code))
    
    return redirect(url_for('incoming'))

@app.route('/update_outgoing_status/<doc_code>', methods=['POST'])
def update_outgoing_status(doc_code):
    """Update the status of an outgoing document"""
    if 'user_id' not in session:
        flash('Please log in to update document status', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_status = request.form.get('status')
        
        # In a real app, update the database with the new status
        # For demo purposes, just flash a message
        flash(f'Document {doc_code} status updated to {new_status}', 'success')
        
        # Log the status change in the document history
        # This would be done in a real implementation
        
        return redirect(url_for('document_details', doc_code=doc_code))
    
    return redirect(url_for('outgoing'))

@app.route('/confirm_document_receipt/<document_code>/<int:transfer_id>', methods=['POST'])
def confirm_document_receipt(document_code, transfer_id):
    """Confirm receipt of a transferred document"""
    if 'user_id' not in session:
        flash('Please log in to confirm document receipt', 'warning')
        return redirect(url_for('login'))
    
    # In a real app, update the database to mark the transfer as received
    # For demo purposes, just flash a message
    flash(f'Document {document_code} receipt confirmed', 'success')
    
@app.route('/download/<filename>')
def download_file(filename):
    """Download a file from the uploads directory"""
    if 'user_id' not in session:
        flash('Please log in to download files', 'warning')
        return redirect(url_for('login'))
    
    # Ensure the filename is secure and exists
    if not filename or '..' in filename:
        flash('Invalid file request', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Check if file exists
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.isfile(file_path):
            flash('File not found', 'danger')
            return redirect(url_for('dashboard'))
        
        # Get original filename from the secured filename
        # In a real app, you'd retrieve this from the database
        # Here we're extracting it from the pattern [document_id]_[timestamp]_[original_filename]
        parts = filename.split('_', 2)
        original_filename = parts[2] if len(parts) >= 3 else filename
        
        # Return the file as an attachment
        return send_from_directory(
            directory=app.config['UPLOAD_FOLDER'],
            path=filename,
            as_attachment=True,
            download_name=original_filename
        )
    except Exception as e:
        app.logger.error(f"File download error: {str(e)}")
        flash('An error occurred while trying to download the file', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/file_manager', methods=['GET', 'POST'])
def file_manager():
    """View and manage uploaded files"""
    if 'user_id' not in session:
        flash('Please log in to access the file manager', 'warning')
        return redirect(url_for('login'))
    
    # Sample files for demonstration
    sample_files = [
        {
            'id': 1, 
            'filename': 'KMR001_2023_Annual_Report.pdf', 
            'original_filename': 'Annual Report 2023.pdf',
            'document_id': 'KMR001',
            'file_size': 2500000,
            'file_size_readable': '2.4 MB',
            'file_type': 'pdf',
            'modified_date': '2023-12-15 14:30:22',
            'department': 'Research'
        },
        {
            'id': 2, 
            'filename': 'KMR002_2023_Lab_Results_Q1.xlsx', 
            'original_filename': 'Lab Results Q1.xlsx',
            'document_id': 'KMR002',
            'file_size': 1200000,
            'file_size_readable': '1.2 MB',
            'file_type': 'xlsx',
            'modified_date': '2023-11-10 09:15:43',
            'department': 'Laboratory'
        },
        {
            'id': 3, 
            'filename': 'KMR003_2023_Project_Proposal.docx', 
            'original_filename': 'Project Proposal.docx',
            'document_id': 'KMR003',
            'file_size': 890000,
            'file_size_readable': '890 KB',
            'file_type': 'docx',
            'modified_date': '2023-12-01 16:45:11',
            'department': 'Projects'
        },
        {
            'id': 4, 
            'filename': 'KMR004_2023_Budget_2024.xlsx', 
            'original_filename': 'Budget 2024.xlsx',
            'document_id': 'KMR004',
            'file_size': 1500000,
            'file_size_readable': '1.5 MB',
            'file_type': 'xlsx',
            'modified_date': '2023-12-20 10:05:38',
            'department': 'Finance'
        },
        {
            'id': 5, 
            'filename': 'KMR005_2023_Meeting_Minutes.pdf', 
            'original_filename': 'Meeting Minutes.pdf',
            'document_id': 'KMR005',
            'file_size': 450000,
            'file_size_readable': '450 KB',
            'file_type': 'pdf',
            'modified_date': '2023-12-18 13:20:17',
            'department': 'Administration'
        }
    ]
    
    # Filter files based on search query if provided
    search_query = request.args.get('search', '')
    files = sample_files
    
    if search_query:
        files = [file for file in files if 
                search_query.lower() in file['original_filename'].lower() or 
                search_query.lower() in file['document_id'].lower() or 
                search_query.lower() in file['file_type'].lower() or 
                search_query.lower() in file.get('department', '').lower()]
    
    # Handle file upload (POST request)
    if request.method == 'POST':
        # Check if file part exists in the request
        if 'file' not in request.files:
            flash('No file part in the request', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user does not select file, the browser submits an empty file
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # In a real app, this would save the file and update the database
            # For demo purposes, we'll just simulate success
            flash('File uploaded successfully', 'success')
            return redirect(url_for('file_manager'))
        else:
            flash('File type not allowed', 'danger')
            return redirect(request.url)
    
    return render_template(
        'file_manager.html',
        active_page='file_manager',
        files=files,
        total_files=len(files),
        total_size=get_human_readable_size(sum(f['file_size'] for f in files)),
        search_query=search_query
    )

@app.route('/delete_file/<filename>', methods=['POST'])
def delete_file(filename):
    """Delete a file from the uploads directory"""
    if 'user_id' not in session:
        flash('Please log in to delete files', 'warning')
        return redirect(url_for('login'))
    
    # Check if user has permission to delete files
    if session.get('role') != 'Administrator':
        flash('You do not have permission to delete files', 'danger')
        return redirect(url_for('file_manager'))
    
    # Ensure the filename is secure and exists
    if not filename or '..' in filename:
        flash('Invalid file request', 'danger')
        return redirect(url_for('file_manager'))
    
    try:
        # For demo purposes, we'll just simulate success
        # In a real app, this would check if the file exists and delete it
        flash(f'File {filename} deleted successfully', 'success')
        return redirect(url_for('file_manager'))
    except Exception as e:
        app.logger.error(f"File deletion error: {str(e)}")
        flash('An error occurred while trying to delete the file', 'danger')
        return redirect(url_for('file_manager'))

@app.route('/add_user', methods=['POST'])
def add_user():
    """Add a new user to the system"""
    if 'user_id' not in session:
        flash('Please log in to access this feature', 'warning')
        return redirect(url_for('login'))
    
    if session['role'] != 'Administrator':
        flash('You do not have permission to add users', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get form data
    username = request.form.get('username')
    email = request.form.get('email')
    role = request.form.get('role')
    department = request.form.get('department', '')
    password = request.form.get('password', 'defaultpassword')  # In production, you should generate a secure password
    
    # Validate required fields
    if not username or not email or not role:
        flash('Username, email, and role are required fields', 'danger')
        return redirect(url_for('user_management'))
    
    try:
        # Connect to database
        conn = get_db_connection()
        
        # Check if username already exists
        existing_user = conn.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()
        if existing_user:
            flash(f'Username "{username}" already exists', 'danger')
            conn.close()
            return redirect(url_for('user_management'))
        
        # Check if email already exists
        existing_email = conn.execute('SELECT * FROM user WHERE email = ?', (email,)).fetchone()
        if existing_email:
            flash(f'Email "{email}" is already registered', 'danger')
            conn.close()
            return redirect(url_for('user_management'))
        
        # Insert new user
        conn.execute(
            'INSERT INTO user (username, email, password, role, department, is_active) VALUES (?, ?, ?, ?, ?, ?)',
            (username, email, password, role, department, 1)
        )
        conn.commit()
        conn.close()
        
        flash(f'User "{username}" created successfully', 'success')
    except Exception as e:
        flash(f'Error creating user: {str(e)}', 'danger')
    
    return redirect(url_for('user_management'))

if __name__ == '__main__':
    # Ensure the database exists
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file {DB_PATH} not found!")
        print("Please run init_db.py to create the database first.")
        exit(1)
    
    app.run(host='0.0.0.0', port=5000, debug=True) 