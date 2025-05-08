import sqlite3
import os
from datetime import datetime

print("Creating activity_log table in the database...")

# Database path - try both possible locations
db_paths = ['app.db', 'instance/kemri.db']
db_path = None

for path in db_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    print("Error: No database found. Please ensure app.db exists.")
    exit(1)

print(f"Using database at {db_path}")

# Connect to SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create activity_log table
cursor.execute('''
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id)
)
''')

# Check if status column is missing and add it if needed
cursor.execute("PRAGMA table_info(activity_log)")
columns = [col[1] for col in cursor.fetchall()]

if 'status' not in columns:
    print("Adding 'status' column to activity_log table")
    cursor.execute("ALTER TABLE activity_log ADD COLUMN status TEXT")

# Add document_type column to document table if it doesn't exist
cursor.execute("PRAGMA table_info(document)")
columns = [col[1] for col in cursor.fetchall()]

if 'document_type' not in columns:
    print("Adding 'document_type' column to document table")
    cursor.execute("ALTER TABLE document ADD COLUMN document_type TEXT DEFAULT 'Outgoing'")

# Commit changes and close connection
conn.commit()
conn.close()

print("Database setup completed successfully!") 