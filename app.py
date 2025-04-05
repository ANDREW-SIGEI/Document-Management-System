from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from config import Config
from datetime import datetime, timedelta
import json
import random
from sqlalchemy import case
from sqlalchemy.sql import expression

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
    return render_template('dashboard_new.html', users=users)

@app.route('/compose')
def compose():
    return render_template('compose.html')

@app.route('/incoming')
def incoming():
    return render_template('incoming.html')

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

@app.route('/maintenance')
def maintenance():
    # Get real system statistics
    total_documents = Document.query.count()
    
    # Calculate storage used (simulated)
    avg_doc_size_kb = 250  # Assume average document is 250KB
    storage_used_kb = total_documents * avg_doc_size_kb
    
    if storage_used_kb < 1024:
        storage_used = f"{storage_used_kb} KB"
    elif storage_used_kb < 1024 * 1024:
        storage_used = f"{storage_used_kb / 1024:.1f} MB"
    else:
        storage_used = f"{storage_used_kb / (1024 * 1024):.2f} GB"
    
    # Get last backup time (simulated)
    last_backup = None
    system_logs = db.session.query(SystemLog).order_by(SystemLog.timestamp.desc()).filter(
        SystemLog.action == 'Backup Completed'
    ).first()
    
    if system_logs:
        last_backup = system_logs.timestamp.strftime('%Y-%m-%d %H:%M')
    
    # Get system logs
    logs = db.session.query(SystemLog).order_by(SystemLog.timestamp.desc()).limit(10).all()
    
    # Calculate timestamps for admin activity logs
    now = datetime.utcnow()
    timestamp_2hr_ago = (now - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
    timestamp_1day_ago = (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    timestamp_2day_ago = (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('maintenance.html', 
                          total_documents=total_documents,
                          storage_used=storage_used,
                          last_backup=last_backup,
                          logs=logs,
                          now=now,
                          timestamp_2hr_ago=timestamp_2hr_ago,
                          timestamp_1day_ago=timestamp_1day_ago,
                          timestamp_2day_ago=timestamp_2day_ago)

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
    users = User.query.all()
    return render_template('user_management.html', users=users)

@app.route('/add-user', methods=['POST'])
def add_user():
    username = request.form.get('username')
    email = request.form.get('email')
    department = request.form.get('department')
    role = request.form.get('role')
    password = request.form.get('password')
    
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
    
    user.username = request.form.get('username')
    user.email = request.form.get('email')
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

@app.route('/my-account')
def my_account():
    # Get the current user (in a real app, this would be the logged-in user)
    user = User.query.first()
    login_activities = LoginActivity.query.filter_by(user_id=user.id).order_by(LoginActivity.login_date.desc()).limit(3).all()
    return render_template('my_account.html', user=user, login_activities=login_activities)

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
    
    return redirect(url_for('maintenance'))

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

if __name__ == '__main__':
    app.run(debug=True) 