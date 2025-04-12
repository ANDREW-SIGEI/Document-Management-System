from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from config import Config
from datetime import datetime, timedelta
import json
import random
from sqlalchemy import case
import uuid
import os
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = 'kemri_secret_key'  # Required for flash messages
db = SQLAlchemy(app)

# Example model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(50), nullable=True)
    password = db.Column(db.String(100), nullable=True)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(50), nullable=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Login Activity Model
class LoginActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    login_date = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    device = db.Column(db.String(100))
    location = db.Column(db.String(100))
    
    user = db.relationship('User', backref=db.backref('login_activities', lazy=True))

# Document Model
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    sender = db.Column(db.String(100), nullable=False)
    recipient = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    required_action = db.Column(db.String(200), nullable=True)
    date_of_letter = db.Column(db.DateTime, default=datetime.utcnow)
    date_received = db.Column(db.DateTime, default=datetime.utcnow)
    priority = db.Column(db.String(20), default='Normal')  # Normal, Priority, Urgent
    status = db.Column(db.String(20), default='Incoming')  # Incoming, Pending, Received, Outgoing, Ended
    current_holder = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    processor = db.relationship('User', backref=db.backref('processed_documents', lazy=True))
    
    def __repr__(self):
        return f'<Document {self.code}>'

# System Log Model
class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    log_type = db.Column(db.String(20))  # Info, Success, Warning, Error
    user = db.Column(db.String(100))
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    
    def __repr__(self):
        return f'<SystemLog {self.action}>'

# Document Action History Model
class DocumentAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    user = db.Column(db.String(100), nullable=False)  # In a real app, this would be a foreign key
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action_description = db.Column(db.Text, nullable=True)
    status_before = db.Column(db.String(20), nullable=True)
    status_after = db.Column(db.String(20), nullable=True)
    
    document = db.relationship('Document', backref=db.backref('actions', lazy=True, order_by='DocumentAction.timestamp'))
    
    def __repr__(self):
        return f'<DocumentAction {self.action}>'

# Initialize the database
with app.app_context():
    # Drop all tables and recreate them
    db.drop_all()
    db.create_all()
    
    # Check if any users exist, if not create a sample user
    if not User.query.first():
        sample_user = User(
            username='admin', 
            email='admin@example.com',
            phone='+1234567890',
            department='IT Department',
            password='password',  # In a real app, this would be hashed
            created_at=datetime.strptime('2025-01-15', '%Y-%m-%d'),
            role='Administrator'
        )
        db.session.add(sample_user)
        db.session.commit()
        
        # Add sample documents
        statuses = ['Incoming', 'Pending', 'Received', 'Outgoing', 'Ended']
        priorities = ['Normal', 'Priority', 'Urgent']
        departments = ['IT Department', 'Finance', 'HR', 'Marketing', 'Research']
        
        for i in range(1, 21):
            # Generate a random date within the last 30 days
            days_ago = random.randint(0, 30)
            date = datetime.utcnow() - timedelta(days=days_ago)
            
            # Generate sample document
            doc = Document(
                code=f'DOC-{2025}-{i:03d}',
                title=f'Sample Document {i}',
                sender=random.choice(departments),
                recipient='KEMRI ' + random.choice(departments),
                details=f'This is a sample document {i} for testing purposes.',
                required_action=random.choice(['Review', 'Approve', 'Comment', 'File', 'Forward']),
                date_of_letter=date,
                date_received=date + timedelta(days=random.randint(1, 3)),
                priority=random.choice(priorities),
                status=random.choice(statuses),
                current_holder=f'User {random.randint(1, 5)}',
                created_at=date,
                updated_at=date + timedelta(days=random.randint(0, 5)),
                processed_by=1
            )
            db.session.add(doc)
        
        db.session.commit()
        
        # Add sample login activities
        activities = [
            LoginActivity(
                user_id=1,
                login_date=datetime.utcnow(),
                ip_address='192.168.1.1',
                device='Chrome on Windows',
                location='New York, USA'
            ),
            LoginActivity(
                user_id=1,
                login_date=datetime.utcnow().replace(day=datetime.utcnow().day-1),
                ip_address='192.168.1.1',
                device='Chrome on Windows',
                location='New York, USA'
            ),
            LoginActivity(
                user_id=1,
                login_date=datetime.strptime('2025-04-03 09:45:00', '%Y-%m-%d %H:%M:%S'),
                ip_address='192.168.1.1',
                device='Chrome on Windows',
                location='New York, USA'
            )
        ]
        db.session.bulk_save_objects(activities)
        db.session.commit()

        # Add sample system logs
        if not SystemLog.query.first():
            logs = [
                SystemLog(
                    timestamp=datetime.utcnow(),
                    log_type='Info',
                    user='System',
                    action='System Started',
                    details='Document management system started successfully'
                ),
                SystemLog(
                    timestamp=datetime.utcnow() - timedelta(minutes=30),
                    log_type='Success',
                    user='Admin',
                    action='Backup Completed',
                    details='System backup completed successfully'
                ),
                SystemLog(
                    timestamp=datetime.utcnow() - timedelta(hours=2),
                    log_type='Warning',
                    user='System',
                    action='Low Storage',
                    details='Storage usage is reaching 80% capacity'
                ),
                SystemLog(
                    timestamp=datetime.utcnow() - timedelta(days=1),
                    log_type='Error',
                    user='System',
                    action='Database Connection',
                    details='Temporary database connection issue (resolved)'
                )
            ]
            db.session.bulk_save_objects(logs)
            db.session.commit()

@app.route('/')
def index():
    """Homepage route - redirects to dashboard or login"""
    # Check if user is authenticated here (not implemented in this demo)
    # In a real app, you would use something like: if current_user.is_authenticated
    authenticated = False
    
    if authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route for user authentication"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False) == 'on'
        
        # Check against database
        user = User.query.filter_by(username=username).first()
        
        # For debugging
        print(f"Login attempt - Username: {username}, Password: {password}")
        if user:
            print(f"User found - Username: {user.username}, Password in DB: {user.password}")
        
        if user and user.password == password:
            # Successful login - redirect to dashboard
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            # Failed login
            flash('Invalid username or password', 'danger')
    
    # GET request or failed login - show login form
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # Count documents by status
    incoming_count = Document.query.filter_by(status='Incoming').count()
    pending_count = Document.query.filter_by(status='Pending').count()
    received_count = Document.query.filter_by(status='Received').count()
    ended_count = Document.query.filter_by(status='Ended').count()
    
    # Get recent documents
    recent_documents = Document.query.order_by(Document.created_at.desc()).limit(10).all()
    
    # For each document, add a deadline field if it doesn't exist
    for doc in recent_documents:
        if not hasattr(doc, 'deadline'):
            # Calculate a mock deadline based on priority
            days = 7  # Normal priority
            if doc.priority == 'Priority':
                days = 5
            elif doc.priority == 'Urgent':
                days = 2
            doc.deadline = (doc.created_at + timedelta(days=days)).strftime('%Y-%m-%d')
    
    return render_template('dashboard.html', 
                          users=User.query.all(),
                          documents=recent_documents,
                          incoming_count=incoming_count,
                          pending_count=pending_count,
                          received_count=received_count,
                          ended_count=ended_count)

@app.route('/compose', methods=['GET', 'POST'])
def compose():
    """Upload new document page"""
    
    if request.method == 'POST':
        # Get form data
        document_direction = request.form.get('document_direction', 'incoming')
        document_title = request.form.get('document_title')
        sender = request.form.get('sender')
        sender_email = request.form.get('sender_email')
        sender_department = request.form.get('sender_department')
        recipient = request.form.get('recipient')
        recipient_email = request.form.get('recipient_email')
        recipient_department = request.form.get('recipient_department')
        details = request.form.get('details')
        required_action = request.form.get('required_action')
        priority = request.form.get('priority', 'Normal')
        is_confidential = request.form.get('is_confidential') == 'on'
        needs_signature = request.form.get('needs_signature') == 'on'
        send_notification = request.form.get('send_notification') == 'on'
        tags = request.form.get('tags', '')
        expected_completion = request.form.get('expected_completion')
        
        # Get the uploaded file
        document_file = request.files.get('document')
        
        if document_file and document_file.filename:
            # Check if a preset tracking code was provided
            preset_code = request.form.get('preset_tracking_code')
            
            if preset_code and preset_code.startswith('DOC-'):
                document_code = preset_code
            else:
                # Generate unique document code
                timestamp = datetime.now().strftime('%Y%m%d')
                random_hex = uuid.uuid4().hex[:8].upper()
                document_code = f"DOC-{timestamp}-{random_hex}"
            
            # Secure the filename and add document code
            filename = secure_filename(document_file.filename)
            stored_filename = f"{document_code}_{filename}"
            
            # Save the file (in a real app, you'd save to a secure location)
            # For demo, just pretend we saved the file
            # document_file.save(os.path.join(app.config['UPLOAD_FOLDER'], stored_filename))
            
            # Calculate deadline based on priority
            deadline = None
            if expected_completion:
                deadline = expected_completion
            else:
                days = 7  # Normal priority
                if priority == 'Priority':
                    days = 5
                elif priority == 'Urgent':
                    days = 2
                deadline = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Determine status based on direction
            status = 'Incoming' if document_direction == 'incoming' else 'Outgoing'
            
            # Determine current holder
            current_holder = recipient if document_direction == 'outgoing' else sender
            
            # Parse tags
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            
            # Create document tracking entry
            document_data = {
                "code": document_code,
                "filename": filename,
                "stored_filename": stored_filename,
                "sender": sender,
                "sender_email": sender_email,
                "sender_department": sender_department,
                "recipient": recipient,
                "recipient_email": recipient_email,
                "recipient_department": recipient_department,
                "details": details,
                "required_action": required_action,
                "date": datetime.now().strftime('%Y-%m-%d'),
                "status": status,
                "priority": priority,
                "current_holder": current_holder,
                "deadline": deadline,
                "workflow_stage": "Initial Review",
                "is_confidential": is_confidential,
                "document_type": os.path.splitext(filename)[1][1:].upper(),
                "file_size": str(len(document_file.read())),
                "tags": tag_list,
                "related_documents": [],
                "version": "1.0",
                "access_permissions": [
                    {
                        "user_id": "1",  # Assuming current user ID is 1
                        "permission": "full"
                    }
                ],
                "notification_status": {
                    "recipients_notified": [],
                    "reminders_sent": []
                },
                "actions": [
                    {
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "user": sender,
                        "user_id": "1",  # Assuming current user ID is 1
                        "action": "Document uploaded",
                        "notes": "Initial upload to the system",
                        "previous_status": None,
                        "new_status": status,
                        "ip_address": request.remote_addr,
                        "device": f"Desktop - {request.user_agent.browser}"
                    }
                ],
                "comments": [],
                "approval_flow": [
                    {
                        "step": 1,
                        "role": "Initial Review",
                        "user_id": None,
                        "status": "pending",
                        "notes": ""
                    },
                    {
                        "step": 2,
                        "role": "Immediate Action",
                        "user_id": None,
                        "status": "not_started",
                        "notes": ""
                    },
                    {
                        "step": 3,
                        "role": "Filing",
                        "user_id": None,
                        "status": "not_started",
                        "notes": ""
                    }
                ],
                "audit_trail": {
                    "created_by": "1",  # Assuming current user ID is 1
                    "created_on": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "last_modified_by": "1",
                    "last_modified_on": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            # In a real app, save to database
            # For demo purposes, let's pretend we're adding it to our fake database
            try:
                # Load existing tracking data
                tracking_file = "document_tracking.json"
                if os.path.exists(tracking_file):
                    with open(tracking_file, 'r') as f:
                        tracking_data = json.load(f)
                        
                    # Add the new document
                    tracking_data['documents'].append(document_data)
                    
                    # Save the updated data
                    with open(tracking_file, 'w') as f:
                        json.dump(tracking_data, f, indent=4)
                else:
                    # Create a new tracking file
                    tracking_data = {
                        "users": [],
                        "documents": [document_data],
                        "system_settings": {
                            "notification_settings": {
                                "email_enabled": True,
                                "sender_email": "noreply@docmanagementsystem.com",
                                "smtp_server": "smtp.example.com",
                                "smtp_port": 587,
                                "urgent_notification_interval": 1,
                                "normal_notification_interval": 24,
                                "reminder_frequency": 48
                            },
                            "retention_policy": {
                                "default_retention_period": 365,
                                "confidential_retention_period": 730,
                                "archive_after_completion": True
                            },
                            "workflow_templates": [
                                {
                                    "name": "Standard Review",
                                    "steps": [
                                        "Initial Review",
                                        "Department Approval",
                                        "Final Approval",
                                        "Filing"
                                    ]
                                },
                                {
                                    "name": "Urgent Process",
                                    "steps": [
                                        "Initial Review",
                                        "Immediate Action",
                                        "Filing"
                                    ]
                                }
                            ]
                        }
                    }
                    with open(tracking_file, 'w') as f:
                        json.dump(tracking_data, f, indent=4)
                
                # If notification is enabled, add notification record
                if send_notification and recipient_email:
                    notification = {
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "user": "System",
                        "user_id": "0",
                        "action": "Notification sent",
                        "notes": "Email notification sent to recipient",
                        "previous_status": status,
                        "new_status": status,
                        "ip_address": request.remote_addr,
                        "device": "Server"
                    }
                    
                    # In a real app, send actual email
                    # For demo, just add to actions list
                    document_data["actions"].append(notification)
                    
                    # Add to notification status
                    document_data["notification_status"]["recipients_notified"].append({
                        "user_id": "0",
                        "notification_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "notification_type": "email",
                        "notification_status": "sent"
                    })
                
                flash(f'Document uploaded successfully with tracking code: {document_code}', 'success')
                
                # Redirect to the document details page or to the appropriate list
                if document_direction == 'incoming':
                    return redirect(url_for('incoming'))
                else:
                    return redirect(url_for('outgoing'))
                    
            except Exception as e:
                # In a real app, log this error
                flash(f'Error saving document: {str(e)}', 'danger')
                return redirect(url_for('compose'))
        else:
            flash('No document file provided', 'danger')
            return redirect(url_for('compose'))
    
    # For GET requests, load the form with workflow templates and users
    workflow_templates = []
    users = []
    
    try:
        # Try to load tracking data for templates and users
        tracking_file = "document_tracking.json"
        if os.path.exists(tracking_file):
            with open(tracking_file, 'r') as f:
                tracking_data = json.load(f)
                workflow_templates = tracking_data.get('system_settings', {}).get('workflow_templates', [])
                users = tracking_data.get('users', [])
    except Exception as e:
        # In a real app, log this error
        print(f"Error loading tracking data: {str(e)}")
        # Provide default templates
        workflow_templates = [
            {"name": "Standard Review", "steps": ["Initial Review", "Department Approval", "Final Approval", "Filing"]},
            {"name": "Urgent Process", "steps": ["Initial Review", "Immediate Action", "Filing"]}
        ]
    
    # Get current user (Mock for demo)
    current_user = {
        "name": "Andrew Sigei",
        "email": "andrew.sigei@example.com",
        "department": "IT Department"
    }
    
    return render_template('compose.html', workflow_templates=workflow_templates, users=users, current_user=current_user)

@app.route('/track_document', methods=['GET', 'POST'])
def track_document():
    # Handle POST requests for direct document code tracking
    if request.method == 'POST':
        document_code = request.form.get('document_code')
        if not document_code:
            flash('Please enter a document code', 'danger')
            return redirect(url_for('track_document'))
        
        # First check if the document exists in the database
        db_document = Document.query.filter_by(code=document_code).first()
        if db_document:
            # If it exists in the database, redirect to the DB document details page
            return redirect(url_for('document_details', doc_code=document_code))
        
        # If not in DB, check in the JSON tracking file
        if os.path.exists('document_tracking.json'):
            try:
                with open('document_tracking.json', 'r') as f:
                    tracking_data = json.load(f)
                
                # Find document in JSON data
                json_document = None
                for doc in tracking_data.get('documents', []):
                    if doc.get('code') == document_code:
                        json_document = doc
                        break
                
                if json_document:
                    # If found in JSON, redirect to JSON document details page
                    return redirect(url_for('track_document_details', document_code=document_code))
            except Exception as e:
                app.logger.error(f"Error searching document in JSON: {str(e)}")
        
        # If not found in either place
        flash(f'Document with code {document_code} not found', 'danger')
        return redirect(url_for('track_document'))
    
    # Handle GET requests for the main tracking page or advanced search
    recent_documents = []
    search_results = []
    is_search = False
    
    # Check if we have a code parameter in the URL - this allows direct links to work
    code_param = request.args.get('code')
    if code_param:
        # If we have a code parameter, perform the lookup like a POST request
        # First check if the document exists in the database
        db_document = Document.query.filter_by(code=code_param).first()
        if db_document:
            # If it exists in the database, redirect to the DB document details page
            return redirect(url_for('document_details', doc_code=code_param))
        
        # If not in DB, check in the JSON tracking file
        if os.path.exists('document_tracking.json'):
            try:
                with open('document_tracking.json', 'r') as f:
                    tracking_data = json.load(f)
                
                # Find document in JSON data
                json_document = None
                for doc in tracking_data.get('documents', []):
                    if doc.get('code') == code_param:
                        json_document = doc
                        break
                
                if json_document:
                    # If found in JSON, redirect to JSON document details page
                    return redirect(url_for('track_document_details', document_code=code_param))
            except Exception as e:
                app.logger.error(f"Error searching document in JSON: {str(e)}")
        
        # If we didn't redirect, it means the document was not found
        # But we'll still pass the code to the template to pre-fill the tracking form
        qr_code_value = code_param
    else:
        qr_code_value = ""
    
    # Check if we have search parameters
    sender = request.args.get('sender', '')
    recipient = request.args.get('recipient', '')
    date_range = request.args.get('date_range', '')
    status = request.args.get('status', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Process the date range filter
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if date_range == 'today':
        start_date_obj = today
        end_date_obj = today + timedelta(days=1) - timedelta(seconds=1)
    elif date_range == 'yesterday':
        start_date_obj = today - timedelta(days=1)
        end_date_obj = today - timedelta(seconds=1)
    elif date_range == 'this_week':
        start_date_obj = today - timedelta(days=today.weekday())
        end_date_obj = start_date_obj + timedelta(days=7) - timedelta(seconds=1)
    elif date_range == 'last_week':
        start_date_obj = today - timedelta(days=today.weekday() + 7)
        end_date_obj = start_date_obj + timedelta(days=7) - timedelta(seconds=1)
    elif date_range == 'this_month':
        start_date_obj = today.replace(day=1)
        if today.month == 12:
            end_date_obj = today.replace(year=today.year + 1, month=1, day=1) - timedelta(seconds=1)
        else:
            end_date_obj = today.replace(month=today.month + 1, day=1) - timedelta(seconds=1)
    elif date_range == 'custom' and start_date and end_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'warning')
            start_date_obj = None
            end_date_obj = None
    else:
        # No date filter or 'all' selected
        start_date_obj = None
        end_date_obj = None
    
    # Check if any search parameter is provided
    if sender or recipient or status != 'all' or start_date_obj:
        is_search = True
        
        # Search in the database
        db_query = Document.query
        
        if sender:
            db_query = db_query.filter(Document.sender.ilike(f'%{sender}%'))
        
        if recipient:
            db_query = db_query.filter(Document.recipient.ilike(f'%{recipient}%'))
        
        if status and status != 'all':
            db_query = db_query.filter(Document.status == status)
        
        if start_date_obj and end_date_obj:
            db_query = db_query.filter(Document.created_at.between(start_date_obj, end_date_obj))
        
        # Get database search results
        db_documents = db_query.order_by(Document.created_at.desc()).all()
        for doc in db_documents:
            search_results.append({
                'code': doc.code,
                'timestamp': doc.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'filename': doc.title,
                'status': doc.status,
                'source': 'database',
                'sender': doc.sender,
                'recipient': doc.recipient
            })
        
        # Search in JSON file if it exists
        if os.path.exists('document_tracking.json'):
            try:
                with open('document_tracking.json', 'r') as f:
                    tracking_data = json.load(f)
                
                if 'documents' in tracking_data:
                    for doc in tracking_data['documents']:
                        # Check if the document matches all search criteria
                        matches = True
                        
                        if sender and sender.lower() not in doc.get('sender', '').lower():
                            matches = False
                        
                        if recipient and recipient.lower() not in doc.get('recipient', '').lower():
                            matches = False
                        
                        if status and status != 'all' and doc.get('status', '') != status:
                            matches = False
                        
                        if start_date_obj and end_date_obj:
                            try:
                                doc_date = datetime.strptime(doc.get('audit_trail', {}).get('created_on', ''), '%Y-%m-%d %H:%M:%S')
                                if not (start_date_obj <= doc_date <= end_date_obj):
                                    matches = False
                            except (ValueError, TypeError):
                                # If date cannot be parsed, consider it non-matching
                                matches = False
                        
                        if matches:
                            search_results.append({
                                'code': doc.get('code', ''),
                                'timestamp': doc.get('audit_trail', {}).get('created_on', ''),
                                'filename': doc.get('filename', ''),
                                'status': doc.get('status', ''),
                                'source': 'json',
                                'sender': doc.get('sender', ''),
                                'recipient': doc.get('recipient', '')
                            })
            except Exception as e:
                app.logger.error(f"Error searching documents in JSON: {str(e)}")
        
        # Sort search results by timestamp
        search_results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # If no search is performed, get recent documents for the main page
    if not is_search:
        # Get recent documents from database
        db_documents = Document.query.order_by(Document.created_at.desc()).limit(5).all()
        for doc in db_documents:
            recent_documents.append({
                'code': doc.code,
                'timestamp': doc.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'filename': doc.title,
                'status': doc.status,
                'source': 'database'
            })
        
        # Get recent documents from JSON file if it exists
        try:
            if os.path.exists('document_tracking.json'):
                with open('document_tracking.json', 'r') as f:
                    tracking_data = json.load(f)
                    
                if 'documents' in tracking_data:
                    # Get documents from JSON, sort by created_on in audit_trail
                    json_docs = tracking_data['documents']
                    json_docs.sort(
                        key=lambda x: x.get('audit_trail', {}).get('created_on', ''), 
                        reverse=True
                    )
                    
                    # Add the 5 most recent JSON documents
                    for doc in json_docs[:5]:
                        recent_documents.append({
                            'code': doc.get('code', ''),
                            'timestamp': doc.get('audit_trail', {}).get('created_on', ''),
                            'filename': doc.get('filename', ''),
                            'status': doc.get('status', ''),
                            'source': 'json'
                        })
        except Exception as e:
            app.logger.error(f"Error loading recent documents from JSON: {str(e)}")
        
        # Sort all documents by timestamp and take the 10 most recent
        recent_documents.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        recent_documents = recent_documents[:10]
    
    # Check for QR code query parameter
    qr_code_value = request.args.get('code', '')
    if qr_code_value:
        # Auto-populate the form if QR code was scanned
        return render_template('track_document.html', 
                              recent_documents=recent_documents,
                              search_results=search_results,
                              is_search=is_search,
                              qr_code_value=qr_code_value,
                              search_params={
                                  'sender': sender,
                                  'recipient': recipient,
                                  'date_range': date_range,
                                  'status': status,
                                  'start_date': start_date,
                                  'end_date': end_date
                              })
    
    return render_template('track_document.html', 
                          recent_documents=recent_documents,
                          search_results=search_results,
                          is_search=is_search,
                          search_params={
                              'sender': sender,
                              'recipient': recipient,
                              'date_range': date_range,
                              'status': status,
                              'start_date': start_date,
                              'end_date': end_date
                          })

@app.route('/document_details/<document_code>')
def track_document_details(document_code):
    try:
        # Check if the document_tracking.json file exists
        if not os.path.exists('document_tracking.json'):
            flash('Document tracking system is not initialized', 'danger')
            return redirect(url_for('dashboard'))
        
        # Load the document tracking data
        with open('document_tracking.json', 'r') as f:
            documents = json.load(f)
        
        # Find the document with the given code
        document = None
        for doc in documents:
            if doc.get('code') == document_code:
                document = doc
                break
        
        if not document:
            flash('Document not found with the provided code', 'danger')
            return redirect(url_for('track_document'))
        
        # Extract actions and comments from the document data
        actions = document.get('actions', [])
        comments = document.get('comments', [])
        
        return render_template('document_details.html', 
                               document=document, 
                               actions=actions, 
                               comments=comments,
                               tracking_code=document_code)
    
    except Exception as e:
        app.logger.error(f"Error retrieving document details: {str(e)}")
        flash(f'Error retrieving document details: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/add_document_action/<document_code>', methods=['POST'])
def add_document_action(document_code):
    try:
        # Check if the document_tracking.json file exists
        if not os.path.exists('document_tracking.json'):
            flash('Document tracking system is not initialized', 'danger')
            return redirect(url_for('track_document_details', document_code=document_code))
        
        # Load the document tracking data
        with open('document_tracking.json', 'r') as f:
            documents = json.load(f)
        
        # Find the document with the given code
        document_index = None
        for i, doc in enumerate(documents):
            if doc.get('code') == document_code:
                document_index = i
                break
        
        if document_index is None:
            flash('Document not found with the provided code', 'danger')
            return redirect(url_for('track_document'))
        
        # Get the action data from the form
        action_type = request.form.get('action_type')
        notes = request.form.get('notes', '')
        new_status = request.form.get('new_status', '')
        
        # Create the action object
        action = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': 'Admin User',  # In a real app, get the current user
            'action': action_type,
            'notes': notes,
            'previous_status': documents[document_index].get('status', '')
        }
        
        # Update the document status if provided
        if new_status:
            documents[document_index]['status'] = new_status
            action['new_status'] = new_status
        else:
            action['new_status'] = documents[document_index].get('status', '')
        
        # Add the action to the document
        if 'actions' not in documents[document_index]:
            documents[document_index]['actions'] = []
        
        documents[document_index]['actions'].append(action)
        
        # Save the updated document tracking data
        with open('document_tracking.json', 'w') as f:
            json.dump(documents, f, indent=4)
        
        flash('Document action added successfully', 'success')
        return redirect(url_for('track_document_details', document_code=document_code))
    
    except Exception as e:
        app.logger.error(f"Error adding document action: {str(e)}")
        flash(f'Error adding document action: {str(e)}', 'danger')
        return redirect(url_for('track_document_details', document_code=document_code))

@app.route('/add_document_comment/<document_code>', methods=['POST'])
def add_document_comment(document_code):
    try:
        # Check if the document_tracking.json file exists
        if not os.path.exists('document_tracking.json'):
            flash('Document tracking system is not initialized', 'danger')
            return redirect(url_for('track_document_details', document_code=document_code))
        
        # Load the document tracking data
        with open('document_tracking.json', 'r') as f:
            documents = json.load(f)
        
        # Find the document with the given code
        document_index = None
        for i, doc in enumerate(documents):
            if doc.get('code') == document_code:
                document_index = i
                break
        
        if document_index is None:
            flash('Document not found with the provided code', 'danger')
            return redirect(url_for('track_document'))
        
        # Get the comment data from the form
        comment_text = request.form.get('comment', '')
        is_private = 'is_private' in request.form
        
        if not comment_text:
            flash('Comment text is required', 'warning')
            return redirect(url_for('track_document_details', document_code=document_code))
        
        # Create the comment object
        comment = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'username': 'Admin User',  # In a real app, get the current user
            'comment': comment_text,
            'is_private': is_private
        }
        
        # Add the comment to the document
        if 'comments' not in documents[document_index]:
            documents[document_index]['comments'] = []
        
        documents[document_index]['comments'].append(comment)
        
        # Save the updated document tracking data
        with open('document_tracking.json', 'w') as f:
            json.dump(documents, f, indent=4)
        
        flash('Comment added successfully', 'success')
        return redirect(url_for('track_document_details', document_code=document_code))
    
    except Exception as e:
        app.logger.error(f"Error adding comment: {str(e)}")
        flash(f'Error adding comment: {str(e)}', 'danger')
        return redirect(url_for('track_document_details', document_code=document_code))

@app.route('/incoming', methods=['GET'])
def incoming():
    # Get query parameters
    search_query = request.args.get('search', '')
    priority_filter = request.args.get('priority', 'All')
    status_filter = request.args.get('status', 'All')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of documents per page
    
    # Start with all documents that are incoming
    query = Document.query.filter(Document.status.in_(['Incoming', 'Pending', 'Received']))
    
    # Apply search filter if provided
    if search_query:
        search_terms = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Document.code.like(search_terms),
                Document.sender.like(search_terms),
                Document.recipient.like(search_terms),
                Document.details.like(search_terms),
                Document.required_action.like(search_terms)
            )
        )
    
    # Apply priority filter if not 'All'
    if priority_filter != 'All':
        query = query.filter(Document.priority == priority_filter)
        
    # Apply status filter if not 'All'
    if status_filter != 'All':
        query = query.filter(Document.status == status_filter)
    
    # Apply sorting
    if sort_by == 'code':
        if sort_order == 'asc':
            query = query.order_by(Document.code.asc())
        else:
            query = query.order_by(Document.code.desc())
    elif sort_by == 'date':
        if sort_order == 'asc':
            query = query.order_by(Document.date_received.asc())
        else:
            query = query.order_by(Document.date_received.desc())
    elif sort_by == 'priority':
        # Custom ordering for priority (Urgent > Priority > Normal)
        if sort_order == 'asc':
            # Normal (3) -> Priority (2) -> Urgent (1)
            query = query.order_by(
                case(
                    whens={
                        'Urgent': 1,
                        'Priority': 2,
                        'Normal': 3
                    },
                    value=Document.priority
                ).asc()
            )
        else:
            # Urgent (1) -> Priority (2) -> Normal (3)
            query = query.order_by(
                case(
                    whens={
                        'Urgent': 1,
                        'Priority': 2,
                        'Normal': 3
                    },
                    value=Document.priority
                ).desc()
            )
    
    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    documents = pagination.items
    
    # Count documents by priority for stats
    priority_counts = {
        'Urgent': Document.query.filter(
            Document.status.in_(['Incoming', 'Pending', 'Received']), 
            Document.priority == 'Urgent'
        ).count(),
        'Priority': Document.query.filter(
            Document.status.in_(['Incoming', 'Pending', 'Received']), 
            Document.priority == 'Priority'
        ).count(),
        'Normal': Document.query.filter(
            Document.status.in_(['Incoming', 'Pending', 'Received']), 
            Document.priority == 'Normal'
        ).count()
    }
    
    # Count documents by status
    status_counts = {
        'Incoming': Document.query.filter(Document.status == 'Incoming').count(),
        'Pending': Document.query.filter(Document.status == 'Pending').count(),
        'Received': Document.query.filter(Document.status == 'Received').count()
    }
    
    return render_template(
        'incoming.html', 
        documents=documents,
        pagination=pagination,
        search_query=search_query,
        priority_filter=priority_filter,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
        priority_counts=priority_counts,
        status_counts=status_counts
    )

@app.route('/incoming/update-status/<string:doc_code>', methods=['POST'])
def update_incoming_status(doc_code):
    """Update the status of an incoming document"""
    document = Document.query.filter_by(code=doc_code).first_or_404()
    
    new_status = request.form.get('status')
    if new_status in ['Incoming', 'Pending', 'Received', 'Outgoing', 'Ended']:
        document.status = new_status
        
        # Log the status change
        new_log = SystemLog(
            log_type='Info',
            user='Admin',
            action='Document Status Update',
            details=f'Document {doc_code} status changed to {new_status}'
        )
        db.session.add(new_log)
        db.session.commit()
        
        flash(f'Document {doc_code} has been updated to {new_status}', 'success')
    else:
        flash('Invalid status selected', 'danger')
    
    return redirect(url_for('incoming'))

@app.route('/incoming/bulk-action', methods=['POST'])
def incoming_bulk_action():
    """Perform bulk actions on selected incoming documents"""
    selected_docs = request.form.getlist('selected_docs')
    action = request.form.get('bulk_action')
    
    if not selected_docs:
        flash('No documents selected', 'warning')
        return redirect(url_for('incoming'))
    
    if action == 'mark_pending':
        for doc_code in selected_docs:
            document = Document.query.filter_by(code=doc_code).first()
            if document:
                document.status = 'Pending'
        
        db.session.commit()
        flash(f'{len(selected_docs)} documents marked as pending', 'success')
    
    elif action == 'mark_received':
        for doc_code in selected_docs:
            document = Document.query.filter_by(code=doc_code).first()
            if document:
                document.status = 'Received'
        
        db.session.commit()
        flash(f'{len(selected_docs)} documents marked as received', 'success')
    
    elif action == 'print':
        # We'll just redirect to a print view with the selected document IDs
        doc_codes = ','.join(selected_docs)
        return redirect(url_for('print_documents', doc_codes=doc_codes))
    
    return redirect(url_for('incoming'))

@app.route('/outgoing', methods=['GET'])
def outgoing():
    # Get query parameters
    search_query = request.args.get('search', '')
    priority_filter = request.args.get('priority', 'All')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of documents per page
    
    # Start with all documents that are outgoing
    query = Document.query.filter(Document.status.in_(['Outgoing', 'Sent']))
    
    # Apply search filter if provided
    if search_query:
        search_terms = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Document.code.like(search_terms),
                Document.sender.like(search_terms),
                Document.recipient.like(search_terms),
                Document.details.like(search_terms),
                Document.required_action.like(search_terms)
            )
        )
    
    # Apply priority filter if not 'All'
    if priority_filter != 'All':
        query = query.filter(Document.priority == priority_filter)
    
    # Apply sorting
    if sort_by == 'code':
        if sort_order == 'asc':
            query = query.order_by(Document.code.asc())
        else:
            query = query.order_by(Document.code.desc())
    elif sort_by == 'date':
        if sort_order == 'asc':
            query = query.order_by(Document.date_of_letter.asc())
        else:
            query = query.order_by(Document.date_of_letter.desc())
    elif sort_by == 'priority':
        # Custom ordering for priority (Urgent > Priority > Normal)
        # Convert the priority to a numeric value for sorting
        if sort_order == 'asc':
            # Normal (3) -> Priority (2) -> Urgent (1)
            query = query.order_by(
                case(
                    whens={
                        'Urgent': 1,
                        'Priority': 2,
                        'Normal': 3
                    },
                    value=Document.priority
                ).asc()
            )
        else:
            # Urgent (1) -> Priority (2) -> Normal (3)
            query = query.order_by(
                case(
                    whens={
                        'Urgent': 1,
                        'Priority': 2,
                        'Normal': 3
                    },
                    value=Document.priority
                ).desc()
            )
    
    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    documents = pagination.items
    
    # Count documents by priority for stats
    priority_counts = {
        'Urgent': Document.query.filter(
            Document.status.in_(['Outgoing', 'Sent']), 
            Document.priority == 'Urgent'
        ).count(),
        'Priority': Document.query.filter(
            Document.status.in_(['Outgoing', 'Sent']), 
            Document.priority == 'Priority'
        ).count(),
        'Normal': Document.query.filter(
            Document.status.in_(['Outgoing', 'Sent']), 
            Document.priority == 'Normal'
        ).count()
    }
    
    return render_template(
        'outgoing.html', 
        documents=documents,
        pagination=pagination,
        search_query=search_query,
        priority_filter=priority_filter,
        sort_by=sort_by,
        sort_order=sort_order,
        priority_counts=priority_counts
    )

@app.route('/outgoing/update-status/<string:doc_code>', methods=['POST'])
def update_outgoing_status(doc_code):
    """Update the status of an outgoing document"""
    document = Document.query.filter_by(code=doc_code).first_or_404()
    
    new_status = request.form.get('status')
    if new_status in ['Outgoing', 'Sent', 'Received', 'Ended']:
        document.status = new_status
        
        # Log the status change
        new_log = SystemLog(
            log_type='Info',
            user='Admin',
            action='Document Status Update',
            details=f'Document {doc_code} status changed to {new_status}'
        )
        db.session.add(new_log)
        db.session.commit()
        
        flash(f'Document {doc_code} has been updated to {new_status}', 'success')
    else:
        flash('Invalid status selected', 'danger')
    
    return redirect(url_for('outgoing'))

@app.route('/outgoing/bulk-action', methods=['POST'])
def outgoing_bulk_action():
    """Perform bulk actions on selected outgoing documents"""
    selected_docs = request.form.getlist('selected_docs')
    action = request.form.get('bulk_action')
    
    if not selected_docs:
        flash('No documents selected', 'warning')
        return redirect(url_for('outgoing'))
    
    if action == 'mark_sent':
        for doc_code in selected_docs:
            document = Document.query.filter_by(code=doc_code).first()
            if document:
                document.status = 'Sent'
        
        db.session.commit()
        flash(f'{len(selected_docs)} documents marked as sent', 'success')
    
    elif action == 'mark_received':
        for doc_code in selected_docs:
            document = Document.query.filter_by(code=doc_code).first()
            if document:
                document.status = 'Received'
        
        db.session.commit()
        flash(f'{len(selected_docs)} documents marked as received', 'success')
    
    elif action == 'print':
        # We'll just redirect to a print view with the selected document IDs
        doc_codes = ','.join(selected_docs)
        return redirect(url_for('print_documents', doc_codes=doc_codes))
    
    return redirect(url_for('outgoing'))

@app.route('/print-documents')
def print_documents():
    """View for printing multiple documents"""
    doc_codes = request.args.get('doc_codes', '').split(',')
    documents = Document.query.filter(Document.code.in_(doc_codes)).all()
    
    return render_template('print_documents.html', documents=documents)

@app.route('/document/<string:doc_code>')
def document_details(doc_code):
    """View detailed information about a document"""
    # Get the document
    document = Document.query.filter_by(code=doc_code).first_or_404()
    
    # Count all documents by status for the sidebar
    document_counts = {
        'Incoming': Document.query.filter_by(status='Incoming').count(),
        'Pending': Document.query.filter_by(status='Pending').count(),
        'Received': Document.query.filter_by(status='Received').count(),
        'Outgoing': Document.query.filter_by(status='Outgoing').count(),
        'Sent': Document.query.filter_by(status='Sent').count(),
        'Ended': Document.query.filter_by(status='Ended').count()
    }
    
    # Get relevant documents (same sender or recipient)
    related_documents = Document.query.filter(
        db.or_(
            Document.sender == document.sender,
            Document.recipient == document.recipient
        ),
        Document.code != document.code
    ).limit(5).all()
    
    return render_template(
        'document_details.html', 
        document=document, 
        document_counts=document_counts,
        related_documents=related_documents
    )

@app.route('/document/<string:doc_code>/update', methods=['POST'])
def update_document(doc_code):
    """Update a document's status and details"""
    document = Document.query.filter_by(code=doc_code).first_or_404()
    
    # Save the previous status for history
    previous_status = document.status
    
    # Update the document
    document.status = request.form.get('status', document.status)
    document.current_holder = request.form.get('holder', document.current_holder)
    document.updated_at = datetime.utcnow()
    
    # Create an action record
    action = DocumentAction(
        document_id=document.id,
        action=f'Status updated to {document.status}',
        user='Admin',  # In a real app, this would be the current user
        action_description=request.form.get('action_description', ''),
        status_before=previous_status,
        status_after=document.status
    )
    
    db.session.add(action)
    
    # Log the status change
    new_log = SystemLog(
        log_type='Info',
        user='Admin',
        action='Document Status Update',
        details=f'Document {doc_code} status changed from {previous_status} to {document.status}'
    )
    db.session.add(new_log)
    
    db.session.commit()
    
    flash(f'Document {doc_code} has been updated successfully', 'success')
    return redirect(url_for('track_document_details', document_code=doc_code))

@app.route('/document/<string:doc_code>/download')
def download_document(doc_code):
    """Mock document download functionality"""
    document = Document.query.filter_by(code=doc_code).first_or_404()
    
    # In a real app, you'd fetch the file from storage and serve it
    # For this mock, we'll just log the action and redirect
    
    # Create an action record
    action = DocumentAction(
        document_id=document.id,
        action='Document downloaded',
        user='Admin',  # In a real app, this would be the current user
        action_description='Document was downloaded'
    )
    
    db.session.add(action)
    db.session.commit()
    
    flash(f'Document {doc_code} would be downloaded in a real system', 'info')
    return redirect(url_for('track_document_details', document_code=doc_code))

@app.route('/reports')
def reports():
    """Reports page with document statistics and charts"""
    # Get date range from request, default to last 30 days
    date_range = request.args.get('date_range', 'last_30_days')
    
    # Get other filters
    doc_type = request.args.get('doc_type', 'all')
    status_filter = request.args.get('status_filter', 'all')
    priority_filter = request.args.get('priority_filter', 'all')
    
    # Create filters dict for template
    filters = {
        'date_range': date_range,
        'type': doc_type,
        'status': status_filter,
        'priority': priority_filter
    }
    
    # Calculate date range
    today = datetime.now()
    if date_range == 'last_7_days':
        start_date = today - timedelta(days=7)
    elif date_range == 'last_30_days':
        start_date = today - timedelta(days=30)
    elif date_range == 'last_90_days':
        start_date = today - timedelta(days=90)
    else:  # Custom or default to 30 days
        start_date = today - timedelta(days=30)
    
    # Base query
    base_query = Document.query.filter(Document.created_at >= start_date)
    
    # Apply filters
    if doc_type != 'all':
        # This is a simplified example. In a real app, you'd have a document_type field
        if doc_type == 'reports':
            base_query = base_query.filter(Document.title.like('%Report%'))
        elif doc_type == 'letters':
            base_query = base_query.filter(Document.title.like('%Letter%'))
        elif doc_type == 'memos':
            base_query = base_query.filter(Document.title.like('%Memo%'))
    
    if status_filter != 'all':
        base_query = base_query.filter(Document.status == status_filter.capitalize())
    
    if priority_filter != 'all':
        base_query = base_query.filter(Document.priority == priority_filter.capitalize())
    
    # Document counts by status
    status_counts = {
        'Incoming': base_query.filter(Document.status == 'Incoming').count(),
        'Pending': base_query.filter(Document.status == 'Pending').count(),
        'Received': base_query.filter(Document.status == 'Received').count(),
        'Outgoing': base_query.filter(Document.status == 'Outgoing').count(),
        'Sent': base_query.filter(Document.status == 'Sent').count(),
        'Ended': base_query.filter(Document.status == 'Ended').count()
    }
    
    # Document counts by priority
    priority_counts = {
        'Urgent': base_query.filter(Document.priority == 'Urgent').count(),
        'Priority': base_query.filter(Document.priority == 'Priority').count(),
        'Normal': base_query.filter(Document.priority == 'Normal').count()
    }
    
    # Create structured status data for template
    status_data = {
        'Incoming': {
            'total': status_counts['Incoming'],
            'normal': base_query.filter(Document.status == 'Incoming', Document.priority == 'Normal').count(),
            'priority': base_query.filter(Document.status == 'Incoming', Document.priority == 'Priority').count(),
            'urgent': base_query.filter(Document.status == 'Incoming', Document.priority == 'Urgent').count()
        },
        'Pending': {
            'total': status_counts['Pending'],
            'normal': base_query.filter(Document.status == 'Pending', Document.priority == 'Normal').count(),
            'priority': base_query.filter(Document.status == 'Pending', Document.priority == 'Priority').count(),
            'urgent': base_query.filter(Document.status == 'Pending', Document.priority == 'Urgent').count()
        },
        'Received': {
            'total': status_counts['Received'],
            'normal': base_query.filter(Document.status == 'Received', Document.priority == 'Normal').count(),
            'priority': base_query.filter(Document.status == 'Received', Document.priority == 'Priority').count(),
            'urgent': base_query.filter(Document.status == 'Received', Document.priority == 'Urgent').count()
        },
        'Outgoing': {
            'total': status_counts['Outgoing'],
            'normal': base_query.filter(Document.status == 'Outgoing', Document.priority == 'Normal').count(),
            'priority': base_query.filter(Document.status == 'Outgoing', Document.priority == 'Priority').count(),
            'urgent': base_query.filter(Document.status == 'Outgoing', Document.priority == 'Urgent').count()
        },
        'Ended': {
            'total': status_counts['Ended'],
            'normal': base_query.filter(Document.status == 'Ended', Document.priority == 'Normal').count(),
            'priority': base_query.filter(Document.status == 'Ended', Document.priority == 'Priority').count(),
            'urgent': base_query.filter(Document.status == 'Ended', Document.priority == 'Urgent').count()
        }
    }
    
    # Calculate average processing times
    # In a real app, you'd calculate this based on document actions
    avg_times = {
        'Incoming': '1.5 days',
        'Pending': '3.2 days',
        'Received': '2.8 days',
        'Outgoing': '1.7 days',
        'Ended': '4.5 days'
    }
    
    # Calculate total documents
    total_documents = sum(status_counts.values())
    
    # Prepare data for status chart
    status_chart_data = [
        {'name': status, 'count': count}
        for status, count in status_counts.items()
    ]
    
    # Prepare data for priority chart
    priority_chart_data = [
        {'name': priority, 'count': count}
        for priority, count in priority_counts.items()
    ]
    
    # Recent activities for activity chart
    recent_activities = SystemLog.query.filter(
        SystemLog.timestamp >= start_date
    ).order_by(SystemLog.timestamp.desc()).limit(20).all()
    
    return render_template(
        'reports.html',
        status_counts=status_counts,
        priority_counts=priority_counts,
        status_data=status_data,
        priority_data=priority_chart_data,
        status_chart_data=status_chart_data,
        recent_activities=recent_activities,
        date_range=date_range,
        doc_type=doc_type,
        status_filter=status_filter,
        priority_filter=priority_filter,
        filters=filters,
        avg_times=avg_times,
        total_documents=total_documents
    )

@app.route('/maintenance')
def maintenance():
    """Render the system maintenance page with system stats"""
    # Calculate stats
    total_documents = Document.query.count()
    
    # Calculate disk storage in MB (simulated)
    doc_size_mb = total_documents * 0.5  # Assume avg 500KB per document
    storage_used = f"{doc_size_mb:.2f} MB"
    
    # Get mock last backup time (one day ago)
    last_backup = datetime.now() - timedelta(days=1)
    
    # Get timestamp for admin activity modal
    now = datetime.now()
    timestamp_2hr_ago = now - timedelta(hours=2)
    timestamp_1day_ago = now - timedelta(days=1)
    timestamp_2day_ago = now - timedelta(days=2)
    
    # Mock system logs
    logs = [
        {
            'timestamp': now - timedelta(minutes=5),
            'log_type': 'Info',
            'user': 'System',
            'action': 'Server Started',
            'details': 'Application server successfully started'
        },
        {
            'timestamp': now - timedelta(minutes=10),
            'log_type': 'Success',
            'user': 'admin',
            'action': 'Login',
            'details': 'Successfully logged in'
        },
        {
            'timestamp': now - timedelta(hours=1),
            'log_type': 'Warning',
            'user': 'System',
            'action': 'Disk Space',
            'details': 'Archive drive space below 20%'
        },
        {
            'timestamp': now - timedelta(hours=3),
            'log_type': 'Success',
            'user': 'System',
            'action': 'Automatic Backup',
            'details': 'Daily backup completed successfully'
        },
        {
            'timestamp': now - timedelta(hours=5),
            'log_type': 'Error',
            'user': 'System',
            'action': 'Email Service',
            'details': 'Failed to send notification emails'
        }
    ]
    
    return render_template('maintenance.html', 
                          total_documents=total_documents,
                          storage_used=storage_used,
                          last_backup=last_backup.strftime('%Y-%m-%d %H:%M'),
                          now=now,
                          timestamp_2hr_ago=timestamp_2hr_ago.strftime('%Y-%m-%d %H:%M:%S'),
                          timestamp_1day_ago=timestamp_1day_ago.strftime('%Y-%m-%d %H:%M:%S'),
                          timestamp_2day_ago=timestamp_2day_ago.strftime('%Y-%m-%d %H:%M:%S'),
                          logs=logs)

@app.route('/maintenance_action', methods=['POST'])
def maintenance_action():
    """Handle maintenance action requests"""
    action = request.form.get('action')
    
    # Simulate actions with appropriate responses
    if action == 'backup':
        # Simulate database backup
        time.sleep(1)  # Simulate some processing time
        flash('Database backup completed successfully!', 'success')
    
    elif action == 'clean':
        # Simulate cleaning temporary files
        time.sleep(0.5)
        flash('Temporary files cleaned successfully. 150MB space recovered.', 'success')
    
    elif action == 'optimize':
        # Simulate database optimization
        time.sleep(1.5)
        flash('Database optimized successfully. Performance improved by 15%.', 'success')
    
    elif action == 'update':
        # Simulate checking for updates
        time.sleep(0.8)
        flash('System is up to date. No new updates available.', 'info')
    
    elif action == 'disk_cleanup':
        # Simulate disk cleanup
        time.sleep(1.2)
        flash('Disk cleanup completed. 500MB of space recovered.', 'success')
    
    elif action == 'reindex':
        # Simulate document reindexing
        time.sleep(2)
        flash('Document reindexing completed. Search performance improved.', 'success')
    
    else:
        flash(f'Unknown action: {action}', 'danger')
    
    return redirect(url_for('maintenance'))

@app.route('/toggle_scheduled_task', methods=['POST'])
def toggle_scheduled_task():
    """API endpoint to toggle scheduled tasks on/off"""
    data = request.json
    task_id = data.get('taskId')
    enabled = data.get('enabled')
    
    # In a real application, this would update a database record
    # For now, just return success
    
    return jsonify({
        'status': 'success',
        'message': f'Task {task_id} is now {"enabled" if enabled else "disabled"}',
        'taskId': task_id,
        'enabled': enabled
    })

@app.route('/update_indexing_settings', methods=['POST'])
def update_indexing_settings():
    """API endpoint to update indexing settings"""
    data = request.json
    
    # In a real application, this would save to a database or config file
    # For now, just log and return success
    
    return jsonify({
        'status': 'success',
        'message': 'Indexing settings updated successfully',
        'settings': data
    })

@app.route('/disk_info', methods=['GET'])
def disk_info():
    """API endpoint to get disk information"""
    # In a real application, this would query actual disk usage
    # For now, return simulated data
    
    return jsonify({
        'main_drive': {
            'total': 50,  # GB
            'used': 32.5,  # GB
            'free': 17.5,  # GB
            'percent_used': 65
        },
        'backup_drive': {
            'total': 100,  # GB
            'used': 40,  # GB
            'free': 60,  # GB
            'percent_used': 40
        },
        'archive_drive': {
            'total': 200,  # GB
            'used': 170,  # GB
            'free': 30,  # GB
            'percent_used': 85
        }
    })

@app.route('/update_profile', methods=['POST'])
def update_profile():
    """Update user profile information"""
    # In a real app, you'd update the user profile in the database
    # For now, just show a flash message
    flash('Profile updated successfully', 'success')
    return redirect(url_for('my_account'))

@app.route('/change_password', methods=['POST'])
def change_password():
    """Change user password"""
    # In a real app, you'd validate the current password and update to the new one
    # For now, just show a flash message
    flash('Password changed successfully', 'success')
    return redirect(url_for('my_account'))

@app.route('/toggle_2fa', methods=['POST'])
def toggle_2fa():
    """Toggle two-factor authentication"""
    # In a real app, you'd setup or disable 2FA
    # For now, just show a flash message
    enabled = request.form.get('twoFactorAuth') == 'on'
    status = 'enabled' if enabled else 'disabled'
    flash(f'Two-factor authentication {status}', 'success')
    return redirect(url_for('my_account'))

@app.route('/user_management')
def user_management():
    """User management page"""
    # Get all users
    users = User.query.all()
    
    # Get user activity
    user_activity = {}
    for user in users:
        activity_count = LoginActivity.query.filter_by(user_id=user.id).count()
        user_activity[user.id] = activity_count
    
    return render_template('user_management.html', users=users, user_activity=user_activity)

@app.route('/add_user', methods=['POST'])
def add_user():
    """Add a new user to the system with enhanced functionality"""
    # Get form data
    username = request.form.get('username')
    email = request.form.get('email')
    department = request.form.get('department')
    role = request.form.get('role')
    password = request.form.get('password')
    password_confirm = request.form.get('passwordConfirm')
    phone = request.form.get('phone', '')
    
    # Enhanced validation
    if not username or not email or not password:
        flash('All required fields must be filled', 'danger')
        return redirect(url_for('user_management'))
    
    if password != password_confirm:
        flash('Passwords do not match', 'danger')
        return redirect(url_for('user_management'))
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        flash(f'Username "{username}" already exists', 'danger')
        return redirect(url_for('user_management'))
    
    if User.query.filter_by(email=email).first():
        flash(f'Email "{email}" already exists', 'danger')
        return redirect(url_for('user_management'))
    
    # Create a new user with the provided information
    new_user = User(
        username=username,
        email=email,
        phone=phone,
        department=department,
        role=role,
        password=password,  # In a real app, this would be hashed
        created_at=datetime.utcnow(),
        last_login=None  # No login yet
    )
    
    db.session.add(new_user)
    
    # Log the action
    log = SystemLog(
        log_type='Info',
        user='Admin',
        action='User Created',
        details=f'New user {username} ({email}) was created with role {role} in department {department}'
    )
    db.session.add(log)
    db.session.commit()
    
    # Provide a confirmation message
    flash(f'User {username} has been created successfully', 'success')
    return redirect(url_for('user_management'))

@app.route('/edit_user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    """Edit an existing user"""
    user = User.query.get_or_404(user_id)
    
    # Update user information
    user.username = request.form.get('username', user.username)
    user.email = request.form.get('email', user.email)
    user.department = request.form.get('department', user.department)
    user.role = request.form.get('role', user.role)
    
    # Log the action
    log = SystemLog(
        log_type='Info',
        user='Admin',
        action='User Updated',
        details=f'User {user.username} (ID: {user_id}) was updated'
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'User {user.username} has been updated successfully', 'success')
    return redirect(url_for('user_management'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    username = user.username
    
    # Delete the user
    db.session.delete(user)
    
    # Log the action
    log = SystemLog(
        log_type='Warning',
        user='Admin',
        action='User Deleted',
        details=f'User {username} (ID: {user_id}) was deleted from the system'
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'User {username} has been deleted', 'success')
    return redirect(url_for('user_management'))

@app.route('/my_account')
def my_account():
    """User account management page"""
    # Mock user data
    user = {
        'username': 'John Doe',
        'email': 'john.doe@example.com',
        'phone': '+254 712 345 678',
        'department': 'IT Department',
        'last_login': datetime.now() - timedelta(days=1),
        'created_at': datetime.now() - timedelta(days=365)
    }
    
    # Mock login activity data
    login_activities = [
        {
            'login_date': datetime.now() - timedelta(hours=2),
            'ip_address': '192.168.1.1',
            'device': 'Chrome on Windows',
            'location': 'Nairobi, Kenya'
        },
        {
            'login_date': datetime.now() - timedelta(days=1),
            'ip_address': '192.168.1.2',
            'device': 'Safari on Mac',
            'location': 'Nairobi, Kenya'
        },
        {
            'login_date': datetime.now() - timedelta(days=3),
            'ip_address': '192.168.1.3',
            'device': 'Firefox on Linux',
            'location': 'Nairobi, Kenya'
        },
        {
            'login_date': datetime.now() - timedelta(days=7),
            'ip_address': '192.168.1.4',
            'device': 'Edge on Windows',
            'location': 'Nairobi, Kenya'
        }
    ]
    
    return render_template('my_account.html', user=user, login_activities=login_activities)

@app.route('/set_document_priority/<document_code>', methods=['POST'])
def set_document_priority(document_code):
    """Update a document's priority level"""
    try:
        # Check if document exists in database
        db_document = Document.query.filter_by(code=document_code).first()
        if db_document:
            # Update database document
            new_priority = request.form.get('priority')
            if new_priority in ['Normal', 'Priority', 'Urgent']:
                old_priority = db_document.priority
                db_document.priority = new_priority
                
                # Create action record
                action = DocumentAction(
                    document_id=db_document.id,
                    action='Priority Changed',
                    user='Admin User',  # In a real app, get the current user
                    action_description=f'Priority changed from {old_priority} to {new_priority}',
                    status_before=db_document.status,
                    status_after=db_document.status
                )
                db.session.add(action)
                db.session.commit()
                
                flash(f'Document priority updated to {new_priority}', 'success')
                return redirect(url_for('document_details', doc_code=document_code))
            else:
                flash('Invalid priority level', 'danger')
                return redirect(url_for('document_details', doc_code=document_code))
        
        # If not in DB, check in JSON tracking file
        if os.path.exists('document_tracking.json'):
            with open('document_tracking.json', 'r') as f:
                tracking_data = json.load(f)
            
            # Find document in tracking data
            document_index = None
            for i, doc in enumerate(tracking_data.get('documents', [])):
                if doc.get('code') == document_code:
                    document_index = i
                    break
            
            if document_index is not None:
                new_priority = request.form.get('priority')
                if new_priority in ['Normal', 'Priority', 'Urgent']:
                    old_priority = tracking_data['documents'][document_index].get('priority', 'Normal')
                    
                    # Create action record
                    action = {
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'user': 'Admin User',  # In a real app, get the current user
                        'action': 'Priority Changed',
                        'notes': f'Priority changed from {old_priority} to {new_priority}',
                        'previous_status': tracking_data['documents'][document_index].get('status', ''),
                        'new_status': tracking_data['documents'][document_index].get('status', '')
                    }
                    
                    # Update document
                    tracking_data['documents'][document_index]['priority'] = new_priority
                    
                    # Add to actions
                    if 'actions' not in tracking_data['documents'][document_index]:
                        tracking_data['documents'][document_index]['actions'] = []
                    
                    tracking_data['documents'][document_index]['actions'].append(action)
                    
                    # Update audit trail
                    tracking_data['documents'][document_index]['audit_trail']['last_modified_by'] = "1"
                    tracking_data['documents'][document_index]['audit_trail']['last_modified_on'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Save updated data
                    with open('document_tracking.json', 'w') as f:
                        json.dump(tracking_data, f, indent=4)
                    
                    flash(f'Document priority updated to {new_priority}', 'success')
                    return redirect(url_for('track_document_details', document_code=document_code))
                else:
                    flash('Invalid priority level', 'danger')
                    return redirect(url_for('track_document_details', document_code=document_code))
        
        flash('Document not found', 'danger')
        return redirect(url_for('track_document'))
        
    except Exception as e:
        app.logger.error(f"Error updating document priority: {str(e)}")
        flash(f'Error updating document priority: {str(e)}', 'danger')
        return redirect(url_for('track_document'))

@app.route('/reassign_document/<document_code>', methods=['POST'])
def reassign_document(document_code):
    """Reassign a document to another user/department"""
    try:
        new_holder = request.form.get('new_holder')
        if not new_holder:
            flash('New holder/department is required', 'warning')
            return redirect(url_for('track_document_details', document_code=document_code))
        
        # Check if document exists in database
        db_document = Document.query.filter_by(code=document_code).first()
        if db_document:
            # Update database document
            old_holder = db_document.current_holder
            db_document.current_holder = new_holder
            
            # Create action record
            action = DocumentAction(
                document_id=db_document.id,
                action='Document Reassigned',
                user='Admin User',  # In a real app, get the current user
                action_description=f'Document reassigned from {old_holder} to {new_holder}',
                status_before=db_document.status,
                status_after=db_document.status
            )
            db.session.add(action)
            db.session.commit()
            
            flash(f'Document reassigned to {new_holder}', 'success')
            return redirect(url_for('document_details', doc_code=document_code))
        
        # If not in DB, check in JSON tracking file
        if os.path.exists('document_tracking.json'):
            with open('document_tracking.json', 'r') as f:
                tracking_data = json.load(f)
            
            # Find document in tracking data
            document_index = None
            for i, doc in enumerate(tracking_data.get('documents', [])):
                if doc.get('code') == document_code:
                    document_index = i
                    break
            
            if document_index is not None:
                old_holder = tracking_data['documents'][document_index].get('current_holder', '')
                
                # Create action record
                action = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'user': 'Admin User',  # In a real app, get the current user
                    'action': 'Document Reassigned',
                    'notes': f'Document reassigned from {old_holder} to {new_holder}',
                    'previous_status': tracking_data['documents'][document_index].get('status', ''),
                    'new_status': tracking_data['documents'][document_index].get('status', '')
                }
                
                # Update document
                tracking_data['documents'][document_index]['current_holder'] = new_holder
                
                # Add to actions
                if 'actions' not in tracking_data['documents'][document_index]:
                    tracking_data['documents'][document_index]['actions'] = []
                
                tracking_data['documents'][document_index]['actions'].append(action)
                
                # Update audit trail
                tracking_data['documents'][document_index]['audit_trail']['last_modified_by'] = "1"
                tracking_data['documents'][document_index]['audit_trail']['last_modified_on'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Save updated data
                with open('document_tracking.json', 'w') as f:
                    json.dump(tracking_data, f, indent=4)
                
                flash(f'Document reassigned to {new_holder}', 'success')
                return redirect(url_for('track_document_details', document_code=document_code))
        
        flash('Document not found', 'danger')
        return redirect(url_for('track_document'))
        
    except Exception as e:
        app.logger.error(f"Error reassigning document: {str(e)}")
        flash(f'Error reassigning document: {str(e)}', 'danger')
        return redirect(url_for('track_document'))

@app.route('/attach_related_document/<document_code>', methods=['POST'])
def attach_related_document(document_code):
    """Attach a related document reference to the current document"""
    try:
        related_doc_code = request.form.get('related_doc_code')
        relationship = request.form.get('relationship', 'Related to')
        
        if not related_doc_code:
            flash('Related document code is required', 'warning')
            return redirect(url_for('track_document_details', document_code=document_code))
        
        # First check if related document exists in either DB or JSON
        related_exists = False
        related_doc_title = ""
        
        # Check in database
        db_related = Document.query.filter_by(code=related_doc_code).first()
        if db_related:
            related_exists = True
            related_doc_title = db_related.title
        
        # If not in DB, check in JSON
        if not related_exists and os.path.exists('document_tracking.json'):
            with open('document_tracking.json', 'r') as f:
                tracking_data = json.load(f)
            
            for doc in tracking_data.get('documents', []):
                if doc.get('code') == related_doc_code:
                    related_exists = True
                    related_doc_title = doc.get('filename', 'Unknown Document')
                    break
        
        if not related_exists:
            flash(f'Related document {related_doc_code} does not exist', 'danger')
            return redirect(url_for('track_document_details', document_code=document_code))
        
        # Now add the relationship
        # Check if document exists in database
        db_document = Document.query.filter_by(code=document_code).first()
        if db_document:
            # In a real app, you'd create a relationship in the database
            # For this demo, we'll just create an action record
            action = DocumentAction(
                document_id=db_document.id,
                action='Related Document Added',
                user='Admin User',  # In a real app, get the current user
                action_description=f'Document {related_doc_code} ({related_doc_title}) added as {relationship}',
                status_before=db_document.status,
                status_after=db_document.status
            )
            db.session.add(action)
            db.session.commit()
            
            flash(f'Related document {related_doc_code} added', 'success')
            return redirect(url_for('document_details', doc_code=document_code))
        
        # If not in DB, check in JSON tracking file
        if os.path.exists('document_tracking.json'):
            with open('document_tracking.json', 'r') as f:
                tracking_data = json.load(f)
            
            # Find document in tracking data
            document_index = None
            for i, doc in enumerate(tracking_data.get('documents', [])):
                if doc.get('code') == document_code:
                    document_index = i
                    break
            
            if document_index is not None:
                # Create action record
                action = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'user': 'Admin User',  # In a real app, get the current user
                    'action': 'Related Document Added',
                    'notes': f'Document {related_doc_code} ({related_doc_title}) added as {relationship}',
                    'previous_status': tracking_data['documents'][document_index].get('status', ''),
                    'new_status': tracking_data['documents'][document_index].get('status', '')
                }
                
                # Add related document to document data
                if 'related_documents' not in tracking_data['documents'][document_index]:
                    tracking_data['documents'][document_index]['related_documents'] = []
                
                tracking_data['documents'][document_index]['related_documents'].append({
                    'code': related_doc_code,
                    'title': related_doc_title,
                    'relationship': relationship,
                    'added_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                # Add to actions
                if 'actions' not in tracking_data['documents'][document_index]:
                    tracking_data['documents'][document_index]['actions'] = []
                
                tracking_data['documents'][document_index]['actions'].append(action)
                
                # Update audit trail
                tracking_data['documents'][document_index]['audit_trail']['last_modified_by'] = "1"
                tracking_data['documents'][document_index]['audit_trail']['last_modified_on'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Save updated data
                with open('document_tracking.json', 'w') as f:
                    json.dump(tracking_data, f, indent=4)
                
                flash(f'Related document {related_doc_code} added', 'success')
                return redirect(url_for('track_document_details', document_code=document_code))
        
        flash('Document not found', 'danger')
        return redirect(url_for('track_document'))
        
    except Exception as e:
        app.logger.error(f"Error attaching related document: {str(e)}")
        flash(f'Error attaching related document: {str(e)}', 'danger')
        return redirect(url_for('track_document'))

@app.route('/export_document_history/<document_code>')
def export_document_history(document_code):
    """Export document history as JSON or CSV"""
    format_type = request.args.get('format', 'json')
    
    try:
        document_data = None
        document_actions = []
        document_comments = []
        document_info = {}
        
        # Check if document exists in database
        db_document = Document.query.filter_by(code=document_code).first()
        if db_document:
            document_info = {
                'code': db_document.code,
                'title': db_document.title,
                'sender': db_document.sender,
                'recipient': db_document.recipient,
                'status': db_document.status,
                'priority': db_document.priority,
                'created_at': db_document.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Get actions
            actions = DocumentAction.query.filter_by(document_id=db_document.id).order_by(DocumentAction.timestamp).all()
            for action in actions:
                document_actions.append({
                    'timestamp': action.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'user': action.user,
                    'action': action.action,
                    'description': action.action_description,
                    'previous_status': action.status_before,
                    'new_status': action.status_after
                })
        
        # If not in DB or to enhance DB data, check in JSON tracking file
        if os.path.exists('document_tracking.json'):
            with open('document_tracking.json', 'r') as f:
                tracking_data = json.load(f)
            
            # Find document in tracking data
            for doc in tracking_data.get('documents', []):
                if doc.get('code') == document_code:
                    # If we didn't find in DB, set document info
                    if not document_info:
                        document_info = {
                            'code': doc.get('code', ''),
                            'title': doc.get('filename', ''),
                            'sender': doc.get('sender', ''),
                            'recipient': doc.get('recipient', ''),
                            'status': doc.get('status', ''),
                            'priority': doc.get('priority', ''),
                            'created_at': doc.get('audit_trail', {}).get('created_on', '')
                        }
                    
                    # Get actions from JSON
                    json_actions = doc.get('actions', [])
                    for action in json_actions:
                        # Only add if this action doesn't exist in our list (avoid duplicates)
                        existing_timestamps = [a.get('timestamp') for a in document_actions]
                        if action.get('timestamp') not in existing_timestamps:
                            document_actions.append({
                                'timestamp': action.get('timestamp', ''),
                                'user': action.get('user', ''),
                                'action': action.get('action', ''),
                                'description': action.get('notes', ''),
                                'previous_status': action.get('previous_status', ''),
                                'new_status': action.get('new_status', '')
                            })
                    
                    # Get comments
                    document_comments = doc.get('comments', [])
                    break
        
        if not document_info:
            flash('Document not found', 'danger')
            return redirect(url_for('track_document'))
        
        # Prepare export data
        export_data = {
            'document': document_info,
            'actions': document_actions,
            'comments': document_comments,
            'export_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Return based on format requested
        if format_type == 'json':
            return jsonify(export_data)
        elif format_type == 'csv':
            # Create CSV string
            csv_data = "Document Tracking History Export\n"
            csv_data += f"Document Code,{document_info.get('code')}\n"
            csv_data += f"Title,{document_info.get('title')}\n"
            csv_data += f"Sender,{document_info.get('sender')}\n"
            csv_data += f"Recipient,{document_info.get('recipient')}\n"
            csv_data += f"Status,{document_info.get('status')}\n"
            csv_data += f"Priority,{document_info.get('priority')}\n"
            csv_data += f"Created,{document_info.get('created_at')}\n\n"
            
            # Add actions
            csv_data += "Action History\n"
            csv_data += "Timestamp,User,Action,Description,Previous Status,New Status\n"
            for action in document_actions:
                csv_data += f"{action.get('timestamp')},{action.get('user')},{action.get('action')},\"{action.get('description')}\",{action.get('previous_status')},{action.get('new_status')}\n"
            
            # Add comments
            if document_comments:
                csv_data += "\nComments\n"
                csv_data += "Timestamp,User,Comment,Private\n"
                for comment in document_comments:
                    is_private = "Yes" if comment.get('is_private') else "No"
                    csv_data += f"{comment.get('timestamp')},{comment.get('username')},\"{comment.get('comment')}\",{is_private}\n"
            
            response = app.response_class(
                response=csv_data,
                status=200,
                mimetype='text/csv',
                headers={"Content-Disposition": f"attachment;filename=document_{document_code}_history.csv"}
            )
            return response
        else:
            flash('Invalid export format', 'danger')
            return redirect(url_for('track_document'))
            
    except Exception as e:
        app.logger.error(f"Error exporting document history: {str(e)}")
        flash(f'Error exporting document history: {str(e)}', 'danger')
        return redirect(url_for('track_document'))

@app.route('/document/update-status', methods=['POST'])
def update_document_status():
    """Update a document's status from the dashboard or other forms"""
    document_code = request.form.get('document_code')
    new_status = request.form.get('status')
    notes = request.form.get('notes', '')
    
    if not document_code or not new_status:
        flash('Missing required information', 'danger')
        return redirect(url_for('dashboard'))
    
    # Find the document in the database
    document = Document.query.filter_by(code=document_code).first()
    
    if document:
        old_status = document.status
        document.status = new_status
        document.updated_at = datetime.utcnow()
        
        # Create an action record
        action = DocumentAction(
            document_id=document.id,
            action=f'Status updated to {new_status}',
            user='Admin',  # In a real app, this would be the current user
            action_description=notes,
            status_before=old_status,
            status_after=new_status
        )
        
        db.session.add(action)
        db.session.commit()
        
        flash(f'Document {document_code} status updated to {new_status}', 'success')
        return redirect(url_for('dashboard'))
    
    # If not in database, check JSON file
    elif os.path.exists('document_tracking.json'):
        try:
            with open('document_tracking.json', 'r') as f:
                tracking_data = json.load(f)
            
            # Find document in tracking data
            document_index = None
            for i, doc in enumerate(tracking_data.get('documents', [])):
                if doc.get('code') == document_code:
                    document_index = i
                    break
            
            if document_index is not None:
                old_status = tracking_data['documents'][document_index].get('status', '')
                
                # Create action record
                action = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'user': 'Admin User',  # In a real app, get the current user
                    'action': 'Status Changed',
                    'notes': notes,
                    'previous_status': old_status,
                    'new_status': new_status
                }
                
                # Update document
                tracking_data['documents'][document_index]['status'] = new_status
                
                # Add to actions
                if 'actions' not in tracking_data['documents'][document_index]:
                    tracking_data['documents'][document_index]['actions'] = []
                
                tracking_data['documents'][document_index]['actions'].append(action)
                
                # Update audit trail
                tracking_data['documents'][document_index]['audit_trail']['last_modified_by'] = "1"
                tracking_data['documents'][document_index]['audit_trail']['last_modified_on'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Save updated data
                with open('document_tracking.json', 'w') as f:
                    json.dump(tracking_data, f, indent=4)
                
                flash(f'Document {document_code} status updated to {new_status}', 'success')
                return redirect(url_for('dashboard'))
        except Exception as e:
            app.logger.error(f"Error updating document status: {str(e)}")
    
    flash(f'Document {document_code} not found', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/reset_password/<int:user_id>', methods=['POST'])
def reset_password(user_id):
    """Reset a user's password to a default value"""
    user = User.query.get_or_404(user_id)
    
    # Set default password
    default_password = "Password123"
    user.password = default_password
    
    # Log the action
    log = SystemLog(
        log_type='Warning',
        user='Admin',
        action='Password Reset',
        details=f'Password was reset for user {user.username} (ID: {user_id})'
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Password for {user.username} has been reset to "{default_password}"', 'success')
    return redirect(url_for('user_management'))

@app.route('/toggle_user_status/<int:user_id>', methods=['POST'])
def toggle_user_status(user_id):
    """Toggle a user's active status"""
    user = User.query.get_or_404(user_id)
    
    # Toggle status by updating role
    current_status = 'Active' if user.role else 'Inactive'
    
    if user.role:  # If has a role (active)
        previous_role = user.role
        user.role = None  # Set to inactive
        new_status = 'Inactive'
    else:  # If inactive
        user.role = 'User'  # Reactivate as basic user
        previous_role = None
        new_status = 'Active'
    
    # Log the action
    log = SystemLog(
        log_type='Info',
        user='Admin',
        action='Status Change',
        details=f'User {user.username} (ID: {user_id}) status changed from {current_status} to {new_status}'
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Status for {user.username} has been changed to {new_status}', 'success')
    return redirect(url_for('user_management'))

if __name__ == '__main__':
    app.run(debug=True) 