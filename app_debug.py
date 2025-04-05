from flask import Flask, render_template, request, redirect, url_for, flash
import os
import uuid
from datetime import datetime, timedelta
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mimetypes
import socket

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TRACKING_FILE'] = 'document_tracking.json'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Create uploads folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize tracking data if file doesn't exist
if not os.path.exists(app.config['TRACKING_FILE']):
    with open(app.config['TRACKING_FILE'], 'w') as f:
        json.dump({
            "users": [],
            "documents": [],
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
        }, f, indent=4)

def generate_unique_code():
    """Generate a unique document code with timestamp."""
    timestamp = datetime.now().strftime('%Y%m%d')
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"DOC-{timestamp}-{unique_id}"

def get_tracking_data():
    """Get all document tracking data."""
    try:
        with open(app.config['TRACKING_FILE'], 'r') as f:
            return json.load(f)
    except:
        return {"users": [], "documents": [], "system_settings": {}}

def save_tracking_data(data):
    """Save document tracking data."""
    with open(app.config['TRACKING_FILE'], 'w') as f:
        json.dump(data, f, indent=4)

def get_user_by_id(user_id):
    """Get user by ID."""
    tracking_data = get_tracking_data()
    for user in tracking_data.get("users", []):
        if user.get("id") == user_id:
            return user
    return None

def get_user_by_email(email):
    """Get user by email."""
    tracking_data = get_tracking_data()
    for user in tracking_data.get("users", []):
        if user.get("email") == email:
            return user
    return None

def get_file_type(filename):
    """Get file type from filename."""
    _, ext = os.path.splitext(filename)
    return ext.upper().replace('.', '')

def get_file_size(file_path):
    """Get file size in bytes."""
    return os.path.getsize(file_path)

def get_client_ip():
    """Get client IP address."""
    return request.remote_addr or "127.0.0.1"

def get_client_device():
    """Get client device information."""
    user_agent = request.user_agent.string
    if "mobile" in user_agent.lower():
        device_type = "Mobile"
    else:
        device_type = "Desktop"
    
    # Basic browser detection
    if "chrome" in user_agent.lower():
        browser = "Chrome"
    elif "firefox" in user_agent.lower():
        browser = "Firefox"
    elif "safari" in user_agent.lower():
        browser = "Safari"
    elif "edge" in user_agent.lower():
        browser = "Edge"
    else:
        browser = "Other"
    
    return f"{device_type} - {browser}"

def calculate_deadline(priority, days=7):
    """Calculate deadline based on priority."""
    today = datetime.now()
    if priority == "Urgent":
        # Urgent documents get 2 days
        days = 2
    elif priority == "Priority":
        # Priority documents get 5 days
        days = 5
    
    deadline = today + timedelta(days=days)
    return deadline.strftime('%Y-%m-%d')

def send_email_notification(recipient_email, subject, message):
    """Send email notification."""
    try:
        tracking_data = get_tracking_data()
        email_settings = tracking_data.get("system_settings", {}).get("notification_settings", {})
        
        if not email_settings.get("email_enabled", False):
            return False
        
        sender_email = email_settings.get("sender_email", "noreply@docmanagementsystem.com")
        smtp_server = email_settings.get("smtp_server", "smtp.example.com")
        smtp_port = email_settings.get("smtp_port", 587)
        
        # For demonstration only - not actually sending emails
        print(f"[NOTIFICATION] To: {recipient_email}, Subject: {subject}, Message: {message}")
        
        # Uncomment to send actual emails
        """
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'html'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, "your-password")
            server.send_message(msg)
        """
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def add_notification_record(document, recipient_id, notification_type="email"):
    """Add notification record to document."""
    if "notification_status" not in document:
        document["notification_status"] = {
            "recipients_notified": [],
            "reminders_sent": []
        }
    
    notification_record = {
        "user_id": recipient_id,
        "notification_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "notification_type": notification_type,
        "notification_status": "sent"
    }
    
    document["notification_status"]["recipients_notified"].append(notification_record)
    return document

def add_action_record(document, user_id, action, notes="", previous_status=None, new_status=None):
    """Add action record to document."""
    if "actions" not in document:
        document["actions"] = []
    
    # Get the username
    user = get_user_by_id(user_id)
    username = user.get("name", "System") if user else "System"
    
    action_record = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "user": username,
        "user_id": user_id,
        "action": action,
        "notes": notes,
        "previous_status": previous_status,
        "new_status": new_status or document.get("status"),
        "ip_address": get_client_ip(),
        "device": get_client_device()
    }
    
    document["actions"].append(action_record)
    return document

def get_next_workflow_stage(current_stage, document_priority):
    """Get next workflow stage based on priority."""
    tracking_data = get_tracking_data()
    workflow_templates = tracking_data.get("system_settings", {}).get("workflow_templates", [])
    
    # Choose workflow based on priority
    workflow_template = None
    if document_priority == "Urgent":
        for template in workflow_templates:
            if template.get("name") == "Urgent Process":
                workflow_template = template
                break
    
    # Default to standard workflow if no urgent workflow or not urgent
    if workflow_template is None:
        for template in workflow_templates:
            if template.get("name") == "Standard Review":
                workflow_template = template
                break
    
    # If still no workflow, return empty
    if workflow_template is None:
        return ""
    
    steps = workflow_template.get("steps", [])
    
    # Find current stage in steps
    try:
        current_index = steps.index(current_stage)
        # Get next stage if exists
        if current_index + 1 < len(steps):
            return steps[current_index + 1]
    except (ValueError, IndexError):
        # If current stage not found, return first stage
        if steps:
            return steps[0]
    
    return ""

@app.route('/')
def home():
    try:
        return render_template('index.html', active_page='home')
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/dashboard')
def dashboard():
    try:
        tracking_data = get_tracking_data()
        documents = tracking_data.get("documents", [])
        
        # Calculate counts for each status
        incoming_count = len([doc for doc in documents if doc.get("status") == "Incoming"])
        pending_count = len([doc for doc in documents if doc.get("status") == "Pending"])
        received_count = len([doc for doc in documents if doc.get("status") == "Received"])
        ended_count = len([doc for doc in documents if doc.get("status") == "Ended"])
        
        # Sort documents by date (newest first)
        documents.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        # Get recent documents (last 10)
        recent_documents = documents[:10]
        
        return render_template('dashboard.html', 
                              documents=recent_documents,
                              incoming_count=incoming_count,
                              pending_count=pending_count,
                              received_count=received_count,
                              ended_count=ended_count,
                              active_page='dashboard')
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/compose', methods=['GET', 'POST'])
def compose():
    try:
        # Get user info - in a real app, get this from session
        current_user_id = "1"  # Default to the first user for demo
        current_user = get_user_by_id(current_user_id) or {"id": "1", "name": "System", "email": "", "department": ""}
        
        if request.method == 'POST':
            # Process uploaded file
            if 'document' not in request.files:
                flash('No file selected', 'danger')
                return redirect(request.url)
            
            file = request.files['document']
            if file.filename == '':
                flash('No file selected', 'danger')
                return redirect(request.url)
            
            # Generate unique document code
            doc_code = generate_unique_code()
            
            # Get form data
            sender = request.form.get('sender', current_user.get("name", "Unknown"))
            sender_email = request.form.get('sender_email', current_user.get("email", ""))
            sender_department = request.form.get('sender_department', current_user.get("department", ""))
            recipient = request.form.get('recipient', '')
            recipient_email = request.form.get('recipient_email', '')
            recipient_department = request.form.get('recipient_department', '')
            details = request.form.get('details', '')
            required_action = request.form.get('required_action', '')
            priority = request.form.get('priority', 'Normal')
            is_confidential = request.form.get('is_confidential', 'off') == 'on'
            tags = request.form.get('tags', '').split(',')
            tags = [tag.strip() for tag in tags if tag.strip()]
            workflow_template = request.form.get('workflow_template', 'Standard Review')
            
            # Get recipient user if exists
            recipient_user = get_user_by_email(recipient_email)
            recipient_id = recipient_user.get("id") if recipient_user else None
            
            # Save the file with the unique code as part of the filename
            filename = f"{doc_code}_{file.filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Calculate deadline based on priority
            deadline = calculate_deadline(priority)
            
            # Get file metadata
            document_type = get_file_type(file.filename)
            file_size = get_file_size(file_path)
            
            # Get workflow stages from the selected template
            tracking_data = get_tracking_data()
            workflow_stages = []
            for template in tracking_data.get("system_settings", {}).get("workflow_templates", []):
                if template.get("name") == workflow_template:
                    workflow_stages = template.get("steps", [])
                    break
            
            initial_stage = workflow_stages[0] if workflow_stages else "Initial Review"
            
            # Create approval flow based on workflow stages
            approval_flow = []
            for i, stage in enumerate(workflow_stages, 1):
                approval_flow.append({
                    "step": i,
                    "role": stage,
                    "user_id": recipient_id if i == 1 else None,
                    "status": "pending" if i == 1 else "not_started",
                    "notes": ""
                })
            
            # Create document tracking record
            document_data = {
                "code": doc_code,
                "filename": file.filename,
                "stored_filename": filename,
                "sender": sender,
                "sender_email": sender_email,
                "sender_department": sender_department,
                "recipient": recipient,
                "recipient_email": recipient_email,
                "recipient_department": recipient_department,
                "details": details,
                "required_action": required_action,
                "date": datetime.now().strftime('%Y-%m-%d'),
                "status": "Incoming",
                "priority": priority,
                "current_holder": recipient or "System",
                "deadline": deadline,
                "workflow_stage": initial_stage,
                "is_confidential": is_confidential,
                "document_type": document_type,
                "file_size": str(file_size),
                "tags": tags,
                "related_documents": [],
                "version": "1.0",
                "access_permissions": [
                    {
                        "user_id": current_user_id,
                        "permission": "full"
                    }
                ],
                "notification_status": {
                    "recipients_notified": [],
                    "reminders_sent": []
                },
                "actions": [],
                "comments": [],
                "approval_flow": approval_flow,
                "audit_trail": {
                    "created_by": current_user_id,
                    "created_on": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "last_modified_by": current_user_id,
                    "last_modified_on": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            # Add action record for document upload
            document_data = add_action_record(
                document_data,
                current_user_id,
                "Document uploaded",
                "Initial upload to the system",
                None,
                "Incoming"
            )
            
            # Add to tracking data
            tracking_data = get_tracking_data()
            tracking_data["documents"].append(document_data)
            save_tracking_data(tracking_data)
            
            # Send notification to recipient if email provided
            if recipient_email:
                subject = f"[{priority}] New Document Received: {doc_code}"
                message = f"""
                <html>
                <body>
                    <h2>New Document Notification</h2>
                    <p>You have received a new document that requires your attention.</p>
                    <p><strong>Document Code:</strong> {doc_code}</p>
                    <p><strong>Sender:</strong> {sender}</p>
                    <p><strong>Priority:</strong> {priority}</p>
                    <p><strong>Required Action:</strong> {required_action}</p>
                    <p><strong>Details:</strong> {details}</p>
                    <p><strong>Deadline:</strong> {deadline}</p>
                    <p>Please log in to the Document Management System to view and process this document.</p>
                </body>
                </html>
                """
                
                notification_sent = send_email_notification(recipient_email, subject, message)
                
                if notification_sent:
                    # Add notification record
                    document_data = add_notification_record(document_data, recipient_id if recipient_id else "0")
                    
                    # Add action record for notification
                    document_data = add_action_record(
                        document_data,
                        "0",  # System user
                        "Notification sent",
                        "Email notification sent to recipient",
                        "Incoming",
                        "Incoming"
                    )
                    
                    # Update the document in tracking data
                    for i, doc in enumerate(tracking_data["documents"]):
                        if doc["code"] == doc_code:
                            tracking_data["documents"][i] = document_data
                            break
                    
                    save_tracking_data(tracking_data)
            
            flash('Document uploaded successfully and notifications sent', 'success')
            return redirect(url_for('dashboard'))
        
        # Get users for recipient selection
        tracking_data = get_tracking_data()
        users = tracking_data.get("users", [])
        workflow_templates = tracking_data.get("system_settings", {}).get("workflow_templates", [])
        
        return render_template('compose.html', 
                              active_page='compose',
                              current_user=current_user,
                              users=users,
                              workflow_templates=workflow_templates)
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/incoming')
def incoming():
    try:
        tracking_data = get_tracking_data()
        incoming_docs = [doc for doc in tracking_data["documents"] if doc["status"] == "Incoming"]
        return render_template('incoming.html', documents=incoming_docs, active_page='incoming')
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/outgoing')
def outgoing():
    try:
        tracking_data = get_tracking_data()
        outgoing_docs = [doc for doc in tracking_data["documents"] if doc["status"] == "Outgoing"]
        return render_template('outgoing.html', documents=outgoing_docs, active_page='outgoing')
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/maintenance')
def maintenance():
    try:
        return render_template('maintenance.html', active_page='maintenance')
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/reports')
def reports():
    try:
        return render_template('reports.html', active_page='reports')
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/user-management')
def user_management():
    try:
        return render_template('user_management.html', active_page='user-management')
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/my-account')
def my_account():
    try:
        return render_template('my_account.html', active_page='my-account')
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/document/<doc_code>')
def document_details(doc_code):
    try:
        tracking_data = get_tracking_data()
        document = next((doc for doc in tracking_data["documents"] if doc["code"] == doc_code), None)
        
        if not document:
            flash('Document not found', 'danger')
            return redirect(url_for('dashboard'))
            
        return render_template('document_details.html', document=document)
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/document/<doc_code>/update', methods=['POST'])
def update_document(doc_code):
    try:
        tracking_data = get_tracking_data()
        document = next((doc for doc in tracking_data["documents"] if doc["code"] == doc_code), None)
        
        if not document:
            flash('Document not found', 'danger')
            return redirect(url_for('dashboard'))
        
        # Update document status and holder
        new_status = request.form.get('status')
        new_holder = request.form.get('holder')
        action_description = request.form.get('action_description')
        
        document["status"] = new_status if new_status else document["status"]
        document["current_holder"] = new_holder if new_holder else document["current_holder"]
        
        # Add action to history
        document["actions"].append({
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "user": "Admin", # In a real system, this would be the logged-in user
            "action": action_description if action_description else f"Status updated to {new_status}"
        })
        
        # Save updated tracking data
        save_tracking_data(tracking_data)
        
        flash('Document updated successfully', 'success')
        return redirect(url_for('document_details', doc_code=doc_code))
    except Exception as e:
        return f"Error: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True) 