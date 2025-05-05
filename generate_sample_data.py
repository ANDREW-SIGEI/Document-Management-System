import os
import random
import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# Import models after db is defined
from debug_app import User, Document, ActivityLog, DocumentStatus, DocumentAction

def create_sample_users():
    """Create sample users with different roles if they don't exist"""
    print("Creating sample users...")
    
    # Common departments
    departments = [
        "Laboratory", "Administration", "Reception", "Finance", 
        "Research", "IT", "Human Resources", "Clinical Services"
    ]
    
    # Sample users with different roles
    sample_users = [
        {"username": "lab_manager", "email": "lab.manager@kemri.org", "phone": "0712345678", 
         "department": "Laboratory", "password": "password", "role": "Manager"},
        
        {"username": "lab_tech1", "email": "lab.tech1@kemri.org", "phone": "0723456789", 
         "department": "Laboratory", "password": "password", "role": "User"},
        
        {"username": "lab_tech2", "email": "lab.tech2@kemri.org", "phone": "0734567890", 
         "department": "Laboratory", "password": "password", "role": "User"},
        
        {"username": "receptionist", "email": "reception@kemri.org", "phone": "0745678901", 
         "department": "Reception", "password": "password", "role": "User"},
        
        {"username": "finance", "email": "finance@kemri.org", "phone": "0756789012", 
         "department": "Finance", "password": "password", "role": "Manager"},
        
        {"username": "hr_manager", "email": "hr@kemri.org", "phone": "0767890123", 
         "department": "Human Resources", "password": "password", "role": "Manager"},
        
        {"username": "researcher", "email": "researcher@kemri.org", "phone": "0778901234", 
         "department": "Research", "password": "password", "role": "User"},
        
        {"username": "it_support", "email": "it.support@kemri.org", "phone": "0789012345", 
         "department": "IT", "password": "password", "role": "Administrator"}
    ]
    
    # Check for existing users and create if they don't exist
    for user_data in sample_users:
        existing_user = User.query.filter_by(username=user_data["username"]).first()
        if not existing_user:
            new_user = User(
                username=user_data["username"],
                email=user_data["email"],
                phone=user_data["phone"],
                department=user_data["department"],
                password=user_data["password"],
                role=user_data["role"],
                is_active=True
            )
            db.session.add(new_user)
    
    # Commit changes
    db.session.commit()
    print("Sample users created successfully")


def create_sample_documents():
    """Create sample documents with different statuses and tracking codes"""
    print("Creating sample documents...")
    
    # Get all users to assign documents to
    users = User.query.all()
    if not users:
        print("No users found. Create users first.")
        return
    
    # Document types
    document_types = [
        "Lab Report", "Requisition Form", "Patient Record", 
        "Research Proposal", "Test Results", "Invoice", 
        "Equipment Request", "Maintenance Log", "Clinical Trial Data"
    ]
    
    # Document priorities
    priorities = ["Low", "Medium", "High", "Urgent"]
    
    # Document statuses
    statuses = ["Pending", "In Progress", "Completed", "Rejected", "On Hold"]
    
    # Create 20 sample documents with varying details
    for i in range(1, 21):
        # Generate a tracking code
        tracking_code = f"KEMRI-{datetime.datetime.now().strftime('%Y%m')}-{i:04d}"
        
        # Check if document already exists with this tracking code
        existing_doc = Document.query.filter_by(tracking_code=tracking_code).first()
        if existing_doc:
            continue
        
        # Select random values
        doc_type = random.choice(document_types)
        sender = random.choice(users)
        recipient = random.choice(users)
        # Make sure sender and recipient are different
        while recipient.id == sender.id:
            recipient = random.choice(users)
            
        priority = random.choice(priorities)
        status = random.choice(statuses)
        
        # Create a date within the last month
        days_ago = random.randint(1, 30)
        date_created = datetime.datetime.now() - datetime.timedelta(days=days_ago)
        
        # Create new document
        new_doc = Document(
            tracking_code=tracking_code,
            document_type=doc_type,
            subject=f"Sample {doc_type} #{i}",
            sender_id=sender.id,
            recipient_id=recipient.id,
            date_created=date_created,
            status=status,
            priority=priority,
            description=f"This is a sample {doc_type.lower()} created for demonstration purposes. " +
                      f"It has {priority.lower()} priority and is currently {status.lower()}."
        )
        db.session.add(new_doc)
        
        # Create status history
        status_history = DocumentStatus(
            document_id=new_doc.id,
            status=status,
            timestamp=date_created,
            user_id=sender.id
        )
        db.session.add(status_history)
        
        # Create some actions for each document
        action_types = ["Review", "Comment", "Forward", "Approve", "Reject"]
        num_actions = random.randint(1, 5)
        
        for j in range(num_actions):
            action_days_ago = random.randint(0, days_ago - 1)
            if action_days_ago < 0:
                action_days_ago = 0
                
            action_date = date_created + datetime.timedelta(days=j)
            if action_date > datetime.datetime.now():
                action_date = datetime.datetime.now()
                
            action_user = random.choice(users)
            action_type = random.choice(action_types)
            
            new_action = DocumentAction(
                document_id=new_doc.id,
                action_type=action_type,
                details=f"{action_type} action taken by {action_user.username}",
                timestamp=action_date,
                user_id=action_user.id
            )
            db.session.add(new_action)
    
    # Commit changes
    db.session.commit()
    print("Sample documents created successfully")


def create_activity_logs():
    """Create sample activity logs"""
    print("Creating sample activity logs...")
    
    # Get all users
    users = User.query.all()
    if not users:
        print("No users found. Create users first.")
        return
    
    # Activity types
    activity_types = [
        "Login", "Logout", "Create Document", "View Document", 
        "Edit Document", "Delete Document", "Change Status",
        "Search", "Export Report", "User Management"
    ]
    
    # Create 50 sample activity logs
    for i in range(50):
        # Select random user
        user = random.choice(users)
        
        # Select random activity
        activity = random.choice(activity_types)
        
        # Create a date within the last week
        days_ago = random.randint(0, 7)
        activity_date = datetime.datetime.now() - datetime.timedelta(days=days_ago)
        
        # Create log entry
        new_log = ActivityLog(
            user_id=user.id,
            activity=activity,
            timestamp=activity_date,
            ip_address="127.0.0.1",
            details=f"{activity} performed by {user.username}"
        )
        db.session.add(new_log)
    
    # Commit changes
    db.session.commit()
    print("Sample activity logs created successfully")


if __name__ == "__main__":
    print("Generating sample data for KEMRI Laboratory System...")
    
    try:
        # Create sample data in order of dependencies
        create_sample_users()
        create_sample_documents()
        create_activity_logs()
        
        print("Sample data generation completed successfully!")
    except Exception as e:
        print(f"Error generating sample data: {str(e)}") 