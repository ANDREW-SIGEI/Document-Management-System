import sqlite3
import os
from datetime import datetime

def get_db_connection():
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_activity_log_table():
    """Create the activity_log table in the database"""
    conn = get_db_connection()
    
    # Create activity_log table if it doesn't exist
    conn.execute('''
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        status TEXT DEFAULT 'success',
        timestamp TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES user (id)
    )
    ''')
    
    # Create index on user_id for faster queries
    conn.execute('CREATE INDEX IF NOT EXISTS idx_activity_log_user_id ON activity_log (user_id)')
    
    # Create index on timestamp for date range queries
    conn.execute('CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON activity_log (timestamp)')
    
    conn.commit()
    print("Activity log table created successfully")
    
    # Add first log entry to verify table creation
    conn.execute(
        'INSERT INTO activity_log (user_id, action, details, status, timestamp) VALUES (?, ?, ?, ?, ?)',
        (1, 'system_init', '{"message": "Activity logging system initialized"}', 'success', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    
    # Verify table was created
    result = conn.execute('SELECT COUNT(*) FROM activity_log').fetchone()[0]
    print(f"Activity log table contains {result} record(s)")
    
    conn.close()

if __name__ == "__main__":
    create_activity_log_table()
    print("Database updated with activity logging capability") 