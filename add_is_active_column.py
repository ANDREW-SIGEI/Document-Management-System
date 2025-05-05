import os
import shutil
import sqlite3
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

def create_backup():
    """Create a backup of the database before making changes"""
    db_path = 'app.db'
    backup_path = 'instance/kemri_backup.db'
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found.")
        return False
    
    try:
        # Create backup
        os.makedirs('instance', exist_ok=True)
        shutil.copy2(db_path, backup_path)
        print(f"Database backup created at {backup_path}")
        return True
    except Exception as e:
        print(f"Error creating backup: {str(e)}")
        return False

def add_is_active_column():
    """Add is_active column to User table if it doesn't exist"""
    try:
        # Connect to database
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'is_active' not in column_names:
            print("Adding is_active column to User table...")
            cursor.execute("ALTER TABLE user ADD COLUMN is_active BOOLEAN DEFAULT 1")
            
            # Update existing records - set to active if they have a role, inactive if role is NULL
            cursor.execute("UPDATE user SET is_active = CASE WHEN role IS NULL THEN 0 ELSE 1 END")
            
            conn.commit()
            print("Column added successfully and existing users updated.")
        else:
            print("is_active column already exists in User table.")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding is_active column: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting database migration to add is_active column...")
    
    # Create backup first
    if create_backup():
        # Add column
        if add_is_active_column():
            print("Migration completed successfully.")
        else:
            print("Migration failed.")
    else:
        print("Backup failed, aborting migration.") 