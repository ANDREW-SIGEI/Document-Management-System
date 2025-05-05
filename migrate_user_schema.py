#!/usr/bin/env python3
"""
Migration script to add is_active column to user table if it doesn't exist
This resolves the SQLite3 error when the app tries to query user.is_active
"""

import sqlite3
import os
import shutil
from datetime import datetime

# Database paths
DB_PATH = 'app.db'
BACKUP_PATH = f'app_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'

def create_backup():
    """Create a backup of the database before migration"""
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"Database backup created at {BACKUP_PATH}")
    else:
        print(f"Database file {DB_PATH} not found. No backup needed.")

def column_exists(conn, table, column):
    """Check if a column exists in a table"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    return any(col[1] == column for col in columns)

def add_column_if_not_exists():
    """Add is_active column to user table if it doesn't exist"""
    if not os.path.exists(DB_PATH):
        print(f"Database file {DB_PATH} not found!")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Check if user table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        if not cursor.fetchone():
            print("User table does not exist.")
            conn.close()
            return False
        
        # Check if is_active column exists
        if column_exists(conn, 'user', 'is_active'):
            print("is_active column already exists in User table.")
            conn.close()
            return True
        
        # Add is_active column with default value of True
        cursor.execute("ALTER TABLE user ADD COLUMN is_active BOOLEAN DEFAULT 1")
        conn.commit()
        print("is_active column added to User table successfully.")
        
        # Update any existing users to set is_active = True
        cursor.execute("UPDATE user SET is_active = 1")
        conn.commit()
        print("Existing users updated with is_active = True")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        conn.close()
        return False

if __name__ == "__main__":
    print("Starting database migration to add is_active column...")
    create_backup()
    success = add_column_if_not_exists()
    if success:
        print("Migration completed successfully.")
    else:
        print("Migration failed.") 