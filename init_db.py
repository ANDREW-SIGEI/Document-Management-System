import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

# Create instance directory if it doesn't exist
if not os.path.exists('instance'):
    os.makedirs('instance')

# Connect to SQLite database
conn = sqlite3.connect('instance/kemri.db')
cursor = conn.cursor()

# Create user table
cursor.execute('''
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    department TEXT,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    role TEXT DEFAULT 'User',
    is_active BOOLEAN DEFAULT 1
)
''')

# Create document table
cursor.execute('''
CREATE TABLE IF NOT EXISTS document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    sender TEXT NOT NULL,
    recipient TEXT NOT NULL,
    status TEXT DEFAULT 'Pending',
    priority TEXT DEFAULT 'Normal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (created_by) REFERENCES user (id)
)
''')

# Create document_history table
cursor.execute('''
CREATE TABLE IF NOT EXISTS document_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    FOREIGN KEY (document_id) REFERENCES document (id),
    FOREIGN KEY (user_id) REFERENCES user (id)
)
''')

# Create system_log table
cursor.execute('''
CREATE TABLE IF NOT EXISTS system_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES user (id)
)
''')

# Create admin user
admin_password = generate_password_hash('admin123')
cursor.execute('''
    INSERT INTO user (username, password, role, is_active)
    VALUES (?, ?, ?, ?)
''', ('admin', admin_password, 'Administrator', 1))

# Insert sample documents
sample_documents = [
    ('DOC001', 'Research Proposal', 'Initial research proposal for new study', 'John Doe', 'Jane Smith', 'Pending', 'Normal'),
    ('DOC002', 'Lab Results', 'Blood test results from last week', 'Jane Smith', 'John Doe', 'Completed', 'Priority'),
    ('DOC003', 'Equipment Request', 'New microscope requisition', 'Mike Johnson', 'Sarah Wilson', 'In Progress', 'Urgent')
]

for doc in sample_documents:
    cursor.execute('''
        INSERT INTO document (tracking_code, title, description, sender, recipient, status, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', doc)

# Commit changes and close connection
conn.commit()
conn.close()

print("Database initialized successfully!") 