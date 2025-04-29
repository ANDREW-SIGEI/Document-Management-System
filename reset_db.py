import os
import sqlite3

# Path to the SQLite database file
db_path = 'app.db'

# Check if the database file exists
if os.path.exists(db_path):
    # Remove the file
    print(f"Removing existing database at {db_path}")
    os.remove(db_path)
    print("Database file removed successfully.")
else:
    print("Database file not found. Will create a new one.")

# Create a new database and the user table with is_active column
print("Creating new database with updated schema...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create user table with is_active column
cursor.execute('''
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone VARCHAR(20),
    department VARCHAR(100),
    password VARCHAR(255) NOT NULL,
    last_login DATETIME,
    created_at DATETIME,
    role VARCHAR(80),
    is_active BOOLEAN DEFAULT 1
)
''')

# Create other essential tables here as needed

conn.commit()
conn.close()

print("Database has been reset with the new schema including is_active column.")
print("Now run 'python app.py' to start the application.") 