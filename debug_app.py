from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify, send_from_directory
import sqlite3
import os
from werkzeug.routing.exceptions import BuildError
from datetime import datetime, timedelta
import json
import random
from werkzeug.utils import secure_filename
from permissions import requires_permission, requires_role, requires_login, has_permission, can_access_menu, log_activity, check_session_valid
import time
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

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

# Function to convert bytes to human-readable size
def get_human_readable_size(size_bytes):
    """
    Convert a size in bytes to a human-readable string (KB, MB, GB).
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Human-readable size string
    """
    if size_bytes is None or size_bytes == 0:
        return "0B"
    
    try:
        size_bytes = float(size_bytes)
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024
            i += 1
        
        return f"{size_bytes:.2f} {size_names[i]}"
    except (TypeError, ValueError):
        return "0B"

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

# Add permissions functions to Jinja environment
app.jinja_env.globals['has_endpoint'] = has_endpoint
app.jinja_env.globals['has_permission'] = has_permission
app.jinja_env.globals['can_access_menu'] = can_access_menu
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
        
        if user:
            # Verify the password with the stored hash
            if check_password_hash(user['password'], password):
                session.clear()  # Ensure we start with a clean session
                
                # Check if user is active
                if 'is_active' in user.keys() and user['is_active'] != 1:
                    flash('Your account is inactive. Please contact an administrator.', 'danger')
                    conn.close()
                    return render_template('login.html', debug_mode=False)
                
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                # Use dictionary access with a default value if the column doesn't exist
                session['department'] = user['department'] if 'department' in user.keys() else 'None'
                session['email'] = user['email'] if 'email' in user.keys() else ''
                session['last_activity'] = time.time()
                
                # Log login activity
                log_activity(user['id'], 'login', {
                    'username': username,
                    'method': 'password',
                    'ip': request.remote_addr
                })
                
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'danger')
                conn.close()
        else:
            flash('Invalid username or password.', 'danger')
            conn.close()
    
    # Set debug_mode to False in production
    debug_mode = False  # Change to True only during development/testing
    
    return render_template('login.html', debug_mode=debug_mode)

@app.route('/dashboard')
@requires_login
def dashboard():
    """Main dashboard page"""
    # If user is not logged in, redirect to login
    if not check_session_valid():
        flash('Please log in to access the dashboard', 'warning')
        return redirect(url_for('login'))
    
    # Log this access
    log_activity(session.get('user_id'), 'view_dashboard', {'request': 'view'})
    
    # Sample dashboard data
    # In a real app, this would be fetched from the database
    role = session.get('role', 'User')
    is_admin = role == 'Administrator'
    is_registry = role == 'Registry'
    
    # Different stats based on role
    if is_admin:
        # Admin sees system-wide stats
        stats = {
            'total_documents': 127,
            'pending_approval': 14,
            'documents_today': 8,
            'active_users': 18
        }
    elif is_registry:
        # Registry staff see document processing stats
        stats = {
            'total_documents': 127,
            'pending_approval': 14,
            'to_be_processed': 6,
            'processed_today': 12
        }
    else:
        # Regular users see their own document stats
        stats = {
            'my_documents': 15,
            'pending_approval': 3,
            'completed': 8,
            'drafts': 4
        }
    
    # Recent activity for the dashboard
    recent_activity = [
        {'type': 'document', 'action': 'created', 'title': 'Research Proposal', 'time': '2 hours ago'},
        {'type': 'document', 'action': 'approved', 'title': 'Budget Request', 'time': '4 hours ago'},
        {'type': 'user', 'action': 'login', 'title': 'System Login', 'time': '5 hours ago'},
        {'type': 'document', 'action': 'rejected', 'title': 'Equipment Request', 'time': '1 day ago'},
        {'type': 'document', 'action': 'modified', 'title': 'Project Timeline', 'time': '2 days ago'}
    ]
    
    # Only show notifications relevant to user role
    notifications = []
    
    if is_admin:
        notifications.extend([
            {'type': 'system', 'message': 'Database backup completed successfully', 'time': '1 hour ago'},
            {'type': 'user', 'message': '2 new user registrations pending approval', 'time': '3 hours ago'}
        ])
    
    if is_admin or is_registry:
        notifications.extend([
            {'type': 'document', 'message': '14 documents awaiting registry approval', 'time': '2 hours ago'},
            {'type': 'workflow', 'message': '3 workflows completed today', 'time': '4 hours ago'}
        ])
    
    # All users see these notifications
    notifications.extend([
        {'type': 'document', 'message': 'Your document "Budget Request" was approved', 'time': '5 hours ago'},
        {'type': 'message', 'message': 'You have 3 unread messages', 'time': '1 day ago'}
    ])
    
    return render_template('dashboard.html', 
                           stats=stats,
                           recent_activity=recent_activity,
                           notifications=notifications,
                           user_role=role)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/user-management', methods=['GET', 'POST'])
@requires_permission('view_users')
def user_management():
    """User management page"""
    # Log this action
    log_activity(session.get('user_id'), 'view_user_management', {'request': 'view'})
    
    # Handle POST request for adding a new user
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        full_name = request.form.get('fullName')
        email = request.form.get('email')
        phone = request.form.get('phone', '')
        department = request.form.get('department')
        role = request.form.get('role')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')
        
        # Basic validation
        if not username or not email or not department or not role or not password:
            flash('All required fields must be filled', 'danger')
            return redirect(url_for('user_management'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('user_management'))
        
        # Check if username or email already exists
        conn = get_db_connection()
        existing_user = conn.execute('SELECT id FROM user WHERE username = ? OR email = ?', 
                                    (username, email)).fetchone()
        
        if existing_user:
            conn.close()
            flash('Username or email already exists', 'danger')
            return redirect(url_for('user_management'))
        
        # Add new user to database
        try:
            # Hash the password
            hashed_password = generate_password_hash(password)
            
            conn.execute(
                'INSERT INTO user (username, email, phone, department, password, role, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (username, email, phone, department, hashed_password, role, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1)
            )
            conn.commit()
            conn.close()
            
            # Log this action
            log_activity(session.get('user_id'), 'add_user', {
                'username': username,
                'email': email,
                'department': department,
                'role': role
            })
            
            flash(f'User {username} has been added successfully', 'success')
        except Exception as e:
            conn.close()
            print(f"Error adding user: {e}")
            flash(f'Error adding user: {str(e)}', 'danger')
        
        return redirect(url_for('user_management'))
    
    # GET request - display user management page
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM user ORDER BY username').fetchall()
    conn.close()
    
    # Comprehensive list of KEMRI departments
    departments = [
        'Central Registry', 
        'IT', 
        'Finance', 
        'HR', 
        'Research', 
        'Laboratory',
        'Clinical Research',
        'Virology',
        'Microbiology',
        'Parasitology',
        'Immunology',
        'Molecular Biology',
        'Epidemiology',
        'Public Health',
        'Administration',
        'Executive Office',
        'Communications',
        'Quality Assurance',
        'Procurement',
        'Legal Affairs',
        'Ethics Review Committee',
        'Grants Management',
        'Biorepository',
        'Bioinformatics'
    ]
    
    # Available roles
    roles = ['Administrator', 'Registry', 'Supervisor', 'User', 'Viewer', 'Manager']
    
    # Custom JavaScript for password visibility toggle
    password_toggle_script = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Add toggle password functionality
        document.querySelectorAll('.toggle-password').forEach(function(button) {
            button.addEventListener('click', function() {
                const targetId = this.getAttribute('data-target');
                const passwordInput = document.getElementById(targetId);
                
                // Toggle password visibility
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    this.innerHTML = '<i class="fas fa-eye-slash"></i>';
                    this.setAttribute('title', 'Hide Password');
                } else {
                    passwordInput.type = 'password';
                    this.innerHTML = '<i class="fas fa-eye"></i>';
                    this.setAttribute('title', 'Show Password');
                }
            });
        });

        // Add password toggle buttons to all password fields
        document.querySelectorAll('input[type="password"]').forEach(function(input) {
            if (!input.parentElement.classList.contains('input-group')) {
                const inputId = input.getAttribute('id');
                const inputGroup = document.createElement('div');
                inputGroup.classList.add('input-group');
                
                // Clone the input to preserve all its attributes and event listeners
                const newInput = input.cloneNode(true);
                
                // Create the toggle button
                const toggleButton = document.createElement('button');
                toggleButton.classList.add('btn', 'btn-outline-secondary', 'toggle-password');
                toggleButton.setAttribute('type', 'button');
                toggleButton.setAttribute('data-target', inputId);
                toggleButton.setAttribute('title', 'Show Password');
                toggleButton.innerHTML = '<i class="fas fa-eye"></i>';
                
                // Add event listener to the new button
                toggleButton.addEventListener('click', function() {
                    const targetId = this.getAttribute('data-target');
                    const passwordInput = document.getElementById(targetId);
                    
                    // Toggle password visibility
                    if (passwordInput.type === 'password') {
                        passwordInput.type = 'text';
                        this.innerHTML = '<i class="fas fa-eye-slash"></i>';
                        this.setAttribute('title', 'Hide Password');
                    } else {
                        passwordInput.type = 'password';
                        this.innerHTML = '<i class="fas fa-eye"></i>';
                        this.setAttribute('title', 'Show Password');
                    }
                });
                
                // Replace the input with the input group
                input.parentNode.replaceChild(inputGroup, input);
                inputGroup.appendChild(newInput);
                inputGroup.appendChild(toggleButton);
            }
        });
    });
    </script>
    """
    
    return render_template('user_management.html', 
                           users=users, 
                           roles=roles, 
                           departments=departments,
                           additional_scripts=password_toggle_script)

@app.route('/user-management-enhanced')
@requires_permission('view_users')
def user_management_enhanced():
    """Enhanced user management page with dashboard and advanced features"""
    # Log this activity
    log_activity(session.get('user_id'), 'view_enhanced_user_management', {'request': 'view'})
    
    # Get all users from the database
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM user ORDER BY username').fetchall()
    
    # Count active/inactive users
    try:
        active_users_count = conn.execute('SELECT COUNT(*) FROM user WHERE is_active = 1').fetchone()[0]
        inactive_users_count = conn.execute('SELECT COUNT(*) FROM user WHERE is_active = 0 OR is_active IS NULL').fetchone()[0]
    except Exception as e:
        print(f"Error counting active/inactive users: {e}")
        active_users_count = 0
        inactive_users_count = 0
    
    # Comprehensive list of KEMRI departments
    departments = [
        'Central Registry', 
        'IT', 
        'Finance', 
        'HR', 
        'Research', 
        'Laboratory',
        'Clinical Research',
        'Virology',
        'Microbiology',
        'Parasitology',
        'Immunology',
        'Molecular Biology',
        'Epidemiology',
        'Public Health',
        'Administration',
        'Executive Office',
        'Communications',
        'Quality Assurance',
        'Procurement',
        'Legal Affairs',
        'Ethics Review Committee',
        'Grants Management',
        'Biorepository',
        'Bioinformatics'
    ]
    
    # Available roles
    roles = ['Administrator', 'Registry', 'Supervisor', 'User', 'Viewer', 'Manager']
    
    # Count users by role
    role_counts = {}
    for role in roles:
        count = conn.execute('SELECT COUNT(*) FROM user WHERE role = ?', (role,)).fetchone()[0]
        role_counts[role] = count
    
    # Count users by department
    department_counts = {}
    for dept in departments:
        count = conn.execute('SELECT COUNT(*) FROM user WHERE department = ?', (dept,)).fetchone()[0]
        department_counts[dept] = count
    
    conn.close()
    
    # Custom JavaScript for password visibility toggle (same as in user_management)
    password_toggle_script = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Add toggle password functionality
        document.querySelectorAll('.toggle-password').forEach(function(button) {
            button.addEventListener('click', function() {
                const targetId = this.getAttribute('data-target');
                const passwordInput = document.getElementById(targetId);
                
                // Toggle password visibility
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    this.innerHTML = '<i class="fas fa-eye-slash"></i>';
                    this.setAttribute('title', 'Hide Password');
                } else {
                    passwordInput.type = 'password';
                    this.innerHTML = '<i class="fas fa-eye"></i>';
                    this.setAttribute('title', 'Show Password');
                }
            });
        });

        // Add password toggle buttons to all password fields
        document.querySelectorAll('input[type="password"]').forEach(function(input) {
            if (!input.parentElement.classList.contains('input-group')) {
                const inputId = input.getAttribute('id');
                const inputGroup = document.createElement('div');
                inputGroup.classList.add('input-group');
                
                // Clone the input to preserve all its attributes and event listeners
                const newInput = input.cloneNode(true);
                
                // Create the toggle button
                const toggleButton = document.createElement('button');
                toggleButton.classList.add('btn', 'btn-outline-secondary', 'toggle-password');
                toggleButton.setAttribute('type', 'button');
                toggleButton.setAttribute('data-target', inputId);
                toggleButton.setAttribute('title', 'Show Password');
                toggleButton.innerHTML = '<i class="fas fa-eye"></i>';
                
                // Add event listener to the new button
                toggleButton.addEventListener('click', function() {
                    const targetId = this.getAttribute('data-target');
                    const passwordInput = document.getElementById(targetId);
                    
                    // Toggle password visibility
                    if (passwordInput.type === 'password') {
                        passwordInput.type = 'text';
                        this.innerHTML = '<i class="fas fa-eye-slash"></i>';
                        this.setAttribute('title', 'Hide Password');
                    } else {
                        passwordInput.type = 'password';
                        this.innerHTML = '<i class="fas fa-eye"></i>';
                        this.setAttribute('title', 'Show Password');
                    }
                });
                
                // Replace the input with the input group
                input.parentNode.replaceChild(inputGroup, input);
                inputGroup.appendChild(newInput);
                inputGroup.appendChild(toggleButton);
            }
        });
    });
    </script>
    """
    
    return render_template('user_management_enhanced.html', 
                          users=users, 
                          roles=roles, 
                          departments=departments,
                          active_users=active_users_count,
                          inactive_users=inactive_users_count,
                          role_counts=role_counts,
                          department_counts=department_counts,
                          additional_scripts=password_toggle_script)

@app.errorhandler(BuildError)
def handle_build_error(error):
    print(f"BuildError: {error}")
    error_str = str(error)
    
    # Provide specific guidance based on the missing endpoint
    if "add_attachment" in error_str:
        flash("Document attachment functionality is not available in debug mode", "warning")
        return redirect(url_for('dashboard'))
    elif "debug_login" in error_str:
        flash("Debug login is not available. Please use the standard login form", "warning")
        return redirect(url_for('login'))
    elif "reassign_document" in error_str:
        flash("Document reassignment is not available in debug mode", "warning")
        return redirect(url_for('dashboard'))
    else:
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
@requires_permission('track_document')
def track_document():
    """Document tracking page with search functionality"""
    # Log this action
    log_activity(session.get('user_id'), 'view_track_document', {'request': 'view'})
    
    search_results = None
    recent_documents = None
    error_message = None
    
    if request.method == 'POST':
        # Handle tracking code search
        tracking_code = request.form.get('tracking_code')
        if tracking_code:
            # In a real app, search the database for this tracking code
            # For demonstration, return a redirect to a details page with sample data
            
            # Simulate tracking code validation
            if tracking_code.startswith('KMR-'):
                # Valid tracking code format
                return redirect(url_for('track_by_code', tracking_code=tracking_code))
            else:
                error_message = f"Invalid tracking code format: {tracking_code}. Please use format KMR-YYYY-XXX."
                
    elif request.method == 'GET':
        # Handle advanced search by fields
        if any(field in request.args for field in ['sender', 'recipient', 'status', 'date_range']):
            sender = request.args.get('sender', '')
            recipient = request.args.get('recipient', '')
            status = request.args.get('status', '')
            date_range = request.args.get('date_range', '')
            
            # In a real app, search the database using these parameters
            # For demonstration, return sample results
            search_results = [
                {
                    'tracking_code': 'KMR-2023-001',
                    'title': 'Research Proposal: Malaria Prevention Study',
                    'sender': 'Dr. Jane Smith',
                    'recipient': 'Ethics Committee', 
                    'status': 'Processing',
                    'date_created': 'March 15, 2023',
                    'priority': 'Priority'
                },
                {
                    'tracking_code': 'KMR-2023-002',
                    'title': 'Annual Budget Report 2023',
                    'sender': 'Finance Department',
                    'recipient': 'Board of Directors',
                    'status': 'Awaiting Approval',
                    'date_created': 'February 10, 2023',
                    'priority': 'Urgent'
                }
            ]
    
    # For initial page load, show recent documents
    if not search_results and not error_message:
        # In a real app, get recent documents from database
        # For demonstration, return sample data
        recent_documents = []
        for i in range(1, 6):
            doc_date = datetime.now() - timedelta(days=i)
            doc = {
                'tracking_code': f'KMR-2023-00{i}',
                'title': f'Sample Document {i}',
                'sender': f'Department {i}',
                'recipient': f'Recipient {i}',
                'status': ['Received', 'Processing', 'Completed', 'Pending', 'Awaiting Approval'][i-1],
                'date_created': doc_date.strftime('%B %d, %Y'),
                'priority': ['Normal', 'Priority', 'Urgent'][i % 3]
            }
            recent_documents.append(doc)
    
    return render_template('track_document.html',
                          search_results=search_results,
                          recent_documents=recent_documents,
                          error_message=error_message)

@app.route('/document_details/<doc_code>')
def document_details(doc_code):
    """View document details page"""
    if 'user_id' not in session:
        flash('Please log in to view document details', 'warning')
        return redirect(url_for('login'))
    
    try:
        # In a real app, fetch document data from database
        # For demo purposes, create a sample document
        document = None
        
        # Check if document exists in session
        if 'composed_documents' in session:
            for doc in session['composed_documents']:
                if doc.get('code') == doc_code or doc.get('tracking_code') == doc_code:
                    document = doc
                    break
        
        # If not found in session, create a demo document
        if not document:
            # Create sample document based on doc_code format
            if doc_code.startswith('KEMRI-') or doc_code.startswith('KMR-'):
                document = {
                    'id': 1,
                    'code': doc_code,
                    'tracking_code': doc_code,
                    'title': f'Document {doc_code}',
                    'type': 'Outgoing',
                    'sender': 'KEMRI Laboratory',
                    'recipient': 'Ministry of Health',
                    'date_created': datetime.now().strftime('%Y-%m-%d'),
                    'date_submitted': datetime.now().strftime('%Y-%m-%d'),
                    'status': 'Pending Registry Approval',
                    'priority': 'Normal',
                    'details': 'This is a sample document for demonstration purposes.',
                    'required_action': 'Review',
                    'current_department': 'Registry',
                    'attachments': [
                        {'name': 'sample_attachment.pdf', 'size': '245 KB', 'date_uploaded': datetime.now().strftime('%Y-%m-%d')}
                    ],
                    'history': [
                        {
                            'action': 'Document Created',
                            'user': 'System Administrator',
                            'timestamp': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                            'notes': 'Document initialized in the system'
                        },
                        {
                            'action': 'Document Submitted',
                            'user': 'System Administrator',
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'notes': 'Document submitted for processing'
                        }
                    ]
                }
            else:
                # Generate a document for DOC-YYYY-XXX format codes
                document = {
                    'id': 1,
                    'code': doc_code,
                    'title': f'Sample Document {doc_code}',
                    'type': 'Incoming',
                    'sender': 'External Organization',
                    'recipient': 'KEMRI Laboratory',
                    'date_received': datetime.now().strftime('%Y-%m-%d'),
                    'status': 'Incoming',
                    'priority': 'Normal',
                    'details': 'This is a sample document for demonstration purposes.',
                    'current_holder': 'Registry Department',
                    'attachments': [
                        {'name': 'sample_document.pdf', 'size': '1.2 MB', 'date_uploaded': datetime.now().strftime('%Y-%m-%d')}
                    ],
                    'history': [
                        {
                            'action': 'Document Received',
                            'user': 'Registry Officer',
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'notes': 'Document received and entered into the system'
                        }
                    ]
                }
        
        # Get comments from session if they exist
        comments = []
        if 'document_comments' in session and doc_code in session['document_comments']:
            comments = session['document_comments'][doc_code]
        
        return render_template('document_details.html', 
                              document=document,
                              comments=comments,
                              doc_code=doc_code,
                              active_page='documents')
    except Exception as e:
        # Log the error
        print(f"Error viewing document details for {doc_code}: {str(e)}")
        flash(f'Error viewing document details: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/add_document_comment/<document_code>', methods=['POST'])
def add_document_comment(document_code):
    """Add a comment to a document"""
    if 'username' not in session:
        flash('You must be logged in to add comments', 'warning')
        return redirect(url_for('login'))
    
    comment_text = request.form.get('comment')
    if not comment_text:
        flash('Comment cannot be empty', 'warning')
        return redirect(url_for('document_details', doc_code=document_code))
    
    # Get current user information
    username = session.get('username', 'Anonymous')
    user_role = session.get('role', 'User')
    
    # Create the comment object
    new_comment = {
        'user': username,
        'user_role': user_role,
        'text': comment_text,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # In a real app, this would be stored in the database
    # For demo purposes, we'll store it in session
    if 'document_comments' not in session:
        session['document_comments'] = {}
    
    if document_code not in session['document_comments']:
        session['document_comments'][document_code] = []
    
    session['document_comments'][document_code].append(new_comment)
    session.modified = True
    
    flash('Comment added successfully', 'success')
    return redirect(url_for('document_details', doc_code=document_code))

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
    """Document composition page"""
    # Log this action
    log_activity(session.get('user_id'), 'view_compose', {'request': 'view'})
    
    # Default to Outgoing document type
    doc_type = request.args.get('type', 'Outgoing')
    
    # Get all users for recipient selection
    conn = get_db_connection()
    users = conn.execute('SELECT username, department, role FROM user WHERE is_active = 1 ORDER BY username').fetchall()
    departments = ['Administration', 'Finance Department', 'Human Resources', 'IT Department', 
                  'Laboratory', 'Legal Department', 'Operations', 'Procurement', 
                  'Registry', 'Research', 'Virology']
    conn.close()
    
    if request.method == 'POST':
        # Process form submission
        doc_type = request.form.get('doc_type')
        title = request.form.get('title')
        sender = request.form.get('sender')
        recipient = request.form.get('recipient')
        details = request.form.get('details', '')
        priority = request.form.get('priority', 'Normal')
        required_action = request.form.get('required_action', '')
        date_of_letter = request.form.get('date_of_letter', '')
        
        # Validate document details
        if not title or not sender or not recipient:
            flash('Please fill in all required fields', 'danger')
            # Return to form with previously entered data
            form_data = {
                'title': title,
                'sender': sender,
                'recipient': recipient,
                'details': details,
                'priority': priority,
                'required_action': required_action,
                'date_of_letter': date_of_letter
            }
            return render_template('compose.html', 
                                  doc_type=doc_type, 
                                  form_data=form_data,
                                  users=users,
                                  departments=departments)
        
        # Process the file upload if present
        file_path = ''
        if 'document_file' in request.files:
            file = request.files['document_file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = handle_file_upload(file)
        
        # Generate a unique tracking code
        tracking_code = generate_tracking_code()
        
        # Save to database
        conn = get_db_connection()
        status = 'Pending Registry Approval'
        
        try:
            # Check if document_type column exists
            column_check = conn.execute("PRAGMA table_info(document)").fetchall()
            columns = [col[1] for col in column_check]
            
            if 'document_type' in columns:
                # Use document_type column if it exists
                conn.execute(
                    'INSERT INTO document (tracking_code, title, sender, recipient, description, status, priority, created_at, document_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (tracking_code, title, sender, recipient, details, status, priority, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), doc_type)
                )
            else:
                # Use the standard columns
                conn.execute(
                    'INSERT INTO document (tracking_code, title, sender, recipient, description, status, priority, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (tracking_code, title, sender, recipient, details, status, priority, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
            
            conn.commit()
            
            # Store document info in session for immediate display
            if 'composed_documents' not in session:
                session['composed_documents'] = []
                
            # Add to session for immediate display
            document = {
                'id': len(session['composed_documents']) + 1,
                'tracking_code': tracking_code,
                'title': title,
                'sender': sender,
                'recipient': recipient,
                'description': details,  # Use description to match database
                'status': status,
                'priority': priority,
                'date_created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'required_action': required_action,
                'document_type': doc_type
            }
            
            session['composed_documents'].append(document)
            session.modified = True
            
        except Exception as e:
            print(f"Error saving document: {e}")
            flash(f"Error saving document: {str(e)}", "danger")
            conn.close()
            return redirect(url_for('compose'))
            
        conn.close()
        
        # Log this action with document details
        log_activity(session.get('user_id'), 'create_document', {
            'tracking_code': tracking_code,
            'title': title,
            'sender': sender,
            'recipient': recipient,
            'document_type': doc_type
        })
        
        # Show success message and redirect to document details
        flash(f'Document created successfully with tracking code: {tracking_code}', 'success')
        
        if doc_type == 'Incoming':
            return redirect(url_for('incoming'))
        else:
            return redirect(url_for('outgoing'))
    
    # Render the form template
    return render_template('compose.html', 
                          doc_type=doc_type, 
                          form_data=None,
                          users=users,
                          departments=departments)

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

@app.route('/view_user/<int:user_id>')
@requires_login
def view_user(user_id):
    """View details of a specific user"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user data from database
    conn = get_db_connection()
    user_data = conn.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    if not user_data:
        flash('User not found', 'danger')
        return redirect(url_for('user_management'))
    
    # Convert to dict for template
    user = dict(user_data)
    
    # Set default values for missing fields
    if 'date_joined' not in user or not user['date_joined']:
        user['date_joined'] = user.get('created_at', datetime.now().strftime('%Y-%m-%d'))
    
    if 'last_login' not in user or not user['last_login']:
        user['last_login'] = 'Never'
    
    # For fields that need datetime conversion
    if isinstance(user['date_joined'], str) and user['date_joined']:
        try:
            date_format = '%Y-%m-%d' if len(user['date_joined']) <= 10 else '%Y-%m-%d %H:%M:%S'
            user['date_joined'] = datetime.strptime(user['date_joined'], date_format)
        except ValueError:
            user['date_joined'] = datetime.now()
    
    if isinstance(user['last_login'], str) and user['last_login'] != 'Never':
        try:
            date_format = '%Y-%m-%d' if len(user['last_login']) <= 10 else '%Y-%m-%d %H:%M:%S'
            user['last_login'] = datetime.strptime(user['last_login'], date_format)
        except ValueError:
            user['last_login'] = 'Never'
    
    # Get user's activity history
    try:
        conn = get_db_connection()
        activities = conn.execute('''
            SELECT action, details, timestamp 
            FROM activity_log 
            WHERE user_id = ? 
            ORDER BY timestamp DESC LIMIT 10
        ''', (user_id,)).fetchall()
        conn.close()
        
        # Convert to list of dicts
        activity_history = [dict(a) for a in activities]
    except Exception as e:
        print(f"Error fetching user activities: {e}")
        activity_history = []
    
    # Dummy login activities if no real data
    login_activities = [
        {'date': '2024-03-15 09:00:00', 'ip': '192.168.1.100', 'status': 'Success'},
        {'date': '2024-03-14 14:30:00', 'ip': '192.168.1.100', 'status': 'Success'},
        {'date': '2024-03-13 11:15:00', 'ip': '192.168.1.101', 'status': 'Failed'}
    ]
    
    return render_template('user_details.html', 
                         user=user,
                         login_activities=login_activities,
                         activity_history=activity_history,
                         active_page='user_management')

@app.route('/incoming')
def incoming():
    """Display incoming documents"""
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
    
    # Initialize documents list
    documents = []
    
    # Try to fetch documents from the database first
    try:
        conn = get_db_connection()
        
        # First, get documents with type "Incoming" or document_type "Incoming"
        query = '''SELECT * FROM document 
                  WHERE document_type = 'Incoming' 
                  OR document_type LIKE '%incoming%'
                  ORDER BY created_at DESC'''
                  
        rows = conn.execute(query).fetchall()
        
        # Convert rows to dictionaries
        for row in rows:
            try:
                doc_dict = dict(row)
                # Get created_at and format it properly
                created_date = datetime.strptime(doc_dict['created_at'], '%Y-%m-%d %H:%M:%S') if doc_dict['created_at'] else datetime.now()
                
                incoming_doc = {
                    'id': doc_dict.get('id', 0),
                    'code': doc_dict.get('tracking_code', ''),
                    'title': doc_dict.get('title', 'Untitled'),
                    'sender': doc_dict.get('sender', 'Unknown'),
                    'recipient': doc_dict.get('recipient', 'Unknown'),
                    'details': doc_dict.get('description', ''),
                    'required_action': doc_dict.get('required_action', ''),
                    'date_received': doc_dict.get('created_at', ''),
                    'date_received_obj': created_date,
                    'status': doc_dict.get('status', 'Incoming'),
                    'priority': doc_dict.get('priority', 'Normal'),
                    'current_holder': 'Registry'
                }
                documents.append(incoming_doc)
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
    except Exception as e:
        print(f"Error fetching documents from database: {e}")
        # Continue to use session documents if database fetch failed
    finally:
        if 'conn' in locals():
            conn.close()
    
    # Get composed incoming documents from session if available (as fallback)
    if 'composed_documents' in session:
        for doc in session['composed_documents']:
            # Only include incoming documents
            if doc.get('type') == 'Incoming' or doc.get('document_type') == 'Incoming':
                # Check if this document is already in our list by tracking code
                if not any(d.get('code') == doc.get('code', doc.get('tracking_code')) for d in documents):
                    # Format the document for the incoming view
                    date_str = doc.get('date_created', doc.get('date_submitted', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    date_format = '%Y-%m-%d' if len(date_str) <= 10 else '%Y-%m-%d %H:%M:%S'
                    
                    try:
                        date_obj = datetime.strptime(date_str, date_format)
                    except ValueError:
                        date_obj = datetime.now()
                    
                    incoming_doc = {
                        'id': doc.get('id', len(documents) + 1),
                        'code': doc.get('code', doc.get('tracking_code', f"DOC-{datetime.now().strftime('%Y')}-{len(documents)+1:03d}")),
                        'title': doc.get('title', 'Untitled Document'),
                        'sender': doc.get('sender', 'Unknown Sender'),
                        'recipient': doc.get('recipient', 'KEMRI Laboratory'),
                        'details': doc.get('details', doc.get('description', '')),
                        'required_action': doc.get('required_action', 'Review'),
                        'date_received': date_str,
                        'date_received_obj': date_obj,
                        'status': doc.get('status', 'Incoming'),
                        'priority': doc.get('priority', 'Normal'),
                        'current_holder': doc.get('current_holder', 'Registry')
                    }
                    documents.append(incoming_doc)
    
    # Generate additional sample documents if needed
    if not documents:
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
                'code': f'DOC-{datetime.now().year}-{i:03d}',
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
            
            documents.append(document)
    
    filtered_documents = []
    
    # Apply filters to all documents
    for document in documents:
        # Status filter
        if status_filter != 'all' and document['status'] != status_filter:
            continue
            
        # Priority filter
        if priority_filter != 'All' and document['priority'] != priority_filter:
            continue
            
        # Search query
        if search_query and search_query.lower() not in document.get('title', '').lower() and search_query.lower() not in document.get('sender', '').lower():
            continue
            
        # Date range filter
        doc_date = document.get('date_received_obj', datetime.now()).date() if isinstance(document.get('date_received_obj'), datetime) else datetime.now().date()
        
        if date_range == 'today' and doc_date != today:
            continue
        elif date_range == 'week' and doc_date < week_start:
            continue
        elif date_range == 'month' and doc_date < month_start:
            continue
        elif date_range == 'custom' and start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            if doc_date < start or doc_date > end:
                continue
        
        filtered_documents.append(document)
    
    # Sort documents
    if sort_by == 'date':
        filtered_documents.sort(key=lambda x: x.get('date_received_obj', datetime.now()), reverse=(sort_order == 'desc'))
    elif sort_by == 'priority':
        priority_order = {'Urgent': 0, 'Priority': 1, 'Normal': 2}
        filtered_documents.sort(key=lambda x: priority_order.get(x.get('priority', 'Normal'), 3), reverse=(sort_order != 'desc'))
    elif sort_by == 'sender':
        filtered_documents.sort(key=lambda x: x.get('sender', ''), reverse=(sort_order == 'desc'))
    
    # Create pagination object
    per_page = 10
    total_filtered = len(filtered_documents)
    
    # Get the documents for the current page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_filtered)
    page_documents = filtered_documents[start_idx:end_idx] if filtered_documents else []
    
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
    """Display outgoing documents"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Log this action
    log_activity(session.get('user_id'), 'view_outgoing', {'request': 'view'})
    
    # Get filter parameters from query string
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    date_filter = request.args.get('date', 'all')
    search_query = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    # Initialize documents list
    documents = []
    total_documents = 0
    
    # Database connection
    conn = get_db_connection()
    try:
        # Count documents by priority for stats
        priority_counts = {
            'urgent': 0,
            'high': 0,
            'normal': 0,
            'low': 0,
            'Urgent': 0,    # Added capitalized versions
            'Priority': 0,  # Added for template compatibility
            'Normal': 0     # Added for template compatibility
        }
        
        # Get total documents in each priority
        try:
            for priority in ['Urgent', 'High', 'Priority', 'Normal', 'Low']:
                count = conn.execute(
                    "SELECT COUNT(*) FROM document WHERE priority = ? AND document_type != 'Incoming'", 
                    (priority,)
                ).fetchone()[0]
                
                # Map to both lowercase and capitalized keys
                lowercase_key = priority.lower()
                if lowercase_key == 'high':
                    priority_counts['Priority'] += count  # Map 'High' to 'Priority'
                else:
                    priority_counts[priority] = count  # Capitalized version
                    priority_counts[lowercase_key] = count  # Lowercase version
        except Exception as e:
            print(f"Error counting documents by priority: {e}")
            # Continue execution with default counts
        
        # Build the query based on filters
        query = "SELECT * FROM document WHERE document_type != 'Incoming'"
        params = []
        
        # Apply status filter
        if status_filter != 'all':
            query += " AND status LIKE ?"
            params.append(f"%{status_filter}%")
        
        # Apply priority filter
        if priority_filter != 'all':
            query += " AND priority = ?"
            params.append(priority_filter.title())
        
        # Apply date filter
        if date_filter != 'all':
            if date_filter == 'today':
                query += " AND DATE(created_at) = DATE('now')"
            elif date_filter == 'week':
                query += " AND created_at >= date('now', '-7 days')"
            elif date_filter == 'month':
                query += " AND created_at >= date('now', '-30 days')"
        
        # Apply search query if present
        if search_query:
            query += " AND (tracking_code LIKE ? OR title LIKE ? OR sender LIKE ? OR recipient LIKE ?)"
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term, search_term])
        
        # Count total documents matching the query for pagination
        try:
            count_query = query.replace("SELECT *", "SELECT COUNT(*)")
            total_documents = conn.execute(count_query, params).fetchone()[0]
        except Exception as e:
            print(f"Error counting documents: {e}")
            total_documents = 0
        
        # Order by most recent first
        query += " ORDER BY created_at DESC"
        
        # Apply pagination manually (don't use LIMIT in SQL as we need all documents for session check)
        rows = conn.execute(query, params).fetchall()
        
        # Convert to dictionary for template
        for row in rows:
            # Convert row to dictionary
            row_dict = dict(row)
            
            # Format dates
            created_date = datetime.strptime(row_dict['created_at'], '%Y-%m-%d %H:%M:%S') if row_dict['created_at'] else datetime.now()
            date_diff = (datetime.now() - created_date).days
            
            document = {
                'id': row_dict['id'],
                'tracking_code': row_dict['tracking_code'],
                'title': row_dict['title'],
                'sender': row_dict['sender'],
                'recipient': row_dict['recipient'],
                'description': row_dict.get('description', ''),
                'status': row_dict['status'],
                'priority': row_dict['priority'],
                'date_created': row_dict['created_at'],
                'days_ago': date_diff,
                'document_type': row_dict.get('document_type', 'Outgoing')
            }
            documents.append(document)
            
    except Exception as e:
        print(f"Error retrieving documents: {e}")
    finally:
        conn.close()
    
    # Add documents from session if available (for demo purposes)
    if 'composed_documents' in session:
        for doc in session['composed_documents']:
            # Skip documents already in our list
            if any(d.get('tracking_code') == doc.get('tracking_code') for d in documents):
                continue
                
            # Skip incoming documents
            if doc.get('document_type') == 'Incoming':
                continue
                
            # Format dates
            if 'date_created' in doc:
                try:
                    created_date = datetime.strptime(doc['date_created'], '%Y-%m-%d %H:%M:%S')
                    date_diff = (datetime.now() - created_date).days
                except (ValueError, TypeError):
                    date_diff = 0
            else:
                date_diff = 0
                
            document = {
                'id': doc.get('id', len(documents) + 1),
                'tracking_code': doc.get('tracking_code'),
                'title': doc.get('title', 'Untitled Document'),
                'sender': doc.get('sender', 'Unknown'),
                'recipient': doc.get('recipient', 'Unknown'),
                'description': doc.get('description', ''),
                'status': doc.get('status', 'Pending'),
                'priority': doc.get('priority', 'Normal'),
                'date_created': doc.get('date_created', datetime.now().strftime('%Y-%m-%d')),
                'days_ago': date_diff,
                'document_type': doc.get('document_type', 'Outgoing')
            }
            
            # Apply filters
            if status_filter != 'all' and status_filter.lower() not in document['status'].lower():
                continue
                
            if priority_filter != 'all' and priority_filter.lower() != document['priority'].lower():
                continue
                
            if search_query and search_query.lower() not in document['title'].lower() and search_query.lower() not in document['tracking_code'].lower():
                continue
                
            documents.append(document)
    
    # Manual pagination
    pagination = Pagination(page, per_page, len(documents))
    start = (page - 1) * per_page
    end = min(start + per_page, len(documents))
    paginated_documents = documents[start:end]
    
    # Statistics for the dashboard header
    stats = {
        'total': len(documents),
        'urgent': priority_counts['urgent'],
        'high': priority_counts['high'],
        'normal': priority_counts['normal'],
        'low': priority_counts['low'],
        'pending': len([d for d in documents if 'pending' in d.get('status', '').lower()]),
        'completed': len([d for d in documents if 'completed' in d.get('status', '').lower() or 'approved' in d.get('status', '').lower()])
    }
    
    # Users for the reassign dropdown
    users = []
    
    # For the sample, get activity timeline (most recent first)
    activities = [
        {
            'user': 'System Administrator',
            'action': 'Approved document',
            'document': 'Financial Report Q1',
            'timestamp': (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
            'tracking_code': 'DOC-2023-004'
        },
        {
            'user': 'Jane Smith',
            'action': 'Added comment',
            'document': 'Project Proposal',
            'timestamp': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'tracking_code': 'DOC-2023-003'
        },
        {
            'user': 'Robert Chen',
            'action': 'Shared document',
            'document': 'HR Guidelines',
            'timestamp': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
            'tracking_code': 'DOC-2023-002'
        }
    ]
    
    return render_template('outgoing.html',
                         documents=paginated_documents,
                         stats=stats,
                         status_filter=status_filter,
                         priority_filter=priority_filter,
                         date_filter=date_filter,
                         search_query=search_query,
                         pagination=pagination,
                         users=users,
                         activities=activities,
                         priority_counts=priority_counts)  # Added priority_counts to the template context

@app.route('/database_management')
@requires_permission('database_management')
def database_management():
    """Database management route"""
    # Log this access
    log_activity(session.get('user_id'), 'view_database_management', {'request': 'view'})
    
    # Get database statistics
    stats = {
        'total_documents': 127,
        'total_users': 18,
        'total_logs': 1523,
        'total_attachments': 324,
        'db_size': '42.8 MB',
        'health': 98
    }
    
    # Sample backup data
    backups = [
        {'filename': 'backup_20250428_full.sql', 'date': '2025-04-28 23:00', 'size': '38.2 MB'},
        {'filename': 'backup_20250427_full.sql', 'date': '2025-04-27 23:00', 'size': '37.9 MB'},
        {'filename': 'backup_20250426_full.sql', 'date': '2025-04-26 23:00', 'size': '37.8 MB'},
        {'filename': 'backup_20250425_full.sql', 'date': '2025-04-25 23:00', 'size': '36.5 MB'},
        {'filename': 'backup_20250424_full.sql', 'date': '2025-04-24 23:00', 'size': '36.1 MB'}
    ]
    
    # Sample recent logs
    logs = [
        {'action': 'Automatic Backup', 'timestamp': '2025-04-29 23:00:12', 'status': 'Success'},
        {'action': 'Index Optimization', 'timestamp': '2025-04-29 22:15:03', 'status': 'Success'},
        {'action': 'Cache Purge', 'timestamp': '2025-04-29 22:00:01', 'status': 'Success'},
        {'action': 'User Import', 'timestamp': '2025-04-29 15:23:45', 'status': 'Success'},
        {'action': 'Manual Backup', 'timestamp': '2025-04-29 14:08:22', 'status': 'Success'}
    ]
    
    # Performance metrics
    performance = {
        'response_time': '125ms',
        'queries_per_second': 42,
        'slow_queries': 3,
        'cache_hit_ratio': '94%'
    }
    
    return render_template('database_management.html', 
                           stats=stats,
                           backups=backups,
                           logs=logs,
                           performance=performance)

@app.route('/reports')
@requires_permission('view_reports')
def reports():
    """Reports and analytics page"""
    # Log this action
    log_activity(session.get('user_id'), 'view_reports', {'request': 'view'})
    
    # Get filters from request args with defaults
    filters = {
        'date_range': request.args.get('date_range', 'last-30-days'),
        'status': request.args.get('status', 'all'),
        'priority': request.args.get('priority', 'all'),
        'department': request.args.get('department', 'all')
    }
    
    # Mock report data
    report_data = {
        'total_documents': 127,
        'incoming_documents': 45,
        'outgoing_documents': 82,
        'pending_approval': 14,
        'overdue': 3,
        'completion_rate': 92,
    }
    
    # Status breakdown data for pie chart
    status_data = {
        'Incoming': {'total': 18, 'percentage': 14, 'trend': 5, 'normal': 10, 'priority': 5, 'urgent': 3},
        'Pending': {'total': 31, 'percentage': 24, 'trend': -3, 'normal': 15, 'priority': 12, 'urgent': 4},
        'Received': {'total': 25, 'percentage': 20, 'trend': 2, 'normal': 12, 'priority': 10, 'urgent': 3},
        'Outgoing': {'total': 45, 'percentage': 35, 'trend': 7, 'normal': 20, 'priority': 18, 'urgent': 7},
        'Ended': {'total': 8, 'percentage': 7, 'trend': -1, 'normal': 4, 'priority': 3, 'urgent': 1}
    }
    
    # Chart data for monthly trends
    chart_data = {
        'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'datasets': [
            {
                'label': 'Incoming',
                'data': [12, 19, 15, 17, 22, 24]
            },
            {
                'label': 'Outgoing',
                'data': [15, 22, 18, 21, 27, 32]
            }
        ]
    }
    
    # Add average times data that the template expects
    avg_times = {
        'Incoming': '1.5 days',
        'Pending': '3.2 days',
        'Received': '2.8 days',
        'Outgoing': '1.7 days',
        'Ended': '4.5 days'
    }
    
    # Add priority and status chart data for template
    status_chart_data = json.dumps([
        {'name': 'Incoming', 'value': 18, 'color': '#2196F3'},
        {'name': 'Pending', 'value': 31, 'color': '#FFC107'},
        {'name': 'Received', 'value': 25, 'color': '#4CAF50'},
        {'name': 'Outgoing', 'value': 45, 'color': '#9C27B0'},
        {'name': 'Ended', 'value': 8, 'color': '#F44336'}
    ])
    
    priority_chart_data = json.dumps([
        {'name': 'Normal', 'value': 56, 'color': '#4CAF50'},
        {'name': 'Priority', 'value': 53, 'color': '#FFC107'},
        {'name': 'Urgent', 'value': 18, 'color': '#F44336'}
    ])
    
    # Only administrators can see system-wide reports
    system_stats = None
    if session.get('role') == 'Administrator':
        system_stats = {
            'active_users': 14,
            'disk_usage': '42.8 MB',
            'avg_response_time': '125ms',
            'total_logins': 187
        }
    
    return render_template('reports.html',
                          filters=filters,
                          report_data=report_data,
                          status_data=status_data,
                          chart_data=chart_data,
                          system_stats=system_stats,
                          avg_times=avg_times,
                          status_chart_data=status_chart_data,
                          priority_chart_data=priority_chart_data,
                          total_documents=127)

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
    """Handle bulk actions on incoming documents"""
    if 'user_id' not in session:
        flash('Please log in to perform bulk actions', 'warning')
        return redirect(url_for('login'))
    
    # Get form data
    bulk_action = request.form.get('bulk_action', '')
    selected_docs = request.form.getlist('selected_docs')
    
    if not bulk_action:
        flash('No action specified', 'danger')
        return redirect(url_for('incoming'))
        
    if not selected_docs:
        flash('No documents selected', 'warning')
        return redirect(url_for('incoming'))
    
    # Initialize counters
    success_count = 0
    fail_count = 0
    
    # Process actions on session documents
    if 'composed_documents' in session:
        for doc in session['composed_documents']:
            # Check if document is selected and is an incoming document
            if ((doc.get('code') in selected_docs or doc.get('tracking_code') in selected_docs) and
                (doc.get('type') == 'Incoming' or doc.get('document_type') == 'Incoming')):
                
                try:
                    # Apply the bulk action
                    if bulk_action == 'mark_received':
                        doc['status'] = 'Received'
                    elif bulk_action == 'mark_pending':
                        doc['status'] = 'Pending'
                    elif bulk_action == 'delete':
                        # Mark for deletion (we'll remove them after the loop)
                        doc['_marked_for_deletion'] = True
                    elif bulk_action == 'export':
                        # No change needed for export, just count it
                        pass
                    elif bulk_action == 'archive':
                        doc['status'] = 'Archived'
                    
                    # Add to history if available
                    if 'history' not in doc:
                        doc['history'] = []
                    
                    doc['history'].append({
                        'action': f"Bulk Action: {bulk_action.replace('_', ' ').title()}",
                        'user': session.get('username', 'User'),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                    success_count += 1
                except Exception as e:
                    # Log any errors
                    fail_count += 1
                    print(f"Error processing document {doc.get('code', doc.get('tracking_code', 'unknown'))}: {str(e)}")
        
        # Delete documents marked for deletion
        if bulk_action == 'delete':
            session['composed_documents'] = [doc for doc in session['composed_documents'] 
                                            if not doc.get('_marked_for_deletion', False)]
        
        # Mark session as modified to save changes
        session.modified = True
    
    # Show result message
    if success_count > 0:
        action_text = bulk_action.replace('_', ' ').title()
        flash(f'Successfully {action_text}ed {success_count} document(s)', 'success')
    
    if fail_count > 0:
        flash(f'Failed to process {fail_count} document(s)', 'danger')
    
    # Handle special case for export action
    if bulk_action == 'export' and success_count > 0:
        flash('Export functionality would generate a file download in a real application', 'info')
    
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
    # Disable this route in production by default
    debug_enabled = False  # Set this to True only in development
    
    if not debug_enabled:
        flash('Debug login is disabled in production mode.', 'warning')
        return redirect(url_for('login'))
        
    # Clear any existing session
    session.clear()
    
    # Set session variables for testing
    role = request.args.get('role', 'Administrator')
    
    if role not in ['Administrator', 'User', 'Registry', 'Supervisor']:
        role = 'Administrator'  # Default to Administrator if invalid role
        
    session['user_id'] = 1
    session['username'] = f'{role.lower()}_user'
    session['role'] = role
    session['department'] = 'Demo Department'
    session['email'] = f'{role.lower()}@example.com'
    session['last_activity'] = time.time()
    
    # Log the debug login activity
    log_activity(1, 'debug_login', {
        'role': role,
        'method': 'debug',
        'ip': request.remote_addr
    })
    
    flash(f'You are now logged in as a {role}', 'success')
    return redirect(url_for('dashboard'))

@app.route('/access-denied')
def access_denied():
    """Show access denied page with reason"""
    missing_permission = request.args.get('permission')
    previous_url = request.args.get('previous') or request.referrer
    
    return render_template('access_denied.html', 
                           missing_permission=missing_permission,
                           previous_url=previous_url)

@app.route('/bulk_user_action', methods=['POST'])
def bulk_user_action():
    """Handle bulk actions on users"""
    if 'user_id' not in session:
        flash('Please log in to perform this action', 'warning')
        return redirect(url_for('login'))
    
    if session['role'] != 'Administrator':
        flash('You do not have permission to perform this action', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get form data
    user_ids = request.form.get('user_ids', '').split(',')
    action = request.form.get('action', '')
    
    if not user_ids or not action:
        flash('No users selected or action specified', 'warning')
        return redirect(url_for('user_management'))
    
    try:
        # Handle different actions
        if action == 'activate':
            # In a real app, update the database to activate users
            flash(f'{len(user_ids)} users activated successfully', 'success')
        
        elif action == 'deactivate':
            # In a real app, update the database to deactivate users
            flash(f'{len(user_ids)} users deactivated successfully', 'success')
        
        elif action == 'delete':
            # In a real app, delete users from the database
            flash(f'{len(user_ids)} users deleted successfully', 'success')
        
        elif action == 'assign_role':
            role = request.form.get('role', '')
            if not role:
                flash('No role specified', 'warning')
                return redirect(url_for('user_management'))
            # In a real app, update the database to assign roles
            flash(f'{len(user_ids)} users assigned to role: {role}', 'success')
        
        elif action == 'assign_department':
            department = request.form.get('department', '')
            if not department:
                flash('No department specified', 'warning')
                return redirect(url_for('user_management'))
            # In a real app, update the database to assign departments
            flash(f'{len(user_ids)} users assigned to department: {department}', 'success')
        
        elif action == 'reset-password':
            # In a real app, reset passwords for users
            flash(f'Password reset for {len(user_ids)} users', 'success')
        
        elif action == 'export':
            # In a real app, export user data to file
            flash(f'User data exported successfully', 'success')
        
        elif action == 'send_credentials':
            # In a real app, send credentials to users
            flash(f'Credentials sent to {len(user_ids)} users', 'success')
        
        else:
            flash(f'Unknown action: {action}', 'warning')
    
    except Exception as e:
        # Log the error and show a flash message
        print(f"Error performing bulk action: {str(e)}")
        flash(f'An error occurred while performing the action: {str(e)}', 'danger')
    
    return redirect(url_for('user_management'))

@app.route('/import_users', methods=['POST'])
def import_users():
    """Import users from uploaded CSV file"""
    if 'user_id' not in session:
        flash('Please log in to import users', 'warning')
        return redirect(url_for('login'))
    
    if session['role'] != 'Administrator':
        flash('You do not have permission to import users', 'danger')
        return redirect(url_for('dashboard'))
    
    # For debug mode, just flash a message and redirect back
    flash('User import functionality is not implemented in debug mode', 'info')
    return redirect(url_for('user_management'))

@app.route('/edit-user/<int:user_id>', methods=['POST'])
@requires_login
def edit_user(user_id):
    """Edit a user's details"""
    print(f"EDIT USER ROUTE CALLED for user ID: {user_id}")
    
    if session.get('role') != 'Administrator':
        flash('You do not have permission to perform this action', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get form data
    fullname = request.form.get('fullName')
    email = request.form.get('email')
    phone = request.form.get('phone', '')
    department = request.form.get('department')
    role = request.form.get('role')
    new_password = request.form.get('password')
    
    # Basic validation
    if not email or not department or not role:
        flash('All required fields must be filled', 'danger')
        return redirect(url_for('user_management'))
    
    # Update user in database
    try:
        conn = get_db_connection()
        
        # Construct update SQL based on whether password is being changed
        if new_password and new_password.strip():
            # Hash the new password
            hashed_password = generate_password_hash(new_password)
            
            conn.execute(
                'UPDATE user SET email = ?, phone = ?, department = ?, role = ?, password = ? WHERE id = ?',
                (email, phone, department, role, hashed_password, user_id)
            )
        else:
            # Don't update password
            conn.execute(
                'UPDATE user SET email = ?, phone = ?, department = ?, role = ? WHERE id = ?',
                (email, phone, department, role, user_id)
            )
        
        conn.commit()
        
        # Get updated user for flashing a message
        user = conn.execute('SELECT username FROM user WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        
        if user:
            # Log this action
            log_activity(session.get('user_id'), 'edit_user', {
                'user_id': user_id,
                'username': user['username']
            })
            
            flash(f'User {user["username"]} has been updated successfully', 'success')
        else:
            flash('User not found', 'danger')
    except Exception as e:
        print(f"Error updating user: {e}")
        flash(f'Error updating user: {str(e)}', 'danger')
    
    return redirect(url_for('user_management'))

@app.route('/delete-user/<int:user_id>', methods=['POST'])
@requires_login
def delete_user(user_id):
    """Delete a user"""
    print(f"DELETE USER ROUTE CALLED for user ID: {user_id}")
    
    if session.get('role') != 'Administrator':
        flash('You do not have permission to perform this action', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if user is trying to delete themselves
    if int(session.get('user_id', 0)) == user_id:
        flash('You cannot delete yourself', 'danger')
        return redirect(url_for('user_management'))
    
    try:
        conn = get_db_connection()
        
        # Get the user first for logging
        user = conn.execute('SELECT username FROM user WHERE id = ?', (user_id,)).fetchone()
        
        if not user:
            conn.close()
            flash('User not found', 'danger')
            return redirect(url_for('user_management'))
        
        # Delete the user
        conn.execute('DELETE FROM user WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        # Log this action
        log_activity(session.get('user_id'), 'delete_user', {
            'user_id': user_id,
            'username': user['username']
        })
        
        flash(f'User {user["username"]} has been deleted successfully', 'success')
    except Exception as e:
        print(f"Error deleting user: {e}")
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('user_management'))

@app.route('/reset-password/<int:user_id>', methods=['POST'])
@requires_login
def reset_password(user_id):
    """Reset a user's password"""
    print(f"RESET PASSWORD ROUTE CALLED for user ID: {user_id}")
    
    if session.get('role') != 'Administrator':
        flash('You do not have permission to perform this action', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if we should generate a random password
    generate_random = request.form.get('generatePassword') == 'on'
    
    if generate_random:
        # Generate a random password
        import random
        import string
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    else:
        # Use the provided password
        new_password = request.form.get('password')
        if not new_password:
            flash('Password cannot be empty', 'danger')
            return redirect(url_for('user_management'))
    
    try:
        conn = get_db_connection()
        
        # Get the user first for logging and feedback
        user = conn.execute('SELECT username FROM user WHERE id = ?', (user_id,)).fetchone()
        
        if not user:
            conn.close()
            flash('User not found', 'danger')
            return redirect(url_for('user_management'))
        
        # Hash the new password
        hashed_password = generate_password_hash(new_password)
        
        # Update the user's password
        conn.execute('UPDATE user SET password = ? WHERE id = ?', (hashed_password, user_id))
        conn.commit()
        conn.close()
        
        # Log this action
        log_activity(session.get('user_id'), 'reset_password', {
            'user_id': user_id,
            'username': user['username']
        })
        
        # Check if we should email the password
        if request.form.get('email_password') == 'on':
            # In a real app you would send an email here
            flash(f'New password would be emailed to user (debug mode)', 'info')
        
        flash(f'Password for {user["username"]} has been reset. New password: {new_password}', 'success')
    except Exception as e:
        print(f"Error resetting password: {e}")
        flash(f'Error resetting password: {str(e)}', 'danger')
    
    return redirect(url_for('user_management'))

@app.route('/toggle-user-status/<int:user_id>', methods=['POST'])
@requires_login
def toggle_user_status(user_id):
    """Activate or deactivate a user"""
    print(f"TOGGLE USER STATUS ROUTE CALLED for user ID: {user_id}")
    
    if session.get('role') != 'Administrator':
        flash('You do not have permission to perform this action', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if user is trying to deactivate themselves
    if int(session.get('user_id', 0)) == user_id:
        flash('You cannot change your own status', 'danger')
        return redirect(url_for('user_management'))
    
    # Get the requested action (activate or deactivate)
    action = request.form.get('action')
    if action not in ['activate', 'deactivate']:
        flash('Invalid action', 'danger')
        return redirect(url_for('user_management'))
    
    # Set is_active based on the action
    is_active = 1 if action == 'activate' else 0
    
    try:
        conn = get_db_connection()
        
        # Get the user first for logging and feedback
        user = conn.execute('SELECT username, is_active FROM user WHERE id = ?', (user_id,)).fetchone()
        
        if not user:
            conn.close()
            flash('User not found', 'danger')
            return redirect(url_for('user_management'))
        
        # Only update if the status is actually changing
        if (is_active == 1 and user['is_active'] == 0) or (is_active == 0 and user['is_active'] == 1):
            # Update the user's status
            conn.execute('UPDATE user SET is_active = ? WHERE id = ?', (is_active, user_id))
            conn.commit()
            
            # Log this action
            log_activity(session.get('user_id'), f'{action}_user', {
                'user_id': user_id,
                'username': user['username']
            })
            
            flash(f'User {user["username"]} has been {"activated" if is_active else "deactivated"} successfully', 'success')
        else:
            flash(f'User {user["username"]} is already {"active" if is_active else "inactive"}', 'info')
        
        conn.close()
    except Exception as e:
        print(f"Error toggling user status: {e}")
        flash(f'Error toggling user status: {str(e)}', 'danger')
    
    return redirect(url_for('user_management'))

@app.errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors"""
    return render_template('access_denied.html'), 403

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
@requires_permission('registry_approval')
def registry_approval():
    """Registry approval workflow page"""
    # Log this action
    log_activity(session.get('user_id'), 'view_registry_workflow', {'request': 'view'})
    
    # Get filter parameters from query string with defaults
    status_filter = request.args.get('status', 'pending')
    department_filter = request.args.get('department', 'all')
    date_filter = request.args.get('date', 'all')
    priority_filter = request.args.get('priority', 'all')
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Fetch documents from database
    documents = []
    conn = get_db_connection()
    
    try:
        # Build the query based on filters
        query = 'SELECT * FROM document'
        
        # Apply status filter - pending means "Pending Registry Approval"
        conditions = []
        params = []
        
        if status_filter == 'pending':
            conditions.append("status = 'Pending Registry Approval'")
        elif status_filter == 'approved':
            conditions.append("status = 'Approved'")
        elif status_filter == 'rejected':
            conditions.append("status = 'Rejected'")
        
        # Department filter
        if department_filter != 'all':
            conditions.append("sender LIKE ?")
            params.append(f"%{department_filter}%")
        
        # Search query
        if search_query:
            conditions.append("(title LIKE ? OR sender LIKE ? OR recipient LIKE ? OR tracking_code LIKE ?)")
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term, search_term])
        
        # Priority filter
        if priority_filter != 'all':
            conditions.append("priority = ?")
            params.append(priority_filter)
        
        # Apply conditions if any
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        
        # Apply sorting
        if sort_by == 'date':
            query += ' ORDER BY created_at'
        elif sort_by == 'priority':
            query += ' ORDER BY priority'
        else:
            query += ' ORDER BY created_at'
        
        # Apply sort order
        if sort_order == 'desc':
            query += ' DESC'
        else:
            query += ' ASC'
        
        # Execute query
        rows = conn.execute(query, params).fetchall()
        
        # Convert to dictionary for template
        for row in rows:
            # Convert row to dictionary
            row_dict = dict(row)
            created_date = datetime.strptime(row_dict['created_at'], '%Y-%m-%d %H:%M:%S') if row_dict['created_at'] else datetime.now()
            days_in_stage = (datetime.now() - created_date).days
            
            documents.append({
                'id': row_dict['id'],
                'tracking_code': row_dict['tracking_code'],
                'title': row_dict['title'],
                'sender': row_dict['sender'],
                'department': row_dict['sender'].split(' - ')[0] if ' - ' in row_dict['sender'] else row_dict['sender'],
                'received_date': row_dict['created_at'],
                'date_submitted': row_dict['created_at'],
                'status': 'pending' if row_dict['status'] == 'Pending Registry Approval' else row_dict['status'].lower(),
                'priority': row_dict['priority'],
                'notes': row_dict.get('description', ''),
                'document_type': row_dict.get('document_type', 'Document'),
                'workflow_stage': 'Initial Review',
                'days_in_stage': days_in_stage
            })
    except Exception as e:
        print(f"Error fetching documents: {e}")
        # If database fails, fall back to sample documents
        documents = [
            {
                'id': 1,
                'tracking_code': 'KEMRI-20250428-1001',
                'title': 'Research Grant Application',
                'sender': 'Dr. Jane Smith',
                'department': 'Research',
                'received_date': '2025-04-28',
                'date_submitted': '2025-04-28',
                'status': 'pending',
                'priority': 'High',
                'notes': 'Awaiting approval to proceed to director',
                'document_type': 'Grant Application',
                'workflow_stage': 'Initial Review',
                'days_in_stage': 2
            },
            # Additional sample documents if needed...
        ]
    finally:
        conn.close()
    
    # Add documents from session if available (for demo purposes)
    if 'composed_documents' in session:
        for doc in session['composed_documents']:
            if doc.get('status') == 'Pending Registry Approval':
                # Only add if not already in list (avoid duplicates)
                if not any(d.get('tracking_code') == doc.get('tracking_code') for d in documents):
                    created_date = datetime.strptime(doc.get('date_created'), '%Y-%m-%d %H:%M:%S') if 'date_created' in doc else datetime.now()
                    days_in_stage = (datetime.now() - created_date).days
                    
                    documents.append({
                        'id': doc.get('id', len(documents) + 1),
                        'tracking_code': doc.get('tracking_code'),
                        'title': doc.get('title', 'Untitled Document'),
                        'sender': doc.get('sender', 'Unknown'),
                        'department': doc.get('sender', 'Unknown').split(' - ')[0] if ' - ' in doc.get('sender', 'Unknown') else doc.get('sender', 'Unknown'),
                        'received_date': doc.get('date_created', datetime.now().strftime('%Y-%m-%d')),
                        'date_submitted': doc.get('date_created', datetime.now().strftime('%Y-%m-%d')),
                        'status': 'pending',
                        'priority': doc.get('priority', 'Normal'),
                        'notes': doc.get('description', ''),
                        'document_type': doc.get('document_type', 'Document'),
                        'workflow_stage': 'Initial Review',
                        'days_in_stage': days_in_stage
                    })
    
    # Statistics for the dashboard
    stats = {
        'total': len(documents),
        'pending': len([d for d in documents if d.get('status') == 'pending']),
        'approved': len([d for d in documents if d.get('status') == 'approved']),
        'rejected': len([d for d in documents if d.get('status') == 'rejected']),
        'high_priority': len([d for d in documents if d.get('priority').lower() == 'high']),
        'older_than_7_days': len([d for d in documents if d.get('days_in_stage', 0) > 7])
    }
    
    return render_template('registry_approval.html',
                          documents=documents,
                          stats=stats,
                          status_filter=status_filter,
                          department_filter=department_filter,
                          date_filter=date_filter,
                          priority_filter=priority_filter,
                          search_query=search_query,
                          sort_by=sort_by,
                          sort_order=sort_order)

@app.route('/registry_decision/<tracking_code>', methods=['POST'])
def registry_decision(tracking_code):
    """Handle registry decision on a document"""
    if 'user_id' not in session:
        flash('Please log in to make registry decisions', 'warning')
        return redirect(url_for('login'))
    
    # Get form data
    decision = request.form.get('decision')
    comments = request.form.get('comments', '')
    next_department = request.form.get('department', '')
    reject_reason = request.form.get('reject_reason', '')
    assignee = request.form.get('assignee', '')
    priority = request.form.get('priority', '')
    due_date = request.form.get('due_date', '')
    
    # Create an audit trail entry
    decision_data = {
        'tracking_code': tracking_code,
        'user_id': session.get('user_id'),
        'decision': decision,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'comments': comments,
        'next_department': next_department,
        'assignee': assignee
    }
    
    # Log this decision
    log_activity(session.get('user_id'), 'registry_decision', decision_data)
    
    # Update document in the database
    conn = None
    try:
        conn = get_db_connection()
        
        # Get the current document
        document = conn.execute('SELECT * FROM document WHERE tracking_code = ?', 
                              (tracking_code,)).fetchone()
        
        if document:
            # Determine the new status based on decision
            new_status = ''
            if decision == 'approve':
                new_status = f"Approved - Forwarded to {next_department}"
            elif decision == 'reject':
                new_status = f"Rejected - {reject_reason}"
            elif decision == 'request_changes':
                new_status = "Changes Requested"
                
            # Update the document status in the database
            conn.execute('UPDATE document SET status = ? WHERE tracking_code = ?', 
                        (new_status, tracking_code))
            
            # Update priority if provided
            if priority:
                conn.execute('UPDATE document SET priority = ? WHERE tracking_code = ?', 
                            (priority, tracking_code))
                
            # Add to document history
            conn.execute(
                'INSERT INTO document_history (document_id, action, details, user_id) VALUES (?, ?, ?, ?)',
                (document['id'], f"Registry {decision.replace('_', ' ').title()}", 
                 f"Comments: {comments}, Next Department: {next_department}", session.get('user_id'))
            )
            
            # Commit the changes
            conn.commit()
            
            # Display appropriate message
            if decision == 'approve':
                flash(f"Document {tracking_code} has been approved and forwarded to {next_department}", 'success')
            elif decision == 'reject':
                flash(f"Document {tracking_code} has been rejected. Reason: {reject_reason}", 'warning')
            elif decision == 'request_changes':
                flash(f"Changes have been requested for document {tracking_code}", 'info')
        else:
            flash(f"Document with tracking code {tracking_code} not found", 'danger')
            
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error updating document: {e}")
        flash(f"Error updating document: {str(e)}", 'danger')
    finally:
        if conn:
            conn.close()
    
    # For demo, also update in the session if the document exists there
    if 'composed_documents' in session:
        for doc in session['composed_documents']:
            if doc.get('tracking_code') == tracking_code:
                if decision == 'approve':
                    doc['status'] = f"Approved - Forwarded to {next_department}"
                elif decision == 'reject':
                    doc['status'] = f"Rejected - {reject_reason}"
                elif decision == 'request_changes':
                    doc['status'] = "Changes Requested"
                
                # Update other fields
                if priority:
                    doc['priority'] = priority
                if assignee:
                    doc['assignee'] = assignee
                if due_date:
                    doc['due_date'] = due_date
                
                # Add decision to document history
                if 'history' not in doc:
                    doc['history'] = []
                
                doc['history'].append({
                    'action': f"Registry {decision.replace('_', ' ').title()}",
                    'user': session.get('username', 'Registry Officer'),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'comments': comments,
                    'next_department': next_department
                })
                
                # Mark session as modified
                session.modified = True
                break
    
    return redirect(url_for('registry_approval'))

@app.route('/update_incoming_status/<doc_code>', methods=['POST'])
def update_incoming_status(doc_code):
    """Update the status of an incoming document"""
    if 'user_id' not in session:
        flash('Please log in to update document status', 'warning')
        return redirect(url_for('login'))
    
    # Get the new status from the form
    new_status = request.form.get('status', '')
    
    if not new_status:
        flash('No status provided', 'danger')
        return redirect(url_for('incoming'))
    
    # Update the document status in the database
    conn = None
    try:
        conn = get_db_connection()
        # Update document status
        result = conn.execute('UPDATE document SET status = ? WHERE tracking_code = ?', 
                           (new_status, doc_code))
        
        if result.rowcount > 0:
            # Add to document history
            document = conn.execute('SELECT id FROM document WHERE tracking_code = ?', 
                                  (doc_code,)).fetchone()
            
            if document:
                conn.execute(
                    'INSERT INTO document_history (document_id, action, details, user_id) VALUES (?, ?, ?, ?)',
                    (document['id'], f"Status Updated", f"New status: {new_status}", session.get('user_id'))
                )
            
            conn.commit()
            flash(f'Document {doc_code} status updated to {new_status}', 'success')
        else:
            flash(f'Document {doc_code} not found', 'warning')
            
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error updating document status: {e}")
        flash(f"Error updating document status: {str(e)}", 'danger')
    finally:
        if conn:
            conn.close()
    
    # For backwards compatibility: also update in the session if the document exists there
    if 'composed_documents' in session:
        found = False
        for doc in session['composed_documents']:
            # Check tracking_code for incoming documents
            if (doc.get('tracking_code') == doc_code and 
                (doc.get('document_type') == 'Incoming')):
                doc['status'] = new_status
                doc['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Add to history if available
                if 'history' not in doc:
                    doc['history'] = []
                
                doc['history'].append({
                    'action': f"Status Updated to {new_status}",
                    'user': session.get('username', 'User'),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': new_status
                })
                
                # Mark session as modified
                session.modified = True
                found = True
                break
    
    # Redirect back to the incoming documents page
    return redirect(url_for('incoming'))

@app.route('/update_outgoing_status/<doc_code>', methods=['POST'])
def update_outgoing_status(doc_code):
    """Update the status of an outgoing document"""
    if 'user_id' not in session:
        flash('Please log in to update document status', 'warning')
        return redirect(url_for('login'))
    
    # Get the new status from the form
    new_status = request.form.get('status', '')
    
    if not new_status:
        flash('No status provided', 'danger')
        return redirect(url_for('outgoing'))
    
    # Update the document status in the database
    conn = None
    try:
        conn = get_db_connection()
        # Update document status
        result = conn.execute('UPDATE document SET status = ? WHERE tracking_code = ?', 
                           (new_status, doc_code))
        
        if result.rowcount > 0:
            # Add to document history
            document = conn.execute('SELECT id FROM document WHERE tracking_code = ?', 
                                  (doc_code,)).fetchone()
            
            if document:
                conn.execute(
                    'INSERT INTO document_history (document_id, action, details, user_id) VALUES (?, ?, ?, ?)',
                    (document['id'], f"Status Updated", f"New status: {new_status}", session.get('user_id'))
                )
            
            conn.commit()
            flash(f'Document {doc_code} status updated to {new_status}', 'success')
        else:
            flash(f'Document {doc_code} not found', 'warning')
            
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error updating document status: {e}")
        flash(f"Error updating document status: {str(e)}", 'danger')
    finally:
        if conn:
            conn.close()
    
    # For backwards compatibility: also update in the session if the document exists there
    if 'composed_documents' in session:
        for doc in session['composed_documents']:
            # Check tracking_code
            if doc.get('tracking_code') == doc_code:
                doc['status'] = new_status
                doc['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Add to history if available
                if 'history' not in doc:
                    doc['history'] = []
                
                doc['history'].append({
                    'action': f"Status Updated to {new_status}",
                    'user': session.get('username', 'User'),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': new_status
                })
                
                # Mark session as modified
                session.modified = True
                break
    
    # Redirect back to the outgoing documents page
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

@app.route('/file_manager')
@requires_permission('file_manager')
def file_manager():
    """File manager route - manage uploaded files"""
    # Log this access
    log_activity(session.get('user_id'), 'view_file_manager', {'request': 'view'})
    
    # Get all files from the uploads directory
    files = []
    total_size = 0
    file_types = {}
    
    try:
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path):
                # Get file stats
                file_stats = os.stat(file_path)
                size = file_stats.st_size
                total_size += size
                
                # Parse the filename to extract metadata
                # Assuming format: [document_id]_[timestamp]_[original_filename]
                parts = filename.split('_', 2)
                doc_id = parts[0] if len(parts) >= 2 else 'unknown'
                original_name = parts[2] if len(parts) >= 3 else filename
                
                # Try to determine file type from extension
                file_ext = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else ''
                
                # Count file types for statistics
                if file_ext:
                    if file_ext in file_types:
                        file_types[file_ext] += 1
                    else:
                        file_types[file_ext] = 1
                
                # Get creation and modification times
                creation_time = datetime.fromtimestamp(file_stats.st_ctime)
                modification_time = datetime.fromtimestamp(file_stats.st_mtime)
                
                files.append({
                    'name': original_name,
                    'filename': filename,  # Stored filename for download
                    'path': filename,      # Keep path for backward compatibility
                    'size': get_human_readable_size(size),
                    'size_bytes': size,
                    'doc_id': doc_id,
                    'type': file_ext.upper() if file_ext else 'UNKNOWN',
                    'file_ext': file_ext,
                    'icon': 'fa-file',  # Assuming a default icon
                    'created': creation_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'modified': modification_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'original_name': original_name
                })
    except Exception as e:
        flash(f'Error accessing files: {str(e)}', 'danger')
    
    # Sort files by creation date (newest first)
    files.sort(key=lambda x: x['created'], reverse=True)
    
    # Get stats
    stats = {
        'total_files': len(files),
        'total_size': get_human_readable_size(total_size),
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'max_upload_size': get_human_readable_size(app.config['MAX_CONTENT_LENGTH']),
        'file_types': file_types
    }
    
    return render_template('file_manager.html', 
                           files=files,
                           stats=stats,
                           active_page='file_manager')

@app.route('/file_upload', methods=['POST'])
@requires_permission('file_manager')
def file_upload():
    """Handle file uploads for the file manager"""
    if 'user_id' not in session:
        flash('Please log in to upload files', 'warning')
        return redirect(url_for('login'))
    
    if request.method != 'POST':
        return redirect(url_for('file_manager'))
    
    # Check if the post request has the file part
    if 'file' not in request.files:
        flash('No file part in the request', 'danger')
        return redirect(url_for('file_manager'))
    
    file = request.files['file']
    
    # If user does not select file, browser also submits an empty part without filename
    if file.filename == '':
        flash('No file selected for uploading', 'danger')
        return redirect(url_for('file_manager'))
    
    # Get form data
    title = request.form.get('title', '').strip()
    document_id = request.form.get('document_id', '').strip()
    
    # Validate file type and size
    if not allowed_file(file.filename):
        allowed_ext_list = ', '.join(app.config['ALLOWED_EXTENSIONS'])
        flash(f'Invalid file type. Allowed types: {allowed_ext_list}', 'danger')
        return redirect(url_for('file_manager'))
    
    try:
        # Upload the file
        file_info = handle_file_upload(file, document_id if document_id else None)
        
        if file_info:
            flash(f'File "{file_info["original_filename"]}" uploaded successfully', 'success')
        else:
            flash('File upload failed', 'danger')
    except Exception as e:
        flash(f'Error uploading file: {str(e)}', 'danger')
    
    return redirect(url_for('file_manager'))

@app.route('/delete_file', methods=['POST'])
@requires_permission('file_manager')
def delete_file():
    """Delete a file from the uploads directory"""
    if 'user_id' not in session:
        flash('Please log in to delete files', 'warning')
        return redirect(url_for('login'))
    
    if request.method != 'POST':
        return redirect(url_for('file_manager'))
    
    # Check if request is AJAX (JSON) or form
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/json'
    
    # Get filename from form data or JSON data
    if request.is_json:
        data = request.get_json()
        filename = data.get('filename')
    else:
        filename = request.form.get('filename')
    
    # Validate filename
    if not filename or '..' in filename:
        message = 'Invalid file request'
        if is_ajax:
            return jsonify({'success': False, 'message': message})
        flash(message, 'danger')
        return redirect(url_for('file_manager'))
    
    try:
        # Check if file exists
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(file_path):
            # Delete the file
            os.remove(file_path)
            message = f'File "{filename}" has been deleted'
            
            # Log the activity
            log_activity(session.get('user_id'), 'delete_file', {'filename': filename, 'path': file_path})
            
            if is_ajax:
                return jsonify({'success': True, 'message': message})
            flash(message, 'success')
        else:
            message = 'File not found'
            if is_ajax:
                return jsonify({'success': False, 'message': message})
            flash(message, 'danger')
    except Exception as e:
        message = f'Error deleting file: {str(e)}'
        if is_ajax:
            return jsonify({'success': False, 'message': message})
        flash(message, 'danger')
    
    return redirect(url_for('file_manager'))

@app.route('/document_workflow/<tracking_code>')
@requires_permission('track_document')
def document_workflow(tracking_code):
    if 'user' not in session:
        flash('Please log in to continue.', 'warning')
        return redirect(url_for('login'))
        
    # In a real app, we would fetch document data from the database
    # For demo, we'll use hardcoded data based on tracking code
    document = None
    
    if tracking_code == 'KMR-2023-001':
        document = {
            'tracking_code': 'KMR-2023-001',
            'title': 'Annual Financial Report 2023',
            'type': 'Financial Report',
            'submitted_by': 'John Smith',
            'date_created': '2023-10-15',
            'current_department': 'Registry',
            'status': 'Pending',
            'priority': 'Urgent',
            'current_stage_time': '1 day 2 hours',
            'total_time': '1 day 3 hours',
            'efficiency': '85%',
            'sla_status': 'On track',
            'steps_completed': 2,
            'total_steps': 6,
            'workflow': [
                {
                    'step': 'Document Created',
                    'status': 'Completed',
                    'icon': 'file-alt',
                    'description': 'John Smith created this document',
                    'timestamp': '2023-10-15 09:30 AM'
                },
                {
                    'step': 'Submitted for Review',
                    'status': 'Completed',
                    'icon': 'paper-plane',
                    'description': 'Document submitted to Registry department',
                    'timestamp': '2023-10-15 10:15 AM'
                },
                {
                    'step': 'Registry Review',
                    'status': 'In Progress',
                    'icon': 'clipboard-check',
                    'description': 'Document is being reviewed by Registry',
                    'timestamp': '2023-10-15 10:20 AM'
                },
                {
                    'step': 'Departmental Review',
                    'status': 'Pending',
                    'icon': 'user-check',
                    'description': 'Department review and approval',
                    'timestamp': None
                },
                {
                    'step': 'Final Approval',
                    'status': 'Pending',
                    'icon': 'check-double',
                    'description': 'Final review and approval process',
                    'timestamp': None
                },
                {
                    'step': 'Process Complete',
                    'status': 'Pending',
                    'icon': 'flag-checkered',
                    'description': 'Document processing completed',
                    'timestamp': None
                }
            ],
            'attachments': [
                {
                    'name': 'Financial_Report_2023.pdf',
                    'type': 'pdf',
                    'icon': 'file-pdf'
                },
                {
                    'name': 'Financial_Data.xlsx',
                    'type': 'excel',
                    'icon': 'file-excel'
                },
                {
                    'name': 'Executive_Summary.docx',
                    'type': 'word',
                    'icon': 'file-word'
                }
            ]
        }
    elif tracking_code == 'KMR-2023-002':
        document = {
            'tracking_code': 'KMR-2023-002',
            'title': 'Research Grant Application',
            'type': 'Grant Application',
            'submitted_by': 'Emily Johnson',
            'date_created': '2023-10-15',
            'current_department': 'Registry',
            'status': 'Pending',
            'priority': 'Priority',
            'current_stage_time': '6 hours',
            'total_time': '8 hours',
            'efficiency': '92%',
            'sla_status': 'On track',
            'steps_completed': 2,
            'total_steps': 6,
            'workflow': [
                {
                    'step': 'Document Created',
                    'status': 'Completed',
                    'icon': 'file-alt',
                    'description': 'Emily Johnson created this document',
                    'timestamp': '2023-10-15 12:30 PM'
                },
                {
                    'step': 'Submitted for Review',
                    'status': 'Completed',
                    'icon': 'paper-plane',
                    'description': 'Document submitted to Registry department',
                    'timestamp': '2023-10-15 01:45 PM'
                },
                {
                    'step': 'Registry Review',
                    'status': 'In Progress',
                    'icon': 'clipboard-check',
                    'description': 'Document is being reviewed by Registry',
                    'timestamp': '2023-10-15 02:00 PM'
                },
                {
                    'step': 'Departmental Review',
                    'status': 'Pending',
                    'icon': 'user-check',
                    'description': 'Department review and approval',
                    'timestamp': None
                },
                {
                    'step': 'Final Approval',
                    'status': 'Pending',
                    'icon': 'check-double',
                    'description': 'Final review and approval process',
                    'timestamp': None
                },
                {
                    'step': 'Process Complete',
                    'status': 'Pending',
                    'icon': 'flag-checkered',
                    'description': 'Document processing completed',
                    'timestamp': None
                }
            ],
            'attachments': [
                {
                    'name': 'Research_Proposal.pdf',
                    'type': 'pdf',
                    'icon': 'file-pdf'
                },
                {
                    'name': 'Budget_Breakdown.xlsx',
                    'type': 'excel',
                    'icon': 'file-excel'
                },
                {
                    'name': 'CV_Emily_Johnson.pdf',
                    'type': 'pdf',
                    'icon': 'file-pdf'
                }
            ]
        }
    
    if document is None:
        flash(f'Document with tracking code {tracking_code} not found.', 'danger')
        return redirect(url_for('track_document'))
        
    return render_template('registry_workflow.html', document=document)

@app.route('/registry_dashboard')
@requires_permission('registry_approval')
def registry_dashboard():
    """Registry workflow dashboard with metrics and overview"""
    # Log this access
    log_activity(session.get('user_id'), 'view_registry_dashboard', {'request': 'view'})
    
    # Get filter parameters
    date_range = request.args.get('date_range', 'week')
    
    # In a real app, these metrics would be calculated from database queries
    # For demo purposes, use sample data
    
    # Sample overall metrics
    overall_metrics = {
        'total_documents': 127,
        'documents_pending': 42,
        'documents_in_review': 35,
        'documents_approved': 38,
        'documents_rejected': 12,
        'avg_processing_time': '2.3 days',
        'sla_compliance': '94%',
        'documents_overdue': 3
    }
    
    # Sample department metrics
    department_metrics = [
        {
            'name': 'Research',
            'total': 45,
            'pending': 15,
            'approved': 20,
            'rejected': 5,
            'in_review': 5,
            'avg_time': '2.1 days'
        },
        {
            'name': 'Finance',
            'total': 30,
            'pending': 10,
            'approved': 12,
            'rejected': 3,
            'in_review': 5,
            'avg_time': '1.8 days'
        },
        {
            'name': 'HR',
            'total': 20,
            'pending': 5,
            'approved': 10,
            'rejected': 2,
            'in_review': 3,
            'avg_time': '1.5 days'
        },
        {
            'name': 'Laboratory',
            'total': 15,
            'pending': 8,
            'approved': 2,
            'rejected': 1,
            'in_review': 4,
            'avg_time': '3.2 days'
        },
        {
            'name': 'IT',
            'total': 17,
            'pending': 4,
            'approved': 8,
            'rejected': 1,
            'in_review': 4,
            'avg_time': '2.0 days'
        }
    ]
    
    # Sample document type metrics
    document_type_metrics = [
        {
            'type': 'Research Proposal',
            'total': 35,
            'pending': 12,
            'approved': 15,
            'rejected': 3,
            'in_review': 5,
            'avg_time': '3.5 days'
        },
        {
            'type': 'Budget Request',
            'total': 28,
            'pending': 8,
            'approved': 12,
            'rejected': 2,
            'in_review': 6,
            'avg_time': '2.2 days'
        },
        {
            'type': 'Equipment Request',
            'total': 22,
            'pending': 10,
            'approved': 5,
            'rejected': 2,
            'in_review': 5,
            'avg_time': '2.8 days'
        },
        {
            'type': 'Leave Application',
            'total': 18,
            'pending': 4,
            'approved': 10,
            'rejected': 1,
            'in_review': 3,
            'avg_time': '1.2 days'
        },
        {
            'type': 'Ethics Application',
            'total': 24,
            'pending': 8,
            'approved': 10,
            'rejected': 4,
            'in_review': 2,
            'avg_time': '4.5 days'
        }
    ]
    
    # Sample workflow bottlenecks (stages with highest average processing time)
    bottlenecks = [
        {
            'stage': 'Ethics Review',
            'avg_time': '5.2 days',
            'documents_in_stage': 8,
            'trend': '+0.5 days',  # Increasing (getting worse)
            'recommendation': 'Add additional reviewer to Ethics Committee'
        },
        {
            'stage': 'Financial Approval',
            'avg_time': '3.8 days',
            'documents_in_stage': 12,
            'trend': '-0.2 days',  # Decreasing (improving)
            'recommendation': 'Continue monitoring'
        },
        {
            'stage': 'Director Review',
            'avg_time': '2.9 days',
            'documents_in_stage': 5,
            'trend': '+0.3 days',
            'recommendation': 'Create pre-review checklist to streamline decisions'
        }
    ]
    
    # Sample recent activity
    recent_activity = [
        {
            'timestamp': '2025-04-30 14:23:15',
            'user': 'John Smith',
            'action': 'Approved',
            'document': 'Research Proposal',
            'tracking_code': 'KEMRI-20250430-1001',
            'notes': 'Approved and forwarded to Ethics Committee'
        },
        {
            'timestamp': '2025-04-30 13:05:42',
            'user': 'Jane Doe',
            'action': 'Rejected',
            'document': 'Budget Request',
            'tracking_code': 'KEMRI-20250430-1002',
            'notes': 'Missing supporting documentation'
        },
        {
            'timestamp': '2025-04-30 11:30:18',
            'user': 'Mark Johnson',
            'action': 'Forwarded',
            'document': 'Equipment Request',
            'tracking_code': 'KEMRI-20250429-1008',
            'notes': 'Forwarded to Finance for final approval'
        },
        {
            'timestamp': '2025-04-30 10:15:33',
            'user': 'Sarah Williams',
            'action': 'Changes Requested',
            'document': 'Research Ethics Application',
            'tracking_code': 'KEMRI-20250429-1006',
            'notes': 'Need additional details on participant consent'
        },
        {
            'timestamp': '2025-04-30 09:45:20',
            'user': 'Robert Brown',
            'action': 'Received',
            'document': 'Leave Application',
            'tracking_code': 'KEMRI-20250430-1003',
            'notes': 'Acknowledged receipt'
        }
    ]
    
    # Generate chart data (for visualization in JavaScript)
    # Daily document volume for the past week
    daily_volume = [
        {'date': '2025-04-24', 'submitted': 18, 'approved': 15, 'rejected': 3},
        {'date': '2025-04-25', 'submitted': 22, 'approved': 18, 'rejected': 4},
        {'date': '2025-04-26', 'submitted': 15, 'approved': 12, 'rejected': 2},
        {'date': '2025-04-27', 'submitted': 8, 'approved': 6, 'rejected': 1},  # Weekend
        {'date': '2025-04-28', 'submitted': 25, 'approved': 20, 'rejected': 5},
        {'date': '2025-04-29', 'submitted': 28, 'approved': 22, 'rejected': 6},
        {'date': '2025-04-30', 'submitted': 20, 'approved': 15, 'rejected': 4}
    ]
    
    # Processing time by document type
    processing_times = [
        {'type': 'Research Proposal', 'time': 3.5},
        {'type': 'Budget Request', 'time': 2.2},
        {'type': 'Equipment Request', 'time': 2.8},
        {'type': 'Leave Application', 'time': 1.2},
        {'type': 'Ethics Application', 'time': 4.5}
    ]
    
    # Status distribution
    status_distribution = [
        {'status': 'Pending', 'count': 42, 'color': '#ffc107'},
        {'status': 'In Review', 'count': 35, 'color': '#17a2b8'},
        {'status': 'Approved', 'count': 38, 'color': '#28a745'},
        {'status': 'Rejected', 'count': 12, 'color': '#dc3545'}
    ]
    
    # Trend data for workflow metrics over time
    trends = {
        'processing_time': [2.8, 2.5, 2.4, 2.3, 2.3, 2.2, 2.3],  # Days (past 7 days)
        'sla_compliance': [90, 92, 93, 91, 94, 95, 94],  # Percentage (past 7 days)
        'document_volume': [18, 22, 15, 8, 25, 28, 20]  # Total documents (past 7 days)
    }
    
    # Documents requiring immediate attention (overdue or high priority)
    urgent_documents = [
        {
            'tracking_code': 'KEMRI-20250428-1005',
            'title': 'COVID-19 Research Funding',
            'status': 'Pending',
            'days_in_stage': 3,
            'due_date': '2025-04-30',
            'priority': 'Urgent',
            'is_overdue': True
        },
        {
            'tracking_code': 'KEMRI-20250429-1003',
            'title': 'Laboratory Safety Audit',
            'status': 'In Review',
            'days_in_stage': 2,
            'due_date': '2025-05-01',
            'priority': 'Urgent',
            'is_overdue': False
        },
        {
            'tracking_code': 'KEMRI-20250427-1008',
            'title': 'Emergency Medical Supplies',
            'status': 'Pending',
            'days_in_stage': 4,
            'due_date': '2025-04-29',
            'priority': 'Urgent',
            'is_overdue': True
        }
    ]
    
    return render_template('registry_dashboard.html',
                           overall_metrics=overall_metrics,
                           department_metrics=department_metrics,
                           document_type_metrics=document_type_metrics,
                           bottlenecks=bottlenecks,
                           recent_activity=recent_activity,
                           daily_volume=daily_volume,
                           processing_times=processing_times,
                           status_distribution=status_distribution,
                           trends=trends,
                           urgent_documents=urgent_documents,
                           date_range=date_range,
                           active_page='registry_dashboard')

@app.route('/workflow_notification', methods=['POST'])
@requires_permission('registry_approval')
def workflow_notification():
    """Send notifications to stakeholders about workflow updates"""
    if request.method != 'POST':
        return jsonify({'success': False, 'message': 'Method not allowed'}), 405
    
    # Get notification data from request
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    tracking_code = data.get('tracking_code')
    recipients = data.get('recipients', [])
    message = data.get('message', '')
    notification_type = data.get('type', 'status_update')
    
    if not tracking_code or not recipients or not message:
        return jsonify({'success': False, 'message': 'Missing required parameters'}), 400
    
    # Log the notification
    log_activity(session.get('user_id'), 'send_workflow_notification', {
        'tracking_code': tracking_code,
        'recipients': recipients,
        'message': message,
        'type': notification_type
    })
    
    # In a real app, this would send actual notifications via email, SMS, or in-app
    # For demo purposes, just return success
    
    return jsonify({
        'success': True,
        'message': f'Notification about document {tracking_code} sent to {len(recipients)} recipients',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/registry_workflow')
@requires_permission('registry_approval')
def registry_workflow():
    if 'user' not in session:
        flash('Please log in to continue.', 'warning')
        return redirect(url_for('login'))
    
    # Start with demo data
    documents = [
        {
            'tracking_code': 'KMR-2023-001',
            'title': 'Annual Financial Report 2023',
            'type': 'Financial Report',
            'submitted_by': 'John Smith',
            'date_created': '2023-10-15',
            'current_department': 'Registry',
            'status': 'Pending',
            'priority': 'Urgent',
            'steps_completed': 2,
            'total_steps': 6,
            'last_activity': '2023-10-15 10:20 AM'
        },
        {
            'tracking_code': 'KMR-2023-002',
            'title': 'Research Grant Application',
            'type': 'Grant Application',
            'submitted_by': 'Emily Johnson',
            'date_created': '2023-10-15',
            'current_department': 'Registry',
            'status': 'Pending',
            'priority': 'Priority',
            'steps_completed': 2,
            'total_steps': 6,
            'last_activity': '2023-10-15 02:00 PM'
        },
        {
            'tracking_code': 'KMR-2023-003',
            'title': 'Equipment Requisition Request',
            'type': 'Procurement',
            'submitted_by': 'Robert Chen',
            'date_created': '2023-10-16',
            'current_department': 'Registry',
            'status': 'Pending',
            'priority': 'Normal',
            'steps_completed': 2,
            'total_steps': 5,
            'last_activity': '2023-10-16 09:15 AM'
        },
        {
            'tracking_code': 'KMR-2023-004',
            'title': 'Staff Training Program Proposal',
            'type': 'HR',
            'submitted_by': 'Sarah Williams',
            'date_created': '2023-10-17',
            'current_department': 'HR',
            'status': 'Approved',
            'priority': 'Priority',
            'steps_completed': 3,
            'total_steps': 5,
            'last_activity': '2023-10-17 03:45 PM'
        },
        {
            'tracking_code': 'KMR-2023-005',
            'title': 'Laboratory Equipment Maintenance Report',
            'type': 'Technical',
            'submitted_by': 'Michael Lee',
            'date_created': '2023-10-18',
            'current_department': 'Finance',
            'status': 'Rejected',
            'priority': 'Normal',
            'steps_completed': 2,
            'total_steps': 4,
            'last_activity': '2023-10-18 11:30 AM'
        }
    ]
    
    # Add any documents from the session
    if 'composed_documents' in session:
        # Add each composed document that's not already in the list
        existing_tracking_codes = [doc['tracking_code'] for doc in documents]
        for doc in session['composed_documents']:
            if doc['tracking_code'] not in existing_tracking_codes:
                # Make sure the document has the required fields
                if 'last_activity' not in doc:
                    doc['last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                if 'steps_completed' not in doc:
                    doc['steps_completed'] = 1
                if 'total_steps' not in doc:
                    doc['total_steps'] = 6
                documents.append(doc)
    
    return render_template('registry_workflow_list.html', documents=documents)

@app.route('/admin_settings')
@requires_permission('view_users')
def admin_settings():
    """Admin settings page"""
    # Log this action
    log_activity(session.get('user_id'), 'view_admin_settings', {'request': 'view'})
    
    settings = {
        'system_name': 'KEMRI Laboratory System',
        'version': '1.0.0',
        'maintenance_mode': False,
        'debug_mode': True,
        'auto_logout_minutes': 30,
        'max_file_size_mb': 16,
        'allowed_file_types': '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.png',
        'smtp_host': 'smtp.example.com',
        'smtp_port': 587,
        'smtp_use_tls': True,
        'notification_email': 'notifications@kemri.org',
        'admin_email': 'admin@kemri.org',
        'backup_frequency': 'Daily',
        'backup_retention_days': 30
    }
    
    return render_template('admin_settings.html', 
                          settings=settings,
                          active_page='admin_settings')

@app.route('/admin_logs')
@requires_permission('view_users')
def admin_logs():
    """Admin logs page"""
    # Log this action
    log_activity(session.get('user_id'), 'view_admin_logs', {'request': 'view'})
    
    # Get recent logs from the activity_log table
    conn = get_db_connection()
    logs = conn.execute('''
        SELECT activity_log.*, user.username 
        FROM activity_log 
        LEFT JOIN user ON activity_log.user_id = user.id
        ORDER BY activity_log.timestamp DESC LIMIT 100
    ''').fetchall()
    conn.close()
    
    return render_template('admin_logs.html', 
                          logs=logs,
                          active_page='admin_logs')

def generate_tracking_code():
    """Generate a unique tracking code in the format KEMRI-YYYYMMDD-XXXX"""
    import random
    # Format: KEMRI-YYYYMMDD-XXXX where XXXX is a random 4-digit number
    today = datetime.now().strftime('%Y%m%d')
    random_digits = random.randint(1000, 9999)
    tracking_code = f"KEMRI-{today}-{random_digits}"
    
    # Check if code already exists in database
    conn = get_db_connection()
    try:
        # Use the correct column name 'tracking_code' instead of 'code'
        exists = conn.execute('SELECT COUNT(*) FROM document WHERE tracking_code = ?', 
                             (tracking_code,)).fetchone()[0] > 0
    except sqlite3.OperationalError as e:
        # If there's an error (like the table doesn't exist yet), assume the code doesn't exist
        print(f"Database error checking tracking code: {e}")
        exists = False
    except Exception as e:
        print(f"Error checking tracking code: {e}")
        exists = False
    finally:
        conn.close()
    
    # If code exists, try again recursively
    if exists:
        return generate_tracking_code()
    
    return tracking_code

@app.route('/add_attachment/<doc_code>', methods=['POST'])
def add_attachment(doc_code):
    """Placeholder route for add_attachment to prevent BuildError"""
    flash('Document attachment functionality is not available in debug mode', 'warning')
    return redirect(url_for('document_details', doc_code=doc_code))

@app.route('/document/<doc_code>')
def document_view(doc_code):
    """Placeholder for document view route"""
    return redirect(url_for('document_details', doc_code=doc_code))

@app.route('/reassign_document/<document_code>', methods=['POST'])
def reassign_document(document_code):
    """Placeholder route for reassign_document to prevent BuildError"""
    flash('Document reassignment is not available in debug mode', 'warning')
    return redirect(url_for('document_details', doc_code=document_code))

@app.route('/test-route/<int:user_id>', methods=['GET'])
def test_route(user_id):
    """Test route to check if routing is working"""
    return f"Test route successful with user_id: {user_id}"

if __name__ == '__main__':
    # Ensure the database exists
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file {DB_PATH} not found!")
        print("Please run init_db.py to create the database first.")
        exit(1)
    
    app.run(host='0.0.0.0', port=5000, debug=True) 