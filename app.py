from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from config import Config
from datetime import datetime, timedelta
import json
import random
from sqlalchemy import case
from sqlalchemy.sql import expression
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = 'kemri_secret_key'  # Required for flash messages
db = SQLAlchemy(app)

# Configure file uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Make current datetime available to templates
@app.context_processor
def inject_now():
    return {'now': lambda: datetime.utcnow()}

# Add route/endpoint helper for templates to avoid BuildError
@app.context_processor
def utility_processor():
    def has_endpoint(endpoint):
        try:
            url_for(endpoint)
            return True
        except:
            return False
    return dict(has_endpoint=has_endpoint)

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

# Document Attachment Model
class DocumentAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # pdf, doc, jpg, etc.
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    document = db.relationship('Document', backref=db.backref('attachments', lazy=True, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<DocumentAttachment {self.original_filename}>'

# Document Comment Model
class DocumentComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    document = db.relationship('Document', backref=db.backref('comments', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    
    def __repr__(self):
        return f'<DocumentComment {self.id}>'

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
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    users = User.query.all()
    
    # Count documents by status for stats
    status_counts = {
        'Incoming': Document.query.filter_by(status='Incoming').count(),
        'Pending': Document.query.filter_by(status='Pending').count(),
        'Received': Document.query.filter_by(status='Received').count(),
        'Outgoing': Document.query.filter_by(status='Outgoing').count(),
        'Ended': Document.query.filter_by(status='Ended').count()
    }
    
    # Get recent activity
    recent_logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(10).all()
    
    # Get urgent documents
    urgent_docs = Document.query.filter_by(priority='Urgent').order_by(Document.created_at.desc()).limit(5).all()
    
    # Get total counts
    total_documents = Document.query.count()
    total_users = User.query.count()
    
    return render_template(
        'dashboard_new.html', 
        users=users,
        status_counts=status_counts,
        recent_logs=recent_logs,
        urgent_docs=urgent_docs,
        total_documents=total_documents,
        total_users=total_users
    )

@app.route('/compose', methods=['GET', 'POST'])
def compose():
    if request.method == 'POST':
        # Get form data
        doc_type = request.form.get('doc_type', 'Incoming')
        title = request.form.get('title')
        sender = request.form.get('sender')
        recipient = request.form.get('recipient')
        details = request.form.get('details')
        required_action = request.form.get('required_action')
        date_of_letter = request.form.get('date_of_letter')
        priority = request.form.get('priority', 'Normal')
        
        # Basic validation
        if not title or not sender or not recipient:
            flash('Please fill in all required fields', 'danger')
            return render_template('compose.html', form_data=request.form)
        
        # Generate document code
        current_year = datetime.utcnow().year
        last_doc = Document.query.filter(Document.code.like(f'DOC-{current_year}-%')).order_by(Document.code.desc()).first()
        
        if last_doc:
            # Extract the sequence number from the last document code
            try:
                last_seq = int(last_doc.code.split('-')[-1])
                new_seq = last_seq + 1
            except ValueError:
                new_seq = 1
        else:
            new_seq = 1
            
        # Create document code with format DOC-YYYY-NNN
        doc_code = f'DOC-{current_year}-{new_seq:03d}'
        
        # Create new document
        new_document = Document(
            code=doc_code,
            title=title,
            sender=sender,
            recipient=recipient,
            details=details,
            required_action=required_action,
            date_of_letter=datetime.strptime(date_of_letter, '%Y-%m-%d') if date_of_letter else datetime.utcnow(),
            date_received=datetime.utcnow(),
            priority=priority,
            status='Incoming' if doc_type == 'Incoming' else 'Outgoing',
            current_holder='Admin'  # In a real app, this would be the current user
        )
        
        db.session.add(new_document)
        db.session.commit()  # Commit to generate the document ID
        
        # Handle file upload if provided
        if 'document_file' in request.files:
            document_file = request.files['document_file']
            
            if document_file and document_file.filename:
                original_filename = document_file.filename
                # Secure filename to prevent security issues
                filename = secure_filename(original_filename)
                # Add document code to filename to ensure uniqueness
                file_parts = os.path.splitext(filename)
                unique_filename = f"{file_parts[0]}_{doc_code}{file_parts[1]}"
                
                # Save the file to the upload folder
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                document_file.save(file_path)
                
                # Get file size and type
                file_size = os.path.getsize(file_path)
                file_type = os.path.splitext(filename)[1][1:].lower()  # Remove the dot from extension
                
                # Create document attachment record
                attachment = DocumentAttachment(
                    document_id=new_document.id,
                    filename=unique_filename,
                    original_filename=original_filename,
                    file_type=file_type,
                    file_size=file_size
                )
                db.session.add(attachment)
        
        # Log the document creation
        new_log = SystemLog(
            log_type='Success',
            user='Admin',  # In a real app, this would be the current user
            action='Document Created',
            details=f'New {doc_type} document created with code {doc_code}'
        )
        db.session.add(new_log)
        db.session.commit()
        
        flash(f'Document {doc_code} has been created successfully', 'success')
        
        # Redirect to the appropriate page based on document type
        if doc_type == 'Incoming':
            return redirect(url_for('incoming'))
        else:
            return redirect(url_for('outgoing'))
    
    # For GET request, render the compose form
    doc_type = request.args.get('type', 'Incoming')
    return render_template('compose.html', doc_type=doc_type)

@app.route('/incoming')
def incoming():
    # Get query parameters
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', 'All')
    priority_filter = request.args.get('priority', 'All')
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
    
    # Apply status filter if not 'All'
    if status_filter != 'All':
        query = query.filter(Document.status == status_filter)
    
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
            query = query.order_by(Document.date_received.asc())
        else:
            query = query.order_by(Document.date_received.desc())
    elif sort_by == 'priority':
        # Custom ordering for priority (Urgent > Priority > Normal)
        if sort_order == 'asc':
            # Normal (3) -> Priority (2) -> Urgent (1)
            priority_case = case([
                (Document.priority == 'Urgent', 1),
                (Document.priority == 'Priority', 2),
                (Document.priority == 'Normal', 3)
            ], else_=4)
            query = query.order_by(priority_case.asc())
        else:
            # Urgent (1) -> Priority (2) -> Normal (3)
            priority_case = case([
                (Document.priority == 'Urgent', 1),
                (Document.priority == 'Priority', 2),
                (Document.priority == 'Normal', 3)
            ], else_=4)
            query = query.order_by(priority_case.desc())
    
    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    documents = pagination.items
    
    # Count documents by status for stats
    status_counts = {
        'Incoming': Document.query.filter_by(status='Incoming').count(),
        'Pending': Document.query.filter_by(status='Pending').count(),
        'Received': Document.query.filter_by(status='Received').count()
    }
    
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
    
    return render_template(
        'incoming.html', 
        documents=documents,
        pagination=pagination,
        search_query=search_query,
        status_filter=status_filter,
        priority_filter=priority_filter,
        sort_by=sort_by,
        sort_order=sort_order,
        status_counts=status_counts,
        priority_counts=priority_counts
    )

@app.route('/track_document')
def track_document():
    # Get the document code from the query parameters
    doc_code = request.args.get('code')
    document = None
    history = []
    
    if doc_code:
        # Try to find the document
        document = Document.query.filter_by(code=doc_code).first()
        
        if document:
            # Simulate document history
            # In a real app, this would come from a document_history table
            current_time = datetime.utcnow()
            history = [
                {
                    'timestamp': document.created_at,
                    'action': 'Document Created',
                    'user': 'Admin',
                    'details': f'Document {doc_code} was created'
                }
            ]
            
            # Add history entries based on document status
            if document.status != 'Incoming':
                history.append({
                    'timestamp': document.updated_at,
                    'action': f'Status Changed to {document.status}',
                    'user': 'Admin',
                    'details': f'Document status updated to {document.status}'
                })
            
            if document.status == 'Received':
                history.append({
                    'timestamp': document.updated_at - timedelta(hours=1),
                    'action': 'Document Received',
                    'user': document.current_holder or 'System',
                    'details': f'Document was received by {document.current_holder}'
                })
                
            # Sort history by timestamp (newest first)
            history.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template(
        'track_document.html',
        document=document,
        history=history,
        search_performed=(doc_code is not None)
    )

@app.route('/logout')
def logout():
    # In a real app, this would log the user out
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

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
            priority_case = case([
                (Document.priority == 'Urgent', 1),
                (Document.priority == 'Priority', 2),
                (Document.priority == 'Normal', 3)
            ], else_=4)
            query = query.order_by(priority_case.asc())
        else:
            # Urgent (1) -> Priority (2) -> Normal (3)
            priority_case = case([
                (Document.priority == 'Urgent', 1),
                (Document.priority == 'Priority', 2),
                (Document.priority == 'Normal', 3)
            ], else_=4)
            query = query.order_by(priority_case.desc())
    
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
    
    elif action == 'export':
        # Handle export action
        flash(f'{len(selected_docs)} documents exported', 'success')
    
    return redirect(url_for('incoming'))

@app.route('/print-documents')
def print_documents():
    """View for printing multiple documents"""
    doc_codes = request.args.get('doc_codes', '').split(',')
    documents = Document.query.filter(Document.code.in_(doc_codes)).all()
    
    # Pass the show_history parameter to control whether document history is included
    show_history = request.args.get('show_history', 'false').lower() == 'true'
    
    return render_template('print_documents.html', documents=documents, show_history=show_history)

@app.route('/document/<string:doc_code>')
def document_details(doc_code):
    """View a single document's details"""
    document = Document.query.filter_by(code=doc_code).first_or_404()
    
    # Get document history (in a real app, this would be from a history table)
    # Here we'll simulate some history entries
    current_time = datetime.utcnow()
    history = [
        {
            'timestamp': current_time - timedelta(days=random.randint(0, 5), hours=random.randint(0, 12)),
            'action': 'Document Created',
            'user': 'Admin',
            'details': f'Document {doc_code} was created'
        },
        {
            'timestamp': current_time - timedelta(days=random.randint(0, 3), hours=random.randint(0, 8)),
            'action': 'Status Changed',
            'user': 'Admin',
            'details': f'Document status changed to {document.status}'
        }
    ]
    
    # Sort history by timestamp (newest first)
    history.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template(
        'document_details.html',
        document=document,
        history=history
    )

@app.route('/maintenance')
def maintenance():
    # Get real system statistics
    total_documents = Document.query.count()
    
    # Calculate storage used (in a real app, this would be the actual size)
    document_attachments = DocumentAttachment.query.all()
    storage_used = sum(attachment.file_size for attachment in document_attachments) / (1024 * 1024)  # Convert to MB
    storage_used = f"{storage_used:.2f} MB"
    
    # Get last backup time
    last_backup = "Never"
    system_logs = db.session.query(SystemLog).filter(
        SystemLog.action == 'Backup Completed'
    ).first()
    
    if system_logs:
        last_backup = system_logs.timestamp.strftime('%Y-%m-%d %H:%M')
    
    # Get system logs
    logs = db.session.query(SystemLog).order_by(SystemLog.timestamp.desc()).limit(10).all()
    
    # Calculate timestamps for admin activity logs
    current_time = datetime.utcnow()
    timestamp_2hr_ago = (current_time - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
    timestamp_1day_ago = (current_time - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    timestamp_2day_ago = (current_time - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
    
    # Create maintenance stats data
    maintenance_stats = {
        'system_uptime': '3 days, 7 hours, 22 minutes',
        'cpu_usage': '32%',
        'memory_usage': '45%',
        'disk_usage': '27%',
        'db_size': '156 MB',
        'active_users': User.query.count(),
        'pending_tasks': Document.query.filter(Document.status == 'Pending').count()
    }
    
    # Create performance data
    performance_data = {
        'response_time': '120ms',
        'queries_per_second': '12.5',
        'slow_queries': '0',
        'cache_hit_ratio': '94%'
    }
    
    return render_template('maintenance.html', 
                          total_documents=total_documents,
                          storage_used=storage_used,
                          last_backup=last_backup,
                          logs=logs,
                          current_time=current_time,
                          timestamp_2hr_ago=timestamp_2hr_ago,
                          timestamp_1day_ago=timestamp_1day_ago,
                          timestamp_2day_ago=timestamp_2day_ago,
                          maintenance_stats=maintenance_stats,
                          performance_data=performance_data)

@app.route('/reports')
def reports():
    # Get filter parameters from query string
    date_range = request.args.get('date_range', 'last-7-days')
    doc_type = request.args.get('type', 'all')
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    
    # Base query
    query = Document.query
    
    # Apply filters
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)
    
    # Get document counts by status
    incoming_count = Document.query.filter_by(status='Incoming').count()
    pending_count = Document.query.filter_by(status='Pending').count()
    received_count = Document.query.filter_by(status='Received').count()
    outgoing_count = Document.query.filter_by(status='Outgoing').count()
    ended_count = Document.query.filter_by(status='Ended').count()
    total_documents = Document.query.count()
    
    # Get document counts by priority and status
    status_data = {}
    for status in ['Incoming', 'Pending', 'Received', 'Outgoing', 'Ended']:
        normal_count = Document.query.filter_by(status=status, priority='Normal').count()
        priority_count = Document.query.filter_by(status=status, priority='Priority').count()
        urgent_count = Document.query.filter_by(status=status, priority='Urgent').count()
        
        status_data[status] = {
            'normal': normal_count,
            'priority': priority_count,
            'urgent': urgent_count,
            'total': normal_count + priority_count + urgent_count,
        }
    
    # Calculate average processing times (simplified)
    # In a real app, you'd calculate this from actual document histories
    avg_times = {
        'Incoming': '2 days',
        'Pending': '5 days',
        'Received': '1 day',
        'Outgoing': 'N/A',
        'Ended': 'N/A'
    }
    
    # Prepare chart data
    status_chart_data = [
        {'name': 'Incoming', 'value': incoming_count, 'color': '#2196F3'},
        {'name': 'Pending', 'value': pending_count, 'color': '#FFC107'},
        {'name': 'Received', 'value': received_count, 'color': '#4CAF50'},
        {'name': 'Outgoing', 'value': outgoing_count, 'color': '#9C27B0'},
        {'name': 'Ended', 'value': ended_count, 'color': '#F44336'}
    ]
    
    priority_chart_data = [
        {'name': 'Normal', 'value': Document.query.filter_by(priority='Normal').count(), 'color': '#4CAF50'},
        {'name': 'Priority', 'value': Document.query.filter_by(priority='Priority').count(), 'color': '#FFC107'},
        {'name': 'Urgent', 'value': Document.query.filter_by(priority='Urgent').count(), 'color': '#F44336'}
    ]
    
    return render_template('reports.html', 
                          incoming_count=incoming_count,
                          pending_count=pending_count,
                          received_count=received_count,
                          outgoing_count=outgoing_count,
                          ended_count=ended_count,
                          total_documents=total_documents,
                          status_data=status_data,
                          avg_times=avg_times,
                          status_chart_data=json.dumps(status_chart_data),
                          priority_chart_data=json.dumps(priority_chart_data),
                          filters={
                              'date_range': date_range,
                              'type': doc_type,
                              'status': status_filter,
                              'priority': priority_filter
                          })

@app.route('/api/report-data')
def report_data():
    report_type = request.args.get('type', 'document-summary')
    date_range = request.args.get('date_range', 'last-7-days')
    
    if date_range == 'last-7-days':
        start_date = datetime.utcnow() - timedelta(days=7)
    elif date_range == 'last-30-days':
        start_date = datetime.utcnow() - timedelta(days=30)
    elif date_range == 'last-90-days':
        start_date = datetime.utcnow() - timedelta(days=90)
    else:
        start_date = datetime.utcnow() - timedelta(days=30)  # Default
    
    if report_type == 'document-summary':
        # Get documents created after start_date
        documents = Document.query.filter(Document.created_at >= start_date).all()
        data = {
            'total': len(documents),
            'by_status': {
                'Incoming': len([d for d in documents if d.status == 'Incoming']),
                'Pending': len([d for d in documents if d.status == 'Pending']),
                'Received': len([d for d in documents if d.status == 'Received']),
                'Outgoing': len([d for d in documents if d.status == 'Outgoing']),
                'Ended': len([d for d in documents if d.status == 'Ended'])
            },
            'by_priority': {
                'Normal': len([d for d in documents if d.priority == 'Normal']),
                'Priority': len([d for d in documents if d.priority == 'Priority']),
                'Urgent': len([d for d in documents if d.priority == 'Urgent'])
            }
        }
        return jsonify(data)
    
    elif report_type == 'activity-analysis':
        # Group documents by day
        documents = Document.query.filter(Document.created_at >= start_date).all()
        
        # Prepare date labels (last n days)
        date_labels = []
        date_data = []
        
        days = (datetime.utcnow() - start_date).days
        for i in range(days, 0, -1):
            day = datetime.utcnow() - timedelta(days=i)
            date_str = day.strftime('%Y-%m-%d')
            date_labels.append(day.strftime('%b %d'))
            
            # Count documents for this day
            count = len([d for d in documents if d.created_at.strftime('%Y-%m-%d') == date_str])
            date_data.append(count)
        
        return jsonify({
            'labels': date_labels,
            'data': date_data
        })
    
    return jsonify({'error': 'Invalid report type'})

@app.route('/user-management')
def user_management():
    # Define available departments and roles for dropdowns
    departments = ['Administration', 'Laboratory', 'Research', 'IT', 'Finance', 'HR', 'Audit']
    roles = ['Administrator', 'Manager', 'Lab Technician', 'Researcher', 'Data Entry', 'User', 'Read Only']
    
    users = User.query.all()
    return render_template('user_management.html', users=users, departments=departments, roles=roles)

@app.route('/database-management')
def database_management():
    """Provides an interface for database management operations"""
    # Get basic database statistics
    total_documents = Document.query.count()
    total_users = User.query.count()
    total_system_logs = SystemLog.query.count()
    total_attachments = DocumentAttachment.query.count()
    
    # Get database size (simulated for demo)
    db_size = "15.7 MB"
    health_percentage = 95
    
    # Get recent database activity
    recent_logs = SystemLog.query.filter(
        SystemLog.action.in_(['Database Optimized', 'Backup Completed', 'Cleanup Completed', 'Database Integrity Check'])
    ).order_by(SystemLog.timestamp.desc()).limit(8).all()
    
    # Get sample backups
    backups = [
        {
            'filename': 'backup_2025-04-23.db',
            'date': '2025-04-23 08:30 AM',
            'size': '14.2 MB'
        },
        {
            'filename': 'backup_2025-04-21.db',
            'date': '2025-04-21 09:15 AM',
            'size': '14.0 MB'
        },
        {
            'filename': 'backup_2025-04-19.db',
            'date': '2025-04-19 07:45 AM',
            'size': '13.8 MB'
        }
    ]
    
    # Get database tables
    tables = [
        {
            'name': 'user',
            'records': total_users,
            'size': '0.2 MB',
            'last_updated': datetime.utcnow().strftime('%Y-%m-%d'),
            'status': 'Good'
        },
        {
            'name': 'document',
            'records': total_documents,
            'size': '2.1 MB',
            'last_updated': datetime.utcnow().strftime('%Y-%m-%d'),
            'status': 'Good'
        },
        {
            'name': 'system_log',
            'records': total_system_logs,
            'size': '1.5 MB',
            'last_updated': datetime.utcnow().strftime('%Y-%m-%d'),
            'status': 'Good'
        },
        {
            'name': 'document_attachment',
            'records': total_attachments,
            'size': '11.9 MB',
            'last_updated': datetime.utcnow().strftime('%Y-%m-%d'),
            'status': 'Good'
        }
    ]
    
    # Performance metrics
    performance = {
        'response_time': '120',
        'queries_per_second': '12.5',
        'slow_queries': '0',
        'cache_hit_ratio': '94'
    }
    
    return render_template('database_management.html', 
                          stats={
                              'total_documents': total_documents,
                              'total_users': total_users,
                              'total_logs': total_system_logs,
                              'total_attachments': total_attachments,
                              'db_size': db_size,
                              'health_percentage': health_percentage
                          },
                          recent_logs=recent_logs,
                          backups=backups,
                          tables=tables,
                          performance=performance)

@app.route('/add-user', methods=['POST'])
def add_user():
    # Get form fields matching the names in the HTML form
    username = request.form.get('fullName')
    email = request.form.get('email')
    phone = request.form.get('phone', '')
    department = request.form.get('department')
    role = request.form.get('role')
    password = request.form.get('password')
    status = 'active' if request.form.get('status') == 'on' else 'inactive'
    
    # Basic validation
    if not username or not email or not password:
        flash('All fields are required!', 'danger')
        return redirect(url_for('user_management'))
    
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        flash('Email already exists!', 'danger')
        return redirect(url_for('user_management'))
    
    # Create new user
    new_user = User(
        username=username,
        email=email,
        phone=phone,
        department=department,
        password=password,  # In a real app, this would be hashed
        role=role
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    flash('User added successfully!', 'success')
    return redirect(url_for('user_management'))

@app.route('/edit-user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    user.username = request.form.get('fullName')
    user.email = request.form.get('email')
    user.phone = request.form.get('phone', '')
    user.department = request.form.get('department')
    user.role = request.form.get('role')
    
    db.session.commit()
    
    flash('User updated successfully!', 'success')
    return redirect(url_for('user_management'))

@app.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Don't allow deleting the last admin
    if user.role == 'Administrator' and User.query.filter_by(role='Administrator').count() <= 1:
        flash('Cannot delete the only administrator!', 'danger')
        return redirect(url_for('user_management'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('user_management'))

@app.route('/my_account')
def my_account():
    # Get the current user (in a real app, this would be the logged-in user)
    user = User.query.first()
    login_activities = LoginActivity.query.filter_by(user_id=user.id).order_by(LoginActivity.login_date.desc()).limit(3).all()
    return render_template('my_account.html', user=user, login_activities=login_activities)

@app.route('/my-account')
def my_account_alt():
    return redirect(url_for('my_account'))

@app.route('/update-profile', methods=['POST'])
def update_profile():
    if request.method == 'POST':
        user = User.query.first()  # In a real app, this would be the logged-in user
        
        # Update user information
        user.username = request.form.get('fullName')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.department = request.form.get('department')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        
    return redirect(url_for('my_account'))

@app.route('/change-password', methods=['POST'])
def change_password():
    if request.method == 'POST':
        user = User.query.first()  # In a real app, this would be the logged-in user
        current_password = request.form.get('currentPassword')
        new_password = request.form.get('newPassword')
        confirm_password = request.form.get('confirmPassword')
        
        # In a real app, you would verify the current password hash
        if current_password != user.password:
            flash('Current password is incorrect', 'danger')
        elif new_password != confirm_password:
            flash('New passwords do not match', 'danger')
        elif not new_password:
            flash('Password cannot be empty', 'danger')
        else:
            # In a real app, you would hash the new password
            user.password = new_password
            db.session.commit()
            flash('Password changed successfully!', 'success')
        
    return redirect(url_for('my_account'))

@app.route('/toggle-2fa', methods=['POST'])
def toggle_2fa():
    # In a real app, this would enable/disable 2FA for the user
    flash('Two-factor authentication settings updated!', 'success')
    return redirect(url_for('my_account'))

@app.route('/maintenance/action', methods=['POST'])
def maintenance_action():
    action = request.form.get('action')
    
    if action == 'backup':
        # Simulate backup
        new_log = SystemLog(
            log_type='Success',
            user='Admin',
            action='Backup Completed',
            details='System backup completed successfully'
        )
        db.session.add(new_log)
        db.session.commit()
        flash('Database backup completed successfully!', 'success')
    
    elif action == 'clean':
        # Simulate cleaning temp files
        new_log = SystemLog(
            log_type='Success',
            user='Admin',
            action='Cleanup Completed',
            details='Temporary files cleaned successfully'
        )
        db.session.add(new_log)
        db.session.commit()
        flash('Temporary files cleaned successfully!', 'success')
    
    elif action == 'optimize':
        # Simulate database optimization
        new_log = SystemLog(
            log_type='Success',
            user='Admin',
            action='Database Optimized',
            details='Database optimization completed'
        )
        db.session.add(new_log)
        db.session.commit()
        flash('Database optimization completed!', 'success')
    
    elif action == 'integrity_check':
        # Simulate database integrity check
        new_log = SystemLog(
            log_type='Success',
            user='Admin',
            action='Database Integrity Check',
            details='Database integrity check completed successfully. All tables are intact.'
        )
        db.session.add(new_log)
        db.session.commit()
        flash('Database integrity check completed. No issues found!', 'success')
    
    elif action == 'vacuum':
        # Simulate database vacuum
        new_log = SystemLog(
            log_type='Success',
            user='Admin',
            action='Database Vacuum',
            details='Database vacuum operation completed successfully. Database size reduced.'
        )
        db.session.add(new_log)
        db.session.commit()
        flash('Database vacuum completed successfully!', 'success')
    
    elif action == 'optimize_table':
        # Get table name from form
        table_name = request.form.get('table_name')
        # Simulate table optimization
        new_log = SystemLog(
            log_type='Success',
            user='Admin',
            action='Table Optimized',
            details=f'Table "{table_name}" optimized successfully.'
        )
        db.session.add(new_log)
        db.session.commit()
        flash(f'Table "{table_name}" optimized successfully!', 'success')
    
    elif action == 'truncate_table':
        # Get table name from form
        table_name = request.form.get('table_name')
        # Simulate table truncation
        new_log = SystemLog(
            log_type='Warning',
            user='Admin',
            action='Table Truncated',
            details=f'Table "{table_name}" truncated, all records removed.'
        )
        db.session.add(new_log)
        db.session.commit()
        flash(f'Table "{table_name}" truncated successfully. All records removed.', 'warning')
    
    elif action == 'restore_backup':
        # Get backup name from form
        backup_name = request.form.get('backup_name')
        # Simulate backup restoration
        new_log = SystemLog(
            log_type='Success',
            user='Admin',
            action='Backup Restored',
            details=f'Database restored from backup "{backup_name}" successfully.'
        )
        db.session.add(new_log)
        db.session.commit()
        flash(f'Database restored from backup "{backup_name}" successfully!', 'success')
    
    elif action == 'download_backup':
        # Get backup name from form
        backup_name = request.form.get('backup_name')
        # In a real app, you would generate a download response
        # For this demo, just provide a success message
        flash(f'Backup "{backup_name}" download started.', 'success')
        # Redirect to database management to avoid the POST-redirect issue
        return redirect(url_for('database_management'))
    
    elif action == 'delete_backup':
        # Get backup name from form
        backup_name = request.form.get('backup_name')
        # Simulate backup deletion
        new_log = SystemLog(
            log_type='Warning',
            user='Admin',
            action='Backup Deleted',
            details=f'Backup "{backup_name}" deleted from the system.'
        )
        db.session.add(new_log)
        db.session.commit()
        flash(f'Backup "{backup_name}" deleted successfully.', 'warning')
    
    elif action == 'update':
        # Simulate checking for updates
        new_log = SystemLog(
            log_type='Info',
            user='System',
            action='Update Check',
            details='No updates available at this time'
        )
        db.session.add(new_log)
        db.session.commit()
        flash('System is up to date!', 'info')
    
    elif action == 'disk_cleanup':
        # Simulate disk cleanup
        new_log = SystemLog(
            log_type='Success',
            user='Admin',
            action='Disk Cleanup',
            details='Disk cleanup operation completed successfully. 1.2 GB space freed.'
        )
        db.session.add(new_log)
        db.session.commit()
        flash('Disk cleanup completed successfully! 1.2 GB of space has been freed.', 'success')
    
    elif action == 'reindex':
        # Simulate document reindexing
        new_log = SystemLog(
            log_type='Success',
            user='Admin',
            action='Document Reindex',
            details=f'Successfully reindexed {Document.query.count()} documents'
        )
        db.session.add(new_log)
        db.session.commit()
        flash(f'Successfully reindexed {Document.query.count()} documents!', 'success')
    
    return redirect(url_for('database_management'))

@app.route('/maintenance/disk-info')
def disk_info():
    """API endpoint to get disk space information"""
    # In a real app, this would get actual disk information
    disk_data = {
        'main_drive': {
            'total': 50,  # GB
            'used': 31.5,  # GB
            'free': 18.5,  # GB
            'percent_used': 63
        },
        'backup_drive': {
            'total': 100,  # GB
            'used': 40,   # GB
            'free': 60,   # GB
            'percent_used': 40
        },
        'archive_drive': {
            'total': 200,  # GB
            'used': 170,  # GB
            'free': 30,   # GB
            'percent_used': 85
        }
    }
    return jsonify(disk_data)

@app.route('/maintenance/scheduled-tasks', methods=['POST'])
def toggle_scheduled_task():
    """API endpoint to toggle scheduled tasks"""
    task_id = request.json.get('taskId')
    enabled = request.json.get('enabled')
    
    # In a real app, this would update task configuration
    
    # Log the action
    new_log = SystemLog(
        log_type='Info',
        user='Admin',
        action='Task Configuration',
        details=f'Task {task_id} {"enabled" if enabled else "disabled"}'
    )
    db.session.add(new_log)
    db.session.commit()
    
    return jsonify({'success': True, 'taskId': task_id, 'enabled': enabled})

@app.route('/maintenance/indexing-settings', methods=['POST'])
def update_indexing_settings():
    """API endpoint to update indexing settings"""
    settings = request.json
    
    # In a real app, this would update indexing configuration
    
    # Log the action
    new_log = SystemLog(
        log_type='Info',
        user='Admin',
        action='Indexing Configuration',
        details=f'Indexing configuration updated: {settings}'
    )
    db.session.add(new_log)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/update_incoming_status/<string:doc_code>', methods=['POST'])
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

@app.route('/add_comment/<string:doc_code>', methods=['POST'])
def add_comment(doc_code):
    """Add a comment to a document"""
    document = Document.query.filter_by(code=doc_code).first_or_404()
    
    comment_text = request.form.get('comment')
    if not comment_text:
        flash('Comment cannot be empty', 'warning')
        return redirect(url_for('document_details', doc_code=doc_code))
    
    # In a real app, get the current user ID from session
    user = User.query.first()  # Just get the first user for now
    
    # Create the comment
    new_comment = DocumentComment(
        document_id=document.id,
        user_id=user.id,
        comment=comment_text
    )
    
    # Log the activity
    new_log = SystemLog(
        log_type='Info',
        user=user.username,
        action='Comment Added',
        details=f'Comment added to document {doc_code}'
    )
    
    db.session.add(new_comment)
    db.session.add(new_log)
    db.session.commit()
    
    flash('Comment added successfully', 'success')
    return redirect(url_for('document_details', doc_code=doc_code))

@app.route('/add_attachment/<string:doc_code>', methods=['POST'])
def add_attachment(doc_code):
    """Add an attachment to a document"""
    document = Document.query.filter_by(code=doc_code).first_or_404()
    
    if 'attachment_file' not in request.files:
        flash('No file selected', 'warning')
        return redirect(url_for('document_details', doc_code=doc_code))
    
    attachment_file = request.files['attachment_file']
    
    if attachment_file.filename == '':
        flash('No file selected', 'warning')
        return redirect(url_for('document_details', doc_code=doc_code))
    
    if attachment_file:
        # Process the file similar to the compose endpoint
        original_filename = attachment_file.filename
        # Secure filename to prevent security issues
        filename = secure_filename(original_filename)
        # Add document code to filename to ensure uniqueness
        file_parts = os.path.splitext(filename)
        unique_filename = f"{file_parts[0]}_{doc_code}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{file_parts[1]}"
        
        # Save the file to the upload folder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        attachment_file.save(file_path)
        
        # Get file size and type
        file_size = os.path.getsize(file_path)
        file_type = os.path.splitext(filename)[1][1:].lower()  # Remove the dot from extension
        
        # Create document attachment record
        attachment = DocumentAttachment(
            document_id=document.id,
            filename=unique_filename,
            original_filename=original_filename,
            file_type=file_type,
            file_size=file_size
        )
        
        # Log the activity
        user = User.query.first()  # Just get the first user for now
        new_log = SystemLog(
            log_type='Info',
            user=user.username,
            action='Attachment Added',
            details=f'File "{original_filename}" added to document {doc_code}'
        )
        
        db.session.add(attachment)
        db.session.add(new_log)
        db.session.commit()
        
        flash('Attachment added successfully', 'success')
    
    return redirect(url_for('document_details', doc_code=doc_code))

@app.route('/download_attachment/<int:attachment_id>')
def download_attachment(attachment_id):
    """Download a document attachment"""
    attachment = DocumentAttachment.query.get_or_404(attachment_id)
    
    # The file is already in the static/uploads folder
    # Redirect to the static URL for the file
    return redirect(url_for('static', filename=f'uploads/{attachment.filename}'))

@app.route('/api/table-structure/<table_name>')
def get_table_structure(table_name):
    """API endpoint to get the structure of a database table"""
    # In a real app, this would query the database information schema
    # For this demo, we'll provide mock data based on the table name
    
    if table_name == 'user':
        columns = [
            {'name': 'id', 'type': 'INTEGER', 'nullable': 'NO', 'default': None, 'key': 'PK'},
            {'name': 'username', 'type': 'VARCHAR(80)', 'nullable': 'NO', 'default': None, 'key': 'UNI'},
            {'name': 'email', 'type': 'VARCHAR(120)', 'nullable': 'NO', 'default': None, 'key': 'UNI'},
            {'name': 'phone', 'type': 'VARCHAR(20)', 'nullable': 'YES', 'default': None, 'key': ''},
            {'name': 'department', 'type': 'VARCHAR(50)', 'nullable': 'YES', 'default': None, 'key': ''},
            {'name': 'password', 'type': 'VARCHAR(100)', 'nullable': 'YES', 'default': None, 'key': ''},
            {'name': 'last_login', 'type': 'DATETIME', 'nullable': 'YES', 'default': 'CURRENT_TIMESTAMP', 'key': ''},
            {'name': 'created_at', 'type': 'DATETIME', 'nullable': 'YES', 'default': 'CURRENT_TIMESTAMP', 'key': ''},
            {'name': 'role', 'type': 'VARCHAR(50)', 'nullable': 'YES', 'default': None, 'key': ''}
        ]
    elif table_name == 'document':
        columns = [
            {'name': 'id', 'type': 'INTEGER', 'nullable': 'NO', 'default': None, 'key': 'PK'},
            {'name': 'code', 'type': 'VARCHAR(20)', 'nullable': 'NO', 'default': None, 'key': 'UNI'},
            {'name': 'title', 'type': 'VARCHAR(200)', 'nullable': 'NO', 'default': None, 'key': ''},
            {'name': 'sender', 'type': 'VARCHAR(100)', 'nullable': 'NO', 'default': None, 'key': ''},
            {'name': 'recipient', 'type': 'VARCHAR(100)', 'nullable': 'NO', 'default': None, 'key': ''},
            {'name': 'details', 'type': 'TEXT', 'nullable': 'YES', 'default': None, 'key': ''},
            {'name': 'required_action', 'type': 'VARCHAR(200)', 'nullable': 'YES', 'default': None, 'key': ''},
            {'name': 'date_of_letter', 'type': 'DATETIME', 'nullable': 'YES', 'default': 'CURRENT_TIMESTAMP', 'key': ''},
            {'name': 'date_received', 'type': 'DATETIME', 'nullable': 'YES', 'default': 'CURRENT_TIMESTAMP', 'key': ''},
            {'name': 'priority', 'type': 'VARCHAR(20)', 'nullable': 'YES', 'default': "'Normal'", 'key': ''},
            {'name': 'status', 'type': 'VARCHAR(20)', 'nullable': 'YES', 'default': "'Incoming'", 'key': ''},
            {'name': 'current_holder', 'type': 'VARCHAR(100)', 'nullable': 'YES', 'default': None, 'key': ''},
            {'name': 'created_at', 'type': 'DATETIME', 'nullable': 'YES', 'default': 'CURRENT_TIMESTAMP', 'key': ''},
            {'name': 'updated_at', 'type': 'DATETIME', 'nullable': 'YES', 'default': 'CURRENT_TIMESTAMP', 'key': ''},
            {'name': 'processed_by', 'type': 'INTEGER', 'nullable': 'YES', 'default': None, 'key': 'FK'}
        ]
    elif table_name == 'system_log':
        columns = [
            {'name': 'id', 'type': 'INTEGER', 'nullable': 'NO', 'default': None, 'key': 'PK'},
            {'name': 'timestamp', 'type': 'DATETIME', 'nullable': 'YES', 'default': 'CURRENT_TIMESTAMP', 'key': ''},
            {'name': 'log_type', 'type': 'VARCHAR(20)', 'nullable': 'YES', 'default': None, 'key': ''},
            {'name': 'user', 'type': 'VARCHAR(100)', 'nullable': 'YES', 'default': None, 'key': ''},
            {'name': 'action', 'type': 'VARCHAR(100)', 'nullable': 'YES', 'default': None, 'key': ''},
            {'name': 'details', 'type': 'TEXT', 'nullable': 'YES', 'default': None, 'key': ''}
        ]
    elif table_name == 'document_attachment':
        columns = [
            {'name': 'id', 'type': 'INTEGER', 'nullable': 'NO', 'default': None, 'key': 'PK'},
            {'name': 'document_id', 'type': 'INTEGER', 'nullable': 'NO', 'default': None, 'key': 'FK'},
            {'name': 'filename', 'type': 'VARCHAR(255)', 'nullable': 'NO', 'default': None, 'key': ''},
            {'name': 'original_filename', 'type': 'VARCHAR(255)', 'nullable': 'NO', 'default': None, 'key': ''},
            {'name': 'file_type', 'type': 'VARCHAR(50)', 'nullable': 'NO', 'default': None, 'key': ''},
            {'name': 'file_size', 'type': 'INTEGER', 'nullable': 'NO', 'default': None, 'key': ''},
            {'name': 'uploaded_at', 'type': 'DATETIME', 'nullable': 'YES', 'default': 'CURRENT_TIMESTAMP', 'key': ''}
        ]
    else:
        # Default empty table for unknown tables
        columns = []
    
    return jsonify({
        'table_name': table_name,
        'columns': columns
    })

if __name__ == '__main__':
    app.run(debug=True) 